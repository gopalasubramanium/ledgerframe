# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reference data (D-005): the single endpoint serving every fixed vocabulary.

Retires the per-master `*/meta` endpoints and all frontend inline lists — the
frontend carries zero vocabulary copies (MASTER-DATA §1). Values are sourced from
the canonical code enums/constants where they exist; the authored vocabularies
(asset_subclass DEF-2, and the sets with no single code home) are defined here
against MASTER-DATA, which is their backend home.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models import AssetClass, TxnType
from app.schemas.common import EntitlementStatus, ValuationMethod
from app.services.accounts import ACCOUNT_KINDS
from app.services.estate import (
    CONTACT_ROLES,
    DOC_CATEGORIES,
    DOC_STATUSES,
    WILL_STATUSES,
)
from app.services.insurance import FREQUENCIES as PREMIUM_FREQUENCIES
from app.services.insurance import POLICY_TYPES
from app.services.planning import GOAL_BASES, OBLIGATION_KINDS, RECURRENCES

router = APIRouter()


def _values(enum_cls) -> list[str]:
    return [m.value for m in enum_cls]


# Authored / no-single-code-home vocabularies (MASTER-DATA §2/§4).
_ASSET_SUBCLASS = ["crypto", "derivative", "equity", "etf", "mutual_fund", "reit"]  # DEF-2 §2 †
_LIQUIDITY_PROFILE = ["listed", "redeemable", "locked", "illiquid", "manual"]  # §2
_ENTITY_KIND = ["self", "spouse", "trust", "company", "other"]  # §2
_CONTRIBUTION_FREQUENCY = ["monthly", "quarterly", "annual", "once"]  # §2
_CONTRIBUTION_KIND = ["invest", "withdraw", "prepay"]  # §2
_COST_BASIS_METHOD = ["fifo", "average"]  # §2 (v2 lanes; `spec` is ROADMAP R-6)
_POLICY_DIMENSION = ["asset_class", "currency", "region"]  # §2
_REGION = ["India", "Singapore", "US", "Europe", "APAC", "Other"]  # §4 (D-083)
_ID_TYPE = ["isin", "cusip", "figi", "sedol", "amfi_code", "kite_token",
            "coingecko_id", "provider_symbol"]  # §2


@router.get("/refdata")
async def refdata() -> dict[str, list[str]]:
    """Every fixed vocabulary, keyed by id. Extensible masters (currency,
    institution, sector, tag) are served by their own endpoints, not here."""
    return {
        "txn_type": _values(TxnType),
        "asset_class": _values(AssetClass),
        "asset_subclass": _ASSET_SUBCLASS,
        "liquidity_profile": _LIQUIDITY_PROFILE,
        "entity_kind": _ENTITY_KIND,
        "goal_basis": list(GOAL_BASES),
        "obligation_recurrence": list(RECURRENCES),
        "obligation_kind": list(OBLIGATION_KINDS),
        "contribution_frequency": _CONTRIBUTION_FREQUENCY,
        "contribution_kind": _CONTRIBUTION_KIND,
        "will_status": list(WILL_STATUSES),
        "estate_doc_status": list(DOC_STATUSES),
        "estate_doc_category": list(DOC_CATEGORIES),
        "contact_role": list(CONTACT_ROLES),
        "valuation_method": _values(ValuationMethod),
        "entitlement": _values(EntitlementStatus),
        "policy_dimension": _POLICY_DIMENSION,
        "region": _REGION,
        "cost_basis_method": _COST_BASIS_METHOD,
        "account_kind": list(ACCOUNT_KINDS),
        "policy_type": list(POLICY_TYPES),
        "premium_frequency": list(PREMIUM_FREQUENCIES),
        "id_type": _ID_TYPE,
    }
