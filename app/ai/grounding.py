# SPDX-License-Identifier: AGPL-3.0-or-later
"""Grounded AI orchestration: gather facts → prompt the model → stream answer.

If the model is unavailable, returns a deterministic template answer built only
from the gathered facts, so "Ask" always works (just without narration). A small
in-process rate limiter protects the NPU from request storms.
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.intent import classify_intent
from app.ai.prompt_builder import build_messages
from app.ai.prompts import REFUSAL_NO_FACTS, strip_reasoning
from app.ai.safety import validate_grounded_answer
from app.ai.tools import AnswerMode, gather_facts
from app.core.config import get_settings
from app.core.disclaimer import DISCLAIMER
from app.providers.ai import get_ai_provider
from app.schemas.ai import AIRequest, GroundingFact

# D-070's ruled, user-visible fallback signal — normative in `SECURITY-BASELINE.md` §5 and
# `DECISIONS.md` D-070, and until now it existed NOWHERE in the codebase (AI-surfaces §0-G:
# grep across app/, frontend/src/ and tests/ returned zero hits). The validator correctly
# discarded unsafe model text and emitted the deterministic template — silently. The reason
# travelled only as `done` event metadata, which no frontend read because no frontend existed.
#
# It is SERVED, not composed client-side: a legal-adjacent string assembled in the browser
# would be a second source of truth for the sentence, which is the §0-C mistake repeated in
# the milestone that fixes it.
#
# Kept string-equal to the spec by `tests/unit/test_d070_fallback_signal.py` (the AC-L3
# spec<->code parity pattern). Edit the spec and the guard carries the change here; edit this
# alone and the guard goes red.
FALLBACK_SIGNAL = "AI answer didn't pass grounding checks — showing facts directly."

_request_times: list[float] = []


def _rate_limited() -> bool:
    now = time.monotonic()
    cutoff = now - 60
    _request_times[:] = [t for t in _request_times if t > cutoff]
    if len(_request_times) >= get_settings().ai_max_requests_per_minute:
        return True
    _request_times.append(now)
    return False


def _answer_mode(health) -> AnswerMode:
    """Declare which tier answers THIS request (R-54 §9-A/§9-F, Phase 1 delta 2).

    Tier 1 (``DETERMINISTIC``) whenever no model will narrate:

    * the model is unavailable — disabled, no-egress, or simply down. All three collapse to
      ``health.available is False`` (`DisabledAIProvider.health()` returns it directly; a live
      provider's health probe fails closed under the egress gate), so ONE check covers them.
    * the model is available but the in-process limiter is exhausted. §9-F: a rate-limited
      tier-2 request **falls back TO tier 1** — the limiter is a reason to REACH the deterministic
      tier, never a reason to withhold it — so it degrades to a real answer, not a bare fact list.

    The limiter is consulted (and its request recorded) ONLY when the model is available. So a
    tier-1 POSTURE never touches it and can never be rate-limited — which is what makes "tier 1
    makes zero network calls, by construction" also mean "tier 1 is never throttled" (§0-I: the
    two conditions that used to share one `if` at the old fallback branch are now resolved into
    one declared mode, so their difference stops being invisible).
    """
    if not health.available:
        return AnswerMode.DETERMINISTIC
    if _rate_limited():
        return AnswerMode.DETERMINISTIC
    return AnswerMode.GROUNDING


def _sentence_chunks(text: str) -> list[str]:
    """Split a validated answer into sentence-sized deltas for streaming."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p + " " for p in parts if p.strip()] or [text]


def _with_disclaimer(body: str) -> str:
    """Return `body` ending in EXACTLY ONE trailing DISCLAIMER (§12-2, owner ruling).

    Commitment 2 binds the ARTIFACT, not the view: every export, stream and copy of an answer
    carries the disclaimer, so the guarantee is applied HERE — at the single point every answer
    text leaves this module — rather than trusted to each path.

    It is normalised rather than merely appended-if-missing. The model is *asked* to end with the
    line (`prompts.py`: "End with exactly: …"), and a model that complies mid-paragraph, or twice,
    would leave the constant somewhere other than the end while a naive `in` check reported the
    guarantee satisfied. Stripping every occurrence and appending one moves a fixed legal sentence
    to its ruled position; it is the one string in an answer whose placement is not the model's to
    choose.
    """
    stripped = body.replace(DISCLAIMER, "").rstrip()
    return f"{stripped}\n\n{DISCLAIMER}" if stripped else DISCLAIMER


def _template_answer(question: str, facts: list[GroundingFact]) -> str:
    """The deterministic fallback body.

    ⊕ 2026-07-20 (§12-1, architect ruling — Finding-1's principle carried one step further).
    This used to re-list every fact under "Here is what the data shows:". The panel ALREADY
    renders the served fact pack as a list above the answer, so that block put **every fact on
    the screen twice** — the projection Finding 1 introduced, immediately echoed underneath.

    THE PROJECTED FACT LIST IS THE DIRECT ANSWER in this state. So the body carries no facts:
    the panel shows signal → fact list ONCE → disclaimer. Nothing is redacted — the same
    projection, shown once — and nothing is lost to a raw-stream consumer either, because the
    facts travel on their own `facts` event, which is where a consumer should read them from
    rather than re-parsing them out of prose.

    With NO facts there is no list to be the answer, so the refusal is the body. That asymmetry
    is the whole rule: the body says what the screen does not already say.
    """
    if not facts:
        return _with_disclaimer(REFUSAL_NO_FACTS)
    return _with_disclaimer("")


def _provenance_event(narrator=None) -> dict:
    """The §14-4 legend, as its own SSE event, emitted BEFORE the deltas of its branch.

    `narrator` is the provider whose text ACTUALLY reached the reader, or **None** when nothing a
    model wrote did. That is the entire input — and the fact that CONFIGURATION is not among the
    inputs is the design, arrived at by getting it wrong first (§15-4).

    ⚠ THE CONFIGURED KIND WAS ORIGINALLY READ HERE, AND IT WAS BOTH A LIE AND DEAD WEIGHT. It was
    a lie because a narrated stream came out labelled `narrated=True` beside *"Built-in
    intelligence only — no model was used."*; the guard caught it. It was dead weight because
    every non-narrated branch collapses to built-in ANYWAY, so the configured kind was never once
    used — and resolving it cost a `settings` read on the hot path of every answer. Removing it
    made the legend truer and the stream lighter at the same time, which is usually the sign that
    the value should not have been there.

    WHY ITS OWN EVENT AND NOT `done` METADATA — which is where the fallback signal travels, so the
    difference is deliberate. The legend decides how the answer text is RENDERED: model-generated
    prose carries a distinct treatment, engine text does not. Delivering it on `done` would leave
    the panel styling the body only after the last token, so a narrated answer would stream in
    plain and then restyle itself — the reader would watch the product change its mind about what
    it was showing them. Every branch below knows its path before it emits its first delta, so the
    legend can lead, and does.

    It is NOT injected into the answer body. §12-1's rule holds: the body says what the screen does
    not already say.
    """
    from app.ai.vocabulary import KIND_BUILT_IN, kind_of_provider, provenance_for

    narrated = narrator is not None
    kind = kind_of_provider(narrator) if narrated else KIND_BUILT_IN
    effective, line = provenance_for(kind, narrated=narrated)
    return {"type": "provenance", "kind": effective, "narrated": narrated, "provenance": line}


async def answer_stream(
    session: AsyncSession, question: str
) -> AsyncIterator[dict]:
    """Yields dicts: {'type': 'facts'|'provenance'|'delta'|'done', ...}. Designed for SSE."""
    # Resolve the tier BEFORE gathering facts — the mode decides the miss behaviour of
    # `gather_facts` itself (R-54 §9-A: tier 1's last-resort is suppressed, so an unroutable
    # question comes back empty and takes the honest-miss shape below).
    provider = get_ai_provider()
    health = await provider.health()
    mode = _answer_mode(health)

    facts = await gather_facts(session, question, mode=mode)
    # Surface the grounding facts to the client first — this is what the UI shows
    # alongside the answer (source + timestamp + stale badges).
    yield {"type": "facts", "facts": [f.model_dump(mode="json") for f in facts]}

    if mode is AnswerMode.DETERMINISTIC:
        # Tier 1 — no model narrates. The template renders the fact pack, or the ratified refusal
        # when the deterministic route came back empty (the honest miss). Never rate-limited: the
        # mode already folded the limiter in (§9-F), so this branch cannot be a throttled tier-2
        # in disguise.
        yield _provenance_event()
        text = _template_answer(question, facts)
        yield {"type": "delta", "delta": text}
        yield {"type": "done", "grounded": True, "provider": "fallback",
               "disclaimer": DISCLAIMER}
        return

    # Tier 2 — a model is available and the limiter has room; narration follows.
    if not facts:
        # The refusal is ENGINE text — the model was never asked. Crediting it to the configured
        # model would credit it with a sentence it did not write.
        yield _provenance_event()
        yield {"type": "delta", "delta": REFUSAL_NO_FACTS}
        yield {"type": "done", "grounded": True, "provider": provider.name,
               "disclaimer": DISCLAIMER}
        return

    intent = classify_intent(question)
    messages = build_messages(question, intent, facts)
    req = AIRequest(messages=messages)

    # §3 SAFE STREAMING: buffer the model output server-side and validate it BEFORE any
    # of it reaches the client. Unsafe model text (a buy/sell recommendation, a
    # secret-like string, a fabricated number/ticker/headline) is therefore never shown —
    # on failure we emit only the deterministic fact-only answer.
    full = ""
    error: str | None = None
    try:
        async for chunk in provider.chat(req):
            if chunk.delta:
                full += chunk.delta        # buffer only — do NOT yield raw model text
            if chunk.done:
                break
    except Exception as exc:  # noqa: BLE001 — never crash the stream; surface the reason
        error = str(exc)[:300]

    answer = strip_reasoning(full)
    if not answer:
        # Model returned nothing usable (or only reasoning) → deterministic fallback.
        yield _provenance_event()
        if error:
            # PLAIN TEXT, no markdown emphasis. Finding 3 (§11-C) removed a served string whose
            # underscores rendered literally because the answer body is text; this was the one
            # remaining site of the same defect, unseen only because no screenshot drove the
            # model-error path. The AI reads strings, never styling — and so, here, does the reader.
            yield {"type": "delta",
                   "delta": f"The AI model didn't return an answer ({error}). "
                            "Showing the underlying data instead.\n\n"}
        yield {"type": "delta", "delta": _template_answer(question, facts)}
        yield {"type": "done", "grounded": True, "provider": "fallback",
               "error": error, "disclaimer": DISCLAIMER}
        return

    ok, reason = validate_grounded_answer(answer, facts, question)
    if not ok:
        # Unsafe/ungrounded — the model text is discarded, never shown. D-070: the user is TOLD
        # this happened. Silently swapping a model answer for a template is the product being
        # quietly less than it appeared, which is the opposite of the honesty the fallback exists
        # to protect. The signal leads, so it frames what follows rather than trailing it.
        # The signal travels on the `done` event ONLY — it is not injected into the answer body.
        #
        # It used to be emitted as a leading delta as well. The 0a re-drive showed what that
        # produced once the panel rendered the served field properly: the sentence appeared TWICE,
        # and the second copy carried its markdown underscores literally, because the answer body
        # is rendered as text (the AI reads strings, never styling — and so, here, does the
        # reader). One served string, rendered once, in the place the client puts it.
        #
        # THE LEGEND SAYS BUILT-IN HERE, and this is the branch it matters most on: the model DID
        # write something, and the reader is not seeing a word of it. An answer the validator threw
        # away is not narration — crediting the model would describe a contribution the product
        # deliberately discarded.
        yield _provenance_event()
        yield {"type": "delta", "delta": _template_answer(question, facts)}
        yield {"type": "done", "grounded": True, "provider": "fallback", "validation": reason,
               "fallback_signal": FALLBACK_SIGNAL, "disclaimer": DISCLAIMER}
        return

    # Validated → now safe to emit, chunked by sentence for a mild streaming feel.
    # §12-2: the ARTIFACT ends with the disclaimer even when the model ignored the instruction to
    # end with it. Finding 4's option (b) named exactly this hole — "loses the disclaimer on
    # model-narrated answers where the model may omit it" — and a guarantee that depends on a model
    # complying is not a guarantee.
    # ⚠ THE KIND COMES FROM THE PROVIDER THAT WROTE THIS, NOT FROM `kind` ABOVE. `kind` is the
    # CONFIGURED posture; this is the only branch where a model actually produced the words on
    # screen, and the object that produced them is the only thing that knows what it is. The first
    # implementation used the configured kind here and the guard caught it emitting `narrated=True`
    # beside `Built-in intelligence only — no model was used.` (§15-4).
    yield _provenance_event(provider)
    for piece in _sentence_chunks(_with_disclaimer(answer)):
        yield {"type": "delta", "delta": piece}
    yield {"type": "done", "grounded": True, "provider": provider.name,
           "intent": intent.value,
           "model": health.models[0] if health.models else None,
           "disclaimer": DISCLAIMER}
