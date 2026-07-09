# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2.4 — the OpenAPI contract is published and kept current."""

from __future__ import annotations

import json
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations(spec: dict) -> set[tuple[str, str]]:
    return {(path, m) for path, item in spec.get("paths", {}).items()
            for m in item if m in _METHODS}


def test_committed_openapi_is_valid_and_current():
    committed = json.loads((_ROOT / "docs" / "openapi.json").read_text())
    assert committed.get("openapi", "").startswith("3.")
    assert committed.get("paths")

    from app.main import create_app

    live = create_app().openapi()
    assert _operations(committed) == _operations(live), \
        "docs/openapi.json is stale — regenerate with `python scripts/gen_openapi.py`"


def test_contract_documents_the_token_endpoints():
    committed = json.loads((_ROOT / "docs" / "openapi.json").read_text())
    ops = _operations(committed)
    assert ("/api/v1/tokens", "get") in ops
    assert ("/api/v1/tokens", "post") in ops
    assert ("/api/v1/tokens/{token_id}", "delete") in ops
