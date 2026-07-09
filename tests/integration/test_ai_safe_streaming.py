# SPDX-License-Identifier: AGPL-3.0-or-later
"""§3 safe streaming, §8 grounding-status, §9 briefing validation.

A mock model lets us prove unsafe/ungrounded model text is NEVER emitted — the
buffer-then-validate flow means the client only ever sees a validated answer or the
deterministic fact-only fallback.
"""

from __future__ import annotations

import pytest

from app.ai import grounding
from app.schemas.ai import AIChunk, HealthStatus
from app.seed.demo import seed_demo_data


class _FakeProvider:
    name = "fake-model"

    def __init__(self, text: str, available: bool = True):
        self._text, self._available = text, available

    async def health(self) -> HealthStatus:
        return HealthStatus(available=self._available, provider="fake",
                            models=["fake-1"] if self._available else [])

    async def chat(self, req):
        yield AIChunk(delta=self._text)
        yield AIChunk(done=True)


@pytest.fixture
def mock_model(monkeypatch):
    def _install(text: str, available: bool = True):
        monkeypatch.setattr(grounding, "get_ai_provider", lambda: _FakeProvider(text, available))
    return _install


async def _run(session, question):
    facts, text, done = [], "", None
    async for ev in grounding.answer_stream(session, question):
        if ev["type"] == "facts":
            facts = ev["facts"]
        elif ev["type"] == "delta":
            text += ev["delta"]
        elif ev["type"] == "done":
            done = ev
    return facts, text, done


async def test_unsafe_recommendation_never_shown(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("You should buy NVDA now — it's a strong buy, guaranteed returns.")
    facts, text, done = await _run(session, "what moved in my portfolio today?")
    assert "strong buy" not in text.lower() and "should buy" not in text.lower()
    assert done["provider"] == "fallback" and done.get("validation")
    assert facts  # answer-basis facts still surfaced


async def test_secret_never_shown(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("Sure — the key is LEDGERFRAME_SECRET_KEY=abcdef0123456789.")
    _, text, done = await _run(session, "what is my portfolio value?")
    assert "LEDGERFRAME_SECRET_KEY" not in text and "abcdef0123456789" not in text
    assert done["provider"] == "fallback"


async def test_fabricated_number_never_shown(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("Your portfolio is worth 9,998,877 SGD, up 4,321 SGD today.")
    _, text, done = await _run(session, "what is my portfolio value?")
    assert "9,998,877" not in text
    assert done["provider"] == "fallback"


async def test_valid_answer_is_shown(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("Your portfolio held broadly steady today. Information only, not financial advice.")
    _, text, done = await _run(session, "how is my portfolio?")
    assert "held broadly steady" in text
    assert done["provider"] == "fake-model" and done.get("intent")


async def test_reasoning_only_falls_back(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("<think>lots of secret reasoning about buying</think>")
    _, text, done = await _run(session, "what moved today?")
    assert "secret reasoning" not in text and "<think>" not in text
    assert done["provider"] == "fallback"


async def test_model_unavailable_falls_back(session, mock_model):
    await seed_demo_data(session)
    await session.flush()
    mock_model("irrelevant", available=False)
    _, text, done = await _run(session, "portfolio summary")
    assert done["provider"] == "fallback" and "not financial advice" in text.lower()


# --- §9: Daily Briefing uses the same validation ---------------------------- #

async def test_briefing_rejects_recommendation(session, monkeypatch):
    from app.services import briefing as bmod

    await seed_demo_data(session)
    await session.flush()
    monkeypatch.setattr("app.providers.ai.get_ai_provider",
                        lambda: _FakeProvider("You should sell everything now — strong buy elsewhere."))
    text = await bmod.generate_briefing(session)
    assert "strong buy" not in text.lower() and "sell everything" not in text.lower()
    assert "not financial advice" in text.lower()


async def test_briefing_rejects_secret(session, monkeypatch):
    from app.services import briefing as bmod

    await seed_demo_data(session)
    await session.flush()
    monkeypatch.setattr("app.providers.ai.get_ai_provider",
                        lambda: _FakeProvider("Briefing: LEDGERFRAME_SECRET_KEY=zzz999abc12345 today."))
    text = await bmod.generate_briefing(session)
    assert "LEDGERFRAME_SECRET_KEY" not in text


async def test_briefing_accepts_valid_narration(session, monkeypatch):
    from app.services import briefing as bmod

    await seed_demo_data(session)
    await session.flush()
    monkeypatch.setattr("app.providers.ai.get_ai_provider",
                        lambda: _FakeProvider("Global markets were mixed and your portfolio held broadly steady today."))
    text = await bmod.generate_briefing(session)
    assert "held broadly steady" in text


# --- §8: grounding-status endpoint ------------------------------------------ #

async def test_grounding_status_shape_and_no_secret(app_client):
    s = (await app_client.get("/api/v1/ai/grounding-status")).json()
    assert s["grounded"] is True
    assert s["mode"] in {"deterministic", "local", "remote"}
    assert "privacy_label" in s and isinstance(s["remote"], bool)
    # No secret material anywhere in the response.
    assert "api_key" not in str(s).lower() and "sk-" not in str(s)
