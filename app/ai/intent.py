# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic intent classification (B3).

Rule-based first — the model never invents the intent. Used to shape which facts are
gathered and how the answer is framed. Unknown questions fall back to a general
portfolio+market fact pack.
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
    UNKNOWN_GENERAL_QUESTION = "unknown_general_question"


# Ordered (first match wins) keyword rules. Specific intents before generic ones.
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
    # Region/market questions before generic movement — "US market today" is a market
    # question, not "what moved in my portfolio".
    (Intent.MARKET_REGION_QUESTION, re.compile(r"\b(india|singapore|us market|u\.s\.? market|nifty|sensex|s&p|nasdaq|dow|sti|global market|what happened in (?:the )?(?:us|india|singapore|market))\b", re.I)),
    (Intent.PORTFOLIO_MOVEMENT, re.compile(r"\b(what (?:changed|moved)|why (?:is|am|are).*(?:up|down)|today|move[dr]?|gainers?|losers?|drove)\b", re.I)),
    (Intent.SETTINGS_HELP, re.compile(r"\b(how do i|settings|configure|set up|enable|api key|provider|map (?:a )?fund|add (?:a )?holding)\b", re.I)),
    (Intent.PORTFOLIO_OVERVIEW, re.compile(r"\b(portfolio|net worth|total value|holdings|my (?:money|wealth|assets))\b", re.I)),
]

# A bare ticker or "how is X doing" → instrument question.
_TICKER = re.compile(r"\b([A-Z]{2,6}(?:\.[A-Z]{1,4})?)\b")


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
