# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI provider data contracts and grounding structures."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.disclaimer import DISCLAIMER


class HealthStatus(BaseModel):
    available: bool
    provider: str
    detail: str = ""
    models: list[str] = []


class ModelInfo(BaseModel):
    name: str
    size: str | None = None
    family: str | None = None


class ChatMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


class AIRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.2
    # Generous cap: reasoning models (qwen, deepseek-r1) can spend a couple thousand
    # tokens "thinking" before emitting the answer, so a small cap cuts off before any
    # answer appears. This is only a ceiling — the prompt keeps the *answer* short.
    max_tokens: int = 4000


class AIChunk(BaseModel):
    delta: str = ""
    done: bool = False


class GroundingFact(BaseModel):
    """A single verified fact / evidence item passed to the model and surfaced to the
    user. Core fields (label/value/source/timestamp/entitlement/is_stale) are the
    original contract; the rest are optional evidence metadata (B5) — all additive."""

    label: str
    value: str
    source: str = "ledgerframe"
    timestamp: datetime | None = None
    entitlement: str | None = None
    is_stale: bool = False
    # --- evidence model (B5), all optional ---
    fact_type: str | None = None            # portfolio | holding | market | news | data_quality | disclaimer
    unit: str | None = None
    currency: str | None = None
    provider: str | None = None
    valuation_method: str | None = None
    source_url: str | None = None
    confidence: str | None = None           # high | medium | low
    related_symbols: list[str] = []
    related_holding_ids: list[int] = []
    #: R-54 §9-D — the SERVED SEMANTIC LINK ID for this fact, or None.
    #:
    #: The backend issues an ID; the FRONTEND owns the ID→route registry (Phase 1). That split is
    #: the ruling: route knowledge lives where routes live, and the backend never hardcodes a
    #: frontend path. Namespaced `<kind>:<key>` — `help:<entry-id>`, `page:<route>`.
    #:
    #: `None` is a real answer, not a gap: a fact with no canonical destination gets no link, and
    #: tier-1 must not invent one. A link that resolves to nothing is a dead affordance with extra
    #: steps, which is what the bidirectional guard exists to prevent.
    link_id: str | None = None
    explanation: str | None = None


class AIAnswer(BaseModel):
    text: str
    facts: list[GroundingFact] = []
    provider: str
    model: str | None = None
    grounded: bool = True
    disclaimer: str = DISCLAIMER
