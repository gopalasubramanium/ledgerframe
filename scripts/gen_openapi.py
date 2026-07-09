#!/usr/bin/env python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regenerate docs/openapi.json from the app (§2.4). Run after changing any route."""

from __future__ import annotations

import json
import pathlib


def main() -> None:
    from app.main import create_app

    spec = create_app().openapi()
    out = pathlib.Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out} ({len(spec.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
