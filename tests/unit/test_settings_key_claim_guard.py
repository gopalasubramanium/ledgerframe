# SPDX-License-Identifier: AGPL-3.0-or-later
"""R-58 standing guard — every ``settings.key`` INSERT goes through the claim primitive.

CLAUDE.md: *"A HARD RULE WITHOUT A GUARD IS A REQUEST"* + *"a guard is pinned against going blind"*.

R-58 routed every check-then-insert on ``settings.key`` through ``app.db.claim.claim_setting``
(SAVEPOINT + ``IntegrityError`` absorb) so a concurrent first-write's loser is absorbed, not 500'd.
Without a guard that rule is a *request*: R-63 (``d0a1c81``) introduced a FIFTH instance
(``market._upsert_setting``) AFTER the F10 census had swept for exactly this shape, and **nothing went
red** — the R-58 completeness sweep caught it by hand. This guard makes the sweep STANDING: any new raw
``session.add(Setting(...))`` in ``app/`` outside the sanctioned sites turns this RED, forcing the
author to route it through ``claim_setting`` or add an explicit, reviewed disposition below.

AST-based, not a text grep, so prose in docstrings/comments that merely *describes* the shape does not
trip it. Limitation (recorded, not hidden): it matches ``<session>.add(Setting(...))`` — a future
``add_all([Setting(...)])`` bulk insert would not be seen; that shape is not the check-then-insert race
and none exists in ``app/`` today.
"""

from __future__ import annotations

import ast
from pathlib import Path

_APP = Path(__file__).resolve().parents[2] / "app"

# The ONLY sanctioned raw ``Setting(...)`` insertions in app/ — each reviewed:
#   * db/claim.py  — the ``claim_setting`` primitive itself (the SAVEPOINT insert every site delegates to).
#   * seed/demo.py — the boot-only SEED_FLAG_KEY insert; R-58 I-6 dispositioned it (runs only at boot
#     inside main.py's try/except, so a raced collision is caught + logged, never a request 500).
_SANCTIONED = {"db/claim.py", "seed/demo.py"}


def _setting_insert_lines(source: str) -> list[int]:
    """Line numbers of ``<x>.add(Setting(...))`` calls in real code (comments/docstrings excluded)."""
    out: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Call):
                    f = arg.func
                    name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
                    if name == "Setting":
                        out.append(node.lineno)
    return out


def test_every_settings_key_insert_uses_the_claim_primitive_or_is_sanctioned():
    offenders: dict[str, list[int]] = {}
    for py in _APP.rglob("*.py"):
        rel = py.relative_to(_APP).as_posix()
        lines = _setting_insert_lines(py.read_text(encoding="utf-8"))
        if lines and rel not in _SANCTIONED:
            offenders[rel] = lines
    assert not offenders, (
        "raw `session.add(Setting(...))` outside the sanctioned sites — a check-then-insert on "
        "settings.key races (F10/R-58). Route it through app.db.claim.claim_setting (SAVEPOINT-"
        f"guarded) or add a reviewed disposition to _SANCTIONED. Offenders: {offenders}"
    )


def test_the_guard_is_not_blind_each_sanctioned_insert_still_exists():
    """Pinned against going blind: if the primitive's insert or the seed disposition disappeared, the
    guard above would pass by protecting nothing. Assert each sanctioned insertion is actually there."""
    for rel in _SANCTIONED:
        source = (_APP / rel).read_text(encoding="utf-8")
        assert _setting_insert_lines(source), (
            f"sanctioned Setting insert vanished from {rel} — the guard would be protecting nothing"
        )
