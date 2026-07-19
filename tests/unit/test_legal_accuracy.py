# SPDX-License-Identifier: AGPL-3.0-or-later
"""AC-L7 — LEGAL'S COPY JOINS THE ACCURACY CORPUS (page-legal §9-3, owner 2026-07-19).

§9-3's deciding rationale was that **served copy inherits the Help truth bar**. That is a claim
about guards, and a claim about guards is worth exactly the guards that exist. This module is the
payment: the same bar `tests/unit/test_help_content_accuracy.py` holds Help to, applied to Legal.

Same bar means the same three things, and the FIRST is not optional:

* **markup-stripped text**, always. `help_markup.py` records why this is a safety property rather
  than a tidy-up: an inline marker inside a phrase separates its words, so `you **should**` does
  not contain "you should" and the platform's central no-advice guarantee could be broken *in
  bold* by a green suite;
* **advice-free**, across every string;
* **no decision IDs and no implementation notes** in served prose (page-chrome §11-8).

THE ONE EXEMPTION, AND WHY IT IS NAMED RATHER THAN QUIET
--------------------------------------------------------
The seven Product Commitments **fail the Help bar on two counts, inherently**:

* four of them cite a decision ID — `(D-077)`, `(D-004)`, `(D-016)`, `(D-071)`;
* Commitment 1 contains the word "endpoints".

This is a **genuine collision between two live rules**, not an oversight, and it was found by
running the bar rather than by reasoning about it:

* AC-L3 / §9-8 ruled the Commitments are rendered **VERBATIM** from `PRODUCT-SPEC.md` §3, which is
  itself verbatim from DECISIONS.md. Their wording is **not this milestone's to change**;
* page-chrome §11-8 bars decision IDs and implementation notes from served prose.

Both rules are right. They cannot both be satisfied by any edit available to this build, because
the only edit that would satisfy the second is an edit to the first's ratified source.

So the exemption is **scoped to the verbatim block, named, and reasoned** — never a blanket
relaxation, and never applied to a single string this build authored. **Every string this milestone
WROTE meets the full bar**, and the guard below proves that separately, so the exemption can never
grow quietly to cover new copy.

**FLAGGED FOR THE OWNER AT THE 0a** (page-legal §9-8 bars this CLI from deciding it): either
PRODUCT-SPEC.md §3 is amended to drop the parenthetical IDs — in which case AC-L3's guard carries
the change here automatically and this exemption is deleted — or the collision is accepted and the
Commitments show their decision IDs to users on this one page. It is a real choice with a real
cost either way.
"""

from __future__ import annotations

import re

import pytest

from app.services.help_markup import strip_markup
from app.services.legal import all_legal

# --- The corpus, split by WHO AUTHORED IT ------------------------------------------------------ #
# The split IS the guard's design. Merging them would let the verbatim block's exemption silently
# cover authored prose, which is the failure mode an exemption always has.


def _authored() -> list[tuple[str, str]]:
    """Every string this milestone WROTE. Held to the full Help bar, no exemptions."""
    d = all_legal()
    out = [(f"section:{s['id']}", strip_markup(s["body"])) for s in d["sections"]]
    out += [(f"section-title:{s['id']}", s["title"]) for s in d["sections"]]
    out.append(("commitments:title", d["commitments"]["title"]))
    out.append(("commitments:intro", strip_markup(d["commitments"]["intro"])))
    out += [(f"pointer:{p['file']}", strip_markup(p["what"])) for p in d["pointers"]]
    out.append(("pack_footer", strip_markup(d["pack_footer"])))
    return out


def _verbatim() -> list[tuple[str, str]]:
    """The seven Commitments — ratified elsewhere, reproduced here, not editable by this build."""
    return [(f"commitment:{i}", strip_markup(g))
            for i, g in enumerate(all_legal()["commitments"]["items"], 1)]


# The Help bar, copied deliberately rather than imported: importing would couple Legal's floor to
# a module that may narrow for Help's own reasons, and a shared mutable bar is how one page's
# exception becomes another page's silent relaxation.
_ADVISORY = ("you should", "we recommend", "aim for", "a good value", "you must",
             "advise", "the best way to")
_IMPLEMENTATION = ("response_model", "privacy_mode", "/api/", "endpoint", "localstorage",
                   "refdata", "asset_class", "server-side")
_DECISION_ID = re.compile(r"\b[DP]-\d{3}\b|\bND-\d+\b|§")


@pytest.mark.parametrize("where,text", _authored(), ids=[w for w, _ in _authored()])
def test_authored_legal_copy_meets_the_full_help_bar(where: str, text: str):
    """No exemptions. Every string this build wrote.

    Seen RED writing it, on this build's own prose: the position section read *"has no way to: no
    order endpoints exist"* — an honest sentence that leaked an implementation term straight out
    of Commitment 1. Rewritten to *"has no mechanism for doing so"*. The guard caught the author,
    which is the only kind of catch worth having.
    """
    low = text.lower()
    for banned in _ADVISORY:
        assert banned not in low, f"{where} contains advisory phrasing: {banned!r}"
    for leak in _IMPLEMENTATION:
        assert leak not in low, f"{where} leaks an implementation note: {leak!r}"
    m = _DECISION_ID.search(text)
    assert not m, f"{where} leaks a decision ID into served copy: {m.group(0)!r}"


@pytest.mark.parametrize("where,text", _verbatim(), ids=[w for w, _ in _verbatim()])
def test_verbatim_commitments_are_advice_free(where: str, text: str):
    """The part of the bar the verbatim block IS held to — and it is the part that matters most.

    The exemption covers decision IDs and implementation notes. It does NOT cover advice: the
    Commitments are the product's no-advice promise, and a promise that advised would be
    self-refuting.
    """
    low = text.lower()
    for banned in _ADVISORY:
        assert banned not in low, f"{where} contains advisory phrasing: {banned!r}"


# --- The exemption, asserted rather than assumed ----------------------------------------------- #
# An exemption nobody measures is a hole. These two tests pin its EXACT extent, so the day the
# collision is resolved — or the day it grows — the suite says so instead of staying quiet.

_EXEMPT_IDS = {"commitment:4", "commitment:5", "commitment:6", "commitment:7"}
_EXEMPT_IMPL = {"commitment:1"}


def test_the_verbatim_exemption_is_exactly_as_wide_as_recorded():
    """If this goes RED the collision CHANGED — which is news either way, and news that must be
    read rather than patched.

    Narrower means PRODUCT-SPEC.md §3 was amended and the exemption should SHRINK or be deleted
    (delete the entries here, and delete the module docstring's flag with them). Wider means new
    verbatim text arrived carrying new violations, and the 0a flag needs re-raising with the owner
    before it ships.
    """
    ids = {w for w, t in _verbatim() if _DECISION_ID.search(t)}
    impl = {w for w, t in _verbatim()
            if any(leak in t.lower() for leak in _IMPLEMENTATION)}
    assert ids == _EXEMPT_IDS, (
        f"the decision-ID exemption no longer matches the shipped Commitments.\n"
        f"  recorded: {sorted(_EXEMPT_IDS)}\n  actual  : {sorted(ids)}\n"
        f"See this module's docstring — this is the owner's 0a call, not a test to update."
    )
    assert impl == _EXEMPT_IMPL, (
        f"the implementation-note exemption no longer matches.\n"
        f"  recorded: {sorted(_EXEMPT_IMPL)}\n  actual  : {sorted(impl)}"
    )


def test_no_authored_string_relies_on_the_exemption():
    """The exemption's containment, stated as a test.

    The failure mode of every named exemption is drift: a new string gets written near the exempt
    one, inherits its latitude by proximity, and nobody notices because the suite is green. The
    authored corpus is held to the full bar above; this asserts the two corpora do not overlap, so
    "authored" can never quietly acquire an exempt member.
    """
    assert not ({w for w, _ in _authored()} & {w for w, _ in _verbatim()})
