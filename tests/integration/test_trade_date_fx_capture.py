# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 4.2 Unit B — capture the trade-date FX rate at commit (write-only), with a
trade-date-proximity guard.

A new transaction stores the live native→base rate ONLY when its date is today in UTC — the
one day on which today's live rate genuinely IS the trade-date rate. A backdated trade
(typed into the API form or imported from a CSV of historical trades) stores NULL:
"trade-date FX unavailable", because we have no rate for that past day and must never stamp
today's rate on an older trade. Same-currency is always 1 (domestic, R11); an unresolvable
rate is NULL and never blocks the commit. Nothing reads these columns yet (Unit C), so no
money figure changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.models import Transaction
from app.services import fx
from app.services.csv_import import import_transactions_csv


def _foreign_ccy() -> tuple[str, str]:
    """(base, a currency guaranteed different from base). Robust to other tests that change
    the base currency setting (e.g. to USD)."""
    base = get_settings().base_currency.upper()
    return base, ("EUR" if base != "EUR" else "USD")


_TODAY = datetime.now(UTC).date()
_PAST = datetime(2019, 3, 1, tzinfo=UTC)   # a backdated trade — no historical rate exists


# --------------------------------------------------------------------------- #
# capture_rate() — the shared helper, deterministic via monkeypatch.
# --------------------------------------------------------------------------- #
async def test_capture_same_currency_is_one_even_when_backdated():
    # Domestic rate is 1 on every date — the proximity guard must NOT null it.
    rate, base = await fx.capture_rate("SGD", "SGD", _PAST)
    assert rate == Decimal("1") and base == "SGD"
    assert isinstance(rate, Decimal)  # Decimal precision, not float


async def test_capture_today_foreign_returns_decimal_rate(monkeypatch):
    async def fake_rate(_a, _b):
        return Decimal("1.35")
    monkeypatch.setattr(fx, "get_rate", fake_rate)
    now = datetime.now(UTC)
    rate, base = await fx.capture_rate("USD", "SGD", now)
    assert rate == Decimal("1.35") and base == "SGD"
    assert isinstance(rate, Decimal)


async def test_capture_backdated_foreign_skips_provider_and_is_null(monkeypatch):
    """The guard short-circuits BEFORE any provider call — proving a past-dated foreign
    trade is never stamped with today's (would-be-available) rate."""
    called = False

    async def recorder(_a, _b):
        nonlocal called
        called = True
        return Decimal("1.35")
    monkeypatch.setattr(fx, "get_rate", recorder)

    assert await fx.capture_rate("USD", "SGD", _PAST) == (None, None)
    assert called is False  # provider was never consulted for a backdated trade


async def test_capture_today_provider_failure_is_unavailable(monkeypatch):
    async def boom(_a, _b):
        raise RuntimeError("provider down")
    monkeypatch.setattr(fx, "get_rate", boom)
    assert await fx.capture_rate("USD", "SGD", datetime.now(UTC)) == (None, None)


async def test_capture_today_unresolved_fallback_one_is_unavailable(monkeypatch):
    # get_rate degrades to exactly 1 when it can't resolve a cross rate; that sentinel must
    # be treated as unavailable, not stored as a real (fabricated) rate.
    async def fallback(_a, _b):
        return Decimal("1")
    monkeypatch.setattr(fx, "get_rate", fallback)
    assert await fx.capture_rate("USD", "SGD", datetime.now(UTC)) == (None, None)


# --------------------------------------------------------------------------- #
# commit_import (CSV) — one of the two commit sites.
# --------------------------------------------------------------------------- #
async def test_import_today_captures_trade_date_fx(session):
    """Today-dated foreign row → a captured cross rate + fx_base = base; domestic row → 1."""
    from app.providers.market import reset_provider
    reset_provider()          # deterministic mock provider
    fx.clear_cache()          # no stale cross-rate from another test

    base, foreign = _foreign_ccy()
    csv_bytes = (
        "date,symbol,type,quantity,price,fees,currency,note\n"
        f"{_TODAY.isoformat()},AAPL,buy,10,100,0,{foreign},foreign\n"
        f"{_TODAY.isoformat()},DBS,buy,5,30,0,{base},domestic\n"
    ).encode()
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 2
    txns = {t.currency: t for t in (await session.execute(select(Transaction))).scalars().all()}

    assert txns[foreign].fx_to_base is not None and txns[foreign].fx_to_base > 0
    assert txns[foreign].fx_to_base != Decimal("1")   # a genuine cross rate, not the sentinel
    assert isinstance(txns[foreign].fx_to_base, Decimal)
    assert txns[foreign].fx_base == base
    assert txns[base].fx_to_base == Decimal("1") and txns[base].fx_base == base


async def test_import_backdated_foreign_is_null_domestic_is_one(session):
    """A CSV of historical trades must NOT fabricate rates: a backdated foreign row → NULL,
    while a backdated domestic row is still 1 (domestic is 1 at every date)."""
    from app.providers.market import reset_provider
    reset_provider()
    fx.clear_cache()

    base, foreign = _foreign_ccy()
    csv_bytes = (
        "date,symbol,type,quantity,price,fees,currency,note\n"
        f"2019-03-01,AAPL,buy,10,100,0,{foreign},old-foreign\n"
        f"2019-03-01,DBS,buy,5,30,0,{base},old-domestic\n"
    ).encode()
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 2
    txns = {t.currency: t for t in (await session.execute(select(Transaction))).scalars().all()}

    # Backdated foreign → honestly unavailable, no fabricated rate.
    assert txns[foreign].fx_to_base is None and txns[foreign].fx_base is None
    # Backdated domestic → still exactly 1 (date-proximity does not apply to same-currency).
    assert txns[base].fx_to_base == Decimal("1") and txns[base].fx_base == base


async def test_import_today_fx_failure_stores_null_and_still_commits(session, monkeypatch):
    async def boom(_a, _b):
        raise RuntimeError("provider down")
    monkeypatch.setattr(fx, "get_rate", boom)

    _base, foreign = _foreign_ccy()
    csv_bytes = ("date,symbol,type,quantity,price,fees,currency,note\n"
                 f"{_TODAY.isoformat()},AAPL,buy,10,100,0,{foreign},x\n").encode()
    assert (await import_transactions_csv(session, csv_bytes))["imported"] == 1  # not blocked
    t = (await session.execute(select(Transaction))).scalars().one()
    assert t.fx_to_base is None and t.fx_base is None  # honest-unavailable, not fabricated


# --------------------------------------------------------------------------- #
# add_transaction (API) — the other commit site.
# --------------------------------------------------------------------------- #
async def test_add_transaction_today_captures_trade_date_fx(app_client):
    from app.db.base import get_sessionmaker

    base, foreign = _foreign_ccy()
    r = await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "AAPL", "type": "buy", "ts": f"{_TODAY.isoformat()}T00:00:00Z",
        "quantity": 3, "price": 100, "currency": foreign,
    })
    assert r.status_code == 200
    async with get_sessionmaker()() as s:
        txn = await s.get(Transaction, r.json()["transaction_id"])
    assert txn.fx_to_base is not None and txn.fx_to_base > 0 and txn.fx_to_base != Decimal("1")
    assert txn.fx_base == base and isinstance(txn.fx_to_base, Decimal)


async def test_add_transaction_backdated_is_null(app_client):
    """A backdated foreign trade entered via the API stores NULL — no fabricated rate."""
    from app.db.base import get_sessionmaker

    _base, foreign = _foreign_ccy()
    r = await app_client.post("/api/v1/portfolio/transactions", json={
        "symbol": "AAPL", "type": "buy", "ts": "2019-03-01T00:00:00Z",
        "quantity": 3, "price": 100, "currency": foreign,
    })
    assert r.status_code == 200
    async with get_sessionmaker()() as s:
        txn = await s.get(Transaction, r.json()["transaction_id"])
    assert txn.fx_to_base is None and txn.fx_base is None
