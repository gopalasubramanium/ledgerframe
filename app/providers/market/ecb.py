# SPDX-License-Identifier: AGPL-3.0-or-later
"""ECB reference-FX adapter (opt-in) — daily euro reference rates.

Source: the European Central Bank's ``eurofxref-daily.xml`` (public, no key). All
rates are EUR-based (EUR → X). Any pair is derived: EUR→X is **direct**, X→EUR is
**inverse**, and X→Y is **triangulated** via EUR. Used only as a *reference* FX
fallback for portfolio translation — never a trading quote — and never overrides a
fresher entitled provider rate.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from app.core.egress import egress_client

DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def parse_ecb_daily(xml_text: str) -> tuple[str | None, dict[str, Decimal]]:
    """Parse the ECB daily XML into ``(as_of, {CCY: EUR->CCY rate})`` (incl EUR=1)."""
    rates: dict[str, Decimal] = {"EUR": Decimal("1")}
    as_of: str | None = None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None, rates
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag != "Cube":
            continue
        if el.get("time"):
            as_of = el.get("time")
        cur, rate = el.get("currency"), el.get("rate")
        if cur and rate:
            try:
                d = Decimal(rate)
            except (InvalidOperation, ValueError):
                continue
            if d > 0:
                rates[cur.upper()] = d
    return as_of, rates


async def fetch_ecb_daily(timeout: float = 20.0) -> str:

    async with await egress_client("ECB FX refresh", timeout=timeout, headers={"User-Agent": "LedgerFrame/1.0 (+local)"}, follow_redirects=True) as c:
        r = await c.get(DAILY_URL)
        r.raise_for_status()
        return r.text
