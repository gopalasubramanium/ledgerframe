# SPDX-License-Identifier: AGPL-3.0-or-later
"""D-070's visible fallback signal: ruled, normative — and until now, never shipped.

D-070 (`DECISIONS.md`) and `SECURITY-BASELINE.md` §5 both mandate a **visible signal** when an
answer falls back, with a ruled wording:

    "AI answer didn't pass grounding checks — showing facts directly."

**That string existed nowhere** (AI-surfaces §0-G): a grep across `app/`, `frontend/src/` and
`tests/` returned zero hits. What actually happened on validation failure was correct but
**silent** — the model text was discarded, the deterministic template was emitted, and the reason
travelled only as `done` event metadata that no frontend read, because no frontend existed.

A ruled, normative, user-visible behaviour that has never shipped is the sharpest form of the
CLAUDE.md lesson: the rule was written, and enforced by nobody. Silently swapping a model answer
for a template is the product being quietly less than it appeared — the opposite of the honesty
the fallback exists to protect.

Two properties, and both are needed:

1. **Parity** — the served string is **string-equal to the spec**. This is the AC-L3 pattern the
   Commitments already use: edit the spec and the guard carries the change into the product; edit
   the product alone and the guard goes red. It is what stops the sentence drifting into a
   paraphrase that reads fine and is no longer the ruled one.
2. **Delivery** — it actually reaches the user on the validation-failure path, and **only** there.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.ai.grounding import FALLBACK_SIGNAL, answer_stream
from app.schemas.ai import AIChunk, GroundingFact, HealthStatus

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / "docs" / "specs" / "SECURITY-BASELINE.md"
DECISIONS = REPO / "docs" / "audit" / "DECISIONS.md"


def _normalise(text: str) -> str:
    """Collapse whitespace so a line-wrapped spec quote compares to a one-line constant."""
    return re.sub(r"\s+", " ", text).strip()


# ─── 1: parity with the spec ────────────────────────────────────────────────────

def test_the_served_signal_is_string_equal_to_the_security_baseline():
    spec = _normalise(BASELINE.read_text(encoding="utf-8"))
    assert _normalise(FALLBACK_SIGNAL) in spec, (
        f"The served fallback signal is not the ruled one.\n"
        f"  served: {FALLBACK_SIGNAL!r}\n"
        "SECURITY-BASELINE.md §5 fixes this wording. If the wording should change, change it "
        "THERE and let this guard carry it — a paraphrase that reads fine is still not the "
        "sentence D-070 ruled."
    )


def test_the_served_signal_is_string_equal_to_the_decision():
    """Both records state it, so both are checked. Agreement between them is not assumed."""
    decisions = _normalise(DECISIONS.read_text(encoding="utf-8"))
    assert _normalise(FALLBACK_SIGNAL) in decisions, (
        f"The served fallback signal does not appear in DECISIONS.md's D-070 row.\n"
        f"  served: {FALLBACK_SIGNAL!r}\n"
        "D-070 is the ratifying record; SECURITY-BASELINE.md §5 is the normative statement. A "
        "signal matching one and not the other means the two records have drifted apart."
    )


def test_the_signal_is_not_empty():
    """Pinned against going blind: an empty string is 'in' every document."""
    assert len(FALLBACK_SIGNAL) > 30, (
        f"FALLBACK_SIGNAL is {FALLBACK_SIGNAL!r} — a short or empty constant would satisfy both "
        "parity tests above vacuously, since any document contains the empty string."
    )


# ─── 2: it actually reaches the user, and only on the right path ────────────────

FACTS = [GroundingFact(label="Net worth", value="796,543.93 SGD")]


class _Provider:
    name = "openai_compatible"

    def __init__(self, mode: str):
        self.mode = mode

    async def health(self) -> HealthStatus:
        return HealthStatus(available=True, provider=self.name, models=["m"])

    async def chat(self, request):
        if self.mode == "error":
            raise RuntimeError("500 from model endpoint: boom")
        if self.mode == "unsafe":
            yield AIChunk(delta="You should buy AAPL now.", done=False)
        else:
            yield AIChunk(delta="Your net worth is 796,543.93 SGD.", done=False)
        yield AIChunk(delta="", done=True)


async def _run(monkeypatch, mode: str):
    from app.ai import grounding

    async def fake_facts(session, question):
        return list(FACTS)

    monkeypatch.setattr(grounding, "gather_facts", fake_facts)
    monkeypatch.setattr(grounding, "get_ai_provider", lambda: _Provider(mode))
    grounding._request_times.clear()
    events = [e async for e in answer_stream(None, "how is my portfolio?")]
    text = "".join(e["delta"] for e in events if e["type"] == "delta")
    done = next(e for e in events if e["type"] == "done")
    served = next(e for e in events if e["type"] == "facts")["facts"]
    return text, done, served


async def test_a_validation_failure_SHOWS_the_signal_to_the_user(monkeypatch):
    text, done, _ = await _run(monkeypatch, "unsafe")
    assert done.get("fallback_signal") == FALLBACK_SIGNAL, (
        "The answer fell back and the user was not told. This is §0-G's defect: the discard was "
        "correct and SILENT, so the product was quietly less than it appeared."
    )
    # ⊕ 2026-07-20, 0a re-drive: the signal is SERVED ON THE DONE EVENT and rendered by the client
    # as its own element. It is deliberately NOT also injected into the answer body — doing both
    # showed the reader the same sentence twice, the second time with its markdown underscores
    # rendered literally, because the answer body is text. One served string, rendered once.
    assert FALLBACK_SIGNAL not in text, (
        "The fallback signal was injected into the answer body as well as served on the done "
        "event. The reader sees it twice."
    )
    assert done.get("validation"), "the reason must still travel with it"
    assert "You should buy" not in text, "the rejected model text leaked alongside the signal"


async def test_the_signal_arrives_BEFORE_the_client_can_render_the_answer(monkeypatch):
    """Ordering is the behaviour, not a nicety — asserted where it now lives.

    A signal presented after the answer reads as a footnote to a conclusion the reader has already
    drawn. It used to lead by being the first delta; it now leads because the CLIENT renders the
    served field above the fact pack (owner ruling, §10-B), which is asserted in
    `AskPanel.test.tsx` and, as on-screen geometry, by the 0a driver.

    What this test still owns: the signal must accompany the SAME response that fell back — never
    a later one — so the reason cannot drift away from the answer it explains.
    """
    text, done, served = await _run(monkeypatch, "unsafe")
    assert done.get("fallback_signal") and done.get("validation"), (
        "the fallback response carries no signal/reason pair"
    )
    # ⊕ 2026-07-20 (§12-1). This line read `assert "Net worth" in text` — it asserted THE ECHO,
    # and so pinned the duplicate in place: the fact pack had to be repeated inside the answer body
    # for this test to pass. That is the third test this milestone found holding a defect steady
    # (cf. R-52's retired term, and Phase 0.8's delta injection). A test that pins a behaviour
    # nobody re-derived is how the behaviour survives review.
    #
    # What the test actually means — "the facts reached the user with the signal" — is unchanged;
    # it is now asserted where the facts LIVE, on the served `facts` event, which is where the
    # panel reads them and where a raw-stream consumer should too.
    assert "Net worth" not in text, (
        "the answer body echoes a fact the panel already lists above it (§12-1)"
    )
    assert any(f["label"] == "Net worth" for f in served), (
        "the deterministic fallback arrived without the facts it is built from"
    )


async def test_a_MODEL_ERROR_does_not_claim_a_grounding_failure(monkeypatch):
    """The two fallbacks are different events and must not borrow each other's words.

    D-070's signal says the answer *didn't pass grounding checks*. When the model simply errored,
    nothing was checked and nothing failed grounding — saying so would be a fabricated reason,
    which Commitment 3 forbids as squarely as a fabricated number. That path keeps its own line.
    """
    text, done, _ = await _run(monkeypatch, "error")
    assert FALLBACK_SIGNAL not in text, (
        "A model error was reported as a grounding-check failure. Nothing was checked — the "
        "answer never arrived."
    )
    assert "fallback_signal" not in done
    assert "didn't return an answer" in text, "the model-error path lost its own honest reason"


async def test_a_VALID_answer_shows_no_signal(monkeypatch):
    """Pinned against going blind: a signal on every answer would satisfy the delivery test."""
    text, done, _ = await _run(monkeypatch, "ok")
    assert FALLBACK_SIGNAL not in text, "a passing answer was labelled as a fallback"
    assert "fallback_signal" not in done
