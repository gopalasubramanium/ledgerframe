# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE FIGURE REGISTRY GUARDS — R-54 §9-B, Phase 0-2a.

*Owner:* "Centralizing fact identity into a single parity-guarded backend table prevents drift and
ensures robust reverse-indexing for analytics."

The two ruled fail-firsts:

1.  **A term must not resolve to two sources.** This is F6's lesson (*two sources of truth for one
    fact is the whole defect*) turned into a table and then into a test.
2.  **No row for a figure the engine does not serve.** A registry row is a promise that a number
    exists; a row for a figure nothing serves is a fabricated number with a lookup table in front
    of it. **CAGR is the named case** — D-086 forbids it outright.

Plus the **transitional parity tripwire**: Phase 0-2a deliberately leaves `analytics.py`'s inline
`term_id`s in place (0-2b deletes them), so for one delta the fact lives in two places. That is
made safe the F6 way — a guard that holds them equal — rather than by intending to be careful.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.services.figure_registry import (
    LABELS_NOT_IN_GLOSSARY,
    REGISTRY,
    canonical_label,
    figure_for_label,
    figures_for_term,
    term_id_for_label,
)

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs" / "specs" / "GLOSSARY.md"


# ── Ruled fail-first #1 — one figure, one source ──────────────────────────────────────────────

def test_no_two_rows_claim_the_same_canonical_source():
    """One (endpoint, field) pair may back exactly ONE figure.

    Two rows pointing at the same served value would mean the registry itself had become the
    second source of truth it exists to prevent.
    """
    seen: dict[tuple[str, str], str] = {}
    for f in REGISTRY:
        key = (f.endpoint, f.field)
        assert key not in seen, (
            f"{f.figure_id!r} and {seen[key]!r} both claim {f.endpoint} → {f.field!r}. "
            f"One figure, one source (F6)."
        )
        seen[key] = f.figure_id


def test_no_label_resolves_to_two_figures():
    """A label — canonical or alias — may name exactly one figure.

    THE FAIL-FIRST: proven RED by adding "net worth" as an alias of `gross_assets`, which is the
    real-world shape of the mistake (Net worth and Gross assets are EQUAL for a user with no
    liabilities, so a value-coincidence invites exactly this collapse — `tools.py:28-52`).
    """
    owners: dict[str, str] = {}
    for f in REGISTRY:
        assert f.canonical_label.lower() not in f.aliases, (
            f"{f.figure_id}: the canonical label is repeated in its own aliases — redundant, and "
            f"it makes a self-collision look like an ambiguity."
        )
        for name in (f.canonical_label.lower(), *f.aliases):
            assert owners.get(name, f.figure_id) == f.figure_id, (
                f"label {name!r} resolves to both {owners[name]!r} and {f.figure_id!r} — "
                f"a coincidence of values is not an identity."
            )
            owners[name] = f.figure_id


def test_figure_ids_are_unique():
    ids = [f.figure_id for f in REGISTRY]
    assert len(ids) == len(set(ids)), "duplicate figure_id in REGISTRY"


# ── Ruled fail-first #2 — no row for a figure the engine does not serve ───────────────────────

def test_every_row_names_an_endpoint_the_app_actually_routes():
    """A registry row must point at a real route, verified against the frozen contract.

    Not "a plausible path" — the contract is the list of paths this app serves, so a typo or an
    aspirational endpoint reds here rather than shipping as a dead promise.
    """
    import json

    contract = json.loads((REPO / "docs" / "specs" / "API-CONTRACT.json").read_text())
    paths = set(contract["paths"])
    for f in REGISTRY:
        method, path = f.endpoint.split(" ", 1)
        assert path in paths, f"{f.figure_id}: {path} is not in the frozen API contract"
        assert method.lower() in contract["paths"][path], (
            f"{f.figure_id}: {path} has no {method} operation"
        )


def test_no_registry_row_for_a_prohibited_figure():
    """CAGR is the named case — D-086 (`PRODUCT-SPEC.md:152`) forbids an annualised figure.

    A registry row would give tier-1 a term→endpoint route to a number the product deliberately
    does not compute, which is how a lookup table becomes a fabrication.
    """
    for f in REGISTRY:
        haystack = f"{f.figure_id} {f.canonical_label} {' '.join(f.aliases)}".lower()
        assert "cagr" not in haystack, (
            f"{f.figure_id} names CAGR — D-086 forbids an annualised/CAGR figure. "
            f"The engine does not serve it and the registry must not promise it."
        )
        assert "annualis" not in haystack and "annualiz" not in haystack, (
            f"{f.figure_id} names an annualised figure — see D-086"
        )


# ── GLOSSARY spelling — strict, with exemptions declared BY NAME WITH A REASON ────────────────

def test_every_canonical_label_is_a_glossary_term_or_a_declared_exemption():
    """CLAUDE.md's hard rule, applied to the AI's fact labels for the first time.

    ⚠ THIS GUARD FOUND A LIVE VIOLATION AT PHASE 0-2a. `FIGURE_IDENTITY` — the map whose whole job
    is relabelling figures to their GLOSSARY spelling — itself carried **"Total assets"** and
    **"Total liabilities"**, and GLOSSARY has neither (`:66` is **Gross assets**, `:67` is
    **Liability**). `networth_facts` has been serving both to users. Nothing caught it because
    `test_glossary_parity` measures the HELP store against the spec and never the AI's labels.

    "Total assets" → "Gross assets" is applied here (an existing ratified spelling, D-021 cited in
    the same GLOSSARY row). "Total liabilities" is left OPEN as ledger F-1 with a declared
    exemption, because which spelling is right is an owner call — the exemption keeps the question
    visible instead of settling it by silence.
    """
    spec = SPEC.read_text(encoding="utf-8")
    for f in REGISTRY:
        if f.canonical_label in LABELS_NOT_IN_GLOSSARY:
            continue
        assert f"**{f.canonical_label}**" in spec, (
            f'{f.figure_id}: canonical label "{f.canonical_label}" is not in GLOSSARY.md with '
            f"that exact spelling. Add it to the SPEC first, or declare it in "
            f"LABELS_NOT_IN_GLOSSARY with a reason."
        )


def test_exemptions_are_not_stale():
    """An exemption for a label no row uses is dead weight that hides the next real one."""
    labels = {f.canonical_label for f in REGISTRY}
    stale = sorted(set(LABELS_NOT_IN_GLOSSARY) - labels)
    assert not stale, f"LABELS_NOT_IN_GLOSSARY declares labels no figure uses: {stale}"


def test_gross_assets_carries_the_retired_label_as_an_alias():
    """The old spelling must still RESOLVE, or absorbing FIGURE_IDENTITY would drop a mapping."""
    assert figure_for_label("total assets") is figure_for_label("gross assets")
    assert canonical_label("Total assets") == "Gross assets"


# ── term_id: the reverse index, and its one-to-many shape ─────────────────────────────────────

def test_every_declared_term_id_is_a_real_help_glossary_entry():
    from app.services.help import HELP

    known = {e["id"] for e in HELP if e["category"] == "Glossary"}
    for f in REGISTRY:
        if f.term_id is not None:
            assert f.term_id in known, f"{f.figure_id}: {f.term_id!r} is not a Help glossary entry"


def test_the_reverse_index_is_one_to_many_and_says_so():
    """`term-xirr-twr` explains TWO figures — the reverse index must not collapse them.

    Tier-1(a) shows the entry alongside every figure it explains; a reverse index that returned one
    row would silently pick a winner.
    """
    assert {f.figure_id for f in figures_for_term("term-xirr-twr")} == {"xirr", "twr"}
    assert len(figures_for_term("term-allocation-weight")) == 4
    assert {f.figure_id for f in figures_for_term("term-concentration")} == {
        "largest_position", "concentration_top5"
    }


def test_a_figure_may_have_no_help_entry_and_that_is_a_real_answer():
    """Net worth is the striking case: a GLOSSARY term and the headline figure, with no `term-*`
    Help entry. Tier-1 may show the figure without an explanation; it must never invent one."""
    net_worth = figure_for_label("net worth")
    assert net_worth is not None and net_worth.term_id is None


# ── The transitional parity tripwire (deleted at Phase 0-2b) ──────────────────────────────────

def _analytics_inline_term_ids() -> list[tuple[str, str, int]]:
    """(label, term_id, lineno) for every metric dict in analytics.py carrying an inline term_id.

    Parsed from the AST, not the text — the Phase 0-1 lesson: a guard that reads comments finds
    claims, not code.
    """
    tree = ast.parse((REPO / "app" / "services" / "analytics.py").read_text(encoding="utf-8"))
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        pairs = {
            k.value: v.value
            for k, v in zip(node.keys, node.values, strict=False)
            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
        }
        if "label" in pairs and "term_id" in pairs:
            out.append((pairs["label"], pairs["term_id"], node.lineno))
    return out


def test_the_inline_analytics_term_ids_are_parsed_at_all():
    """Blindness pin. If the parser drifts, the parity test below would pass over an empty list."""
    rows = _analytics_inline_term_ids()
    assert len(rows) >= 18, f"expected analytics' inline term_ids, parsed {len(rows)}"


@pytest.mark.parametrize("label,term_id,lineno", _analytics_inline_term_ids())
def test_analytics_inline_term_id_equals_the_registry(label, term_id, lineno):
    """THE TRANSITIONAL TRIPWIRE — Phase 0-2a leaves the fact in two places, deliberately.

    §9-B rules that analytics' `term_id` becomes the derived reverse index of this table. Phase
    0-2a builds the table AI-side only and leaves `analytics.py` untouched, so for exactly one
    delta the mapping exists twice. Two sources for one fact is the defect this registry exists to
    end — so the transitional state is made safe the F6 way, with a guard rather than an intention.

    **This test is DELETED by Phase 0-2b**, when the inline copies go and analytics derives from
    here. If you are reading it after 0-2b landed, that is the bug.
    """
    assert term_id_for_label(label) == term_id, (
        f"analytics.py:{lineno} metric {label!r} declares term_id {term_id!r} but the registry "
        f"says {term_id_for_label(label)!r}. Until Phase 0-2b these must agree exactly."
    )


def test_the_registry_covers_every_metric_analytics_labels_with_a_term():
    """Coverage in the other direction — a metric the registry does not know is a hole in it."""
    missing = [
        (label, lineno)
        for label, _term, lineno in _analytics_inline_term_ids()
        if figure_for_label(label) is None
    ]
    assert not missing, f"analytics metrics with no registry row: {missing}"


# ── FIGURE_IDENTITY is absorbed, not duplicated ───────────────────────────────────────────────

def test_figure_identity_no_longer_exists_as_a_second_table():
    """Absorbed means GONE. A surviving copy is precisely the two-tables defect."""
    src = (REPO / "app" / "ai" / "tools.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    assigned = {
        t.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for t in ([node.target] if isinstance(node, ast.AnnAssign) else node.targets)
        if isinstance(t, ast.Name)
    }
    assert "FIGURE_IDENTITY" not in assigned, (
        "app/ai/tools.py still defines FIGURE_IDENTITY — §9-B ruled it ABSORBED into the "
        "figure registry, and two tables for one fact is the defect."
    )
    # Blindness pin: prove tools.py still routes through the registry, so deleting the
    # integration would not make this guard pass by having nothing to check.
    assert re.search(r"from app\.services\.figure_registry import", src), (
        "tools.py no longer imports the figure registry — this guard has gone blind."
    )
