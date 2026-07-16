# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estate page-build Phase 0 — the §9 contract/behaviour deltas, fail-first.

Each test is written to be RED on the pre-delta code and GREEN after the delta it guards
(page-estate §9, owner-ruled one-pass 2026-07-16). Grouped by the ruling number it pins.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# 9-1 — GET /estate/meta is DELETED; /refdata is the single D-005 vocab source.
# The removal is discriminated by response SHAPE, not status: an unmatched /api/ path
# is an honest JSON 404 today, but the SPA catch-all returns 200 HTML in production, so
# only a shape assertion is portable (page-estate §3b, the Insurance §9-3 precedent).
# --------------------------------------------------------------------------- #
async def test_estate_meta_endpoint_removed_by_shape(app_client):
    """The retired endpoint no longer serves the meta shape. RED today: it returns the
    four bare-list vocab keys (`doc_categories`, `contact_roles`, ...)."""
    r = await app_client.get("/api/v1/estate/meta")
    ctype = r.headers.get("content-type", "")
    body = r.json() if ctype.startswith("application/json") else None
    # The meta shape (its four vocab keys) is GONE — not merely a different status.
    assert not (isinstance(body, dict) and "doc_categories" in body and "contact_roles" in body), (
        "GET /estate/meta still serves the meta shape — it must be deleted (§9-1)"
    )
    # /refdata is the single source and still serves all four estate vocabs as {value,label}.
    refdata = (await app_client.get("/api/v1/refdata")).json()
    for key in ("will_status", "estate_doc_status", "estate_doc_category", "contact_role"):
        assert refdata[key], f"/refdata must serve {key}"
        assert all({"value", "label"} <= set(o) for o in refdata[key])


# --------------------------------------------------------------------------- #
# 9-5 (+ Amendment E) — `relationship` is retired: the served contact no longer
# carries it (the field is dropped from ContactIn + _contact_dict; the column is
# dropped by migration with a fold-into-notes backfill — see the migration test).
# --------------------------------------------------------------------------- #
async def test_served_contact_has_no_relationship_field(app_client):
    """The estate contact shape no longer serves `relationship` (D-010/D-063: dropped,
    folded into roles/notes). RED today: `_contact_dict` still serves the free-text field."""
    r = await app_client.post("/api/v1/estate/contacts",
                              json={"name": "Spouse", "roles": ["nominee", "executor"]})
    created = r.json()
    assert created["ok"]
    assert "relationship" not in created, "the write response must not carry `relationship`"
    contacts = (await app_client.get("/api/v1/estate")).json()["contacts"]
    assert contacts, "expected the created contact to be served"
    assert all("relationship" not in c for c in contacts), (
        "GET /estate contacts must not carry `relationship` — it is retired (§9-5)"
    )
    # A stray `relationship` in the request body is simply ignored (extra field), never persisted/served.
    r2 = await app_client.post("/api/v1/estate/contacts",
                               json={"name": "Sibling", "relationship": "sister", "roles": ["emergency"]})
    assert r2.json()["ok"]
    assert "relationship" not in r2.json()

