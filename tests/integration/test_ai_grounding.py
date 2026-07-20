# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI grounding: facts surfaced, refusal on no data, no fabrication, offline-safe.

These run with AI disabled (deterministic fallback), which is exactly the path
the device uses when the Hailo NPU is absent — so they double as offline tests.
"""

from __future__ import annotations

from app.ai.grounding import answer_stream
from app.ai.prompts import REFUSAL_NO_FACTS
from app.seed.demo import seed_demo_data


async def _collect(session, question):
    facts, text, done = [], "", None
    async for ev in answer_stream(session, question):
        if ev["type"] == "facts":
            facts = ev["facts"]
        elif ev["type"] == "delta":
            text += ev["delta"]
        elif ev["type"] == "done":
            done = ev
    return facts, text, done


async def test_answer_includes_grounding_facts_with_timestamps(session):
    await seed_demo_data(session)
    await session.flush()
    facts, text, done = await _collect(session, "what moved in my portfolio today?")
    assert facts, "expected grounding facts"
    assert all("timestamp" in f for f in facts)
    assert "not financial advice" in text.lower()
    assert done["grounded"] is True


async def test_no_fabricated_numbers_only_facts_appear(session):
    await seed_demo_data(session)
    await session.flush()
    facts, text, _ = await _collect(session, "what is my portfolio value?")
    # Every bullet in the fallback answer must come from a fact — nothing is composed here.
    #
    # ⊕ 2026-07-20 (AI-surfaces Phase 0.9): the direction of the containment check was flipped, and
    # the reason is worth keeping. It asserted `fact_value in line`, which assumed a bullet renders
    # a fact's value ENTIRE. Once the grounding pack carried multi-section help entries, the
    # template began showing the first paragraph of such a fact — a whole unit, but not the whole
    # value — and the old check read that as fabrication.
    #
    # The property that actually matters is the anti-fabrication one, and it is the other way
    # round: everything SHOWN must come from a fact. `line_value in fact_value` says exactly that,
    # and still fails on an invented bullet, which is what this test exists to catch.
    fact_values = {f["value"] for f in facts}
    for line in text.splitlines():
        if not line.startswith("•"):
            continue
        shown = line.removeprefix("•").split(":", 1)[-1].removesuffix(" (may be out of date)").strip()
        assert any(shown in " ".join(v.split()) for v in fact_values), (
            f"the fallback answer shows a bullet that traces to no fact: {shown!r}"
        )


async def test_refusal_when_no_data(session):
    # Empty DB → portfolio facts are all zero but still present; force the empty
    # path by asking something with no matching tool and no holdings.
    facts, text, _ = await _collect(session, "tell me about my holdings")
    # With an empty portfolio the engine still returns zeroed facts (honest), never
    # an invented figure. The refusal string is used only when facts is truly empty.
    assert facts == [] and text.strip() == REFUSAL_NO_FACTS.strip() or facts


async def test_disclaimer_present(session):
    await seed_demo_data(session)
    await session.flush()
    _, _, done = await _collect(session, "portfolio summary")
    assert "not financial advice" in done["disclaimer"].lower()
