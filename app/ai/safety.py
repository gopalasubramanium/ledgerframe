# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI safety: prompt-injection resistance (B11) and answer validation (B7).

News headlines, RSS summaries and provider text are **untrusted input**. They are
treated as data, never instructions — embedded commands are neutralised before they
reach the model, and the model's answer is checked for recommendation language and
secret leakage before it is shown.
"""

from __future__ import annotations

import re

# Instructions an attacker might embed in a headline / summary to hijack the model.
_INJECTION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (?:all|any|the|your|previous|prior|above)[^.\n]*?(?:instructions?|prompts?|rules?)",
        r"disregard (?:all|any|the|previous|prior|above)[^.\n]*",
        r"forget (?:everything|all|your|the)[^.\n]*",
        r"(?:reveal|print|show|expose|leak|dump|output)[^.\n]*?(?:api[ _-]?key|secret|token|password|env(?:ironment)?|system prompt|credentials?)",
        r"you are now[^.\n]*",
        r"new (?:instructions?|system prompt|rules?)[:\s]",
        r"(?:^|\n)\s*(?:system|assistant|developer)\s*:",
        r"act as[^.\n]*",
        r"pretend (?:to be|you are)[^.\n]*",
        r"jailbreak|do anything now|DAN mode",
    )
]

# Language we must never emit as if it were our own recommendation (hard fail → fall
# back to the deterministic, fact-only answer).
_RECOMMENDATION = re.compile(
    r"\b(?:you should (?:buy|sell)|i(?:'d| would)? recommend|we recommend|"
    r"(?:strong|table[- ]pounding) buy|buy now|sell now|"
    r"(?:definitely|you must|you need to) (?:buy|sell)|"
    r"guaranteed (?:returns?|profit)|risk[- ]free (?:return|investment))\b",
    re.IGNORECASE,
)
# Anything resembling a leaked secret in the answer.
_SECRET = re.compile(
    r"(?:sk-[A-Za-z0-9]{12,}|api[ _-]?key\s*[:=]\s*\S|LEDGERFRAME_[A-Z_]+\s*=\s*\S|bearer\s+[A-Za-z0-9._-]{16,})",
    re.IGNORECASE,
)


def sanitize_untrusted(text: str | None) -> str:
    """Neutralise instructions embedded in untrusted content so it is treated as data.

    Strips HTML/script, drops embedded-instruction phrases, and caps length. Used on
    every news headline/summary before it enters a fact pack.
    """
    if not text:
        return ""
    t = re.sub(r"<[^>]*>", " ", text)                 # strip any HTML/script tags
    for pat in _INJECTION:
        t = pat.sub("[filtered]", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:300]


def validate_answer(answer: str) -> tuple[bool, str | None]:
    """Check a model-generated answer before showing it. Returns ``(ok, reason)``;
    ``ok=False`` means fall back to the deterministic fact-only answer.

    Hard fails only (to avoid false positives on legitimate answers): buy/sell/…
    recommendation language, and anything resembling a leaked secret.
    """
    if not answer or not answer.strip():
        return False, "empty answer"
    if _SECRET.search(answer):
        return False, "possible secret leakage"
    if _RECOMMENDATION.search(answer):
        return False, "unsupported buy/sell recommendation"
    return True, None


# --- grounded validation (B10 / §10) ---------------------------------------- #

# Uppercase tokens that look like tickers but are ordinary words/units (never blocked).
_TICKER_TOKEN = re.compile(r"\b[A-Z]{2,6}(?:\.[A-Z]{1,4})?\b")
_TICKER_OK = {
    "USD", "SGD", "INR", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "HKD", "CNY", "AED",
    "AI", "FX", "PL", "OK", "US", "UK", "EU", "CEO", "CFO", "IPO", "GDP", "FAQ", "ROI",
    "ETF", "NAV", "XIRR", "TWR", "RSI", "MA", "YTD", "EOD", "P", "E", "PE", "FD", "SIP",
    "AMFI", "ECB", "RBI", "MAS", "SGX", "NSE", "BSE", "MCX", "F", "O", "AND", "THE", "FOR",
}
_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)(\s*%)?")
# Claims LedgerFrame can never truthfully make (it is delayed / EOD, never real-time).
_REALTIME = re.compile(r"\b(real[\s-]?time|live (?:price|quote|data|feed))\b", re.IGNORECASE)


def _sig3(token: str) -> str:
    """First three significant digits of a number (formatting/rounding-insensitive)."""
    digits = token.replace(",", "").replace(".", "").lstrip("0")
    return digits[:3]


def _fact_text(facts) -> str:
    """Concatenate fact text. Accepts GroundingFact objects or plain strings (the
    Daily/News briefings pass pre-rendered fact strings)."""
    parts: list[str] = []
    for f in facts:
        if isinstance(f, str):
            parts.append(f)
        else:
            parts.append(f"{getattr(f, 'label', '')} {getattr(f, 'value', '')} "
                         f"{getattr(f, 'explanation', '') or ''}")
    return " ".join(parts)


def validate_grounded_answer(answer: str, facts, question: str = "") -> tuple[bool, str | None]:
    """Stricter grounded check used for Ask, Daily Briefing and News AI briefing.

    On top of :func:`validate_answer` (recommendations/secrets), conservatively blocks
    answers that introduce facts not in the pack: an unsupported money/percentage number,
    an unrelated ticker, an invented quoted headline, or a "real-time/live" claim (the
    data is delayed). On failure the caller shows the deterministic fact-only answer, so
    the checks err toward safety without ever fabricating.
    """
    ok, reason = validate_answer(answer)
    if not ok:
        return ok, reason

    if _REALTIME.search(answer):
        return False, "claims real-time/live data (prices are delayed)"

    facts_text = _fact_text(facts)
    q = question or ""

    # 1) Money/percentage numbers must trace to a fact (by leading significant digits).
    fact_sigs = {_sig3(m.group(1)) for m in _NUM.finditer(facts_text + " " + q)}
    fact_sigs.discard("")
    for m in _NUM.finditer(answer):
        token, pct = m.group(1), m.group(2)
        raw = token.replace(",", "")
        is_year = "." not in token and "," not in token and raw.isdigit() and 1900 <= int(raw) <= 2100
        significant = ("." in token or "," in token or bool(pct)) or (raw.isdigit() and len(raw) >= 4)
        if not significant or is_year:
            continue
        if _sig3(token) not in fact_sigs:
            return False, f"unsupported figure '{token.strip()}' not in the facts"

    # 2) Tickers mentioned must exist in the facts or the question.
    haystack = (facts_text + " " + q).upper()
    for tok in _TICKER_TOKEN.findall(answer):
        if tok in _TICKER_OK:
            continue
        if tok.upper() not in haystack:
            return False, f"unsupported symbol '{tok}' not in the facts"

    # 3) A long quoted string (a headline) must appear in the facts.
    for quoted in re.findall(r"[\"“”']([^\"“”']{25,})[\"“”']", answer):
        if quoted.strip().lower() not in facts_text.lower():
            return False, "quoted text not found in the facts"

    return True, None
