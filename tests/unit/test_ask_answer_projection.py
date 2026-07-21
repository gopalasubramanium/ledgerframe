# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fallback answer is shown ONCE, and every answer ENDS with the disclaimer.

Two owner rulings from the 0a screenshot walk (2026-07-20), guarded together because they are the
two halves of one shape — **what the artifact contains** versus **what the reader sees**.

**§12-1 — the echo (architect ruling, Finding-1's principle).** In the fallback state the panel
already renders the served fact pack as a list. The deterministic template then re-listed those
same facts under *"Here is what the data shows:"*, so **every fact appeared twice on one screen**.
Finding 1 established that the fact pack is PROJECTED for display; this is the same principle one
step further — **the projected fact list IS the direct answer**, so the body must not echo it.
Fallback body = **signal → fact list once → disclaimer**. Nothing is redacted: the same projection,
shown once.

**§12-2 — the disclaimer (owner ruling: the synthesis of Finding 4's options (a) and (b)).**
Finding 4 recorded that the disclaimer rendered twice — once ending the answer body, once as the
served element — and that (a) and (b) traded **the same guarantee against two different readers**:
(a) kept the panel clean and lost the trailing line for any raw-stream consumer; (b) kept the
artifact whole and risked losing it on model-narrated answers. The owner ruled neither, but both:

    the answer TEXT always ends with the served DISCLAIMER constant — **Commitment 2 binds the
    ARTIFACT**, so every export, stream and copy carries it — and the PANEL projects the body
    without the trailing line, rendering the footer element once.

**De-duplication at display is a PROJECTION, not a redaction.** That is the distinction the whole
0a walk turns on, and it is why the two assertions below must BOTH hold: drop the first and the
reader sees the sentence twice; drop the second and the artifact stops carrying its own disclaimer
the moment it leaves the panel. Either alone reads as reasonable and breaks the other reader.

The display half of §12-2 lives where display lives — `AskPanel.test.tsx` (exactly one visible
instance) and the 0a driver (on-screen geometry). This file owns the SERVED artifact.
"""

from __future__ import annotations

from app.ai.grounding import answer_stream
from app.core.disclaimer import DISCLAIMER
from app.schemas.ai import AIChunk, GroundingFact, HealthStatus

# Values chosen to be unmistakable if echoed: a number that appears nowhere else, and a help fact
# whose body is the multi-paragraph shape that made the echo a wall of prose (Phase 0.9 widening).
FACTS = [
    GroundingFact(label="Net worth", value="796,543.93 SGD"),
    GroundingFact(
        label="Help · Extended internal rate of return (XIRR)",
        value=(
            "The annualised return of your portfolio, accounting for the timing and size of "
            "every cash flow.\n\n"
            "It answers 'what rate would my money have had to grow at' rather than 'how much "
            "did it grow'."
        ),
        fact_type="help",
    ),
]


class _Provider:
    name = "openai_compatible"

    def __init__(self, mode: str):
        self.mode = mode

    async def health(self) -> HealthStatus:
        return HealthStatus(available=self.mode != "down", provider=self.name, models=["m"])

    async def chat(self, request):
        if self.mode == "error":
            raise RuntimeError("500 from model endpoint: boom")
        if self.mode == "unsafe":
            yield AIChunk(delta="You should buy AAPL now.", done=False)
        elif self.mode == "empty":
            # Reasoning only — `strip_reasoning` leaves nothing usable.
            yield AIChunk(delta="<think>hmm</think>", done=False)
        elif self.mode == "ok_no_disclaimer":
            # A COMPLIANT, VALID answer that simply omits the trailing line. The system prompt
            # asks for it ("End with exactly: …"); asking is not enforcing.
            yield AIChunk(delta="Your net worth is 796,543.93 SGD.", done=False)
        else:
            yield AIChunk(
                delta="Your net worth is 796,543.93 SGD. " + DISCLAIMER, done=False
            )
        yield AIChunk(delta="", done=True)


async def _run(monkeypatch, mode: str, facts: list[GroundingFact] | None = None):
    from app.ai import grounding

    async def fake_facts(session, question, *, mode=None):
        return list(FACTS if facts is None else facts)

    monkeypatch.setattr(grounding, "gather_facts", fake_facts)
    monkeypatch.setattr(grounding, "get_ai_provider", lambda: _Provider(mode))
    grounding._request_times.clear()
    events = [e async for e in answer_stream(None, "how is my portfolio?")]
    text = "".join(e["delta"] for e in events if e["type"] == "delta")
    served = next(e for e in events if e["type"] == "facts")["facts"]
    return text, served


# ─── §12-1: the fact pack is not echoed into the answer body ────────────────────

# Every path that ends in the deterministic template. They are listed rather than collapsed
# because they reach it for DIFFERENT reasons — provider down, validator rejection, empty model
# reply — and a fix that cleaned up one and left the others is the shape of defect this catches.
FALLBACK_MODES = ["down", "unsafe", "empty"]


async def test_the_fallback_body_does_not_echo_the_served_facts(monkeypatch):
    for mode in FALLBACK_MODES:
        text, served = await _run(monkeypatch, mode)
        for fact in served:
            assert fact["label"] not in text, (
                f"[{mode}] the answer body repeats the fact LABEL {fact['label']!r}, which the "
                "panel already renders in the fact list above it. The reader sees the same fact "
                "twice on one screen — §12-1: the projected fact list IS the direct answer."
            )
            # The first paragraph is what the old template pasted into each bullet.
            first_para = " ".join(fact["value"].split("\n\n")[0].split())
            assert first_para not in text, (
                f"[{mode}] the answer body repeats the fact VALUE {first_para!r} already served "
                "on the facts event and rendered in the list above."
            )


async def test_the_echo_HEADER_is_gone(monkeypatch):
    """The header is named explicitly: it is the seam the owner pointed at."""
    for mode in FALLBACK_MODES:
        text, _ = await _run(monkeypatch, mode)
        assert "Here is what the data shows" not in text, (
            f"[{mode}] the duplicate block's header survived. It introduces a second copy of the "
            "fact pack; there is no second copy for it to introduce."
        )


async def test_the_model_error_path_KEEPS_its_own_honest_reason(monkeypatch):
    """Pinned against going blind: emptying the body entirely would satisfy the tests above.

    The echo is what goes; the reasons do not. A model error still says a model error happened,
    because that sentence is not a repeat of anything — nothing else on screen says it.
    """
    text, _ = await _run(monkeypatch, "error")
    assert "didn't return an answer" in text, (
        "the model-error path lost its own honest reason along with the echo"
    )


async def test_a_NO_FACTS_refusal_still_says_something(monkeypatch):
    """Also against going blind: with no facts there is no list, so the body must carry the answer."""
    text, served = await _run(monkeypatch, "down", facts=[])
    assert served == []
    assert "don't have the data needed" in text, (
        "with an empty fact pack the panel renders no list — an empty body would leave the reader "
        "with nothing at all. The refusal is the answer here, not an echo of one."
    )


# ─── §12-2: the ARTIFACT always ends with the disclaimer ────────────────────────

async def test_every_answer_text_ENDS_with_the_served_disclaimer(monkeypatch):
    """Commitment 2 binds the artifact, not the view.

    Checked on every path — including the narrated one, where the model is *asked* to end with the
    disclaimer and therefore might not. A guarantee that depends on a model complying is not a
    guarantee.
    """
    for mode in [*FALLBACK_MODES, "error", "ok", "ok_no_disclaimer"]:
        text, _ = await _run(monkeypatch, mode)
        assert text.strip().endswith(DISCLAIMER), (
            f"[{mode}] the answer text does not END with the served disclaimer constant.\n"
            f"  tail: {text.strip()[-120:]!r}\n"
            "Commitment 2 binds the ARTIFACT: every export, stream and copy carries it. The panel "
            "may PROJECT the body without this line — that is a display decision — but it may "
            "never be absent from the text itself."
        )


async def test_the_disclaimer_appears_ONCE_in_the_answer_text(monkeypatch):
    """The artifact carries it once. Two trailing copies is the Finding-4 defect moved, not fixed."""
    for mode in [*FALLBACK_MODES, "error", "ok", "ok_no_disclaimer"]:
        text, _ = await _run(monkeypatch, mode)
        assert text.count(DISCLAIMER) == 1, (
            f"[{mode}] the disclaimer appears {text.count(DISCLAIMER)}× in the answer text; "
            "exactly one trailing instance is the guarantee."
        )
