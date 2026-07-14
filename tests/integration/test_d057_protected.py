# SPDX-License-Identifier: AGPL-3.0-or-later
"""D-057 — the two §0-PROTECTED cash-flow semantics, PINNED IN CODE.

DECISIONS §0 lists these beside the not-a-Sharpe disclaimer and the honest-NULL FX: they are
deliberate honesty features, and they may not be removed.

    1. Contributions NEVER reduce the cash runway.
    2. `once` obligations are EXCLUDED from recurring net burn.

Both hold today BY CONSTRUCTION — `runway_report` never queries the Contribution table at all, and
`MONTHLY_FACTOR` simply has no key for `once`. That is a strong way to hold an invariant, but it is
not a CONTRACT: nothing fails if a refactor quietly changes either. A ratified semantic with no code
test is a sentence the code is free to silently disagree with (the D-084 lesson, verbatim).

These tests are the contract. (page-cash-flow §9-1, owner-ruled 2026-07-15.)
"""

from __future__ import annotations

BASE = "/api/v1"


async def _runway(client) -> dict:
    return (await client.get(f"{BASE}/portfolio/runway")).json()


async def _add_obligation(client, **kw) -> None:
    body = {"name": "Rent", "amount": 2000, "due_date": "2026-08-01",
            "recurrence": "monthly", "kind": "expense"}
    body.update(kw)
    r = await client.post(f"{BASE}/obligations", json=body)
    assert r.status_code == 200, r.text


async def _add_contribution(client, **kw) -> None:
    body = {"name": "Monthly SIP", "amount": 3000, "frequency": "monthly", "kind": "invest"}
    body.update(kw)
    r = await client.post(f"{BASE}/contributions", json=body)
    assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# §0 INVARIANT 1 — a contribution NEVER reduces the runway.
# --------------------------------------------------------------------------- #


async def test_contributions_never_reduce_the_runway(app_client):
    """A contribution BUILDS wealth; it is not consumption. It may not shorten the runway."""
    await _add_obligation(app_client)                    # gives us a finite runway to move
    before = await _runway(app_client)
    assert before["status"] == "finite" and before["runway_months"] > 0

    # A contribution far larger than the monthly burn — if it leaked into the burn at ALL, the
    # runway would collapse.
    await _add_contribution(app_client, amount=100_000, frequency="monthly", kind="invest")
    after = await _runway(app_client)

    assert after["runway_months"] == before["runway_months"]
    assert after["net_monthly_burn"] == before["net_monthly_burn"]
    assert after["monthly_expense"] == before["monthly_expense"]
    assert after["status"] == before["status"]


async def test_no_contribution_kind_reaches_the_runway(app_client):
    """Not one of the three kinds — invest, withdraw, prepay — may touch the burn."""
    await _add_obligation(app_client)
    before = await _runway(app_client)
    for kind in ("invest", "withdraw", "prepay"):
        await _add_contribution(app_client, name=f"{kind} plan", amount=50_000, kind=kind)
    after = await _runway(app_client)
    assert after["net_monthly_burn"] == before["net_monthly_burn"]
    assert after["runway_months"] == before["runway_months"]


async def test_contributions_are_still_reported_as_planned_cash_out(app_client):
    """The guarantee is that contributions don't touch the RUNWAY — not that they are hidden.

    They are still shown as planned cash movements, and the reader says so in protected copy.
    """
    await _add_obligation(app_client)
    await _add_contribution(app_client, amount=1000)
    c = (await app_client.get(f"{BASE}/contributions")).json()
    assert c["monthly_invest"] == 1000
    # A fuller liquidity picture WITHOUT changing the runway itself.
    assert c["monthly_cash_out_with_expenses"] == 1000 + 2000
    assert "do not reduce the cash runway" in c["disclaimer"].lower()


# --------------------------------------------------------------------------- #
# §0 INVARIANT 2 — a `once` obligation is EXCLUDED from recurring net burn...
#                  ...and is STILL a real future outflow.
# --------------------------------------------------------------------------- #


async def test_once_obligation_is_excluded_from_recurring_burn(app_client):
    """A one-off is lumpy, not a steady burn. It may not enter the monthly figures."""
    await _add_obligation(app_client, name="Rent", amount=2000, recurrence="monthly")
    before = await _runway(app_client)

    await _add_obligation(app_client, name="Tax bill", amount=90_000,
                          recurrence="once", due_date="2026-09-01")
    after = await _runway(app_client)

    assert after["monthly_expense"] == before["monthly_expense"] == 2000
    assert after["net_monthly_burn"] == before["net_monthly_burn"]
    assert after["runway_months"] == before["runway_months"]


async def test_a_once_obligation_still_appears_in_the_twelve_month_total(app_client):
    """The other half of the invariant: excluded from BURN is not excluded from EXISTENCE.

    A one-off tax bill is a real future outflow — hiding it would be its own dishonesty.
    """
    await _add_obligation(app_client, name="Tax bill", amount=90_000,
                          recurrence="once", due_date="2026-09-01")
    o = (await app_client.get(f"{BASE}/obligations")).json()

    row = next(r for r in o["obligations"] if r["name"] == "Tax bill")
    assert row["recurrence"] == "once"
    assert row["occurrences_12m"] == 1
    assert o["next_12m_total"] == 90_000          # it IS counted as a future outflow
    assert (await _runway(app_client))["monthly_expense"] == 0   # ...and NOT as a burn


async def test_once_income_is_also_excluded_from_the_burn(app_client):
    """Symmetry: the exclusion is about RECURRENCE, not about kind."""
    await _add_obligation(app_client, name="Rent", amount=2000, recurrence="monthly")
    before = await _runway(app_client)
    await _add_obligation(app_client, name="Bonus", amount=50_000, recurrence="once",
                          kind="income", due_date="2026-09-01")
    after = await _runway(app_client)
    assert after["monthly_income"] == before["monthly_income"] == 0
    assert after["net_monthly_burn"] == before["net_monthly_burn"]
