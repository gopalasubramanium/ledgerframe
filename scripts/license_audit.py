#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dependency-licence audit over the FULL TRANSITIVE graph — backend + frontend.

release-readiness Gate **A8** (RD-2). Committed to the repo so it is **repeatable**, not a one-off:
E4 re-runs it against the final public set, and **no public claim ships before it runs clean**.

What it does NOT do: **adjudicate.** It reports what it finds and flags anything copyleft-ish or
unknown. Whether a given licence is compatible with shipping AGPL-3.0-or-later — and with the D-001
"future proprietary layer" — is **owner/counsel territory**, not a script's.

Two scopes, deliberately separate, because they carry different risk:

* **RUNTIME** — what a user actually receives and runs. This is what a distribution claim is about.
* **DEV** — build/test tooling. It does not ship, but it is reported anyway so the owner can see it.

Exit codes: ``0`` clean · ``1`` something needs a human (flagged or unknown licences).

    python scripts/license_audit.py            # report + exit code
    python scripts/license_audit.py --write     # also refresh docs/audit/LICENSES.md
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import subprocess
import sys
import tomllib
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SELF = {"ledgerframe", "ledgerframe-frontend"}

#: Licence families that CONSTRAIN redistribution and therefore need a human decision. This list is
#: deliberately broad: a false flag costs a glance, a missed one costs a licence violation.
FLAG = re.compile(
    r"\b(a?gpl|lgpl|mpl|mozilla|epl|eclipse|cddl|sspl|bsl|business source|osl|eupl|cc-by-sa|"
    r"cc-by-nc|prosperity|commons clause|elastic license|non-?commercial)\b",
    re.I,
)
PERMISSIVE = re.compile(r"\b(mit|bsd|apache|isc|python software foundation|psf|zlib|unlicense|cc0|0bsd|"
                        r"public domain|wtfpl|hpnd|mit-0)\b", re.I)


# --- backend -------------------------------------------------------------------------------------


def _runtime_closure() -> set[str]:
    """The transitive closure of what SHIPS — pyproject's `dependencies`, walked to the leaves."""
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text())
    roots = [re.split(r"[<>=!~\[; ]", d)[0].strip().lower()
             for d in pyproject["project"].get("dependencies", [])]

    seen: set[str] = set()
    queue = deque(roots)
    while queue:
        name = queue.popleft()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            dist = md.distribution(key)
        except md.PackageNotFoundError:
            continue
        for req in dist.requires or []:
            # Skip extras-only requirements ("foo; extra == 'bar'") — they don't ship unless asked for.
            if "extra ==" in req:
                continue
            dep = re.split(r"[<>=!~\[; ]", req)[0].strip().lower()
            if dep and dep not in seen:
                queue.append(dep)
    return seen


def _licence_of(dist: md.Distribution) -> str:
    meta = dist.metadata
    expr = meta.get("License-Expression") or ""
    if expr:
        return expr.strip()
    classifiers = [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return "; ".join(c.split("::")[-1].strip() for c in classifiers)
    lic = (meta.get("License") or "").strip()
    if lic and "\n" not in lic and len(lic) < 80:
        return lic
    return "UNKNOWN"


def audit_backend() -> list[dict]:
    runtime = _runtime_closure()
    rows = []
    for dist in md.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name or name.lower() in SELF:
            continue
        rows.append({
            "name": name,
            "version": dist.version,
            "licence": _licence_of(dist),
            "scope": "runtime" if name.lower().replace("_", "-") in runtime else "dev",
            "eco": "python",
        })
    return sorted({r["name"]: r for r in rows}.values(), key=lambda r: r["name"].lower())


# --- frontend ------------------------------------------------------------------------------------


def audit_frontend() -> list[dict]:
    """The PRODUCTION tree (`--omit=dev`), walked in full — this is what reaches a browser."""
    fe = REPO / "frontend"
    rows: list[dict] = []

    def _walk(node: dict, scope: str) -> None:
        for name, info in (node.get("dependencies") or {}).items():
            if name in SELF:
                continue
            # `npm ls` omits `path` for packages it did not install here (optional per-platform
            # binaries, e.g. @esbuild/win32-*). Fall back to node_modules, then to the package's own
            # manifest. Left unresolved they would report as 300 UNKNOWNs and drown the real signal.
            cand = [Path(info["path"])] if info.get("path") else []
            cand.append(fe / "node_modules" / name)
            lic = "UNKNOWN"
            not_installed = False
            for c in cand:
                mf = c / "package.json"
                if not mf.is_file():
                    continue
                pkg = json.loads(mf.read_text())
                raw = pkg.get("license") or pkg.get("licenses")
                if isinstance(raw, list):
                    lic = " OR ".join(x.get("type", "?") if isinstance(x, dict) else str(x) for x in raw)
                elif isinstance(raw, dict):
                    lic = raw.get("type", "UNKNOWN")
                elif raw:
                    lic = str(raw)
                break
            else:
                not_installed = True
            rows.append({"name": name, "version": info.get("version", "?"), "licence": lic,
                         "scope": scope, "eco": "npm",
                         "note": "not installed on this platform" if not_installed else ""})
            _walk(info, scope)

    for scope, flags in (("runtime", ["--omit=dev"]), ("dev", [])):
        try:
            out = subprocess.run(["npm", "ls", "--all", "--json", "--long", *flags],
                                 cwd=fe, capture_output=True, text=True, check=False).stdout
            _walk(json.loads(out or "{}"), scope)
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"  ! could not read the npm {scope} tree (is `npm install` done?)", file=sys.stderr)

    # A package appearing in both trees is RUNTIME — that is the stricter, honest classification.
    best: dict[str, dict] = {}
    for r in rows:
        k = r["name"]
        if k not in best or (r["scope"] == "runtime" and best[k]["scope"] == "dev"):
            best[k] = r
    return sorted(best.values(), key=lambda r: r["name"].lower())


# --- report --------------------------------------------------------------------------------------


def classify(lic: str) -> str:
    if lic == "UNKNOWN" or not lic.strip():
        return "UNKNOWN"
    if FLAG.search(lic):
        return "FLAG"
    if PERMISSIVE.search(lic):
        return "ok"
    return "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="refresh docs/audit/LICENSES.md")
    args = ap.parse_args()

    rows = audit_backend() + audit_frontend()
    for r in rows:
        # Packages npm declares but did not install here are esbuild's OPTIONAL per-platform binaries
        # (@esbuild/win32-*, etc). They are not present, not built, and not shipped from this machine.
        # They get their own verdict rather than being silently dropped (that would be a lie) or
        # reported as UNKNOWN (that would bury the one finding that matters under 300 non-findings).
        r["verdict"] = "not-installed" if r.get("note") else classify(r["licence"])

    needs_human = [r for r in rows if r["verdict"] in ("FLAG", "UNKNOWN") and r["scope"] == "runtime"]
    dev_flags = [r for r in rows if r["verdict"] in ("FLAG", "UNKNOWN") and r["scope"] == "dev"]
    absent = [r for r in rows if r["verdict"] == "not-installed"]

    print(f"\nDependency-licence audit — {len(rows)} packages "
          f"({sum(r['scope'] == 'runtime' for r in rows)} runtime, "
          f"{sum(r['scope'] == 'dev' for r in rows)} dev; "
          f"{len(absent)} declared-but-not-installed)\n")

    for r in needs_human:
        print(f"  [{r['verdict']:7}] RUNTIME  {r['eco']:6} {r['name']}=={r['version']}  →  {r['licence']}")
    for r in dev_flags:
        print(f"  [{r['verdict']:7}] dev      {r['eco']:6} {r['name']}=={r['version']}  →  {r['licence']}")

    if args.write:
        out = REPO / "docs" / "audit" / "LICENSES.md"
        lines = [
            "# Dependency licences — FULL transitive graph",
            "",
            "*Generated by `scripts/license_audit.py` (release-readiness Gate A8 / RD-2). Regenerate,",
            "never hand-edit. E4 re-runs it against the final public set.*",
            "",
            "**This file reports; it does not adjudicate.** Whether a flagged licence is compatible with",
            "shipping AGPL-3.0-or-later — and with the D-001 future-proprietary-layer path — is an",
            "**owner/counsel** decision, not a script's.",
            "",
            "**RUNTIME** = what a user receives and runs (the scope a distribution claim is about).",
            "**dev** = build/test tooling; it does not ship, and is listed for completeness.",
            "",
            f"- packages: **{len(rows)}** ({sum(r['scope'] == 'runtime' for r in rows)} runtime, "
            f"{sum(r['scope'] == 'dev' for r in rows)} dev)",
            f"- runtime needing a human: **{len(needs_human)}**",
            f"- dev needing a human: **{len(dev_flags)}**",
            "",
            "| Scope | Eco | Package | Version | Licence | Verdict |",
            "|---|---|---|---|---|---|",
        ]
        order = {"FLAG": 0, "UNKNOWN": 1, "ok": 2, "not-installed": 3}
        for r in sorted(rows, key=lambda r: (r["scope"] != "runtime", order[r["verdict"]], r["name"].lower())):
            mark = {"ok": "ok", "FLAG": "⚠ **FLAG**", "UNKNOWN": "⚠ **UNKNOWN**",
                    "not-installed": "— not installed here"}[r["verdict"]]
            lines.append(f"| {r['scope']} | {r['eco']} | `{r['name']}` | {r['version']} | {r['licence']} | {mark} |")
        out.write_text("\n".join(lines) + "\n")
        print(f"\nwrote {out.relative_to(REPO)}")

    if needs_human or dev_flags:
        print(f"\nNOT CLEAN — {len(needs_human)} RUNTIME + {len(dev_flags)} dev entries need a human.")
        print("This script does NOT adjudicate: whether these are compatible with shipping")
        print("AGPL-3.0-or-later (and with D-001's future proprietary layer) is owner/counsel territory.")
        print("No public claim ships until the RUNTIME set is adjudicated (Gate A8 / E4).")
        return 1

    print("\nclean — every dependency resolves to a recognised permissive licence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
