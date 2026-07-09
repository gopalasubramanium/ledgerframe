# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 1.4 — secret-key enforcement on startup."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.main import _enforce_secret_key, _secret_key_is_weak, create_app


def test_weak_secret_key_detection():
    assert _secret_key_is_weak("")
    assert _secret_key_is_weak("change-me-to-a-long-random-string")   # placeholder
    assert _secret_key_is_weak("short")                              # < 32
    assert not _secret_key_is_weak("x" * 32)


def test_enforce_refuses_weak_key_when_lan_exposed():
    s = get_settings()
    orig = (s.allow_lan, s.secret_key)
    s.allow_lan, s.secret_key = True, "change-me-to-a-long-random-string"
    try:
        with pytest.raises(RuntimeError):
            _enforce_secret_key(s)
    finally:
        s.allow_lan, s.secret_key = orig


def test_enforce_warns_but_allows_weak_key_on_loopback():
    s = get_settings()
    orig = (s.allow_lan, s.secret_key)
    s.allow_lan, s.secret_key = False, "change-me-to-a-long-random-string"
    try:
        _enforce_secret_key(s)     # must NOT raise on a loopback-only bind
    finally:
        s.allow_lan, s.secret_key = orig


def test_enforce_allows_strong_key_when_lan_exposed():
    s = get_settings()
    orig = (s.allow_lan, s.secret_key)
    s.allow_lan, s.secret_key = True, "x" * 48
    try:
        _enforce_secret_key(s)
    finally:
        s.allow_lan, s.secret_key = orig


async def test_lifespan_refuses_to_start_with_weak_key_when_lan_exposed():
    s = get_settings()
    orig = (s.allow_lan, s.secret_key)
    s.allow_lan, s.secret_key = True, "change-me-to-a-long-random-string"
    try:
        app = create_app()
        with pytest.raises(RuntimeError):
            async with app.router.lifespan_context(app):
                pass
    finally:
        s.allow_lan, s.secret_key = orig
