# SPDX-License-Identifier: AGPL-3.0-or-later
"""Minimal in-process metrics in Prometheus text format (§2.3) — no external dependency.

Records HTTP request counts + latency (labelled by method/status only, to keep cardinality
bounded) and worker job outcomes. Rendered by the gated /metrics endpoint.
"""

from __future__ import annotations

import threading
from collections import defaultdict

_LOCK = threading.Lock()
_req_total: dict[tuple[str, str], int] = defaultdict(int)   # (method, status) -> count
_dur_sum: dict[str, float] = defaultdict(float)             # method -> total seconds
_dur_count: dict[str, int] = defaultdict(int)               # method -> observations
_worker_jobs: dict[tuple[str, str], int] = defaultdict(int)  # (job, outcome) -> count


def record_request(method: str, status: int, duration: float) -> None:
    with _LOCK:
        _req_total[(method, str(status))] += 1
        _dur_sum[method] += duration
        _dur_count[method] += 1


def _worker_file():
    from app.core.config import get_settings

    return get_settings().cache_dir / "worker_metrics.json"


def _persist_worker() -> None:
    """Snapshot worker counters to a shared file so the API process (a different process)
    can expose them via /metrics. One writer (the worker); atomic replace."""
    import json
    import os

    f = _worker_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    data = {f"{job}\t{outcome}": n for (job, outcome), n in _worker_jobs.items()}
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, f)


def _load_worker() -> dict[tuple[str, str], int]:
    import json

    f = _worker_file()
    if not f.exists():
        return {}
    try:
        raw = json.loads(f.read_text())
        return {tuple(k.split("\t", 1)): int(v) for k, v in raw.items()}  # type: ignore[misc]
    except Exception:  # noqa: BLE001
        return {}


def record_worker_job(job: str, outcome: str) -> None:
    with _LOCK:
        _worker_jobs[(job, outcome)] += 1
        try:
            _persist_worker()
        except Exception:  # noqa: BLE001 — metrics must never break a worker job
            pass


def reset() -> None:
    """Clear all metrics (test isolation)."""
    with _LOCK:
        _req_total.clear()
        _dur_sum.clear()
        _dur_count.clear()
        _worker_jobs.clear()
        try:
            _worker_file().unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass


def render() -> str:
    lines: list[str] = []
    with _LOCK:
        lines.append("# HELP ledgerframe_http_requests_total Total HTTP requests handled.")
        lines.append("# TYPE ledgerframe_http_requests_total counter")
        for (method, status), n in sorted(_req_total.items()):
            lines.append(f'ledgerframe_http_requests_total{{method="{method}",status="{status}"}} {n}')

        lines.append("# HELP ledgerframe_http_request_duration_seconds Request duration.")
        lines.append("# TYPE ledgerframe_http_request_duration_seconds summary")
        for method in sorted(_dur_sum):
            lines.append(f'ledgerframe_http_request_duration_seconds_sum{{method="{method}"}} {_dur_sum[method]:.6f}')
            lines.append(f'ledgerframe_http_request_duration_seconds_count{{method="{method}"}} {_dur_count[method]}')

        # Worker runs in a separate process; read its shared snapshot (fallback: in-process).
        worker = _load_worker() or dict(_worker_jobs)
        lines.append("# HELP ledgerframe_worker_job_runs_total Worker job runs by outcome.")
        lines.append("# TYPE ledgerframe_worker_job_runs_total counter")
        for (job, outcome), n in sorted(worker.items()):
            lines.append(f'ledgerframe_worker_job_runs_total{{job="{job}",outcome="{outcome}"}} {n}')
    return "\n".join(lines) + "\n"
