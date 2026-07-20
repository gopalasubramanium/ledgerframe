# SPDX-License-Identifier: AGPL-3.0-or-later
"""INFLECTIONS MUST ROUTE — the guard for a regression this milestone SHIPPED.

WHAT HAPPENED, PLAINLY
----------------------
R-54 Phase 0-1 replaced ``gather_facts``' substring matcher with word-boundary rules. Several
alternations in ``_RULES`` were **stems** written for that substring matcher — ``perform``,
``return``, ``concentrat``, ``diversif`` — and under ``\\b(...)\\b`` the **trailing** boundary
requires the word to end there. So the stems stopped matching their own inflections:

    "How is my portfolio performing?"  → PORTFOLIO_OVERVIEW   (not PERFORMANCE_ANALYSIS)
    "What is my concentration?"        → UNKNOWN_GENERAL      (not RISK_CONCENTRATION)
    "How diversified am I?"            → UNKNOWN_GENERAL      (not ALLOCATION_ANALYSIS)

**Six of nine probe questions misrouted, and the 1982-test suite stayed green.** The single
performance test survived because its question — *"How is my portfolio performing and what's the
risk?"* — also contains the word **"risk"**, so it reached performance facts through
``RISK_CONCENTRATION`` instead. *A test that can reach its assertion by two routes cannot tell you
that one of them broke.*

Found at Phase 0-4 while asking a different question entirely (whether XIRR reaches the pack), which
is the honest account: it was not caught by the delta that introduced it, nor by its gates.

THE GUARD
---------
Every stem is pinned **through an inflected form**, not through the bare stem the rule literally
contains. A probe that used the bare word would pass against the broken regex and prove nothing.
"""

from __future__ import annotations

import pytest

from app.ai.intent import Intent, classify_intent

# (question, expected intent) — every question uses an INFLECTED form of a stem in `_RULES`.
PROBES = [
    ("How is my portfolio performing?", Intent.PERFORMANCE_ANALYSIS),
    ("What is my performance?", Intent.PERFORMANCE_ANALYSIS),
    ("Are my returns good?", Intent.PERFORMANCE_ANALYSIS),
    ("What were the returns last year?", Intent.PERFORMANCE_ANALYSIS),
    ("How diversified am I?", Intent.ALLOCATION_ANALYSIS),
    ("Show me diversification", Intent.ALLOCATION_ANALYSIS),
    ("Is my portfolio concentrated?", Intent.RISK_CONCENTRATION),
    ("What is my concentration?", Intent.RISK_CONCENTRATION),
    ("Are there risks I should know about?", Intent.RISK_CONCENTRATION),
    ("What is moving in my portfolio?", Intent.PORTFOLIO_MOVEMENT),
    ("Any movement today?", Intent.PORTFOLIO_MOVEMENT),
    ("Any headlines?", Intent.NEWS_QUESTION),
    # Added because the blindness pin below CAUGHT it unprobed — which is the pin working.
    ("What are my liabilities?", Intent.PORTFOLIO_OVERVIEW),
    # Unchanged behaviour, kept so the fix cannot be "achieved" by loosening everything.
    ("How exposed am I to India?", Intent.EXPOSURE_ANALYSIS),
    ("Show my allocation", Intent.ALLOCATION_ANALYSIS),
    ("What moved today?", Intent.PORTFOLIO_MOVEMENT),
]


@pytest.mark.parametrize("question,expected", PROBES)
def test_an_inflected_stem_routes_to_its_intent(question, expected):
    actual = classify_intent(question)
    assert actual is expected, (
        f"{question!r} routed to {actual.name}, expected {expected.name}. A stem in `_RULES` has "
        f"lost its `\\w*` — the trailing `\\b` then requires an exact word match and the "
        f"inflection silently misroutes."
    )


def test_the_substring_hazards_are_still_refused():
    """The fix must not be achieved by loosening back toward substring matching.

    `\\w*` opens a stem at the END only; it stays anchored at the start. These are the Phase 0-1
    specimens, re-asserted here so the two corrections cannot cancel each other out.
    """
    assert classify_intent("How do I download my data?") is not Intent.PORTFOLIO_MOVEMENT
    assert classify_intent("What is a closed-end fund?") is not Intent.PORTFOLIO_MOVEMENT
    assert classify_intent("Can I open the export in a spreadsheet?") is Intent.UNKNOWN_GENERAL_QUESTION


def test_every_stem_in_the_rules_is_probed():
    """Blindness pin: a stem nobody probes is a stem that can break silently.

    Scans `_RULES` for alternatives ending in `\\w*` and requires each to appear — inflected — in
    at least one probe above. Adding a stem without a probe fails here rather than in production.
    """
    import re

    from app.ai.intent import _RULES

    stems = set()
    for _intent, pattern in _RULES:
        stems.update(re.findall(r"([a-z]{4,})\\w\*", pattern.pattern))

    assert stems, "no `\\w*` stems found in _RULES — the parser has drifted and this guard is blind"

    probed = " ".join(q.lower() for q, _ in PROBES)
    unprobed = sorted(s for s in stems if s not in probed)
    assert not unprobed, (
        f"stems with no inflected probe: {unprobed}. Add one to PROBES — an unprobed stem is "
        f"exactly what broke at Phase 0-1 without any gate noticing."
    )
