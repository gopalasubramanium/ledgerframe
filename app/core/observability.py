# SPDX-License-Identifier: AGPL-3.0-or-later
"""Observability seam (§2.3) — request-id propagation for log correlation.

A pure-ASGI middleware (same layer as SecurityHeadersMiddleware) assigns a request id
(honouring an inbound X-Request-ID or minting a UUID), binds it into a contextvar so log
records can carry it, and echoes it back in the response header. Additive only.
"""

from __future__ import annotations

import contextvars
import logging
import re
import time
import uuid

from app.core import metrics

# Current request's id; "-" outside any request (startup, worker, tests).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Only allow a conservative id charset (defends logs/headers from injection via a header).
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")


def _clean_id(raw: bytes | None) -> str:
    if not raw:
        return uuid.uuid4().hex
    cleaned = _SAFE_ID.sub("", raw.decode("latin-1", "ignore"))[:64]
    return cleaned or uuid.uuid4().hex


def get_request_id() -> str:
    return request_id_var.get()


class RequestContextFilter(logging.Filter):
    """Injects the current request id into every log record (so the formatter can show it)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RequestContextMiddleware:
    """Assign/propagate the request id, bind it into logs, and echo X-Request-ID."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        rid = _clean_id(headers.get(b"x-request-id"))
        token = request_id_var.set(rid)
        method = scope.get("method", "GET")
        started = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                msg_headers = message.setdefault("headers", [])
                if not any(k.lower() == b"x-request-id" for k, _ in msg_headers):
                    msg_headers.append((b"x-request-id", rid.encode("ascii", "ignore")))
                metrics.record_request(method, message["status"], time.perf_counter() - started)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)
