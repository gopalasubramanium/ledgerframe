# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI chat endpoint — grounded, streaming via Server-Sent Events."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.grounding import answer_stream
from app.api.deps import get_db

router = APIRouter()


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.get("/ai/facts")
async def ai_facts(q: str = Query(min_length=1, max_length=500),
                   session: AsyncSession = Depends(get_db)) -> dict:
    """The grounded fact pack + classified intent for a question — the 'answer basis'.
    No model call; read-only; the same facts the assistant is allowed to use."""
    from app.ai.intent import classify_intent
    from app.ai.tools import gather_facts

    facts = await gather_facts(session, q)
    return {
        "intent": classify_intent(q).value,
        "facts": [f.model_dump(mode="json") for f in facts],
        "count": len(facts),
        "disclaimer": "Information only, not financial advice.",
    }


def _is_local_url(url: str) -> bool:
    """True if the URL points at this device (localhost), so nothing leaves it."""
    u = (url or "").lower()
    return any(h in u for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "://::1"))


@router.get("/ai/grounding-status")
async def ai_grounding_status() -> dict:
    """Whether AI answers are grounded, how they're narrated, and where data goes.
    No secrets — only the base URL's host is considered, never the key (§8)."""
    from app.core.config import get_settings
    from app.providers.ai import get_ai_provider

    s = get_settings()
    provider = get_ai_provider()
    health = await provider.health()

    # Determine the privacy mode from the configured provider (not just health).
    if not s.ai_enabled or s.ai_provider == "disabled":
        mode, remote, privacy = "deterministic", False, "Deterministic — fact-only answers; nothing is sent anywhere."
    elif s.ai_provider == "openai_compatible" and s.openai_base_url:
        local = _is_local_url(s.openai_base_url)
        remote = not local
        mode = "local" if local else "remote"
        privacy = ("On-device (local OpenAI-compatible endpoint) — data stays on this device."
                   if local else
                   "Remote — prompts (incl. portfolio facts) are sent to the configured provider.")
    else:  # hailo / ollama (local NPU)
        mode, remote, privacy = "local", False, "On-device (local Hailo/Ollama) — portfolio facts stay on this device."

    return {
        "grounded": True,
        "narration": provider.name if health.available else "deterministic-fallback",
        "model": (health.models[0] if health.models else None),
        "ai_enabled": s.ai_enabled,
        "mode": mode,
        "remote": remote,
        "privacy_label": privacy,
        "last_error": health.detail or None,
    }


@router.post("/ai/chat")
async def ai_chat(payload: ChatIn, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    async def event_gen():
        async for event in answer_stream(session, payload.question):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
