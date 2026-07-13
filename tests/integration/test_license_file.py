# SPDX-License-Identifier: AGPL-3.0-or-later
"""release-readiness Gate B1 — the LICENSE file, and the headers that claim it.

FAIL-FIRST: there was **no LICENSE file at all** (§1-1a), while `pyproject.toml:7` and an SPDX header
on **every** source file already declared `AGPL-3.0-or-later`. The licence was **asserted everywhere
and shipped nowhere**.

Two things are pinned here, and the second is the one that rots quietly:

1. **The licence text is BYTE-EXACT canonical.** Not paraphrased, not reformatted, not reflowed. It is
   the FSF's own published `agpl-3.0.txt`. Its SHA-256 is recorded below: if anyone edits so much as a
   space, this fails. **A licence you have "tidied up" is not the licence you think you are shipping.**

2. **The headers and the file agree — drift in EITHER direction is a defect.** A header claiming a
   licence the repo does not carry is a false claim; a LICENSE file nobody's headers point at is a
   dead file. Both are caught.

*Provenance of the text (verified 2026-07-14, not taken from memory):* fetched from
``https://www.gnu.org/licenses/agpl-3.0.txt`` and cross-checked, word for word, against SPDX's
``license-list-data`` copy. The two differ **only** in whitespace reflow and `http`→`https` on the FSF
URLs; the licence body is identical. The GNU copy is used because it preserves the canonical layout.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LICENSE = REPO / "LICENSE"

#: SHA-256 of the canonical FSF text (https://www.gnu.org/licenses/agpl-3.0.txt), fetched + verified
#: against SPDX on 2026-07-14. This is the whole point of the file: it must never drift.
CANONICAL_SHA256 = "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"

DECLARED = "AGPL-3.0-or-later"


def test_a_LICENSE_file_exists_at_the_repo_root() -> None:
    """It did not. Every header claimed a licence the project never shipped."""
    assert LICENSE.is_file(), "no LICENSE at the repo root — the SPDX headers are writing cheques"


def test_the_licence_text_is_BYTE_EXACT_canonical() -> None:
    digest = hashlib.sha256(LICENSE.read_bytes()).hexdigest()
    assert digest == CANONICAL_SHA256, (
        "LICENSE is not the canonical FSF AGPL-3.0 text (byte-for-byte).\n"
        f"  expected {CANONICAL_SHA256}\n  found    {digest}\n"
        "A licence that has been reformatted, re-wrapped or 'tidied' is not the licence you think "
        "you are shipping. Restore it from https://www.gnu.org/licenses/agpl-3.0.txt"
    )


def test_the_licence_is_unmistakably_the_AGPL() -> None:
    """Cheap, independent of the hash — so a wrong-but-consistent file cannot sail through."""
    text = LICENSE.read_text()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 19 November 2007" in text
    assert "Remote Network Interaction" in text, "the §13 network clause — the reason it is AGPL, not GPL"


def test_pyproject_agrees_with_the_file() -> None:
    meta = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert meta["project"]["license"] == DECLARED, (
        f"pyproject declares {meta['project']['license']!r} but the repo ships the AGPL"
    )


def test_every_source_SPDX_header_agrees_with_the_file() -> None:
    """Drift in EITHER direction is a defect (checklist B1).

    A header pointing at a licence we don't ship is a false claim. A LICENSE nobody points at is dead.
    """
    wrong: list[str] = []
    checked = 0
    for path in [*(REPO / "app").rglob("*.py"), *(REPO / "scripts").glob("*.py"),
                 *(REPO / "scripts").glob("*.sh"), *(REPO / "scripts" / "lib").glob("*.sh")]:
        head = path.read_text(errors="replace")[:400]
        m = re.search(r"SPDX-License-Identifier:\s*(\S+)", head)
        if not m:
            continue
        checked += 1
        if m.group(1) != DECLARED:
            wrong.append(f"{path.relative_to(REPO)} → {m.group(1)}")

    assert checked > 20, "hardly any SPDX headers found — this test is not actually checking anything"
    assert not wrong, f"SPDX headers disagree with the shipped LICENSE: {wrong}"
