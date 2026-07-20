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
from app.core.disclaimer import DISCLAIMER

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
        "disclaimer": DISCLAIMER,
    }


# ── RATIFIED POSTURE COPY (§9 (f): "strings stay PROPOSED until 0a"; ratified 2026-07-20) ──
#
# The one sentence on the Ask panel that states what the DEVICE is doing. It is served, never
# composed client-side, for the reason §0-C exists: a posture sentence assembled in the browser is
# a second source of truth for a claim the product makes about itself.
#
# Named constants rather than inline literals so the ratified wording can be PINNED
# (`tests/unit/test_posture_copy_ratified.py`, the AC-L3 spec<->code parity pattern). Inline
# literals in a route body cannot be bound to a record without grepping a function, and a string
# nobody can bind is a string that drifts.
#
# ⚠ NO_EGRESS carries a divergence found at the 0a walk — see ai-surfaces.md §12-3. The drafted
# copy said no-egress meant no AI at all; what SHIPPED says answers are still built, from the
# user's data, without narration. The shipped sentence is the true one, and R-54 (tier-1
# deterministic answering) owns the amendment when that capability formally lands.
POSTURE_NO_EGRESS = ("No-egress is on — this device makes no outbound calls, so answers are built "
                     "from your data only, with no AI narration.")
POSTURE_DISABLED = "Deterministic — fact-only answers; nothing is sent anywhere."
POSTURE_LOCAL_OPENAI = "On-device (local OpenAI-compatible endpoint) — data stays on this device."
POSTURE_REMOTE = "Remote — prompts (incl. portfolio facts) are sent to the configured provider."
POSTURE_LOCAL_NPU = "On-device (local Hailo/Ollama) — portfolio facts stay on this device."

#: Every posture string the product can serve. The guard iterates THIS, so a new posture branch
#: that forgets to add its string here is caught by a coverage assertion rather than shipping
#: unratified copy on the one surface built to be honest about posture.
POSTURE_COPY = {
    "no_egress": POSTURE_NO_EGRESS,
    "disabled": POSTURE_DISABLED,
    "local_openai": POSTURE_LOCAL_OPENAI,
    "remote": POSTURE_REMOTE,
    "local_npu": POSTURE_LOCAL_NPU,
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

    # NO-EGRESS FIRST, and it OVERRIDES the configured provider (R-22 AMENDMENT, owner
    # 2026-07-20, option (b)). No-egress means zero outbound calls INCLUDING LOOPBACK, so a
    # configured local provider is not answering either: `egress_client` refuses before it looks
    # at any URL. Reporting "On-device — portfolio facts stay on this device" here would describe
    # a local AI that is not running, on the one surface built to be honest about posture.
    #
    # This is why the flag is SERVED rather than inferred from `health.available`. An unavailable
    # provider and a switched-off one look identical from the client, and they are the opposite of
    # each other: one is broken, one is the product doing exactly what it promised. That is the
    # distinction Commitment 3 turns on, and the same one the typed EgressBlocked re-raise
    # preserves inside the providers.
    from app.core.egress import egress_allowed

    no_egress = not await egress_allowed()

    if no_egress:
        mode, remote, privacy = "deterministic", False, POSTURE_NO_EGRESS
    elif not s.ai_enabled or s.ai_provider == "disabled":
        mode, remote, privacy = "deterministic", False, POSTURE_DISABLED
    elif s.ai_provider == "openai_compatible" and s.openai_base_url:
        local = _is_local_url(s.openai_base_url)
        remote = not local
        mode = "local" if local else "remote"
        privacy = POSTURE_LOCAL_OPENAI if local else POSTURE_REMOTE
    else:  # hailo / ollama (local NPU)
        mode, remote, privacy = "local", False, POSTURE_LOCAL_NPU

    return {
        "grounded": True,
        "narration": provider.name if health.available else "deterministic-fallback",
        "model": (health.models[0] if health.models else None),
        "ai_enabled": s.ai_enabled,
        "mode": mode,
        "remote": remote,
        "no_egress": no_egress,
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
