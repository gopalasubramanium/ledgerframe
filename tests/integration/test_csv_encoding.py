# SPDX-License-Identifier: AGPL-3.0-or-later
"""§14rp-3 (page-reports owner walk 2026-07-17) — CSV exports ship UTF-8 WITH a BOM (utf-8-sig).

The owner's Excel screenshot showed an em dash garbled ("â€"") because the files shipped UTF-8
WITHOUT a BOM and Excel decoded cp1252. Encoding is part of honesty, so it is guarded at the BYTE
level — every server-side CSV export must start with the UTF-8 BOM (EF BB BF). The guard is proven
fail-first (RED on the pre-fix, BOM-less responses) and re-runs green while the files still parse
correctly WITH the BOM (the importer decodes utf-8-sig, so a round-trip is lossless).
"""

from __future__ import annotations

import codecs
import csv
import io

# Every server-side CSV endpoint (D-050 / P-5). The four Reports artifacts named in §14 PLUS the
# already-delivered holdings/transactions/import-template — "utf-8-sig always" is app-wide.
_CSV_ENDPOINTS = [
    "/api/v1/portfolio/statements.csv",
    "/api/v1/portfolio/realised-gains.csv",
    "/api/v1/portfolio/tax-lots.csv",
    "/api/v1/portfolio/attribution.csv",
    "/api/v1/portfolio/holdings.csv",
    "/api/v1/portfolio/transactions.csv",
    "/api/v1/portfolio/import/template",
]


async def test_every_csv_export_ships_a_utf8_bom(app_client):
    """BYTE-LEVEL fail-first: each artifact's raw bytes begin with the UTF-8 BOM. RED today (the
    PlainTextResponses emitted BOM-less UTF-8)."""
    for url in _CSV_ENDPOINTS:
        r = await app_client.get(url)
        assert r.status_code == 200, f"{url} -> {r.status_code}"
        assert r.headers["content-type"].startswith("text/csv"), url
        assert r.content.startswith(codecs.BOM_UTF8), f"{url} did not lead with the UTF-8 BOM"


async def test_csv_exports_still_parse_correctly_with_the_bom(app_client):
    """The BOM must not break parsing — decoded as utf-8-sig the BOM is stripped, so the first cell
    of the first row is clean (no stray \\ufeff glued to it) and the file is valid CSV. Proves BOTH:
    the byte-level BOM is present AND the artifact stays computable."""
    for url in _CSV_ENDPOINTS:
        r = await app_client.get(url)
        text = r.content.decode("utf-8-sig")            # the importer's decoder — strips the BOM
        assert not text.startswith("\ufeff"), f"{url}: utf-8-sig decode left a BOM"
        rows = list(csv.reader(io.StringIO(text)))
        assert rows, f"{url}: no rows parsed"
        first_cell = rows[0][0] if rows[0] else ""
        assert not first_cell.startswith("\ufeff"), f"{url}: BOM glued to the first cell"
