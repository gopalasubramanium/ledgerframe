# SPDX-License-Identifier: AGPL-3.0-or-later
"""What the AI actually RETRIEVES from the help corpus — pinned against ranker drift.

AI-surfaces §9(a), which reframed the question it was given. The kickoff asked *"how do we
keep the grounding corpus fresh / regenerate it"*. The survey (§0-I) found there is nothing
to regenerate: the corpus is a **Python literal** (`app/services/help.py:14`), read by
`search_help` with **no cache, no index and no build step**. There is no cache, so there is
no drift to flush.

**The real exposure is the RANKER.** One source serves both the Help page and the AI
(`help.py:4-6`), but the AI consumes it *through* `search_help`, so **a ranking change is a
grounding change**. That is not hypothetical — `help.py:1311-1315` records it happening:
adding the *"What LedgerFrame is"* entry made `search_help("what is xirr")` return the
platform blurb first, so *"the AI would have answered a question about XIRR with the platform
blurb"*. `page-help.md:1084-1086` records the same event in the sharpest available words —
**"a ranking regression reached the AI before it reached the page."**

`tests/integration/test_help.py:147` asserts only that *some* help fact comes back. It would
have stayed green through that entire regression.

So this file pins **what the AI is actually handed**, for a fixed question set, on the AI's own
path (`help_facts` → `search_help(limit=3)`) rather than the page's. A ranker edit that changes
the AI's view now reds **on the AI path, by name**.

**Content currency is pinned here too**, because the corpus moved twice under this milestone's
feet: the Help milestone **rewrote the knowledge base** (the v1 entries were factually wrong)
and the Legal milestone **renamed Product Guarantees → Product Commitments** and rewrote the
entry-and-gate truth. `CURRENT.md:63-76` rules that no pre-2026-07-19 review of AI help-grounding
is still valid. These tests read the **post-rewrite, post-rename** corpus and fail if retired
vocabulary reappears in what the model is fed.

⚠ **Scope, stated rather than implied.** This pins the SERVER ranker, which is the one feeding
the model. `page-help.md:1071-1078` records that a **second, client-side ranker** exists for the
page's type-ahead and that the two *"could drift"*. This file cannot see that one; the divergence
remains a known, recorded gap and not something these greens should be read as covering.
"""

from __future__ import annotations

import pytest

from app.ai.tools import help_facts

# (question, entry id the AI must be handed). Chosen for what they protect, not for coverage:
#   - xirr        — the RECORDED regression (§0-I). A definition question must retrieve the
#                   definition, not the platform blurb.
#   - commitments — post-RENAME content (Legal milestone).
#   - acceptance  — post-LEGAL content: the gate is new truth the corpus has to carry.
#   - net worth   — the headline figure; the most consequential thing to mis-ground.
#   - allocation  — a "how do I" against a page entry, the shape most likely to be out-ranked
#                   by a glossary definition (the coverage-vs-tier case help.py:1338 documents).
RETRIEVAL_PINS = [
    ("what is xirr", "term-xirr-twr"),
    ("what are the product commitments", "page-legal"),
    ("why do I have to accept terms", "page-legal"),
    ("what is net worth", "page-net-worth"),
    ("how do I set a target allocation", "page-policy"),
]


def _retrieved_titles(question: str) -> list[str]:
    """The help titles the AI is handed — its own path, not the page's."""
    return [f.label.removeprefix("Help · ") for f in help_facts(question)]


def _titles_by_id() -> dict[str, str]:
    from app.services.help import HELP

    return {e["id"]: e["title"] for e in HELP}


@pytest.mark.parametrize("question,entry_id", RETRIEVAL_PINS, ids=[q for q, _ in RETRIEVAL_PINS])
def test_the_ai_retrieves_the_right_help_entry(question: str, entry_id: str):
    titles = _titles_by_id()
    assert entry_id in titles, (
        f"pinned entry id {entry_id!r} no longer exists in the corpus. Fix the pin deliberately — "
        "an entry disappearing is itself a grounding change."
    )
    expected = titles[entry_id]
    retrieved = _retrieved_titles(question)

    assert expected in retrieved, (
        f"For {question!r} the AI is handed {retrieved} — {expected!r} is not among them.\n"
        "A ranking change IS a grounding change: the AI reads the corpus through search_help, so "
        "this is the model being fed different facts, not a search-results cosmetic. "
        "help.py:1311-1315 records this exact failure reaching the AI before the page."
    )


def test_the_xirr_regression_specifically_cannot_recur():
    """The recorded incident, pinned as itself rather than as a general principle.

    Adding *"What LedgerFrame is"* once made `search_help("what is xirr")` return the platform
    blurb FIRST. `_STOPWORDS` fixed it. This asserts the ordering, not merely the membership —
    the entry the AI leads with is the one it answers from.
    """
    retrieved = _retrieved_titles("what is xirr")
    assert retrieved, "the AI was handed no help facts for a definition question"
    assert "xirr" in retrieved[0].lower() or "twr" in retrieved[0].lower(), (
        f"the AI leads with {retrieved[0]!r} for 'what is xirr'. This is help.py:1311-1315's "
        "regression recurring — the AI would answer a question about XIRR from whatever this is."
    )


def test_the_ai_is_never_fed_retired_vocabulary():
    """Post-RENAME currency, at the point the model actually sees the words.

    The Legal milestone renamed Product Guarantees → Product Commitments. `help.py` is not just
    page copy — `tools.py:145` feeds it to the model as fact, so a stale entry here teaches the
    AI retired vocabulary that then comes back out in prose no copy review reads.

    ⚠ The ordinary English word is NOT retired (GLOSSARY's deprecated table carves this out
    explicitly: *"indicative, not a guarantee of sale price or timing"* is plain English). Only
    the TERM is — hence the specific phrases rather than a bare word match.
    """
    questions = [q for q, _ in RETRIEVAL_PINS] + [
        "what will ledgerframe never do", "what are my rights", "is my data private",
    ]
    for question in questions:
        for fact in help_facts(question):
            body = fact.value.lower()
            for retired in ("product guarantees", "product guarantee ", "guarantee 5", "guarantee 7"):
                assert retired not in body, (
                    f"For {question!r} the AI is fed {fact.label!r}, whose body contains retired "
                    f"vocabulary {retired!r}. The rename was 2026-07-20 (page-legal §11-1); the "
                    "corpus the model reads must carry it too."
                )


def test_the_ai_receives_the_BODY_PROJECTION_ONLY():
    """The grounding projection is `body` — pinned, because changing it is a grounding change.

    ⚠ **FOUND WRITING THIS FILE, and it is not what it looks like.** The first draft asserted
    that the Legal facts the AI receives mention acceptance. It went RED — and the entry is not
    stale. `page-legal`'s **`interpret`** field carries a full, ruled *"Accepting the terms"*
    section (declining is a real answer; a changed document re-asks; a reset clears acceptance).
    **The AI never sees a word of it.**

    `search_help` projects to `(id, category, title, body)` (`help.py:1358-1359`) and `help_facts`
    hands `body` alone to the model (`tools.py:145-148`). So *"one source serves both consumers"*
    (`help.py:4-6`) is true of the SOURCE and not of the VIEW: the Help page renders the whole
    entry, and the model is given its opening paragraph. Asked *"why do I have to accept terms"*,
    the AI is handed a paragraph about the document's six-article STRUCTURE while the corpus holds
    the actual answer one field away.

    **This test does not fix that, and deliberately does not assert a richer projection** — what
    the fact pack should carry is a scoping decision (pack size, and the validation contract's
    verbatim-quoting surface both change with it), and it is filed as an open item in
    `CURRENT.md` rather than settled by whoever happened to be writing a test. What it DOES do is
    pin the projection as it stands, so widening it becomes a deliberate, visible change to what
    the model is fed rather than a side effect of editing a search function.
    """
    from app.services.help import HELP

    bodies = {e["title"]: e["body"] for e in HELP}
    facts = help_facts("what is xirr")
    assert facts, "no help facts retrieved"
    for fact in facts:
        title = fact.label.removeprefix("Help · ")
        assert title in bodies, f"retrieved an entry not in the corpus: {title!r}"
        assert fact.value.strip(), f"{title!r} was handed to the model as an empty fact"
        # Markup-stripped body, not the raw one — help.py:1352-1357's reason: the AI reads
        # strings, never styling, so markers must not reach it.
        assert "**" not in fact.value, (
            f"{title!r} reached the model with markdown markers in it — help.py:1352-1357."
        )


def test_the_retrieval_pins_are_not_vacuous():
    """Pinned against going blind: empty retrieval would satisfy nothing above except by luck."""
    for question, _ in RETRIEVAL_PINS:
        assert _retrieved_titles(question), (
            f"help_facts({question!r}) returned nothing — the AI's help grounding is silently "
            "off, and the pins above would be asserting membership in an empty list."
        )
