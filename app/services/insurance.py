# SPDX-License-Identifier: AGPL-3.0-or-later
"""Insurance (W3) — a first-class protection register.

Reporting only: records, totals and renewal reminders. It never rates whether cover is
adequate and never suggests buying or switching. cash_value is reported here but is NOT
injected into net worth (isolated register, by design). All base-currency totals use
*current* FX and are clearly caveated.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.money import format_money_display
from app.models import InsurancePolicy
from app.services import fx

POLICY_TYPES = ["term_life", "whole_life", "health", "critical_illness", "disability",
                "personal_accident", "property", "motor", "travel", "other"]
FREQUENCIES = ["monthly", "quarterly", "annual", "single"]
# Fixed vocab (page-insurance §9-10) — served via /refdata; enforced in _apply exactly like
# policy_type/premium_frequency (unknown → default). Only `active` policies count toward the totals.
POLICY_STATUSES = ["active", "lapsed", "expired"]
_FREQ_MULT = {"monthly": 12, "quarterly": 4, "annual": 1, "single": 0}
_RENEWAL_SOON_DAYS = 60


def _dec(v) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


async def _to_base(amount: Decimal | None, ccy: str, base: str) -> Decimal:
    if not amount:
        return Decimal("0")
    if ccy == base:
        return amount
    try:
        return await fx.convert(amount, ccy, base)
    except Exception:  # noqa: BLE001 — best-effort; fall back to raw
        return amount


def _serialize(r: InsurancePolicy) -> dict:
    docs = []
    if r.documents:
        try:
            docs = json.loads(r.documents)
        except (ValueError, TypeError):
            docs = []
    return {
        "id": r.id, "name": r.name, "insurer": r.insurer, "policy_type": r.policy_type,
        "policy_number": r.policy_number, "insured_person": r.insured_person,
        # Money is served as a display string (D-105); the raw float stays alongside for callers that
        # still read it (e.g. Net worth's exclusion line reads the total's display). None passes through
        # so a missing cash value / premium stays honestly empty, never a fabricated 0 (Guarantee 3).
        "cover_amount": float(r.cover_amount or 0),
        "cover_amount_display": format_money_display(r.cover_amount or Decimal("0")),
        "currency": r.currency,
        "cash_value": (float(r.cash_value) if r.cash_value is not None else None),
        "cash_value_display": format_money_display(r.cash_value),
        "premium": (float(r.premium) if r.premium is not None else None),
        "premium_display": format_money_display(r.premium),
        "premium_frequency": r.premium_frequency,
        "start_date": r.start_date, "renewal_date": r.renewal_date,
        "nominee": r.nominee, "linked_goal_id": r.linked_goal_id,
        "documents": docs, "notes": r.notes, "status": r.status,
    }


_FIELDS = {"name", "insurer", "policy_type", "policy_number", "insured_person", "currency",
           "premium_frequency", "start_date", "renewal_date", "nominee", "linked_goal_id",
           "notes", "status"}
_DEC_FIELDS = {"cover_amount", "cash_value", "premium"}


_REQUIRED = {"name", "currency", "premium_frequency", "status"}


def _apply(p: InsurancePolicy, data: dict) -> None:
    for k, v in data.items():
        if k in _FIELDS:
            val = v.strip() if isinstance(v, str) else v
            if k in _REQUIRED and not val:
                continue  # never null a required column — keep existing/default
            setattr(p, k, val if val not in ("", None) else None)
        elif k in _DEC_FIELDS:
            setattr(p, k, _dec(v))
        elif k == "documents" and v is not None:
            p.documents = json.dumps(v)[:4000]
    if not p.policy_type or p.policy_type not in POLICY_TYPES:
        p.policy_type = "other"
    if p.premium_frequency not in FREQUENCIES:
        p.premium_frequency = "annual"
    if not p.status or p.status not in POLICY_STATUSES:
        p.status = "active"


async def create_policy(session: AsyncSession, data: dict) -> dict:
    p = InsurancePolicy(name=(data.get("name") or "Policy").strip()[:120], cover_amount=Decimal("0"),
                        currency=get_settings().base_currency)
    _apply(p, data)
    session.add(p)
    await session.flush()
    return _serialize(p)


async def update_policy(session: AsyncSession, pid: int, data: dict) -> dict:
    p = await session.get(InsurancePolicy, pid)
    if p is None:
        raise ValueError("policy not found")
    _apply(p, data)
    await session.flush()
    return _serialize(p)


async def delete_policy(session: AsyncSession, pid: int) -> None:
    p = await session.get(InsurancePolicy, pid)
    if p is not None:
        await session.delete(p)


async def insurance_report(session: AsyncSession) -> dict:
    base = get_settings().base_currency
    rows = (await session.execute(
        select(InsurancePolicy).order_by(InsurancePolicy.renewal_date.is_(None),
                                         InsurancePolicy.renewal_date))).scalars().all()
    today = datetime.now(UTC).date()
    by_type: dict[str, float] = {}
    total_cover = total_cash = total_prem = Decimal("0")
    active_count = 0
    upcoming: list[dict] = []
    for r in rows:
        if r.status != "active":
            continue
        active_count += 1
        cb = await _to_base(r.cover_amount, r.currency, base)
        by_type[r.policy_type] = by_type.get(r.policy_type, 0.0) + float(cb)
        total_cover += cb
        total_cash += await _to_base(r.cash_value, r.currency, base)
        mult = _FREQ_MULT.get(r.premium_frequency, 1)
        if r.premium and mult:
            total_prem += await _to_base(r.premium, r.currency, base) * mult
        if r.renewal_date:
            try:
                days = (date.fromisoformat(r.renewal_date) - today).days
                if days <= _RENEWAL_SOON_DAYS:
                    upcoming.append({"id": r.id, "name": r.name, "renewal_date": r.renewal_date, "days": days})
            except ValueError:
                pass
    return {
        "base_currency": base,
        "policies": [_serialize(r) for r in rows],   # ALL rows (inactive visible, excluded from totals)
        # `count` is ACTIVE policies only, so it agrees with the totals it rides beside on Net worth's
        # D-081 excluded line (page-insurance §9-10, Amendment A). The records table uses policies.length.
        "count": active_count,
        "total_cover": float(round(total_cover, 0)),
        "total_cover_display": format_money_display(total_cover),
        "total_cash_value": float(round(total_cash, 0)),
        "total_cash_value_display": format_money_display(total_cash),
        "total_annual_premium": float(round(total_prem, 0)),
        "total_annual_premium_display": format_money_display(total_prem),
        "cover_by_type": sorted(({"type": k, "value": round(v, 0),
                                  "value_display": format_money_display(v)} for k, v in by_type.items()),
                                key=lambda x: x["value"], reverse=True),
        "upcoming_renewals": sorted(upcoming, key=lambda x: x["days"]),
        "disclaimer": "Records and reminders only — not an assessment of whether your cover is "
                      "adequate, and not advice. Base-currency totals use current FX.",
    }


async def renewal_reminders(session: AsyncSession, within_days: int = 30) -> list[dict]:
    """Active policies whose renewal is due within ``within_days`` — for the review feed."""
    rows = (await session.execute(select(InsurancePolicy))).scalars().all()
    today = datetime.now(UTC).date()
    out = []
    for r in rows:
        if r.status != "active" or not r.renewal_date:
            continue
        try:
            days = (date.fromisoformat(r.renewal_date) - today).days
        except ValueError:
            continue
        if -3650 <= days <= within_days:
            out.append({"name": r.name, "renewal_date": r.renewal_date, "days": days})
    return out
