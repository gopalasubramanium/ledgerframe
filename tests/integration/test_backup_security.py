# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1.6 — backup restore path-traversal safety (negative tests)."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "..", "sub/x.db", "a/../../x"])
async def test_restore_rejects_path_traversal(app_client, bad):
    r = await app_client.post("/api/v1/backup/restore", json={"filename": bad})
    assert r.status_code == 400, (bad, r.text)


async def test_restore_rejects_identity_file_outside_data_dir(app_client, tmp_path):
    # A syntactically valid backup name but an identity file outside the data dir → 400.
    r = await app_client.post("/api/v1/backup/restore",
                              json={"filename": "ledgerframe-x.db.age",
                                    "identity_file": "/etc/shadow"})
    assert r.status_code == 400
    assert "identity file" in r.text.lower() or "outside" in r.text.lower()
