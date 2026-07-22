# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared enums and value objects used across providers, services, and the API."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EntitlementStatus(str, enum.Enum):
    REALTIME = "real-time"
    DELAYED = "delayed"
    END_OF_DAY = "end-of-day"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class FailureState(str, enum.Enum):
    """WHY a quote could not be priced — the distinct causes R-63 §9-2 refuses to collapse into
    one flat "none". Set on a Quote whose ``price is None`` (or carried by a refresh outcome) so
    Pricing Health can name the real reason instead of a single misleading message. Two origins:

    * from the PROVIDER (a fetch was attempted) — ``throttled`` / ``empty`` / ``errored`` /
      ``parse_error``;
    * from ROUTING (no fetch was possible) — ``unmapped`` / ``no_key`` / ``unsupported``.
    """

    THROTTLED = "throttled"      # the provider rate-limited us (transient; will retry)
    EMPTY = "empty"              # the provider responded but had NO price for this symbol
    PARSE_ERROR = "parse_error"  # the provider returned data we could not interpret
    ERRORED = "errored"          # a network / HTTP error reaching the provider
    UNMAPPED = "unmapped"        # needs an identifier mapping first (fund → AMFI, crypto → id)
    NO_KEY = "no_key"            # the lane needs a credential this instance does not hold
    UNSUPPORTED = "unsupported"  # no configured source can price this instrument


class MarketState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE = "pre-market"
    POST = "post-market"
    UNKNOWN = "unknown"


class ValuationMethod(str, enum.Enum):
    """HOW a value was arrived at — kept SEPARATE from entitlement (which is about
    data recency/rights). A holding shows both: e.g. entitlement=delayed +
    method=market_quote, or entitlement=unavailable + method=manual_valuation."""

    MARKET_QUOTE = "market_quote"          # a live/delayed exchange or provider quote
    OFFICIAL_NAV = "official_nav"          # fund NAV from an official source (e.g. AMFI)
    BROKER_QUOTE = "broker_quote"          # a broker-supplied mark
    FX_REFERENCE = "fx_reference"          # reference FX (central bank / fallback)
    MANUAL_VALUATION = "manual_valuation"  # user-entered value (cash, property, private)
    STATEMENT_IMPORT = "statement_import"  # value taken from an imported statement
    CALCULATED_ACCRUAL = "calculated_accrual"  # principal + accrued interest (FD/bond)
    ESTIMATED_VALUE = "estimated_value"    # best-effort estimate (e.g. cost fallback)
    UNAVAILABLE = "unavailable"            # no value available


class MoneyModel(BaseModel):
    """Base model that serialises Decimal as float at the JSON edge."""

    model_config = ConfigDict(json_encoders={Decimal: lambda d: float(d)}, from_attributes=True)


class Quote(MoneyModel):
    symbol: str
    exchange: str | None = None
    price: Decimal | None = None  # None == genuinely unavailable; never fabricated
    # D-105: the served DISPLAY string for `price` at class-appropriate precision (set by the quote
    # display formatter; the frontend renders it verbatim, no client formatting). None when no price.
    price_display: str | None = None
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_pct: Decimal | None = None
    currency: str = "USD"
    source: str = "mock"
    entitlement: EntitlementStatus = EntitlementStatus.DELAYED
    # How this value was derived (separate from entitlement). Defaults to a market
    # quote so every existing provider/quote stays valid without changes.
    valuation_method: ValuationMethod = ValuationMethod.MARKET_QUOTE
    market_time: datetime | None = None
    received_at: datetime
    is_stale: bool = False
    # R-63 §9-2: WHY there is no price, when there is none. Set by a provider adapter (throttled/
    # empty/errored/parse_error) or the refresh path (unmapped/no_key/unsupported); None on a
    # priced quote. Distinct causes must never collapse into one "none".
    failure_state: FailureState | None = None


class Candle(MoneyModel):
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None


class Instrument(MoneyModel):
    symbol: str
    exchange: str | None = None
    name: str = ""
    asset_class: str = "equity"
    currency: str = "USD"
    sector: str | None = None
    country: str | None = None


class MarketStatus(MoneyModel):
    market: str
    state: MarketState
    as_of: datetime
    next_change: datetime | None = None


class FxRate(MoneyModel):
    base: str
    quote: str
    rate: Decimal
    source: str = "mock"
    received_at: datetime
    is_stale: bool = False


class NewsItem(MoneyModel):
    headline: str
    summary: str | None = None
    url: str | None = None
    source: str
    published_at: datetime
    symbols: list[str] = []
