#!/usr/bin/env python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Freeze / verify the v2 OpenAPI contract.

The frozen baseline is ``docs/specs/API-CONTRACT.json`` — the inherited HTTP
contract, generated from the running FastAPI app. ``docs/openapi.json`` is the
same document in the machine location the inherited test reads; both are written
and checked here so they can never diverge.

Usage:
    python scripts/check_api_contract.py            # drift check: exit 1 if stale
    python scripts/check_api_contract.py --write     # (re)freeze the contract

Rule (see docs/specs/API-CONTRACT.md): any endpoint change must update the
contract in the same commit. CI runs the drift check.
"""

from __future__ import annotations

import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Every file that must hold the exact serialized contract.
_TARGETS = [
    _ROOT / "docs" / "specs" / "API-CONTRACT.json",  # frozen v2 baseline (authoritative)
    _ROOT / "docs" / "openapi.json",                 # inherited artifact (same bytes)
]


def _serialize() -> str:
    """Deterministic serialization so diffs are meaningful (sorted keys)."""
    from app.main import create_app

    spec = create_app().openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> int:
    write = "--write" in sys.argv[1:]
    current = _serialize()

    if write:
        for target in _TARGETS:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(current)
            print(f"wrote {target.relative_to(_ROOT)}")
        return 0

    stale: list[str] = []
    for target in _TARGETS:
        if not target.exists():
            stale.append(f"{target.relative_to(_ROOT)} (missing)")
        elif target.read_text() != current:
            stale.append(f"{target.relative_to(_ROOT)} (differs from the live app)")

    if stale:
        print("API contract drift detected:", file=sys.stderr)
        for s in stale:
            print(f"  - {s}", file=sys.stderr)
        print(
            "\nThe HTTP contract changed but the committed contract was not updated.\n"
            "Regenerate and commit in the SAME change:\n"
            "    python scripts/check_api_contract.py --write\n"
            "(see docs/specs/API-CONTRACT.md)",
            file=sys.stderr,
        )
        return 1

    print("API contract is current (docs/specs/API-CONTRACT.json).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
