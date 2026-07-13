# SPDX-License-Identifier: AGPL-3.0-or-later
"""release-readiness Gate A8 (RD-2) — the dependency-licence audit is REPEATABLE.

FAIL-FIRST: neither `scripts/license_audit.py` nor `docs/audit/LICENSES.md` existed. §1-1f recorded
that only the **direct** dependency set had ever been read — the **transitive** graph (381 packages)
had never been looked at.

**What these tests deliberately DO NOT assert: that the audit is CLEAN.** It is not, and pretending
otherwise in a test would be exactly the self-certification this project keeps refusing. The audit
found one **RUNTIME** flag (`certifi`, MPL-2.0) and three dev ones. **Whether those are compatible
with shipping AGPL-3.0-or-later — and with D-001's future proprietary layer — is an owner/counsel
decision, not a script's and not a test's.** The *release* gate (Gate A8 / E4) is the owner
adjudicating that list; the *CI* gate is only that the list is real and current.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts" / "license_audit.py"
REPORT = REPO / "docs" / "audit" / "LICENSES.md"


def test_the_audit_tool_is_committed_so_it_is_repeatable() -> None:
    """E4 re-runs this against the final public set — a one-off audit on someone's laptop is not one."""
    assert TOOL.is_file(), "scripts/license_audit.py is missing — the audit cannot be repeated"


def test_the_report_exists_and_covers_the_TRANSITIVE_graph() -> None:
    assert REPORT.is_file(), "docs/audit/LICENSES.md is missing"
    text = REPORT.read_text()
    # §1-1d/1e had read ~16 DIRECT dependencies. The real graph is an order of magnitude bigger.
    rows = [ln for ln in text.splitlines() if ln.startswith("| ")]
    assert len(rows) > 100, (
        f"only {len(rows)} packages audited — that is the DIRECT set again, not the transitive graph"
    )


def test_the_report_does_not_adjudicate() -> None:
    """The tool reports; the owner decides. The file must say so, so nobody later mistakes it for
    a clearance."""
    assert "does not adjudicate" in REPORT.read_text()


def test_the_audit_runs_and_reports_its_verdict_via_exit_code() -> None:
    """Exit 0 = clean, 1 = something needs a human. The release gate reads this; so can CI, later."""
    r = subprocess.run([sys.executable, str(TOOL)], cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), f"unexpected exit {r.returncode}: {r.stderr[:300]}"
    assert "Dependency-licence audit" in r.stdout
    # Whatever the verdict, the RUNTIME scope must be stated — that is the scope a public claim is about.
    assert "runtime" in r.stdout.lower()


def test_the_committed_report_is_not_STALE() -> None:
    """Regenerating must not change the file.

    Without this the report rots the moment a dependency moves, and a stale licence audit is worse
    than none: it looks like diligence.
    """
    before = REPORT.read_text()
    subprocess.run([sys.executable, str(TOOL), "--write"], cwd=REPO, capture_output=True, text=True)
    after = REPORT.read_text()
    if before != after:
        REPORT.write_text(before)  # leave the tree as we found it; the failure is the message
        raise AssertionError(
            "docs/audit/LICENSES.md is stale — dependencies changed since it was generated. "
            "Re-run: python scripts/license_audit.py --write"
        )
