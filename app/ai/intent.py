# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic intent classification (B3) — THE SINGLE INTENT AUTHORITY.

Rule-based first — the model never invents the intent. Used to shape which facts are
gathered and how the answer is framed. Unknown questions fall back to a general
portfolio+market fact pack.

R-54 §9-A (owner ruling, chat 2026-07-20) — ONE ROUTER
------------------------------------------------------
This module is now the **only** intent authority in the product. Until R-54 Phase 0-1 there were
**TWO routers that did not share code and could disagree** (r54 §0-A): this one, and an independent
set of eight boolean flags inside ``gather_facts`` computed from bare SUBSTRING membership
(``any(w in q for w in ws)``). ``classify_intent`` was consulted twice, and only to *add* facts —
it never governed the branching it appears to govern.

The substring matcher was not merely imprecise, it was reliably wrong: ``"los"`` matched *closed*
and *lost*, ``"own"`` matched *download* and *downgrade*, ``"mov"`` matched *remove*. A user asking
*"how do I download my data"* was handed their gainers and detractors as the grounded basis of the
answer — and because the pack is capped at 20 (`tools._dedupe`), those junk facts **evicted real
ones**. Determinism is tier-1's whole claim; a deterministically wrong route is worse than a noisy
one.

*Owner:* "A single source of truth for intent resolution prevents contradictory states;
deterministic matching is superior to probabilistic guessing for core navigation."

So: the enum below is closed and authoritative, every rule matches on **word boundaries**, and
``INTENT_FACT_SOURCES`` is the **one table** from which ``gather_facts`` derives what it gathers.
A miss returns ``UNKNOWN_GENERAL_QUESTION`` and the caller falls back to the ratified shape —
**tier-1 never guesses**.

**The enum must be able to express everything the flags could**, or consolidating would silently
drop a capability: that is why ``WATCHLIST_QUESTION`` exists here (the old ``is_watch`` flag had no
intent) and why several rules gained the vocabulary their corresponding flag carried.
"""

from __future__ import annotations

import enum
import re


class Intent(str, enum.Enum):
    PORTFOLIO_OVERVIEW = "portfolio_overview"
    PORTFOLIO_MOVEMENT = "portfolio_movement"
    ALLOCATION_ANALYSIS = "allocation_analysis"
    EXPOSURE_ANALYSIS = "exposure_analysis"
    RISK_CONCENTRATION = "risk_concentration"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    INSTRUMENT_QUESTION = "instrument_question"
    MARKET_REGION_QUESTION = "market_region_question"
    NEWS_QUESTION = "news_question"
    PRICING_HEALTH_QUESTION = "pricing_health_question"
    DATA_QUALITY_QUESTION = "data_quality_question"
    SETTINGS_HELP = "settings_help"
    EXPLANATION_OF_METRIC = "explanation_of_metric"
    DAILY_BRIEFING = "daily_briefing"
    AI_NEWS_BRIEFING = "ai_news_briefing"
    # R-54 Phase 0-1: the old `is_watch` flag had no intent, so the enum could not express a
    # watchlist question. An authority that cannot name a route cannot own it.
    WATCHLIST_QUESTION = "watchlist_question"
    UNKNOWN_GENERAL_QUESTION = "unknown_general_question"


# Ordered (first match wins) keyword rules. Specific intents before generic ones.
#
# EVERY PATTERN MATCHES ON WORD BOUNDARIES (R-54 §9-A). A rule that can fire on a fragment inside
# an unrelated word is not a deterministic rule; see the module docstring for what that cost.
_RULES: list[tuple[Intent, re.Pattern]] = [
    (Intent.DAILY_BRIEFING, re.compile(r"\b(daily briefing|morning briefing|before (?:market )?open|start of day|brief me)\b", re.I)),
    (Intent.AI_NEWS_BRIEFING, re.compile(r"\bnews briefing|summar(?:ise|ize) (?:the )?news\b", re.I)),
    (Intent.PRICING_HEALTH_QUESTION, re.compile(r"\b(stale|unpriced|unavailable|no price|not priced|needs? mapping|pricing health)\b", re.I)),
    (Intent.DATA_QUALITY_QUESTION, re.compile(r"\b(missing|what data|data quality|needs? (?:attention|mapping|fixing)|unmapped|which .* need)\b", re.I)),
    (Intent.NEWS_QUESTION, re.compile(r"\b(news|headline|happening|announced|report(?:ed)?)\b", re.I)),
    (Intent.EXPLANATION_OF_METRIC, re.compile(r"\b(what (?:is|does|are)|explain|why does .* show|meaning of)\b.*\b(xirr|twr|nav|official nav|entitlement|valuation|sharpe|drawdown|volatility|canonical|delayed|stale)\b", re.I)),
    (Intent.ALLOCATION_ANALYSIS, re.compile(r"\b(allocation|asset mix|breakdown|diversif|weighting|how much .* in)\b", re.I)),
    (Intent.EXPOSURE_ANALYSIS, re.compile(r"\bexpos|how exposed|geograph|currency exposure|region(?:al)? (?:exposure|mix)\b", re.I)),
    (Intent.RISK_CONCENTRATION, re.compile(r"\b(risk|concentrat|biggest position|largest holding|too much in|over.?weight)\b", re.I)),
    (Intent.PERFORMANCE_ANALYSIS, re.compile(r"\b(perform|return|xirr|twr|vs (?:benchmark|s&p|index)|how (?:am i|have i) (?:doing|done)|cagr)\b", re.I)),
    # Watchlist before the market/movement rules — "what's on my watchlist today" is a watchlist
    # question, not a movement one. (R-54 Phase 0-1: absorbs the old `is_watch` flag.)
    (Intent.WATCHLIST_QUESTION, re.compile(r"\bwatch ?lists?\b", re.I)),
    # Region/market questions before generic movement — "US market today" is a market
    # question, not "what moved in my portfolio".
    # R-54 Phase 0-1: gained the vocabulary the old `is_market` flag carried (plain "market(s)",
    # "indices", the remaining index names) so the single authority is at least as capable as the
    # two routers it replaces — otherwise consolidating would quietly narrow the product.
    (Intent.MARKET_REGION_QUESTION, re.compile(r"\b(india|singapore|us market|u\.s\.? market|nifty|sensex|s&p|s ?& ?p|nasdaq|dow|sti|markets?|indices|nikkei|ftse|hang seng|stoxx|wall street|global market|what happened in (?:the )?(?:us|india|singapore|market))\b", re.I)),
    (Intent.PORTFOLIO_MOVEMENT, re.compile(r"\b(what (?:changed|moved)|why (?:is|am|are).*(?:up|down)|today|move[dr]?|gainers?|losers?|detractors?|drove)\b", re.I)),
    (Intent.SETTINGS_HELP, re.compile(r"\b(how do i|settings|configure|set up|enable|api key|provider|map (?:a )?fund|add (?:a )?holding)\b", re.I)),
    # R-54 Phase 0-1: gained the vocabulary the old `is_networth`/`is_holdings` flags carried
    # (assets, liabilities, cash, wealth, positions) — same reason as the market rule above.
    (Intent.PORTFOLIO_OVERVIEW, re.compile(r"\b(portfolio|net ?worth|total value|holdings?|positions?|assets?|liabilit\w*|cash|wealth|biggest|largest|my (?:money|wealth|assets))\b", re.I)),
]

# A bare ticker or "how is X doing" → instrument question.
_TICKER = re.compile(r"\b([A-Z]{2,6}(?:\.[A-Z]{1,4})?)\b")


# ── THE ONE TABLE (R-54 §9-A) ────────────────────────────────────────────────────────────────
#
# `gather_facts` derives every fact source it gathers from THIS MAPPING and from nothing else.
# Before Phase 0-1 it computed eight independent booleans from its own word lists, which is what
# made it a second router; now the flags are a projection of the intent, and the two can no longer
# disagree BECAUSE THERE IS ONLY ONE. That is a structural guarantee, not a test.
#
# Sources are named by the fact-gathering coroutine they select in `app/ai/tools.py`:
#   market · news · networth · perf · alloc · movers · holdings · watch
#
# Deliberately EMPTY sets are as meaningful as populated ones and are written out rather than
# omitted, so a reader can tell "this intent gathers nothing extra" from "someone forgot a row":
#   * PRICING_HEALTH / DATA_QUALITY  — served by `data_quality_facts`, prepended separately
#   * SETTINGS_HELP / EXPLANATION_OF_METRIC — served by `help_facts`, prepended separately
#   * INSTRUMENT_QUESTION — served by `instrument_deep_facts` off the resolved symbols
#   * UNKNOWN_GENERAL_QUESTION — the honest miss: no source is guessed at; the caller's
#     ratified fallback supplies the portfolio anchor. TIER-1 NEVER GUESSES.
INTENT_FACT_SOURCES: dict[Intent, frozenset[str]] = {
    Intent.PORTFOLIO_OVERVIEW: frozenset({"networth", "holdings"}),
    Intent.PORTFOLIO_MOVEMENT: frozenset({"movers"}),
    Intent.ALLOCATION_ANALYSIS: frozenset({"alloc"}),
    Intent.EXPOSURE_ANALYSIS: frozenset({"alloc"}),
    # Risk asks two questions at once — how volatile, and how concentrated — so it draws on the
    # performance metrics AND the allocation split. The old flags reached both by accident (the
    # word "risk" sat in `is_perf`); this reaches both on purpose.
    Intent.RISK_CONCENTRATION: frozenset({"perf", "alloc"}),
    Intent.PERFORMANCE_ANALYSIS: frozenset({"perf"}),
    Intent.MARKET_REGION_QUESTION: frozenset({"market"}),
    Intent.NEWS_QUESTION: frozenset({"news"}),
    Intent.WATCHLIST_QUESTION: frozenset({"watch"}),
    # A briefing is broad BY DEFINITION — it is the one intent for which breadth is the answer.
    Intent.DAILY_BRIEFING: frozenset({"networth", "movers", "market", "news"}),
    Intent.AI_NEWS_BRIEFING: frozenset({"news"}),
    Intent.PRICING_HEALTH_QUESTION: frozenset(),
    Intent.DATA_QUALITY_QUESTION: frozenset(),
    Intent.SETTINGS_HELP: frozenset(),
    Intent.EXPLANATION_OF_METRIC: frozenset(),
    Intent.INSTRUMENT_QUESTION: frozenset(),
    Intent.UNKNOWN_GENERAL_QUESTION: frozenset(),
}


def fact_sources(intent: Intent) -> frozenset[str]:
    """The fact sources an intent selects — the ONLY input to `gather_facts`' branching.

    Raises on an unregistered intent rather than returning an empty set: a new enum member that
    nobody mapped is a routing hole, and a silent empty set would present it as a deliberate
    "gathers nothing". Guarded for coverage by `tests/unit/test_intent_routing_table.py`.
    """
    try:
        return INTENT_FACT_SOURCES[intent]
    except KeyError:  # pragma: no cover - the coverage guard makes this unreachable
        raise KeyError(
            f"{intent!r} has no row in INTENT_FACT_SOURCES. Every Intent must declare its "
            f"sources — an unmapped intent routes to nothing and looks deliberate."
        ) from None


def classify_intent(question: str) -> Intent:
    """Best-effort intent for a natural-language question (deterministic)."""
    q = (question or "").strip()
    if not q:
        return Intent.UNKNOWN_GENERAL_QUESTION
    for intent, pat in _RULES:
        if pat.search(q):
            return intent
    # "How is <TICKER> doing" / "<TICKER> performance" without portfolio words.
    if _TICKER.search(q) and re.search(r"\b(how is|doing|price|performance|chart|trading)\b", q, re.I):
        return Intent.INSTRUMENT_QUESTION
    return Intent.UNKNOWN_GENERAL_QUESTION
