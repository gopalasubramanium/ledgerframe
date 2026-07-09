# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4: AMFI NAVAll.txt parser — deterministic, fixture-driven (no network)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.providers.market.amfi import parse_nav_all

FIXTURE = (Path(__file__).parents[1] / "fixtures" / "amfi_navall_sample.txt").read_text()


def test_parse_nav_all_extracts_schemes():
    schemes = {s.code: s for s in parse_nav_all(FIXTURE)}
    assert set(schemes) == {"119551", "119552", "118989", "100048", "999999"}

    s = schemes["119551"]
    assert s.nav == Decimal("512.3456")
    assert s.nav_date == date(2026, 7, 3)
    assert s.isin_growth == "INF209K01YM2"
    assert s.fund_house == "Aditya Birla Sun Life Mutual Fund"
    assert "Large Cap" in (s.category or "")

    # Different category/fund-house section is tracked correctly.
    assert schemes["100048"].fund_house == "HDFC Mutual Fund"
    assert "Liquid" in (schemes["100048"].category or "")


def test_defunct_or_na_nav_is_none_never_fabricated():
    schemes = {s.code: s for s in parse_nav_all(FIXTURE)}
    assert schemes["999999"].nav is None            # "N.A." → None
    assert schemes["119551"].nav is not None


def test_header_and_blank_lines_ignored():
    # The header row and section-header lines must not become scheme rows.
    codes = [s.code for s in parse_nav_all(FIXTURE)]
    assert "Scheme" not in "".join(codes)
    assert all(c.isdigit() for c in codes)


def test_nav_url_is_canonical_portal_host():
    # Regression: the old www.amfiindia.com URL 302-redirects; we must point at the
    # portal host (and follow redirects) so Refresh NAVs actually gets the data.
    from app.providers.market import amfi
    assert amfi.NAV_ALL_URL == "https://portal.amfiindia.com/spages/NAVAll.txt"
