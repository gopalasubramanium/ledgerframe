# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §20 (F-9) — AMFI's portal page was diagnosed as a malformed report.

Owner evidence (`instrument_acquisitions` + `ledgerframe.log`, 04:19 and 12:19): both held funds
failed with *"AMFI history report: parsed 0 row(s) (< 1) — refusing a truncated/malformed payload"*.

The F-4 integrity refusal is CORRECT and is left untouched. The defect is upstream: the fetcher
handed it a payload that was never a report. Captured live with the exact fetcher request shape —
AMFI intermittently answers **HTTP 200, `content-type: text/plain`**, with its XHTML frameset
portal page ("View/Download NAV History", 13,694 bytes) instead of the CSV. That page contains
``;`` characters, so the guard's "has data lines" precondition held, it parsed to zero records, and
the guard reported *malformed* — an alarming, wrong diagnosis of a transient provider hiccup.

Verified live during the investigation:
  * the same window served **73 MB of real data** on later attempts (transient, not a data problem);
  * that window genuinely contains **61 rows for scheme 102000 and 75 for 145834** — so the windows
    were never the problem;
  * timing in the DB (both funds failing ~16 s apart) matches a small fast payload, not a 21 s
    70 MB download — i.e. the funds died on their FIRST window and lost all remaining ones.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

# The captured shape of AMFI's portal-page response (prefix of the real 13,694-byte body, which is
# served with content-type text/plain). The trailing markup is what made it look like a data
# payload to the old guard: these lines contain ';'.
AMFI_PORTAL_PAGE = (
    '\r\n\r\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" '
    '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">\r\n'
    "<!-- XHTML 1.0 Frameset --><!-- !DOCTYPE html Only (X)HTML5 -->\r\n"
    "<html>\r\n<head><title>\r\n\tView/Download NAV History\r\n</title>"
    '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\r\n'
    '<style type="text/css">body { font-family: Arial; margin: 0; }</style>\r\n'
    "</head>\r\n<body>&nbsp;</body>\r\n</html>\r\n"
)

# A real report, same shape as the live payload's opening lines.
def _report(code: str = "102000", days: int = 3) -> str:
    head = ("Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;"
            "Net Asset Value;Repurchase Price;Sale Price;Date\r\n\r\n"
            "Open Ended Schemes ( Growth )\r\n\r\nSome Mutual Fund\r\n")
    rows = "".join(
        f"{code};SOME FUND - GROWTH;INF001;;{45 + n}.1000;;;"
        f"{(date(2026, 3, 2) + timedelta(days=n)).strftime('%d-%b-%Y')}\r\n"
        for n in range(days))
    return head + rows


# --------------------------------------------------------------------------- #
# The classifier — the piece the fetcher was missing
# --------------------------------------------------------------------------- #
def test_portal_page_is_not_recognised_as_a_report():
    """RED: nothing distinguished 'not the report' from 'a broken report'."""
    from app.providers.market.amfi import looks_like_nav_report

    assert looks_like_nav_report(AMFI_PORTAL_PAGE) is False
    assert looks_like_nav_report(_report()) is True


async def test_the_portal_page_would_still_trip_the_integrity_guard(session):
    """The guard is CORRECT and deliberately unchanged — this reproduces the owner's exact error
    from the exact payload, documenting why that payload must never reach it. If this ever stops
    raising, the F-4 protection has been weakened rather than correctly bypassed."""
    from app.services.amfi import ingest_nav_history
    from app.services.ingest_guard import IngestIntegrityError

    with pytest.raises(IngestIntegrityError) as ei:
        await ingest_nav_history(session, 1, "102000", AMFI_PORTAL_PAGE, verify=True)

    assert "parsed 0 row(s)" in str(ei.value)
    assert "truncated/malformed" in str(ei.value)


async def test_fetcher_retries_then_raises_a_named_transient_error(monkeypatch):
    """The fetcher must retry (the condition is transient) and, if it persists, raise its OWN named
    error — never hand a non-report downstream to be misdiagnosed."""
    from app.providers.market import amfi

    calls: list = []

    class _Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            calls.append(params)
            return _Resp(AMFI_PORTAL_PAGE)

    async def _client(*a, **kw): return _Client()
    monkeypatch.setattr(amfi, "egress_client", _client)
    monkeypatch.setattr(amfi, "NAV_HISTORY_RETRY_BACKOFF_S", 0)

    with pytest.raises(amfi.AmfiReportUnavailable) as ei:
        await amfi.fetch_nav_history(date(2026, 4, 20), date(2026, 7, 18))

    assert len(calls) == amfi.NAV_HISTORY_ATTEMPTS, "the transient case must be retried"
    assert "portal page" in str(ei.value)
    assert "malformed" not in str(ei.value).lower(), "this is not a malformed-report diagnosis"


async def test_fetcher_returns_the_report_when_a_retry_succeeds(monkeypatch):
    """Transient means recoverable: a portal page followed by the real report must succeed."""
    from app.providers.market import amfi

    payloads = [AMFI_PORTAL_PAGE, _report()]

    class _Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            return _Resp(payloads.pop(0))

    async def _client(*a, **kw): return _Client()
    monkeypatch.setattr(amfi, "egress_client", _client)
    monkeypatch.setattr(amfi, "NAV_HISTORY_RETRY_BACKOFF_S", 0)

    text = await amfi.fetch_nav_history(date(2026, 4, 20), date(2026, 7, 18))
    assert text.startswith("Scheme Code;")


# --------------------------------------------------------------------------- #
# The acquisition loop — one bad window must not cost the fund
# --------------------------------------------------------------------------- #
async def _seed_fund(session, *, code: str = "102000", bought: date = date(2025, 6, 25)):
    from app.models import Account, AssetClass, Instrument, InstrumentIdentifier, TxnType
    from app.models import Transaction as Txn
    from app.services.portfolio import rebuild_holdings_from_transactions

    acc = Account(name="A", currency="INR")
    session.add(acc)
    await session.flush()
    fund = Instrument(symbol=code, currency="INR", pricing_currency="INR",
                      asset_class=AssetClass.MUTUAL_FUND)
    session.add(fund)
    await session.flush()
    session.add(InstrumentIdentifier(instrument_id=fund.id, id_type="amfi_code", value=code))
    session.add(Txn(account_id=acc.id, instrument_id=fund.id, type=TxnType.BUY,
                    ts=datetime(bought.year, bought.month, bought.day, tzinfo=UTC),
                    quantity=Decimal("10"), price=Decimal("45"), currency="INR"))
    await session.flush()
    await rebuild_holdings_from_transactions(session)
    await session.commit()
    return fund


async def test_one_unavailable_window_does_not_discard_the_whole_fund(session, monkeypatch):
    """RED (the owner's loss): the first bad window raised out of the chunk loop, so every
    remaining window was skipped and the fund recorded zero rows. Good windows must still land."""
    from sqlalchemy import select

    from app.models import PriceHistory
    from app.providers.market.amfi import AmfiReportUnavailable
    from app.services import acquire

    fund = await _seed_fund(session, bought=date(2025, 1, 6))
    seen: list = []

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        seen.append((a, b))
        if len(seen) == 1:                       # the FIRST window fails, as it did live
            raise AmfiReportUnavailable("AMFI served its portal page instead of the report")
        return _report()
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    await acquire.acquire_prices(session, "INR")

    assert len(seen) > 1, "the loop stopped at the first bad window"
    rows = (await session.execute(
        select(PriceHistory).where(PriceHistory.instrument_id == fund.id))).scalars().all()
    assert rows, "the windows that DID succeed were discarded"


async def test_a_partially_unavailable_fund_reports_an_honest_partial_note(session, monkeypatch):
    """The outcome must say what is missing and why — not a clean success, not a malformed refusal."""
    from app.models import InstrumentAcquisition
    from app.providers.market.amfi import AmfiReportUnavailable
    from app.services import acquire

    fund = await _seed_fund(session, bought=date(2025, 1, 6))
    n = 0

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        nonlocal n
        n += 1
        if n == 1:
            raise AmfiReportUnavailable("AMFI served its portal page instead of the report")
        return _report()
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    await acquire.acquire_prices(session, "INR")

    outcome = await session.get(InstrumentAcquisition, fund.id)
    assert outcome is not None and outcome.rows > 0
    assert outcome.reason and "windows unavailable" in outcome.reason
    assert "malformed" not in outcome.reason.lower()


async def test_a_genuinely_empty_window_is_not_a_malformed_refusal(session, monkeypatch):
    """The owner's pin: a valid report that simply holds no rows for THIS scheme (an old window,
    before the fund reported) degrades quietly — it is not evidence of a broken payload."""
    from app.services import acquire

    fund = await _seed_fund(session, bought=date(2026, 1, 5))

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        return _report(code="999999")             # a real report, other schemes only
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    await acquire.acquire_prices(session, "INR")

    from app.models import InstrumentAcquisition
    outcome = await session.get(InstrumentAcquisition, fund.id)
    assert outcome is not None and outcome.rows == 0
    assert "malformed" not in (outcome.reason or "").lower()
    assert "truncated" not in (outcome.reason or "").lower()


async def test_history_windows_start_at_the_instruments_own_first_transaction(session, monkeypatch):
    """F-9 waste: the global earliest transaction made a fund bought in 2025 request windows back
    to 2019 — 31 whole-market downloads of ~70 MB each, and 26 extra chances to hit the transient
    failure. Windows must start where the holding does."""
    from app.models import Account, AssetClass, Instrument, TxnType
    from app.models import Transaction as Txn
    from app.services import acquire

    # An OLD holding of a different instrument sets the book's global earliest date.
    acc = (await session.execute(__import__("sqlalchemy").select(Account))).scalars().first()
    if acc is None:
        acc = Account(name="A", currency="INR")
        session.add(acc)
        await session.flush()
    old = Instrument(symbol="OLDEQ", currency="INR", pricing_currency="INR",
                     asset_class=AssetClass.EQUITY)
    session.add(old)
    await session.flush()
    session.add(Txn(account_id=acc.id, instrument_id=old.id, type=TxnType.BUY,
                    ts=datetime(2019, 1, 18, tzinfo=UTC), quantity=Decimal("1"),
                    price=Decimal("10"), currency="INR"))
    await session.flush()
    fund = await _seed_fund(session, bought=date(2026, 5, 1))

    windows: list = []

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        windows.append(a)
        return _report()
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    async def _noop_equity(sess, symbol, interval, start, end, **kw):
        return []
    monkeypatch.setattr("app.services.market.get_history_cached", _noop_equity)

    await acquire.acquire_prices(session, "INR")

    assert windows, "the fund was never fetched"
    assert min(windows) >= date(2026, 5, 1), (
        f"windows began {min(windows)} — before the fund was ever held")
    assert fund is not None


# ---------------------------------------------------------------------------------------------
# F-9c (R-43 §21) — two tuning-class defects found on the owner's live re-run.
# ---------------------------------------------------------------------------------------------


def test_the_amfi_history_stage_gets_its_own_larger_read_timeout():
    """RED: the whole-market history payload is ~70 MB; on a slow AMFI server it cannot clear a
    60 s wall, so every window died as a ReadTimeout. The AMFI stage carries its own timeout —
    and the outer wall covers the fetcher's full retry budget, so it never cancels a live retry."""
    from app.providers.market.amfi import NAV_HISTORY_ATTEMPTS
    from app.services import acquire

    assert acquire.AMFI_HISTORY_TIMEOUT_S == 180
    assert acquire.AMFI_HISTORY_TIMEOUT_S > acquire.PRICE_FETCH_TIMEOUT_S, (
        "the AMFI-specific timeout must exceed the general price-fetch wall")
    assert acquire.AMFI_HISTORY_WALL_S >= acquire.AMFI_HISTORY_TIMEOUT_S * NAV_HISTORY_ATTEMPTS, (
        "the outer wall would cancel the fetcher's own retry mid-flight")
    # F-4 discipline stands elsewhere: the general wall is unchanged.
    assert acquire.PRICE_FETCH_TIMEOUT_S == 60


async def test_the_amfi_history_timeout_is_the_one_actually_sent(session, monkeypatch):
    """A constant nobody passes is not a timeout. The fetcher must receive it."""
    from app.services import acquire

    await _seed_fund(session, bought=date(2026, 5, 1))
    sent: list = []

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        sent.append(timeout)
        return _report()
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    await acquire.acquire_prices(session, "INR")

    assert sent, "the fund was never fetched"
    assert set(sent) == {acquire.AMFI_HISTORY_TIMEOUT_S}


async def test_a_timed_out_fetch_degrades_honestly_by_name(session, monkeypatch, caplog):
    """RED (owner evidence, 13:33:30/13:34:01): the log line read "degrading honestly:" with an
    EMPTY reason, because a bare asyncio TimeoutError stringifies to "". The DB row carried the
    named reason; the log did not. Both must name it — and the run must survive to retry later."""
    import logging

    from app.models import InstrumentAcquisition
    from app.services import acquire

    fund = await _seed_fund(session, bought=date(2026, 5, 1))

    async def _fetch(a, b, mf=None, tp=None, timeout=30.0):
        raise TimeoutError()                      # str() == "" — exactly the live case
    monkeypatch.setattr("app.services.acquire.fetch_nav_history", _fetch)

    with caplog.at_level(logging.WARNING, logger="ledgerframe"):
        await acquire.acquire_prices(session, "INR")

    line = next(r.getMessage() for r in caplog.records if "degrading honestly" in r.getMessage())
    assert not line.rstrip().endswith("degrading honestly:"), "the reason is still empty"
    assert "timed out" in line

    outcome = await session.get(InstrumentAcquisition, fund.id)
    assert outcome is not None and outcome.ok is False
    assert outcome.reason and "timed out" in outcome.reason
    # The log and the row say the SAME thing — one reason, two places.
    assert outcome.reason in line
