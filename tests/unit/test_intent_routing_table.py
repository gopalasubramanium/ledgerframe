# SPDX-License-Identifier: AGPL-3.0-or-later
"""ONE ROUTER, ONE TABLE — the R-54 §9-A structural guards.

R-54 §9-A (owner ruling, chat 2026-07-20) made `classify_intent`'s closed enum the SINGLE intent
authority and `INTENT_FACT_SOURCES` the ONE table `gather_facts` derives its branching from. Two
routers can no longer disagree **because there is only one** — that is structural, and structure is
exactly what rots quietly. These guards keep the structure honest:

1.  **Coverage.** Every `Intent` member has a row. A new member nobody mapped would route to
    nothing while *looking* deliberate — the failure mode `fact_sources()` raises on at runtime.
2.  **No second word list.** `gather_facts` must not regrow its own routing vocabulary. This is
    the guard that would have caught the original defect, and it is written in the shape
    `check:primitives` uses (`r54 §0-M`): a narrow scan with a **blindness pin**, so it fails loudly
    rather than passing by protecting nothing.
3.  **Declared sources are real.** A row naming a source no assembler consumes is a dead branch.

*Owner:* "A single source of truth for intent resolution prevents contradictory states;
deterministic matching is superior to probabilistic guessing for core navigation."
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from app.ai.intent import INTENT_FACT_SOURCES, Intent, classify_intent, fact_sources

# Every source name the table is allowed to use — each must be consumed by `gather_facts`.
KNOWN_SOURCES = {"market", "news", "networth", "perf", "alloc", "movers", "holdings", "watch"}


def test_every_intent_has_a_row_in_the_table():
    """Coverage. An unmapped intent is a routing hole that reads as a deliberate empty set."""
    missing = [i.name for i in Intent if i not in INTENT_FACT_SOURCES]
    assert not missing, (
        f"Intent members with no INTENT_FACT_SOURCES row: {missing}. Every intent declares its "
        f"sources — add a row (an empty frozenset is a valid, and meaningful, answer)."
    )


def test_the_table_declares_no_unknown_source():
    """A row naming a source nothing consumes is a dead branch that will never fire."""
    for intent, sources in INTENT_FACT_SOURCES.items():
        unknown = set(sources) - KNOWN_SOURCES
        assert not unknown, f"{intent.name} declares unknown source(s) {unknown}"


def test_fact_sources_raises_on_an_unregistered_intent():
    """The runtime half of the coverage guard — proven, not assumed.

    `fact_sources` refuses rather than returning an empty set, so a hole cannot masquerade as a
    deliberate "gathers nothing".
    """
    class _Bogus:
        pass

    with pytest.raises(KeyError, match="no row in INTENT_FACT_SOURCES"):
        fact_sources(_Bogus())  # type: ignore[arg-type]


def test_gather_facts_does_not_regrow_its_own_routing_word_lists():
    """THE GUARD FOR THE DEFECT ITSELF — `gather_facts` must not become a second router again.

    Before R-54 Phase 0-1 the routing decision was eight booleans built from `has(*ws)`, a bare
    substring matcher (`any(w in q for w in ws)`). This asserts that helper is gone and that the
    flags are read from the table.

    **Blindness pin** (r54 §0-M, the `check:primitives` shape): if `gather_facts` ever stops
    mentioning the table at all, this test FAILS rather than passing vacuously — otherwise deleting
    the derivation would make the guard green by removing its subject.
    """
    src = inspect.getsource(
        __import__("app.ai.tools", fromlist=["gather_facts"]).gather_facts
    )

    # Blindness pin FIRST: prove the subject is still here before asserting anything about it.
    assert "fact_sources" in src and "sources" in src, (
        "gather_facts no longer reads the intent table — this guard has gone blind. "
        "Either the routing moved (update this guard deliberately) or the single-authority "
        "consolidation was reverted."
    )

    assert not re.search(r"\bdef has\(", src), (
        "gather_facts has regrown a `has(*ws)` substring matcher — that helper WAS the second "
        "router (R-54 §0-A). Route from Intent via INTENT_FACT_SOURCES."
    )
    for flag in ("is_market", "is_news", "is_networth", "is_perf",
                 "is_alloc", "is_movers", "is_holdings", "is_watch"):
        m = re.search(rf"^\s*{flag} = (.+)$", src, re.M)
        assert m, f"{flag} is gone from gather_facts — update this guard deliberately"
        assert "in sources" in m.group(1), (
            f"{flag} is no longer derived from the intent table (got: {m.group(1).strip()!r}). "
            f"A flag computed from the question text is a second routing authority."
        )


# ── The substring hazards, at the classifier ──────────────────────────────────────────────────
# The served-pack proof lives in tests/integration/test_intent_word_boundary.py (the level the
# defect actually shipped at). These pin the same specimens one layer down, so a regression names
# the classifier directly instead of surfacing as a puzzling fact-pack diff.

@pytest.mark.parametrize("question,forbidden", [
    ("How do I download my data?", Intent.PORTFOLIO_MOVEMENT),
    ("What is a closed-end fund?", Intent.PORTFOLIO_MOVEMENT),
    ("What does it mean when a bond is downgraded?", Intent.PORTFOLIO_MOVEMENT),
    ("Can I open the export in a spreadsheet?", Intent.ALLOCATION_ANALYSIS),
    ("How do I remove a holding I entered by mistake?", Intent.PORTFOLIO_MOVEMENT),
])
def test_a_fragment_inside_a_word_does_not_select_an_intent(question, forbidden):
    """"los" ⊄ closed, "own" ⊄ download, "mov" ⊄ remove, "spread" ⊄ spreadsheet."""
    assert classify_intent(question) is not forbidden


def test_the_honest_miss_is_unknown_and_gathers_nothing():
    """A question with no routable intent returns UNKNOWN and selects NO source.

    This is the "tier-1 never guesses" half of §9-A: the miss is a declared empty set that the
    caller's ratified fallback handles, never a nearest-neighbour guess.
    """
    intent = classify_intent("Can I open the export in a spreadsheet?")
    assert intent is Intent.UNKNOWN_GENERAL_QUESTION
    assert fact_sources(intent) == frozenset()


def test_the_intent_module_is_the_only_routing_authority_on_disk():
    """No other module may read the table directly — it is consumed through `fact_sources()`.

    ⚠ THIS GUARD PARSES THE AST, NOT THE TEXT, AND THE FIRST DRAFT DID NOT.

    Written as a substring sweep, it went RED on `app/ai/tools.py` — whose only mention of the
    table is a **comment** explaining where its flags now come from. A guard that reads comments
    finds claims, not code: the same defect page-help §9-bis-9(d) records (a guard that read
    comments found "the control exists" corroborated by a comment saying it did **not** exist yet),
    and the same reason `check-ui-primitives.mjs:54-62` strips comments before scanning.

    Walking the AST means only a real `Name`/`Attribute` reference counts, so the guard cannot be
    tripped by prose or silenced by deleting a comment.
    """
    import ast

    root = Path(__file__).resolve().parents[2] / "app"
    hits: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            name = getattr(node, "id", None) or getattr(node, "attr", None)
            if name == "INTENT_FACT_SOURCES":
                hits.append(path.relative_to(root).as_posix())
                break

    assert sorted(hits) == ["ai/intent.py"], (
        f"INTENT_FACT_SOURCES is READ outside its module: {sorted(hits)}. It is consumed through "
        f"`fact_sources()`; a direct second reader is how a table becomes two tables."
    )
