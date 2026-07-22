# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-43 §18-R4 (F-7b ruling (a)) — the priority chain distinguishes "keyed here" from
"supported, no key".

The chain is the shipped policy constant ``DEFAULT_PRIORITY``: it names every provider that
COULD price the lane, including keyed ones this instance has no credential for. Undifferentiated,
those entries read as providers that do not exist — the P1 "phantom providers" false alarm that
reached two levels of review (§18-F7b #1). Presentation only: chain membership still selects
nothing (§18-F7b #2), and the chain stays read-only (D-072).
"""

from __future__ import annotations

from app.providers.market.router import UNKEYED_NOTE, ProviderAvailability, route


def _route(**kw):
    base = {
        "instrument_id": 1, "symbol": "X", "asset_class": "equity", "asset_subclass": None,
        "listing_country": None, "mappings": set(), "active_provider": "alphavantage",
        "has_manual": False,
    }
    base.update(kw)
    return route(**base)


def _keyed_alphavantage() -> dict[str, ProviderAvailability]:
    """The owner's shape: AV active WITH a key; nothing else credentialed."""
    return {"alphavantage": ProviderAvailability(
        name="alphavantage", configured=True, has_credentials=True, enabled=True)}


def _entries(diag) -> dict[str, tuple[bool, str | None]]:
    return {e.source: (e.keyed, e.note) for e in diag.priority_chain_detail}


def test_sbicard_chain_shows_kite_and_eodhd_unkeyed_av_normal():
    """The §18 pin: SBICARD.BSE's in_equity chain renders kite/eodhd visibly unkeyed while the
    keyed provider renders normally."""
    d = _route(symbol="SBICARD.BSE", listing_country="IN", availability=_keyed_alphavantage())
    e = _entries(d)
    assert e["kite"] == (False, UNKEYED_NOTE)
    assert e["eodhd"] == (False, UNKEYED_NOTE)
    assert e["alphavantage"] == (True, None)


def test_detail_covers_the_chain_exactly_and_in_order():
    """Same chain, annotated — not a second, divergent list."""
    d = _route(symbol="TSLA", listing_country="US", availability=_keyed_alphavantage())
    assert [e.source for e in d.priority_chain_detail] == d.priority_chain


def test_keyless_and_terminal_entries_are_never_annotated():
    """yahoo/csv/coingecko need no key; manual/statement are not providers at all."""
    d = _route(symbol="BTC", asset_class="crypto", availability=_keyed_alphavantage())
    e = _entries(d)
    assert e["coingecko"] == (True, None)
    assert e["yahoo"] == (True, None)
    assert e["manual"] == (True, None)


def test_a_credential_flips_the_entry_to_normal():
    """The annotation tracks the real credential state, not a hardcoded provider list."""
    av = _keyed_alphavantage()
    av["kite"] = ProviderAvailability(
        name="kite", configured=True, has_credentials=True, enabled=True)
    d = _route(symbol="SBICARD.BSE", listing_country="IN", availability=av)
    assert _entries(d)["kite"] == (True, None)
    # ...and a half-configured Kite (api key, no access token) is still honestly unkeyed.
    av["kite"] = ProviderAvailability(
        name="kite", configured=True, has_credentials=False, enabled=True)
    d2 = _route(symbol="SBICARD.BSE", listing_country="IN", availability=av)
    assert _entries(d2)["kite"] == (False, UNKEYED_NOTE)


def test_no_availability_map_asserts_no_absence():
    """A pure-policy call cannot see credentials, so it must not claim any are missing."""
    d = _route(symbol="SBICARD.BSE", listing_country="IN")
    assert all(e.keyed and e.note is None for e in d.priority_chain_detail)


def test_annotation_does_not_change_routing():
    """§18-F7b #2 — chain membership never selects a provider; annotating it changes nothing."""
    with_av = _route(symbol="SBICARD.BSE", listing_country="IN", availability=_keyed_alphavantage())
    assert with_av.source_selected == "alphavantage"
    # R-63 §9-6 free-first order (keyless yahoo leads; kite the India specialist before the other paid).
    assert with_av.priority_chain == [
        "yahoo", "kite", "alphavantage", "eodhd", "csv", "manual"]
