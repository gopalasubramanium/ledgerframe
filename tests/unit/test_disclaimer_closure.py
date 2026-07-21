# SPDX-License-Identifier: AGPL-3.0-or-later
"""Commitment 2's guard: the disclaimer is ONE sentence, and every answer path ends with it.

`PRODUCT-SPEC.md` §3 Commitment 2 — *"Every AI answer ends with the fixed
information-only disclaimer."* **"Fixed" is a claim about identity across paths.**
Before `app/core/disclaimer.py` the sentence was 13 independent literals that agreed
by coincidence (AI-surfaces §0-C); nothing asserted they agreed, so the Commitment
rested on nobody having edited one of them yet.

This file is the mechanism the Commitment never had, in two halves that need each other:

1. **Closure** — the literal appears in `app/` exactly once, in its definition module.
2. **Coverage** — every terminal ``done`` event of ``answer_stream`` carries it.

Half 1 alone would pass vacuously if the sentence were deleted product-wide; half 2
alone would not notice a second copy drifting. Together they are pinned against going
blind (CLAUDE.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.ai import grounding
from app.core.disclaimer import DISCLAIMER
from app.schemas.ai import AIChunk, GroundingFact, HealthStatus

APP = Path(__file__).resolve().parents[2] / "app"
DEFINITION = APP / "core" / "disclaimer.py"


# ─── half 1: closure ────────────────────────────────────────────────────────────

def test_the_disclaimer_sentence_is_written_in_exactly_one_place_in_app():
    """A second literal of the sentence is a second source of truth. There is one.

    Fails loudly with the offending paths rather than a bare count, because the fix
    is always the same and the reader should not have to grep for it: import
    ``DISCLAIMER`` from ``app.core.disclaimer``.
    """
    offenders = [
        p.relative_to(APP.parent).as_posix()
        for p in sorted(APP.rglob("*.py"))
        if p != DEFINITION and DISCLAIMER in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        "The fixed disclaimer is written as a literal outside its definition module:\n  "
        + "\n  ".join(offenders)
        + f"\n\nThere must be exactly ONE definition ({DEFINITION.relative_to(APP.parent)}). "
        "Import DISCLAIMER from app.core.disclaimer instead — Commitment 2 promises the "
        "disclaimer is FIXED, and a repeated literal can only promise that by coincidence."
    )


def test_the_definition_actually_defines_the_sentence():
    """Pins half 1 against going blind: closure over an empty set is not closure.

    If the sentence were deleted product-wide, the scan above would go green while the
    product silently stopped making Commitment 2's promise. This asserts there is
    something to be closed over, and that it is the sentence the spec names.
    """
    assert DISCLAIMER == "Information only, not financial advice."
    assert DISCLAIMER in DEFINITION.read_text(encoding="utf-8")


def test_the_scoped_caveats_are_not_absorbed_into_the_product_disclaimer():
    """D-106 kind (a) stays where it is — this guard must never drive its removal.

    `IA:425-440` rules the scoped caveats **part of the figure**: Legal *"does not own,
    absorb, shorten, or centralise them"*, and removing one is an honesty regression
    (AC-L6). The closure scan above searches for the PRODUCT-level sentence only, so it
    cannot see them — this test states that separation as an intention rather than
    leaving it to be re-derived by whoever next reads the scan and 'tidies up'.
    """
    caption = (APP / "services" / "reports_pack.py").read_text(encoding="utf-8")
    assert "Reporting only, not advice." in caption, (
        "The Reports Pack's scoped caveat is gone. It is D-106 kind (a) — part of the "
        "figure, not the product-level disclaimer — and removing it is an honesty "
        "regression (AC-L6). It is NOT redundant with app.core.disclaimer.DISCLAIMER."
    )


# ─── half 2: coverage ───────────────────────────────────────────────────────────

class _FakeProvider:
    """Drives ``answer_stream`` down one terminal path per mode."""

    name = "openai_compatible"

    def __init__(self, mode: str):
        self.mode = mode

    async def health(self) -> HealthStatus:
        if self.mode == "unavailable":
            return HealthStatus(available=False, provider=self.name, models=[])
        return HealthStatus(available=True, provider=self.name, models=["m"])

    async def chat(self, request) -> AsyncIterator[AIChunk]:
        if self.mode == "error":
            raise RuntimeError("500 from model endpoint: boom")
        if self.mode == "unsafe":
            # A buy recommendation — the validator must reject it, discarding the model
            # text and falling back to the deterministic template.
            yield AIChunk(delta="You should buy AAPL right now, it is a great deal.", done=False)
            yield AIChunk(delta="", done=True)
        else:
            yield AIChunk(delta="Your portfolio is described by the facts above.", done=False)
            yield AIChunk(delta="", done=True)


async def _done_event(monkeypatch, mode: str, *, facts: bool = True) -> dict:
    async def fake_facts(session, question, *, mode=None):
        return [GroundingFact(label="Net worth", value="100 SGD")] if facts else []

    monkeypatch.setattr(grounding, "gather_facts", fake_facts)
    monkeypatch.setattr(grounding, "get_ai_provider", lambda: _FakeProvider(mode))
    grounding._request_times.clear()

    events = [e async for e in grounding.answer_stream(None, "How is my portfolio?")]
    return next(e for e in events if e["type"] == "done")


# Every terminal path in ``answer_stream``. Named for the branch each one lands on so a
# future branch that forgets its disclaimer is reported by NAME, not by index.
TERMINAL_PATHS = [
    ("provider unavailable → deterministic fallback", {"mode": "unavailable"}),
    ("no facts → refusal", {"mode": "normal", "facts": False}),
    ("model errored → data fallback", {"mode": "error"}),
    ("validation rejected the answer → data fallback", {"mode": "unsafe"}),
    ("validated answer → model text", {"mode": "normal"}),
]


@pytest.mark.parametrize("label,kwargs", TERMINAL_PATHS, ids=[p[0] for p in TERMINAL_PATHS])
async def test_every_terminal_done_event_carries_the_disclaimer(monkeypatch, label, kwargs):
    done = await _done_event(monkeypatch, **kwargs)
    assert done.get("disclaimer") == DISCLAIMER, (
        f"The '{label}' path ends the stream without the fixed disclaimer. "
        "Commitment 2 says EVERY AI answer ends with it — including the ones that "
        "give up."
    )


async def test_all_terminal_paths_are_reachable(monkeypatch):
    """Pins half 2 against going blind: a path that stopped being reachable is a hole.

    If a refactor made one of these modes fall through to a shared branch, the
    parametrised test above would still pass — it would just be asserting the same
    branch five times. Asserting the paths are DISTINCT is what keeps the coverage
    claim honest.
    """
    seen = [await _done_event(monkeypatch, **kw) for _, kw in TERMINAL_PATHS]
    providers = [d.get("provider") for d in seen]
    assert providers.count("fallback") == 3, (
        f"Expected three deterministic-fallback terminal paths, saw {providers}. "
        "answer_stream's branch structure changed — re-derive TERMINAL_PATHS rather "
        "than adjusting this number."
    )
    assert providers.count("openai_compatible") == 2, (
        f"Expected two model-answer terminal paths, saw {providers}."
    )
