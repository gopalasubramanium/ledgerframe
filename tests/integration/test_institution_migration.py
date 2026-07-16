# SPDX-License-Identifier: AGPL-3.0-or-later
"""Institution FK re-pointing (page-accounts §9-1 + Amendment F, Phase 0 commit 3).

The three-step fold: seed the master from the distinct free-text values of BOTH
``accounts.institution`` and ``insurance_policy.insurer`` → re-point every row onto the
FK (``institution_id``) → drop both String columns. Read-shape compat: ``/accounts`` still
serves the institution name and ``/insurance`` still serves ``insurer``, both now via the join.
The write path resolves-or-creates a master row from a NAME (upsert per Amendment F).
"""

from __future__ import annotations


async def test_demo_seed_populates_the_institution_master(app_client):
    # Amendment F: the demo policies' insurers seed the master (fold-then-drop, values migrate IN).
    names = {i["name"] for i in (await app_client.get("/api/v1/institutions")).json()["institutions"]}
    assert "AIA Singapore" in names
    assert "Prudential Assurance Singapore" in names


async def test_insurance_still_serves_insurer_name_via_join(app_client):
    pols = (await app_client.get("/api/v1/insurance")).json()["policies"]
    insurers = {p["insurer"] for p in pols}
    assert "AIA Singapore" in insurers  # served shape unchanged (name, now via the join)


async def test_account_write_resolves_or_creates_and_collapses_case(app_client):
    await app_client.post("/api/v1/accounts", json={"name": "A1", "institution": "DBS "})
    await app_client.post("/api/v1/accounts", json={"name": "A2", "institution": "dbs"})

    rep = {a["name"]: a for a in (await app_client.get("/api/v1/accounts")).json()["accounts"]}
    # Both accounts serve the FIRST-SEEN casing (Amendment F), via the join.
    assert rep["A1"]["institution"] == "DBS"
    assert rep["A2"]["institution"] == "DBS"
    # ...and exactly one master row exists for it.
    dbs = [i for i in (await app_client.get("/api/v1/institutions")).json()["institutions"]
           if i["name"] == "DBS"]
    assert len(dbs) == 1


async def test_delete_institution_blocked_once_an_account_references_it(app_client):
    # This is the RED path the commit-1 guard was built for — reachable now the FK column exists.
    await app_client.post("/api/v1/accounts", json={"name": "A", "institution": "DBS"})
    iid = next(i["id"] for i in (await app_client.get("/api/v1/institutions")).json()["institutions"]
               if i["name"] == "DBS")
    d = await app_client.delete(f"/api/v1/institutions/{iid}")
    assert d.status_code == 400
    assert "merge" in d.json()["detail"].lower()


async def test_merge_repoints_a_referencing_account_onto_the_survivor(app_client):
    await app_client.post("/api/v1/accounts", json={"name": "A", "institution": "DBS"})
    await app_client.post("/api/v1/accounts", json={"name": "B", "institution": "DBS Bank"})
    ids = {i["name"]: i["id"] for i in (await app_client.get("/api/v1/institutions")).json()["institutions"]}

    m = await app_client.post("/api/v1/institutions/merge",
                              json={"survivor_id": ids["DBS"], "duplicate_id": ids["DBS Bank"]})
    assert m.status_code == 200 and m.json()["repointed"] >= 1

    rep = {a["name"]: a for a in (await app_client.get("/api/v1/accounts")).json()["accounts"]}
    assert rep["B"]["institution"] == "DBS"  # re-pointed off the folded duplicate onto the survivor
