# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE TIER-1/TIER-2 MISS SPLIT — R-54 §9-A, Phase 1 delta 2, ruled at 0a-i (item 4).

`gather_facts` ends with a LAST-RESORT: when nothing routed, hand back
`portfolio_facts + movers_facts` so *something* is grounded (`app/ai/tools.py`, the
`if not facts:` block). That is a **tier-2 grounding** behaviour — the point is to give the
MODEL something to narrate from. In **tier 1** (deterministic — no model narrates, by
construction under no-egress/disabled, or because the model is down / the limiter is
exhausted) an unroutable question is a **MISS**: it must take the ratified honest-miss shape
(the empty fallback + what CAN be asked), never a portfolio+movers guess.

RULING (0a-i, owner 2026-07-21; r54 plan §Phase-0a-i, item 4): "the last-resort
(`tools.py`) is scoped to TIER-2 GROUNDING ONLY. Tier-1's unroutable path takes the ratified
honest-miss shape. Phase 1 implements the split; guard: a tier-1 response carrying facts for
an unroutable question turns RED."

ASSERTED AT THE SERVED PACK, NOT THE HELPER — the F5/Finding-5 lesson
(`test_ai_fact_pack_canonical.py`): the split lives on the SERVING path, so a helper test can
pass while the pack the panel renders still carries the guess. These drive `POST /ai/chat`,
which under the suite's default posture (`LEDGERFRAME_AI_ENABLED=false` →
`DisabledAIProvider` → `health.available is False`) is **tier 1** — exactly the posture the
split governs.

FAIL-FIRST: the miss assertion was seen RED on the pre-split build — an unroutable question
returned the last-resort `Gainer …`/`Detractor …` movers pack instead of the empty shape.
"""

from __future__ import annotations

import json

# Two genuinely unroutable questions: `classify_intent` → UNKNOWN_GENERAL_QUESTION with an
# EMPTY source set, no resolvable symbol, and no Help match (`help_facts(...) == []`). So the
# routed pack is empty and only the last-resort could populate it — which is the whole point.
_UNROUTABLE = ["xyzzy plugh frobnicate", "blahblah zzzz qqqq"]


async def _events(app_client, question: str) -> list[dict]:
    r = await app_client.post("/api/v1/ai/chat", json={"question": question})
    assert r.status_code == 200
    out: list[dict] = []
    for line in r.text.splitlines():
        if line.startswith("data:"):
            out.append(json.loads(line[5:].strip()))
    return out


def _facts(events: list[dict]) -> list[str]:
    fe = next(e for e in events if e.get("type") == "facts")
    return [f["label"] for f in fe["facts"]]


async def test_tier1_miss_returns_the_honest_empty_shape_not_the_last_resort(app_client):
    """FAIL-FIRST. An unroutable tier-1 question carries NO facts — the honest miss.

    On the pre-split build the `if not facts:` last-resort fired unconditionally, so this
    event carried `portfolio_facts + movers_facts` (`Gainer …`/`Detractor …`, the net-worth
    headline, …). Tier-1 never guesses: the miss is a miss.
    """
    for q in _UNROUTABLE:
        labels = _facts(await _events(app_client, q))
        assert labels == [], (
            f"tier-1 miss on {q!r} carried last-resort facts instead of the empty shape: {labels}"
        )


async def test_tier1_miss_body_is_the_refusal_not_an_approximate_answer(app_client):
    """The miss BODY is the served refusal — never an approximate answer (§7-A).

    With no facts there is no fact list to be the answer, so `_template_answer` returns
    `REFUSAL_NO_FACTS`. The panel goes to its honest-miss state, not a nearest match.
    """
    events = await _events(app_client, _UNROUTABLE[0])
    body = "".join(e["delta"] for e in events if e.get("type") == "delta")
    assert "don't have the data needed" in body
    done = next(e for e in events if e.get("type") == "done")
    assert done["provider"] == "fallback"  # tier-1 deterministic, no model


async def test_tier1_ROUTABLE_question_still_carries_its_facts(app_client):
    """The discriminator — the guard is NOT the vacuous "tier-1 is always empty".

    A routable tier-1 question ("what is my net worth") still resolves to real facts through
    the deterministic route; only the UNROUTABLE path goes empty. Without this, the miss guard
    would pass even if the split had accidentally emptied every tier-1 answer.
    """
    labels = _facts(await _events(app_client, "What is my net worth?"))
    assert labels, "a routable tier-1 question must still carry its routed facts"


# ── THE SPLIT IS SYMMETRIC — tier 2 KEEPS the last-resort ────────────────────────────────────
# The served path above runs tier-1 (the suite's default posture). The complementary half — that
# GROUNDING mode is byte-identical to the historical behaviour and STILL hands an unroutable
# question the portfolio+movers last-resort — is asserted at the helper with a seeded session,
# because the point of the split is precisely that the two modes DIFFER on this input. Without it,
# a future change that dropped the last-resort for BOTH modes would leave the tier-1 guard green
# while quietly breaking tier 2.
async def test_tier2_grounding_mode_still_applies_the_last_resort(session):
    from app.ai.tools import AnswerMode, gather_facts
    from app.seed.demo import seed_demo_data

    await seed_demo_data(session)
    await session.flush()

    q = _UNROUTABLE[0]
    tier2 = await gather_facts(session, q, mode=AnswerMode.GROUNDING)
    tier1 = await gather_facts(session, q, mode=AnswerMode.DETERMINISTIC)

    assert tier2, "tier-2 (grounding) must still hand an unroutable question the last-resort pack"
    assert tier1 == [], "tier-1 (deterministic) must return the empty honest miss"
    # And the default is GROUNDING — every un-opted caller (`/ai/facts`, every legacy test) sees
    # the historical pack. Compare LABELS: the values are identical, only each call's per-fact
    # `timestamp` differs (facts carry the moment they were read).
    default_labels = [f.label for f in await gather_facts(session, q)]
    assert default_labels == [f.label for f in tier2]
