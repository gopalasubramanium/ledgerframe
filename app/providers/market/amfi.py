# SPDX-License-Identifier: AGPL-3.0-or-later
"""AMFI NAV adapter (opt-in) — official Indian mutual-fund NAVs.

Source: the AMFI daily ``NAVAll.txt`` (public, no key). This module is the *parser*
+ HTTP fetch only; storage/lookup lives in ``app/services/amfi.py``. Design rules
from the product spec:

- Use the official source only; never scrape a fund website.
- Parse scheme code, ISIN(s), name, NAV and date safely; a missing / ``N.A.`` /
  non-positive NAV yields ``nav=None`` (defunct/unpriced) — never a fabricated value.
- Match a holding by **exact AMFI scheme code or verified ISIN** — never by a
  similar name.
- Deterministic, fixture-driven tests; no network in normal test runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# AMFI moved this file to the `portal.` host; the old `www.` URL 302-redirects here.
# We point at the canonical host AND follow redirects, so it works either way.
NAV_ALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

# Section-header lines (no ';') that name a scheme *category* rather than a fund house.
_CATEGORY_PREFIXES = ("Open Ended", "Close Ended", "Closed Ended", "Interval")


@dataclass(frozen=True)
class SchemeNav:
    code: str
    name: str
    nav: Decimal | None          # None = N.A./defunct/unpriced (never fabricated)
    nav_date: date | None
    isin_growth: str | None = None
    isin_reinvest: str | None = None
    fund_house: str | None = None
    category: str | None = None


def _parse_nav(text: str) -> Decimal | None:
    text = (text or "").strip()
    if not text or text.upper() in {"N.A.", "NA", "-", "0", "0.0", "0.00"}:
        return None
    try:
        v = Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return v if v > 0 else None


def _parse_date(text: str) -> date | None:
    text = (text or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_nav_all(text: str) -> list[SchemeNav]:
    """Parse the AMFI NAVAll.txt payload into scheme records. Robust to the file's
    section headers, blank lines and defunct (N.A.) NAVs."""
    out: list[SchemeNav] = []
    fund_house: str | None = None
    category: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Scheme Code;"):
            continue
        if ";" not in line:
            if line.startswith(_CATEGORY_PREFIXES):
                category = line
            else:
                fund_house = line
            continue
        parts = line.split(";")
        if len(parts) < 6:
            continue
        code, isin_g, isin_r, name, nav_s, date_s = (p.strip() for p in parts[:6])
        if not code or not code.isdigit():
            continue
        out.append(SchemeNav(
            code=code, name=name,
            nav=_parse_nav(nav_s), nav_date=_parse_date(date_s),
            isin_growth=isin_g or None, isin_reinvest=isin_r or None,
            fund_house=fund_house, category=category,
        ))
    return out


async def fetch_nav_all(timeout: float = 20.0) -> str:
    """Download the official NAVAll.txt (opt-in; never called in tests). Whitelisted
    host only — no arbitrary URLs."""
    import httpx

    headers = {"User-Agent": "LedgerFrame/1.0 (+local)", "Accept": "text/plain, */*"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        r = await client.get(NAV_ALL_URL)
        r.raise_for_status()
        return r.text
