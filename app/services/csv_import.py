# SPDX-License-Identifier: AGPL-3.0-or-later
"""Safe CSV import for transactions and holdings.

Hardening:
- Hard size cap (rejects oversized uploads before parsing).
- Row cap to bound memory.
- Formula-injection guard on every cell (leading = + - @ tab/CR are neutralised)
  for both import sanity and to keep round-tripped exports safe.
- Strict typing via the money helpers; bad rows are skipped and reported.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.money import D, money
from app.models import Account, AssetClass, AuditEvent, Instrument, Transaction, TxnType
from app.services import fx

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
_DANGEROUS_PREFIX = ("=", "+", "-", "@", "\t", "\r")

TRANSACTION_TEMPLATE = (
    # Optional trailing columns classify a NEW instrument so it lands in the right
    # allocation/region. All are optional — leave blank to auto-detect from the symbol;
    # unknown values are ignored (never fail a row). Supported optional columns:
    #   asset_class (equity|etf|mutual_fund|crypto|bond|commodity|…), country (ISO-2),
    #   exchange, name, source, identifier_type (isin|amfi_code|coingecko_id|…),
    #   identifier_value, valuation_method, statement_date.
    "date,symbol,type,quantity,price,fees,taxes,currency,note,asset_class,country\n"
    "2024-01-15,AAPL,buy,10,185.50,1.00,0.00,USD,Initial purchase,equity,US\n"
    "2024-03-01,AAPL,dividend,0,0,0,0,USD,Q1 dividend,,\n"
    "2024-05-01,RELIANCE.NSE,buy,20,2900,10,0,INR,,equity,IN\n"
    "2024-05-10,BTC,buy,0.1,64000,5,0,USD,,crypto,\n"
    "2024-06-20,AAPL,sell,5,210.00,1.00,0.50,USD,Trim position,,\n"
)


def sanitize_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection (used on export too)."""
    if value and value[0] in _DANGEROUS_PREFIX:
        return "'" + value
    return value


def _clean(value: str | None) -> str:
    return (value or "").strip()


async def import_transactions_csv(
    session: AsyncSession, content: bytes, account_id: int | None = None
) -> dict:
    """Legacy CSV import endpoint — now routes through the **safe v2 commit** so it gets
    the same classification (asset_class/country/exchange), optional-metadata columns,
    duplicate detection, formula-injection guard and idempotency. Kept only as a
    backward-compatible wrapper; the UI uses preview → commit."""
    r = await commit_import(session, content, account_id)
    # Preserve the legacy response shape.
    return {
        "imported": r.get("imported", 0), "errors": r.get("errors", [])[:50],
        "batch": r.get("batch"), "account_id": account_id,
        "skipped_duplicates": r.get("skipped_duplicates", 0),
    }


# --------------------------------------------------------------------------- #
# CSV v2: two-step import — preview (validate/dedupe, NO mutation) then commit
# (idempotent by content hash, atomic). Safe for statements & manual assets.
# --------------------------------------------------------------------------- #
def _batch_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def _fingerprint(f: dict) -> str:
    return "|".join(str(f[k]) for k in ("date", "symbol", "type", "quantity", "price"))


def _validate_row(row: dict, i: int) -> dict:
    """Validate one CSV row without touching the DB. Returns a preview record."""
    out: dict[str, Any] = {"row": i, "ok": False, "error": None, "duplicate": False}
    try:
        ttype = TxnType(_clean(row.get("type")).lower())
        date = _clean(row.get("date"))
        datetime.fromisoformat(date)  # validates
        # Optional metadata columns (added post-v1.10) so imported instruments are
        # classified. Unknown/blank values are ignored (never fail a row).
        raw_ac = _clean(row.get("asset_class")).lower()
        try:
            asset_class = AssetClass(raw_ac).value if raw_ac else ""
        except ValueError:
            asset_class = ""  # unknown class → ignore, don't fail the row
        # More optional metadata (all ignored if blank/unknown, never fail a row).
        from app.schemas.common import ValuationMethod
        raw_vm = _clean(row.get("valuation_method")).lower()
        try:
            valuation_method = ValuationMethod(raw_vm).value if raw_vm else ""
        except ValueError:
            valuation_method = ""
        out.update({
            "date": date, "type": ttype.value, "symbol": _clean(row.get("symbol")).upper(),
            "quantity": str(D(_clean(row.get("quantity")) or 0)),
            "price": str(D(_clean(row.get("price")) or 0)),
            "fees": str(D(_clean(row.get("fees")) or 0)),
            "taxes": str(D(_clean(row.get("taxes")) or 0)),
            "currency": (_clean(row.get("currency")) or "USD").upper(),
            "note": sanitize_cell(_clean(row.get("note")))[:255],
            "asset_class": asset_class,
            "country": _clean(row.get("country")).upper()[:2],
            "exchange": _clean(row.get("exchange")).upper()[:20] or None,
            "name": sanitize_cell(_clean(row.get("name")))[:160] or None,
            "source": _clean(row.get("source")).lower()[:40] or None,
            "identifier_type": _clean(row.get("identifier_type")).lower()[:24] or None,
            "identifier_value": _clean(row.get("identifier_value"))[:64] or None,
            "valuation_method": valuation_method,
            "statement_date": _clean(row.get("statement_date"))[:12] or None,
            "ok": True,
        })
    except (ValueError, KeyError) as exc:
        out["error"] = str(exc)[:160]
    return out


async def _existing_fingerprints(session: AsyncSession, limit: int = 20000) -> set[str]:
    rows = (await session.execute(
        # §3.5 R10: a soft-deleted row's fingerprint must not block re-importing it
        # (otherwise undo→re-import is defeated). Excluded here just like the batch guard.
        select(Transaction).where(Transaction.deleted_at.is_(None)).order_by(Transaction.ts.desc()).limit(limit)
    )).scalars().all()
    out: set[str] = set()
    for t in rows:
        sym = ""
        if t.instrument_id:
            instr = await session.get(Instrument, t.instrument_id)
            sym = instr.symbol if instr else ""
        ttype = t.type.value if hasattr(t.type, "value") else str(t.type)
        out.add("|".join([t.ts.date().isoformat(), sym, ttype, str(D(t.quantity)), str(D(t.price))]))
    return out


async def _batch_already_imported(session: AsyncSession, batch_hash: str) -> bool:
    row = (await session.execute(
        # §3.5 R10: a soft-deleted import must not block re-importing the same file.
        select(Transaction.id).where(Transaction.import_batch == batch_hash)
        .where(Transaction.deleted_at.is_(None)).limit(1)
    )).first()
    return row is not None


async def preview_import(session: AsyncSession, content: bytes) -> dict:
    """Parse + validate + flag duplicates. Makes NO changes. The UI shows this so the
    user confirms before anything is written."""
    if len(content) > MAX_BYTES:
        raise ValueError(f"file too large (max {MAX_BYTES // 1024 // 1024} MB)")
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    batch = _batch_hash(content)
    already = await _batch_already_imported(session, batch)
    existing = await _existing_fingerprints(session)
    seen: set[str] = set()
    rows, valid, errors, dups = [], 0, 0, 0
    for i, row in enumerate(reader, start=2):
        if i - 1 > MAX_ROWS:
            break
        rec = _validate_row(row, i)
        if rec["ok"]:
            fp = _fingerprint(rec)
            rec["duplicate"] = fp in existing or fp in seen
            seen.add(fp)
            valid += 1
            dups += 1 if rec["duplicate"] else 0
        else:
            errors += 1
        rows.append(rec)
    return {
        "batch": batch, "already_imported": already,
        "summary": {"total": len(rows), "valid": valid, "errors": errors,
                    "duplicates": dups, "new": valid - dups},
        "rows": rows[:500],
    }


async def commit_import(
    session: AsyncSession, content: bytes, account_id: int | None = None,
    skip_duplicates: bool = True,
) -> dict:
    """Idempotent, atomic commit. Re-importing the same file is a no-op (matched by
    content hash). Only valid, non-duplicate rows are written."""
    if len(content) > MAX_BYTES:
        raise ValueError(f"file too large (max {MAX_BYTES // 1024 // 1024} MB)")
    batch = _batch_hash(content)
    if await _batch_already_imported(session, batch):
        return {"ok": True, "skipped": True, "imported": 0, "batch": batch,
                "note": "This exact file was already imported — no changes made."}

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    account = await _ensure_account(session, account_id)
    base = get_settings().base_currency  # §4.2: base to capture each row's trade-date FX against
    existing = await _existing_fingerprints(session)
    seen: set[str] = set()
    imported, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        if i - 1 > MAX_ROWS:
            errors.append(f"stopped at row cap {MAX_ROWS}")
            break
        rec = _validate_row(row, i)
        if not rec["ok"]:
            errors.append(f"row {i}: {rec['error']}")
            continue
        fp = _fingerprint(rec)
        if skip_duplicates and (fp in existing or fp in seen):
            skipped += 1
            continue
        seen.add(fp)
        ttype = TxnType(rec["type"])
        sym = rec["symbol"]
        instrument = await _ensure_instrument(
            session, sym, asset_class=rec.get("asset_class") or None,
            country=rec.get("country") or None, name=rec.get("name"),
            exchange=rec.get("exchange") or (sym.split(".")[-1] if "." in sym else None),
        ) if sym else None
        # Apply optional metadata columns (identifier / valuation method / source) —
        # each best-effort; a bad identifier is reported, it never fails the import.
        if instrument is not None:
            if rec.get("valuation_method"):
                instrument.valuation_method = rec["valuation_method"]
            if rec.get("source"):
                # §5: validate the source override; a bad value is reported as a row
                # error and left unset rather than stored as an authoritative source.
                from app.services.market import validate_source_override
                await session.flush()  # ensure instrument.id + class are queryable
                normalized, err = await validate_source_override(session, instrument, rec["source"])
                if err:
                    errors.append(f"row {rec['row']}: source '{rec['source']}' ignored — {err}")
                else:
                    instrument.source_override = normalized
            if rec.get("identifier_type") and rec.get("identifier_value"):
                from app.services.identity import DuplicateIdentifierError, set_identifier
                try:
                    await set_identifier(session, instrument.id, rec["identifier_type"], rec["identifier_value"])
                except DuplicateIdentifierError as exc:
                    errors.append(f"row {rec['row']}: {exc}")
        qty, price = D(rec["quantity"]), D(rec["price"])
        fees, taxes = D(rec["fees"]), D(rec["taxes"])
        ts = datetime.fromisoformat(rec["date"]).replace(tzinfo=UTC)
        # §4.2 Unit B: capture the live native→base rate as trade-date FX (write only). The
        # proximity guard NULLs backdated rows (a CSV of historical trades), so import never
        # fabricates a rate either.
        fx_to_base, fx_base = await fx.capture_rate(rec["currency"], base, ts)
        session.add(Transaction(
            account_id=account.id, instrument_id=instrument.id if instrument else None,
            type=ttype, ts=ts,
            quantity=qty, price=price, fees=fees, taxes=taxes,
            amount=money(_cash_impact(ttype, qty, price, fees + taxes)),
            currency=rec["currency"], note=rec["note"] or None, import_batch=batch,
            fx_to_base=fx_to_base, fx_base=fx_base,
        ))
        imported += 1
    session.add(AuditEvent(category="mutation", action="import_csv",
                           detail=f"batch={batch} imported={imported} skipped={skipped}"))
    await session.flush()
    return {"ok": True, "imported": imported, "skipped_duplicates": skipped,
            "errors": errors[:50], "batch": batch, "account_id": account.id}


def _cash_impact(ttype: TxnType, qty: Decimal, price: Decimal, fees: Decimal) -> Decimal:
    gross = qty * price
    if ttype in (TxnType.BUY,):
        return -(gross + fees)
    if ttype in (TxnType.SELL, TxnType.DIVIDEND, TxnType.INTEREST, TxnType.DEPOSIT):
        return gross - fees if ttype == TxnType.SELL else gross or -fees
    if ttype in (TxnType.WITHDRAWAL, TxnType.FEE):
        return -(gross + fees) if gross else -fees
    return D(0)


async def _ensure_account(session: AsyncSession, account_id: int | None) -> Account:
    if account_id:
        acc = await session.get(Account, account_id)
        if acc:
            return acc
    acc = (await session.execute(select(Account).limit(1))).scalars().first()
    if acc is None:
        acc = Account(name="Imported", kind="brokerage")
        session.add(acc)
        await session.flush()
    return acc


async def _ensure_instrument(
    session: AsyncSession,
    symbol: str,
    *,
    asset_class=None,
    name: str | None = None,
    exchange: str | None = None,
    country: str | None = None,
) -> Instrument:
    """Find-or-create an instrument, classifying it on create (asset class / country /
    name) and backfilling those fields on an existing bare row. Prevents user-added
    holdings from defaulting to an unclassified US equity."""
    from app.core.symbols import country_for_symbol, currency_for_symbol
    from app.models import AssetClass
    from app.services.identity import classify_defaults

    ac = asset_class if isinstance(asset_class, AssetClass) else (
        AssetClass(asset_class) if asset_class else AssetClass.EQUITY
    )
    ccy = currency_for_symbol(symbol, exchange) or "USD"
    ctry = country or country_for_symbol(symbol, exchange, ccy)

    instr = (
        await session.execute(select(Instrument).where(Instrument.symbol == symbol))
    ).scalars().first()
    if instr is None:
        instr = Instrument(
            symbol=symbol, name=name or symbol, currency=ccy,
            exchange=exchange, country=ctry, asset_class=ac,
            **classify_defaults(ac, is_manual_price=False, currency=ccy),
        )
        session.add(instr)
        await session.flush()
        return instr
    # Backfill missing metadata on an existing bare instrument (never overwrite).
    if name and (not instr.name or instr.name == instr.symbol):
        instr.name = name
    if ctry and not instr.country:
        instr.country = ctry
    if exchange and not instr.exchange:
        instr.exchange = exchange
    if asset_class is not None and (instr.asset_class is None or instr.asset_class == AssetClass.EQUITY):
        instr.asset_class = ac
    return instr
