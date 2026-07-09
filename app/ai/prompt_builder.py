# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prompt assembly (B6): build the model messages from the question, its classified
intent, and the grounded fact pack — using structured templates, not ad-hoc string
concatenation. The system policy lives in prompts.SYSTEM_PROMPT; here we add the
intent focus and the fact pack.
"""

from __future__ import annotations

from app.ai.intent import Intent
from app.ai.prompts import SYSTEM_PROMPT, render_facts
from app.schemas.ai import ChatMessage, GroundingFact

# A short, intent-specific instruction appended to the user turn so the answer is
# shaped to what was asked — without ever inventing facts.
_INTENT_FOCUS: dict[Intent, str] = {
    Intent.PORTFOLIO_OVERVIEW: "Give the headline value and how it's made up; keep it tight.",
    Intent.PORTFOLIO_MOVEMENT: "Explain what drove today's change and rank the biggest contributors/detractors.",
    Intent.ALLOCATION_ANALYSIS: "Summarise the asset mix; note where it's concentrated vs diversified.",
    Intent.EXPOSURE_ANALYSIS: "Quantify the exposure asked about (region/currency/class) as a share.",
    Intent.RISK_CONCENTRATION: "Point out the largest positions and any concentration, using the given weights.",
    Intent.PERFORMANCE_ANALYSIS: "Report the return/risk figures present and, if a benchmark is given, compare.",
    Intent.INSTRUMENT_QUESTION: "Give the price and today's move, then the trend/range and whether it's held.",
    Intent.MARKET_REGION_QUESTION: "Summarise the relevant indices and their moves for that region.",
    Intent.NEWS_QUESTION: "Summarise only the retrieved headlines; don't imply causation not in the facts.",
    Intent.PRICING_HEALTH_QUESTION: "List which holdings are stale/unpriced and the next action for each.",
    Intent.DATA_QUALITY_QUESTION: "List what's missing/stale/unmapped and the action to fix it.",
    Intent.EXPLANATION_OF_METRIC: "Explain the metric plainly using the value present; no advice.",
    Intent.DAILY_BRIEFING: "Give a concise start-of-day briefing from the facts (value, movers, context, data notes).",
    Intent.AI_NEWS_BRIEFING: "Summarise the retrieved headlines, grouped and deduped; note if none are relevant.",
}


def build_messages(
    question: str, intent: Intent, facts: list[GroundingFact]
) -> list[ChatMessage]:
    """The system policy + the fact pack + the user turn (with an intent focus line)."""
    focus = _INTENT_FOCUS.get(intent)
    user = question.strip()
    if focus:
        user += f"\n\n(Focus: {focus} Use only the FACTS. If something isn't in them, say so.)"
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="system", content=render_facts(facts)),
        ChatMessage(role="user", content=user),
    ]
