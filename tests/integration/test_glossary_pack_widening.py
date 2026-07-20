# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE GLOSSARY CATEGORY REACHES THE FACT PACK — R-54 Phase 0-3.

THE FAIL-FIRST, and it is a census rather than a specimen
---------------------------------------------------------
The Phase-0.9 widening shipped ``_HELP_FACT_CORE = ("body", "interpret")`` and
``_HELP_FACT_EXTRA = ("outputs", "inputs")``. R-54 §0-C executed the corpus and found those tier
lists were named from **page-entry** field names only:

    glossary entries: 29    with interpret: 0
    fields on a glossary entry: body, example, improves, keywords, level, title, what, why

So **every one of the 29 ``term-*`` entries projected ``body`` alone** — the exact failure the
widening was ruled to fix, landing on the one category tier-1(a) (*"what is XIRR"*) is built from.
A budget that silently drops the most important field is worse than no budget: it succeeds quietly.

Amended by the owner (recorded as a dated amendment on the Phase-0.9 ruling's own record in
``docs/plans/CURRENT.md``): for the Glossary category, **``what`` + ``why`` are unconditional** and
**``improves`` + ``example`` are budgeted** — the same intent as the original ruling (the entry's
MEANING is unconditional, structural extras are budgeted), applied to a corrected census.

These tests assert the census directly, so the guard is the shape of the defect and not a
hand-picked example: *no glossary entry may project body alone.*
"""

from __future__ import annotations

import json

from app.ai.tools import _HELP_FACT_BUDGET, _render_help_fact
from app.services.help import HELP

GLOSSARY = [e for e in HELP if e["category"] == "Glossary"]
PAGES = [e for e in HELP if e["category"] != "Glossary"]


def test_the_corpus_still_has_the_shape_this_guard_assumes():
    """Blindness pin. If the categories or field names drift, every test below goes vacuous."""
    assert len(GLOSSARY) >= 29, f"only {len(GLOSSARY)} glossary entries — corpus drifted"
    assert all(e.get("what") for e in GLOSSARY), "glossary entries no longer carry `what`"
    assert not any(e.get("interpret") for e in GLOSSARY), (
        "a glossary entry now carries `interpret` — the census this widening was built from has "
        "changed; re-derive the tiers rather than trusting these assertions"
    )


def test_no_glossary_entry_projects_body_alone():
    """THE CENSUS ASSERTION — the §0-C defect, stated as the rule it violates."""
    thin = [e["id"] for e in GLOSSARY if _render_help_fact(e).strip() == (e.get("body") or "").strip()]
    assert not thin, (
        f"{len(thin)} glossary entries still project `body` alone: {thin[:5]}… "
        f"The Glossary category carries what/why/improves/example, not interpret/outputs/inputs."
    )


def test_what_and_why_are_unconditional_for_every_glossary_entry():
    """Unconditional means unconditional — not "usually", and not "if it fits"."""
    for e in GLOSSARY:
        rendered = _render_help_fact(e)
        for field in ("what", "why"):
            if e.get(field):
                assert f"{field.capitalize()}:" in rendered, (
                    f"{e['id']}: `{field}` is a CORE field for the Glossary category and is missing "
                    f"from the projection"
                )


def test_core_fields_survive_a_budget_that_cannot_fit_them():
    """UNCONDITIONAL MEANS UNCONDITIONAL — proven against a budget that cannot pay for anything.

    ⚠ WRITTEN BECAUSE A MUTATION EXPOSED THIS GUARD FILE'S BLIND SPOT. Demoting `why` from core to
    budgeted left every assertion above GREEN, because glossary entries are small (largest renders
    1,499 chars against a 3,600 budget) so a demoted field still *fits* and still appears. The
    tests proved PRESENCE and called it unconditionality — and presence is exactly what a budget
    also provides, right up until an entry grows.

    The tier configuration is separately pinned in `test_ai_grounding_corpus.py`, which is what
    actually caught that mutation. This test closes the behavioural half: a synthetic entry whose
    tail is far too large for any budget must STILL carry `what` and `why`.
    """
    # ⚠ SECOND CORRECTION, SAME TEST. The first draft used SHORT core fields and a huge tail — and
    # it still did not fire when `why` was demoted, because a short field fits the budget whether it
    # is core or budgeted. **The discriminating property is size, not position**: only a core field
    # too large to have been afforded proves it was never charged for. Both blind spots were found
    # by mutating, not by reading.
    oversized = "y" * (_HELP_FACT_BUDGET * 3)
    tail = "z" * (_HELP_FACT_BUDGET * 3)
    entry = {
        "id": "term-synthetic", "category": "Glossary", "title": "Synthetic",
        "body": "B", "what": f"WHAT-CORE {oversized}", "why": f"WHY-CORE {oversized}",
        "improves": tail, "example": tail,
    }
    rendered = _render_help_fact(entry)
    assert "What: WHAT-CORE" in rendered, (
        "`what` was dropped although it is CORE — a core field is never charged to the budget, "
        "however large it is"
    )
    assert "Why: WHY-CORE" in rendered, (
        "`why` was dropped although it is CORE — if this fires after a tier edit, the field was "
        "demoted to the budgeted tail"
    )
    assert tail not in rendered, (
        "an oversized budgeted field was admitted — the budget governs the tail and admits whole "
        "fields only"
    )


def test_page_entries_are_untouched_by_the_glossary_widening():
    """The page category keeps body+interpret core and outputs+inputs budgeted.

    A widening that quietly re-tiered the OTHER category would be a second defect wearing this
    delta's clothes.
    """
    for e in PAGES:
        rendered = _render_help_fact(e)
        if e.get("interpret"):
            assert "Interpret:" in rendered, f"{e['id']}: page entry lost its core `interpret`"
        assert "What:" not in rendered, (
            f"{e['id']}: a page entry projected `what` — the Glossary tiers leaked across categories"
        )


def test_the_budget_is_adhered_to_and_whole_fields_only():
    """Budgeted fields are admitted ENTIRE or not at all — never truncated mid-text.

    A caveat cut in half reads as complete, which is worse than one never sent.
    """
    for e in GLOSSARY:
        rendered = _render_help_fact(e)
        for field in ("improves", "example"):
            raw = e.get(field)
            if not raw:
                continue
            from app.services.help import strip_markup

            whole = strip_markup(raw).strip()
            if f"{field.capitalize()}:" in rendered:
                assert whole in rendered, (
                    f"{e['id']}: `{field}` was included but not WHOLE — a budgeted field is "
                    f"admitted entire or omitted, never truncated"
                )


def test_the_core_tier_is_never_dropped_by_the_budget():
    """The budget governs the TAIL only.

    This is the Phase-0.9 lesson, re-proven for the Glossary tiers: a single priority list under one
    budget dropped `interpret` from the largest entry — the very entry whose missing interpretation
    caused that ruling.
    """
    for e in GLOSSARY:
        core = sum(len(str(e.get(f) or "")) for f in ("what", "why"))
        if core > _HELP_FACT_BUDGET:
            rendered = _render_help_fact(e)
            assert "What:" in rendered, f"{e['id']}: core dropped by the budget"


# ── The ratified size pins, RE-PROVEN with the widened tiers ─────────────────────────────────
# These numbers are the owner's Phase-0.9 ruling ("largest rendered fact ≤ 4000; per-question help
# portion ≤ 12000"). A widening is exactly the change that could breach them, so they are re-proven
# HERE against the new projection rather than left to the corpus test written for the old one.

def test_largest_rendered_glossary_fact_is_within_4000():
    sizes = sorted(((len(_render_help_fact(e)), e["id"]) for e in GLOSSARY), reverse=True)
    largest, entry_id = sizes[0]
    assert largest <= 4000, f"widened glossary fact {entry_id} renders {largest} chars (> 4000)"


def test_largest_rendered_fact_of_any_category_is_within_4000():
    sizes = sorted(((len(_render_help_fact(e)), e["id"]) for e in HELP), reverse=True)
    largest, entry_id = sizes[0]
    assert largest <= 4000, f"{entry_id} renders {largest} chars (> 4000)"


async def test_per_question_help_portion_is_within_12000(app_client):
    """Asserted on the SERVED pack, over term questions the widening most affects."""
    for question in ("what is XIRR", "explain total return", "what is cash runway"):
        r = await app_client.post("/api/v1/ai/chat", json={"question": question})
        assert r.status_code == 200
        facts: list[dict] = []
        for line in r.text.splitlines():
            if line.startswith("data:"):
                ev = json.loads(line[5:].strip())
                if ev.get("type") == "facts":
                    facts = ev["facts"]
        help_chars = sum(len(f["value"]) for f in facts if f["label"].startswith("Help · "))
        assert help_chars <= 12000, (
            f"{question!r}: help portion is {help_chars} chars (> 12000) after the widening"
        )
