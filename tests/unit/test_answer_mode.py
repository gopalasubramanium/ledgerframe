# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE DECLARED ANSWER-MODE — R-54 §9-A/§9-F, Phase 1 delta 2.

`_answer_mode` is where the tier boundary is DECLARED from provider health + the in-process
limiter. It replaces the old fallback branch's `not health.available or _rate_limited()`, whose
two conditions shared one `if` and were therefore indistinguishable (§0-I). Splitting them into a
named mode is what lets the two §9-F promises be guarded separately:

  * tier 1 (deterministic posture) NEVER consults the limiter, so it can never be rate-limited —
    "zero network calls by construction" also means "never throttled";
  * a rate-limited tier 2 FALLS BACK TO tier 1 (a real deterministic answer), never withheld.

The served-path consequence — a tier-1 miss carries no facts — is proven end-to-end in
`tests/integration/test_tier1_miss_split.py`. This file pins the resolver in isolation.
"""

from __future__ import annotations

import pytest

from app.ai import grounding
from app.ai.tools import AnswerMode
from app.core.config import get_settings
from app.schemas.ai import HealthStatus


def _health(available: bool) -> HealthStatus:
    return HealthStatus(available=available, provider="test")


@pytest.fixture(autouse=True)
def _clear_limiter():
    grounding._request_times.clear()
    yield
    grounding._request_times.clear()


def test_model_unavailable_is_tier1_deterministic():
    assert grounding._answer_mode(_health(False)) is AnswerMode.DETERMINISTIC


def test_model_available_with_room_is_tier2_grounding():
    assert grounding._answer_mode(_health(True)) is AnswerMode.GROUNDING


def test_rate_limited_tier2_falls_back_to_tier1(monkeypatch):
    """§9-F: an available model whose limiter is exhausted degrades to tier 1, not to an error."""
    cap = get_settings().ai_max_requests_per_minute
    grounding._request_times[:] = [1e9] * cap  # far-future stamps → all still inside the window
    assert grounding._answer_mode(_health(True)) is AnswerMode.DETERMINISTIC


def test_tier1_posture_never_consults_the_limiter(monkeypatch):
    """The limiter is consulted ONLY when the model is available.

    A tier-1 posture (model unavailable) must not record a request — otherwise a burst of
    no-egress answers could exhaust a budget that exists to protect a model they never call, and
    "tier 1 is never rate-limited" would be false. Proven by side-effect: resolving the mode many
    times on an unavailable model leaves the limiter's recorded set empty.
    """
    for _ in range(get_settings().ai_max_requests_per_minute + 5):
        assert grounding._answer_mode(_health(False)) is AnswerMode.DETERMINISTIC
    assert grounding._request_times == [], (
        "tier-1 mode resolution consumed limiter budget it must never touch"
    )


def test_tier2_resolution_DOES_record_a_request():
    """The discriminator — the limiter side-effect is real for tier 2.

    Without this, `test_tier1_posture_never_consults_the_limiter` would pass even if the limiter
    had been disconnected entirely: it must be recording SOMETHING on the tier-2 path for its
    silence on the tier-1 path to mean anything.
    """
    grounding._answer_mode(_health(True))
    assert len(grounding._request_times) == 1
