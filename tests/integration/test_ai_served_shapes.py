# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE SERVED AI SHAPES ARE PINNED HERE — R-54 §3b / Phase 0-6.

THE GAP THIS FILLS
------------------
`/ai/facts` is declared `-> dict` (`ai.py:26`) and `/ai/chat` is a `StreamingResponse`
(`ai.py:134`). `GroundingFact` is a Pydantic model that **never reaches the OpenAPI contract**,
because no route declares it as a `response_model`. So `make api-contract-check` stays green while
the shape the frontend consumes changes underneath it — the §3b finding, stated plainly:

    A contract check that cannot see a shape is not a guard for that shape.

Phase 0-5 already proved this happening for real: `GroundingFact` gained `link_id`, a new field on
the served `/ai/facts` and SSE `facts` shapes, and the contract counts did not move. `test_fact_pack_kinds`
then changed the *rendered value* of pct/ratio facts with the counts again unmoved. **Nothing
structural reds when tier-1 changes what the panel is handed.** This file is that guard, and it is
the release-relevant cover for the finding; R-61 (typed AI responses + contract regen) is the
durable fix and is post-release.

WHAT IT PINS
------------
* `/ai/facts` envelope keys/types + the `count` invariant + the served disclaimer.
* Every served fact carries **every field `frontend/src/api/ai.ts::GroundingFactDTO` declares** —
  the panel's own contract, read from the frontend source, not a copy — PLUS `link_id` (served since
  0-5, consumed by the Phase-1 registry).
* The served fact key set equals the **full `GroundingFact` model** — so a field the backend drops in
  serialization reds, and a new backend field is *noticed* (the frontend contract then updated
  deliberately, not by silent drift).
* The SSE `facts` / `provenance` / `done` event shapes, and their ordering (facts lead; the legend
  precedes its deltas; done is last and unique). `fallback_signal` on the validator-rejected branch —
  the D-070 served field the panel reads.

REDUNDANT-ROUTE AUDIT (F-6 consequence, and it MATTERS here). The shapes are read from the SERVED
WIRE — `GET /ai/facts` and the `POST /ai/chat` SSE stream — never from `GroundingFact` in-process.
Asserting against the Python model would be **circular**: it would stay green even if a route stopped
serving the model (typed a `response_model` that stripped keys, changed `model_dump`, hand-built a
narrower dict). The model is used only to DERIVE the expected field set; the SERVED bytes are what is
checked against it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.disclaimer import DISCLAIMER
from app.schemas.ai import GroundingFact

REPO = Path(__file__).resolve().parents[2]
AI_TS = REPO / "frontend" / "src" / "api" / "ai.ts"


# ── Reading the FRONTEND's own declared contract (not a copy of it) ──────────────────────────

def _ts_interface_fields(name: str) -> set[str]:
    """The field names of a TypeScript interface in `ai.ts` — the frontend's OWN declaration.

    Parsed from the source (as `test_served_link_ids` parses `AppRoutes.tsx`) so the pin tracks what
    the panel actually consumes: add a field to the DTO and this guard extends to require it,
    automatically.
    """
    src = AI_TS.read_text(encoding="utf-8")
    m = re.search(rf"export interface {name} \{{(.*?)\n\}}", src, re.S)
    assert m, f"interface {name} not found in ai.ts — the parser drifted and this guard is blind"
    return set(re.findall(r"^\s*(\w+)\??:", m.group(1), re.M))


FRONTEND_FACT_FIELDS = _ts_interface_fields("GroundingFactDTO")
FRONTEND_FACTPACK_FIELDS = _ts_interface_fields("FactPack")
MODEL_FACT_FIELDS = set(GroundingFact.model_fields)


async def _stream_events(app_client, question: str = "What is my net worth?") -> list[dict]:
    r = await app_client.post("/api/v1/ai/chat", json={"question": question})
    assert r.status_code == 200
    out: list[dict] = []
    for line in r.text.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload:
                out.append(json.loads(payload))
    return out


def _facts_of(events: list[dict]) -> list[dict]:
    return next(e["facts"] for e in events if e.get("type") == "facts")


# ── Blindness pins for the parsed contracts ──────────────────────────────────────────────────

def test_the_parsed_frontend_contract_is_not_vacuous():
    """If the ai.ts parse yields nothing, every pin below passes by requiring nothing."""
    assert {"label", "value"} <= FRONTEND_FACT_FIELDS, (
        f"GroundingFactDTO parsed as {sorted(FRONTEND_FACT_FIELDS)} — missing label/value means the "
        f"parser drifted and the fact-shape pins have gone blind"
    )
    assert {"intent", "facts", "count", "disclaimer"} <= FRONTEND_FACTPACK_FIELDS, (
        f"FactPack parsed as {sorted(FRONTEND_FACTPACK_FIELDS)} — the envelope pin has gone blind"
    )
    assert len(MODEL_FACT_FIELDS) >= len(FRONTEND_FACT_FIELDS), (
        "the frontend declares more fact fields than the backend model has — a contract inversion"
    )


# ── `/ai/facts` envelope ─────────────────────────────────────────────────────────────────────

async def test_ai_facts_envelope_matches_the_frontend_factpack_shape(app_client):
    """The GET envelope carries exactly the keys `FactPack` declares, with the invariant types."""
    r = await app_client.get("/api/v1/ai/facts", params={"q": "What is my net worth?"})
    assert r.status_code == 200
    body = r.json()

    assert set(body) == FRONTEND_FACTPACK_FIELDS, (
        f"/ai/facts served keys {sorted(body)} but the frontend FactPack expects "
        f"{sorted(FRONTEND_FACTPACK_FIELDS)} — the panel reads this envelope by name"
    )
    assert isinstance(body["intent"], str) and body["intent"]
    assert isinstance(body["facts"], list)
    assert isinstance(body["count"], int)
    assert body["count"] == len(body["facts"]), (
        f"count={body['count']} disagrees with {len(body['facts'])} served facts — the panel trusts count"
    )
    assert body["disclaimer"] == DISCLAIMER, (
        "the served disclaimer must be the ONE permitted literal (Commitment 2), not a variant"
    )


# ── The served fact shape — both the GET pack and the SSE facts event ────────────────────────

async def test_every_served_fact_carries_the_full_frontend_and_model_field_set(app_client):
    """A served fact must satisfy BOTH the frontend's declared needs AND the full backend model.

    THE STRUCTURAL PIN. `link_id` is in the model set and therefore required here — the field
    Phase 0-5 added that the contract counts could not see. If a route ever serves a narrower dict
    (a `response_model` that strips undeclared keys is the classic way), this reds; the contract
    check does not.
    """
    # Both surfaces the panel can read facts from must carry the same shape.
    get_facts = (await app_client.get("/api/v1/ai/facts",
                                      params={"q": "what is XIRR"})).json()["facts"]
    sse_facts = _facts_of(await _stream_events(app_client, "what is XIRR"))

    for surface, facts in (("/ai/facts", get_facts), ("SSE facts", sse_facts)):
        assert facts, f"{surface} served no facts — the shape pin is vacuous for this question"
        for f in facts:
            keys = set(f)
            missing_frontend = FRONTEND_FACT_FIELDS - keys
            assert not missing_frontend, (
                f"{surface} fact {f.get('label')!r} is missing frontend-consumed field(s) "
                f"{sorted(missing_frontend)} — the panel reads these by name (ai.ts)"
            )
            assert keys == MODEL_FACT_FIELDS, (
                f"{surface} fact {f.get('label')!r} served keys {sorted(keys)} but the "
                f"GroundingFact model is {sorted(MODEL_FACT_FIELDS)}. A dropped field breaks the "
                f"panel invisibly to the contract check; a new field must update the frontend "
                f"contract deliberately (§3b / R-61)."
            )
            assert isinstance(f["label"], str) and isinstance(f["value"], str), (
                f"{surface}: label/value must be strings — the panel renders them verbatim"
            )
            assert f["link_id"] is None or isinstance(f["link_id"], str), (
                f"{surface}: link_id must be a string or null (never omitted) — {f['link_id']!r}"
            )


# ── The SSE event shapes ─────────────────────────────────────────────────────────────────────

async def test_the_facts_event_leads_and_carries_a_list(app_client):
    events = await _stream_events(app_client)
    types = [e["type"] for e in events]
    assert types[0] == "facts", f"the facts event must lead the stream (clause 7); order was {types}"
    assert isinstance(events[0]["facts"], list)
    assert set(events[0]) == {"type", "facts"}, (
        f"the facts event carries only type+facts; served {sorted(events[0])}"
    )


async def test_the_provenance_event_shape_is_exact(app_client):
    """{type, kind, narrated, provenance} — the panel reads kind/narrated/provenance by name.

    narrated is a bool the panel keys its italic model-text treatment on; a string here would be
    truthy and mis-style every answer.
    """
    events = await _stream_events(app_client)
    prov = next(e for e in events if e.get("type") == "provenance")
    assert set(prov) == {"type", "kind", "narrated", "provenance"}, (
        f"provenance event served keys {sorted(prov)} — the panel reads these by name (ai.ts ChatEvent)"
    )
    assert isinstance(prov["kind"], str) and prov["kind"]
    assert isinstance(prov["narrated"], bool), (
        f"narrated must be a bool, not {type(prov['narrated']).__name__} — the panel's model-text "
        f"treatment keys on it, and any string is truthy"
    )
    assert isinstance(prov["provenance"], str) and prov["provenance"]


async def test_the_done_event_carries_its_required_keys(app_client):
    """done always carries {type, grounded, provider, disclaimer}; it is last and unique."""
    events = await _stream_events(app_client)
    types = [e["type"] for e in events]
    assert types[-1] == "done", f"done must terminate the stream; order was {types}"
    assert types.count("done") == 1, "exactly one done event per answer"

    done = events[-1]
    assert {"type", "grounded", "provider", "disclaimer"} <= set(done), (
        f"done served {sorted(done)} — missing a required key the panel reads"
    )
    assert isinstance(done["grounded"], bool)
    assert isinstance(done["provider"], str) and done["provider"]
    assert done["disclaimer"] == DISCLAIMER


async def test_the_fallback_signal_shape_on_the_validator_rejected_branch(app_client, monkeypatch):
    """D-070's served signal is a string on `done`, present ONLY when the answer was rejected.

    Driven against the real reject branch (an ungrounded provider), because that is the only place
    the field appears — a shape pinned on a branch that never emits it is a pin on nothing. The
    provenance/legend semantics are `test_ai_provenance`'s job; here it is purely the SHAPE the panel
    reads (`AskPanel.tsx:196` → `event.fallback_signal`).
    """
    from app.providers.ai import reset_ai_provider
    from app.schemas.ai import AIChunk, HealthStatus

    class _UngroundedProvider:
        name = "openai_compatible"

        async def health(self):
            return HealthStatus(available=True, provider=self.name, models=["stub"])

        async def chat(self, req):
            yield AIChunk(delta="Your net worth is 9,999,999.99 SGD and you should buy more.")
            yield AIChunk(done=True)

    reset_ai_provider()
    monkeypatch.setattr("app.ai.grounding.get_ai_provider", lambda: _UngroundedProvider())
    try:
        done = next(e for e in await _stream_events(app_client) if e["type"] == "done")
    finally:
        reset_ai_provider()

    assert "fallback_signal" in done, (
        "the validator-rejected branch did not serve fallback_signal — D-070's signal is the field "
        "the panel shows to say the model's answer was withheld"
    )
    assert isinstance(done["fallback_signal"], str) and done["fallback_signal"]


def test_this_pin_is_what_the_contract_cannot_see():
    """The §3b statement, asserted: `GroundingFact` is NOT in the frozen contract's schemas.

    If a future change DID type the AI responses (R-61), this reds — a deliberate signpost that the
    served-shape guarding can then move to the contract and this file's job is done, rather than the
    two silently overlapping.
    """
    contract = json.loads((REPO / "docs" / "specs" / "API-CONTRACT.json").read_text())
    assert "GroundingFact" not in contract.get("schemas", {}), (
        "GroundingFact is now a contract schema — the AI responses were typed (R-61?). The contract "
        "can see these shapes now; retire or narrow this file's overlap deliberately."
    )
