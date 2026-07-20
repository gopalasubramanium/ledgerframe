# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE FACT PACK IS THE TRUST SURFACE — one canonical fact per figure, every figure formatted.

AI-surfaces §14-3 / Finding 5 (owner-ruled 2026-07-20, option (c) — both halves).

WHAT THE 0a WALK FOUND, and what the 78/78 run walked straight past:

    | Total unrealised P/L | 79,326.30 SGD |
    | Unrealised P/L       | 79326.3 SGD   |
    | Total return %       | 11.45%        |
    | Total return         | 11.45%        |

The same figure twice, under two labels, one copy raw — on the ONE list in the product whose
entire purpose is to let a reader check the answer against its basis. A basis list that shows one
number twice, spelled two ways, reads as a product that does not know its own figures.

MECHANISM: the pack merges two sources that overlap. ``portfolio_facts`` formats money through
``_fmt``; ``performance_facts`` (the analytics ``key_stats`` path) rendered it as ``f"{v} {base}"``
— no formatting at all. And ``_dedupe`` deduplicated by **LABEL**, so two labels for one figure
were, to it, two facts.

⚠ THE CANONICAL LABEL AND THE CANONICAL FORMAT CAME FROM DIFFERENT SIDES. This is why the fix is
not "keep one source and drop the other": ``GLOSSARY.md:157/161`` makes **Unrealised P/L** and
**Total return** the canonical spellings (the ``performance_facts`` side), while ``_fmt`` is the
canonical rendering (the ``portfolio_facts`` side). Neither source was wholly right. Deduplicating
on figure identity and formatting BOTH sides is the only combination that ends with a list that is
canonical in both respects.

WHY FIGURE IDENTITY IS DECLARED AND NOT INFERRED FROM THE VALUE. The obvious cheap guard — "no two
facts in the pack render the same number" — is WRONG, and would ship a data-loss bug the day a
user has no liabilities: **Net worth** and **Total assets** are then equal, and they are two
genuinely different figures that happen to coincide. Collapsing them would delete a fact the
reader asked for. So identity is an explicit, reviewable map in ``app/ai/tools.py`` — a coincidence
of values is never treated as a duplicate.
"""

from __future__ import annotations

import json
import re

import pytest

# Questions chosen to force the OVERLAP: each routes through both `portfolio_facts` (the anchor
# that `gather_facts` prepends on any portfolio intent) and `performance_facts` (the analytics
# path). The 0a screenshot was the first of these.
_OVERLAPPING_QUESTIONS = [
    "How is my portfolio performing?",
    "How am I doing overall?",
    "What is my total return and unrealised P/L?",
    "How is my portfolio performing and what's the risk?",
]


async def _pack(app_client, question: str) -> list[dict]:
    r = await app_client.post("/api/v1/ai/chat", json={"question": question})
    assert r.status_code == 200
    facts: list[dict] = []
    for line in r.text.splitlines():
        if line.startswith("data:"):
            ev = json.loads(line[5:].strip())
            if ev.get("type") == "facts":
                facts = ev["facts"]
    assert facts, f"no fact pack served for {question!r} — the guard would pass by seeing nothing"
    return facts


# --- Half 1: ONE CANONICAL FACT PER FIGURE ----------------------------------------------------- #


@pytest.mark.parametrize("question", _OVERLAPPING_QUESTIONS)
async def test_no_two_facts_in_the_pack_resolve_to_the_same_figure(app_client, question: str):
    """SEEN RED on the shipped build: 'Total unrealised P/L' + 'Unrealised P/L' in one pack.

    Asserted on FIGURE IDENTITY, which is the map the implementation deduplicates on — so this is
    the guard for the rule, not a restatement of the code. A new fact source that reintroduces an
    alias for a figure already in the pack reds here.
    """
    from app.ai.tools import figure_identity

    facts = await _pack(app_client, question)
    by_figure: dict[str, list[str]] = {}
    for f in facts:
        fig = figure_identity(f["label"])
        if fig is None:
            continue  # not a figure with declared identity — nothing to collide with
        by_figure.setdefault(fig, []).append(f["label"])

    dupes = {fig: labels for fig, labels in by_figure.items() if len(labels) > 1}
    assert not dupes, (
        f"the fact pack for {question!r} shows ONE figure under more than one label:\n  "
        + "\n  ".join(f"{fig}: {labels}" for fig, labels in dupes.items())
        + "\nThis list is the panel's trust surface — the reader checks the answer against it. "
        "One figure, one canonical label (AI-surfaces §14-3 / Finding 5)."
    )


@pytest.mark.parametrize("question", _OVERLAPPING_QUESTIONS)
async def test_the_canonical_label_is_the_glossary_spelling(app_client, question: str):
    """"Canonical wins" means the GLOSSARY spelling wins, not whichever source ran first.

    SEEN RED: the pre-fix pack kept 'Total unrealised P/L' (no GLOSSARY row) and 'Total return %'
    while dropping the canonical 'Unrealised P/L' / 'Total return'. Ordering decided the label,
    and ordering is not a decision.
    """
    labels = {f["label"] for f in await _pack(app_client, question)}
    retired_shapes = {"Total unrealised P/L", "Total return %"}
    assert not (labels & retired_shapes), (
        f"the pack for {question!r} still serves a non-canonical alias: "
        f"{sorted(labels & retired_shapes)}. GLOSSARY.md:157/161 spell these "
        f"'Unrealised P/L' and 'Total return'."
    )


# --- Half 2: NO UNFORMATTED MONEY -------------------------------------------------------------- #

# A money value in the pack looks like  "79,326.30 SGD"  — optionally signed, optionally trailed by
# a parenthetical the fact itself adds ("(12.3%)", "(indicative)"). The currency code is what makes
# a value MONEY; everything else in the pack is a percentage, a ratio, a count or prose.
_MONEY = re.compile(r"^-?\d{1,3}(?:,\d{3})*\.\d{2} [A-Z]{3}(?: [–-] -?\d{1,3}(?:,\d{3})*\.\d{2} [A-Z]{3})?(?: \(.*\))?$")
_HAS_CURRENCY = re.compile(r"(?:^|[\s(])-?\d[\d,]*(?:\.\d+)? [A-Z]{3}\b")


@pytest.mark.parametrize("question", _OVERLAPPING_QUESTIONS + ["What is my net worth?",
                                                               "What do I own?",
                                                               "What are my biggest positions?"])
async def test_every_money_value_in_the_pack_is_in_the_served_display_format(app_client, question):
    """D-105 — no raw numbers on a user-facing money surface.

    SEEN RED on the shipped build: 'Unrealised P/L: 79326.3 SGD' and
    'Income (div/int): 0.0 SGD' — no thousands separator, one decimal place, directly beneath a
    correctly-formatted copy of the same figure.

    ⚠ This asserts on the SERVED pack, not on `_fmt`. Testing the formatter would have been green
    throughout: `_fmt` was never broken, it was BYPASSED. A guard on the helper cannot see a
    caller that does not call it.
    """
    offenders = [
        (f["label"], f["value"])
        for f in await _pack(app_client, question)
        if _HAS_CURRENCY.search(f["value"]) and not _MONEY.match(f["value"])
    ]
    assert not offenders, (
        f"raw money in the fact pack for {question!r}:\n  "
        + "\n  ".join(f"{label}: {value!r}" for label, value in offenders)
        + "\nEvery money value the pack serves renders through the display format (D-105)."
    )


# --- The anti-blind pin ------------------------------------------------------------------------ #


async def test_the_money_guard_can_actually_see_money(app_client):
    """Both guards above pass trivially against a pack with no money in it, and a pack with no
    money in it is itself a defect nobody would notice. Assert the corpus is non-empty.

    (CLAUDE.md: a guard is pinned against going blind — if the thing it protects disappears it
    must fail loudly rather than pass by protecting nothing.)
    """
    facts = await _pack(app_client, "How is my portfolio performing?")
    money = [f for f in facts if _HAS_CURRENCY.search(f["value"])]
    assert money, (
        "no money-shaped value in the performance fact pack — either the pack stopped serving "
        "figures or _HAS_CURRENCY has drifted. Both make the format guard blind."
    )


def test_the_figure_identity_map_is_not_empty():
    """The de-duplication guard is blind if nothing declares identity.

    ⊕ R-54 Phase 0-2a — REPOINTED, NOT REWRITTEN. This pin used to import `FIGURE_IDENTITY` from
    `app/ai/tools.py`; §9-B absorbed that map into `app/services/figure_registry.py`, so the pin's
    SUBJECT moved. It is repointed deliberately and kept asserting the same property — a blindness
    pin that is deleted because its import broke is a guard silently retired, which is the exact
    failure the pin exists to prevent.

    It now asserts the two halves separately: that identities are declared at all, and that the
    lookup `_dedupe` actually calls still resolves one. An empty registry and a registry the
    resolver cannot reach are both "protecting nothing", and only the first is visible from the
    table alone.
    """
    from app.ai.tools import figure_identity
    from app.services.figure_registry import REGISTRY

    assert REGISTRY, "no declared figure identities — the de-dupe guard protects nothing"
    assert figure_identity("Net worth") == "net_worth", (
        "the identity lookup no longer resolves a known label — the de-dupe guard is blind even "
        "though the registry is populated"
    )
