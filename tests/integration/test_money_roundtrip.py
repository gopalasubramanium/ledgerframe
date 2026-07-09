# SPDX-License-Identifier: AGPL-3.0-or-later
"""Money is stored as an EXACT Decimal on whatever backend the suite runs against.

Runs against SQLite by default and against Postgres when LEDGERFRAME_DB_URL points at one, so
the same guarantee is proven on both. Values in == Decimals out — exact value, exact textual
form (no scale padding), correct type (Decimal, never float). Includes precision beyond
NUMERIC(38,12)'s 12 fractional digits, which TEXT preserves and a native NUMERIC would have
silently truncated.
"""

from __future__ import annotations

from decimal import Decimal

import sqlalchemy as sa

from app.db.base import DecimalText

# Each is exact and chosen to break a float or a fixed-scale NUMERIC if one were involved.
CASES = [
    "0",
    "0.1",                                   # not representable in binary float
    "-0.1",
    "100.00",                                # trailing zeros must survive verbatim
    "0.30000000000",                         # 11 trailing zeros preserved (NUMERIC would repad)
    "1234567890.123456789",                  # 9 fractional digits
    "3.141592653589793238462643383",         # 27 fractional digits > NUMERIC(38,12)'s 12
    "0.000000000000001",                     # 1e-15, below 12 dp
    "99999999999999999999999.99",            # 23 integer digits
    "-273.15",
]


async def test_decimaltext_money_roundtrips_exact(session):
    md = sa.MetaData()
    tbl = sa.Table(
        "_money_roundtrip", md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("amount", DecimalText, nullable=False),
    )
    conn = await session.connection()
    await conn.run_sync(tbl.create)
    try:
        for i, s in enumerate(CASES):
            await session.execute(tbl.insert().values(id=i, amount=Decimal(s)))
        await session.flush()

        for i, s in enumerate(CASES):
            want = Decimal(s)
            got = (await session.execute(sa.select(tbl.c.amount).where(tbl.c.id == i))).scalar_one()
            assert type(got) is Decimal, f"{s!r} came back as {type(got).__name__}, not Decimal"
            assert got == want, f"value changed: {s!r} -> {got!r}"
            # Canonical form (digits AND scale/exponent) survives storage — proves no float and
            # no fixed-scale rounding (a NUMERIC(38,12) would have altered the >12-dp cases).
            assert str(got) == str(want), f"exact form not preserved: {str(want)!r} -> {str(got)!r}"
            assert got.as_tuple() == want.as_tuple()  # sign, digits, exponent all identical
    finally:
        await conn.run_sync(tbl.drop)
