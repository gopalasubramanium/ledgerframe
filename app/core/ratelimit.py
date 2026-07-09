# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-process PIN brute-force limiter (§1.2) — no external dependencies.

Per-key (client IP) failure tracking with exponential backoff after 5 failures and a hard
15-minute lockout after 10. The audit trail (unlock_failed / rate_limited AuditEvents)
provides the durable record; this module is the fast in-memory gate.
"""

from __future__ import annotations

import threading
import time

_LOCK = threading.Lock()
_STATE: dict[str, dict] = {}

BACKOFF_AFTER = 5            # failures 1–4 are free; the 5th arms backoff
HARD_LOCK_AFTER = 10        # 10 failures → hard lockout
HARD_LOCK_SECONDS = 15 * 60


def retry_after(key: str) -> float:
    """Seconds the caller must wait before another attempt (0.0 if allowed now)."""
    now = time.monotonic()
    with _LOCK:
        st = _STATE.get(key)
        if not st:
            return 0.0
        return max(0.0, max(st["locked_until"], st["next_allowed"]) - now)


def record_failure(key: str) -> None:
    now = time.monotonic()
    with _LOCK:
        st = _STATE.setdefault(key, {"failures": 0, "locked_until": 0.0, "next_allowed": 0.0})
        st["failures"] += 1
        f = st["failures"]
        if f >= HARD_LOCK_AFTER:
            st["locked_until"] = now + HARD_LOCK_SECONDS
        elif f >= BACKOFF_AFTER:
            st["next_allowed"] = now + float(2 ** (f - BACKOFF_AFTER))  # 1,2,4,8,16s…


def record_success(key: str) -> None:
    with _LOCK:
        _STATE.pop(key, None)


def reset() -> None:
    """Clear all state (used by test fixtures for isolation)."""
    with _LOCK:
        _STATE.clear()
