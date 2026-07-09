# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 2.3 — request-id middleware: mint or propagate, echo in the response header."""

from __future__ import annotations


async def test_generates_request_id_when_absent(app_client):
    r = await app_client.get("/health")
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) >= 8         # a minted UUID hex


async def test_propagates_inbound_request_id(app_client):
    r = await app_client.get("/health", headers={"X-Request-ID": "abc-123_trace"})
    assert r.headers.get("x-request-id") == "abc-123_trace"


async def test_sanitises_malicious_request_id(app_client):
    # CR/LF and other unsafe chars must be stripped (log/header injection defence).
    r = await app_client.get("/health", headers={"X-Request-ID": "a b\r\nSet-Cookie: x=y"})
    rid = r.headers.get("x-request-id")
    assert "\n" not in rid and "\r" not in rid and " " not in rid and ":" not in rid


def test_filter_sets_request_id_on_records():
    import logging

    from app.core.observability import RequestContextFilter, request_id_var

    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", (), None)
    tok = request_id_var.set("rid-42")
    try:
        assert RequestContextFilter().filter(rec) is True
        assert rec.request_id == "rid-42"
    finally:
        request_id_var.reset(tok)
