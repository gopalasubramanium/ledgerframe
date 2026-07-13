# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ONE gate every outbound call passes through — Product Guarantee 5.

**Guarantee 5 is an absolute:** with no-egress on, the device makes **ZERO** outbound calls. Not
"fewer". Not "none that matter". Zero.

**It was not being kept.** ``no_egress_enabled`` (``app/services/feeds.py``) was consulted from the
news, briefing and version-check surfaces only. **Every other outbound path ignored it**: the market
price providers (kite · eodhd · coingecko · amfi · yahoo · external), the ECB FX feed, and both AI
providers. Under ``privacy_mode`` a price refresh or an AI call still went out over the network.

It *looked* fine only because a no-egress user typically also runs ``market_provider=mock`` — but
**that is a configuration coincidence, not a guard**. A guarantee that holds by accident is not a
guarantee, and this one is written into the product's promises.

**The fix is a choke point, not a sprinkling of checks** (the ND-2 defence-in-depth pattern). An HTTP
client cannot be *constructed* without passing through here, so a future provider cannot forget to
ask: there is no other way to get a client. A structural test pins that — ``httpx.AsyncClient`` may
not be constructed anywhere outside this module.

The gate reads ``privacy_mode`` from the DB on its own session, because the providers are transport
code and have none. When it is on, we **never construct the client** — the request is not made,
attempted, or timed out. It raises ``EgressBlocked``, which the calling services already treat like
any provider failure: the value is **withheld with a reason**, never guessed (Guarantee 3).
"""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Setting


class EgressBlocked(RuntimeError):
    """Raised instead of making an outbound call while no-egress is on.

    Callers may let this propagate: the services around the providers already treat a provider
    failure as "no value, and here is why" — which is precisely the honest outcome (Guarantee 3/5).
    """

    def __init__(self, what: str = "outbound call") -> None:
        super().__init__(
            f"No-egress is on — the {what} was not made. "
            "The device makes zero outbound calls in this mode (Product Guarantee 5)."
        )
        self.what = what


async def no_egress_enabled(session: AsyncSession) -> bool:
    """True when the no-egress toggle (``privacy_mode``) is on."""
    row = (
        await session.execute(select(Setting).where(Setting.key == "privacy_mode"))
    ).scalars().first()
    return bool(row and str(row.value).strip().lower() in ("1", "true", "yes", "on"))


async def egress_allowed() -> bool:
    """Read the toggle on our own session (transport code has none of its own)."""
    from app.db.base import get_sessionmaker

    async with get_sessionmaker()() as session:
        return not await no_egress_enabled(session)


async def assert_egress_allowed(what: str = "outbound call") -> None:
    """Raise ``EgressBlocked`` if the device must make no outbound calls."""
    if not await egress_allowed():
        raise EgressBlocked(what)


async def egress_client(what: str = "outbound call", **kwargs) -> httpx.AsyncClient:
    """The ONLY way to get an HTTP client in this codebase.

    Checks the gate *before* constructing anything, so under no-egress the client is never built —
    no socket, no DNS lookup, no timeout to wait out. Use it exactly like ``httpx.AsyncClient``::

        async with await egress_client("price refresh", timeout=10) as client:
            ...
    """
    await assert_egress_allowed(what)
    return httpx.AsyncClient(**kwargs)
