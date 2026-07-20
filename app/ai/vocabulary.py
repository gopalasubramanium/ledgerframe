# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE THREE KINDS OF INTELLIGENCE — one resolver, one vocabulary, one source of truth.

Owner ruling, AI-surfaces §14-2 (2026-07-20). ``GLOSSARY.md`` is the parent record; this module is
the code half, and `tests/unit/test_intelligence_vocabulary.py` binds the two (the AC-L3 spec↔code
parity pattern).

    Built-in intelligence   deterministic answers from the user's own figures; NO model involved;
                            works in every posture including no-egress.
    On-device model         an LLM running on this device (Ollama or compatible); questions and
                            figures never leave the device, but the narration IS model-generated.
    External model          a cloud API; data leaves the device, and the copy says so plainly.

WHY THIS MODULE EXISTS AT ALL, rather than each surface working the answer out for itself
-----------------------------------------------------------------------------------------
Because that is precisely what went wrong. **Finding 6** (§13-C): `/system/ai-config` answered from
``read_env()`` — the repo-root ``.env`` FILE — while `/ai/grounding-status` answered from
``get_settings()``, the EFFECTIVE resolution. Pydantic settings let OS environment override
``.env``, so the two disagreed the moment OS env was set, and the Settings tab could name a
provider that was **not the one answering** — on the surface whose ratified note promises *"this
line reflects the served configuration only"*.

**Two sources of truth for one fact is the whole defect.** So there is now ONE resolver, and every
surface that describes how an answer is produced calls it:

* `/ai/grounding-status` → the Ask panel's posture line
* `/system/ai-config`    → the Settings AI tab
* `app/ai/grounding.py`  → the per-answer provenance legend (§14-4)

A new surface that describes the AI must call `resolve_posture()`. Working it out again locally is
how this defect gets rebuilt.

NAMING THE STANDARD, NOT THE VENDOR
-----------------------------------
The served label is **"On-device model (Ollama-compatible)"**, never "hailo". The endpoint is
OpenAI-compatible and works with Ollama and its lookalikes, so a label naming one implementation is
false the moment a second one is what is running — the same defect class as Finding 6 itself, in
the vocabulary rather than in the plumbing. "hailo" survives as an internal provider id, a module
name and the ``LEDGERFRAME_HAILO_*`` env keys, all unchanged: the owner's live ``.env`` must keep
working across this rename (GLOSSARY.md deprecated table, AI-surfaces §14-2).
"""

from __future__ import annotations

# --- The three kinds ---------------------------------------------------------------------------- #

KIND_BUILT_IN = "built_in"
KIND_ON_DEVICE_MODEL = "on_device_model"
KIND_EXTERNAL_MODEL = "external_model"

#: The user-facing name of each kind. Kept string-equal to GLOSSARY.md by the parity guard.
KIND_LABEL: dict[str, str] = {
    KIND_BUILT_IN: "Built-in intelligence",
    KIND_ON_DEVICE_MODEL: "On-device model (Ollama-compatible)",
    KIND_EXTERNAL_MODEL: "External model",
}

#: Whether data leaves this device under each kind. The one consequence a reader most needs, and
#: the reason the three kinds are distinguished at all.
KIND_IS_REMOTE: dict[str, bool] = {
    KIND_BUILT_IN: False,
    KIND_ON_DEVICE_MODEL: False,
    KIND_EXTERNAL_MODEL: True,
}

#: Posture key (the five branches `/ai/grounding-status` reports) → kind. FIVE postures, THREE
#: kinds: the postures distinguish *why* nothing is being narrated (switched off vs sealed off),
#: which the Ask panel's posture line must say; the kinds distinguish *who wrote the sentence*,
#: which is what every other surface needs. Neither collapses into the other.
POSTURE_KIND: dict[str, str] = {
    "no_egress": KIND_BUILT_IN,
    "disabled": KIND_BUILT_IN,
    "local_openai": KIND_ON_DEVICE_MODEL,
    "local_npu": KIND_ON_DEVICE_MODEL,
    "remote": KIND_EXTERNAL_MODEL,
}


# --- THE PROVENANCE LEGEND (§14-4, owner ruling 2026-07-20 — the walk's centrepiece) ------------ #
#
# ⚑ PROPOSED until the owner's 3b look.
#
# WHY THIS EXISTS, in the owner's framing: the panel already showed the reader WHAT AN ANSWER IS
# BUILT FROM. It never showed WHO WROTE THE SENTENCE. Those are different questions, and the second
# is the one a reader needs in order to weigh the first — a figure they can check themselves and a
# figure a model phrased for them warrant different scrutiny even when they are the same figure.
#
# ⚠ THE LEGEND DESCRIBES WHAT HAPPENED, NEVER WHAT IS CONFIGURED. That distinction is the whole
# guard. A device configured with an on-device model that FELL BACK — provider down, rate limited,
# validation rejected the wording — produced a built-in answer, and must say so. Reading the legend
# off `resolve_posture()` would have been the natural implementation and would have been a LIE in
# exactly the states the fallback exists to handle: the panel would credit a model that wrote
# nothing. So `provenance_for()` takes the kind AND whether narration actually survived, and the
# guard drives a real fallback to prove it (`tests/integration/test_ai_provenance.py`).
PROVENANCE_BUILT_IN = "Built-in intelligence only — no model was used."
PROVENANCE_ON_DEVICE = "Facts: built-in · Narration: on-device model — nothing left this device."
PROVENANCE_EXTERNAL = "Facts: built-in · Narration: external model."

#: Every provenance line the product can serve. The guard iterates THIS, so a new generation path
#: that forgets to register its line is caught by a coverage assertion rather than shipping an
#: unratified — or absent — claim about authorship. Same shape as POSTURE_COPY (§12-3).
PROVENANCE_COPY: dict[str, str] = {
    KIND_BUILT_IN: PROVENANCE_BUILT_IN,
    KIND_ON_DEVICE_MODEL: PROVENANCE_ON_DEVICE,
    KIND_EXTERNAL_MODEL: PROVENANCE_EXTERNAL,
}


def kind_of_provider(provider) -> str:
    """The kind of the provider that ACTUALLY produced text — asked of the provider, not of config.

    ⚠ THIS EXISTS BECAUSE THE FIRST IMPLEMENTATION WAS WRONG, and the guard caught it. The legend
    originally took the kind from `resolve_posture()`, i.e. from CONFIGURATION. Driving a real
    narrated stream produced ``narrated=True`` alongside ``kind="built_in"`` — a narrated answer
    labelled *"no model was used"*, which is the precise lie §14-4 exists to prevent, arrived at by
    the precise route its own docstring warned about. Configuration describes what was set up. Only
    the object that emitted the tokens knows who wrote them.

    ⚠ AN UNDECLARED PROVIDER IS TREATED AS EXTERNAL, and the asymmetry is deliberate. The two
    possible errors here are not equally bad: calling a remote model "on-device" tells a user their
    data stayed put when it left, which is a **privacy claim the product cannot honour**; calling a
    local model "external" is a warning that is merely too strong. When the answer is unknown, the
    honest default is the one that cannot mislead about egress.
    """
    kind = getattr(provider, "kind", None)
    return kind if kind in PROVENANCE_COPY else KIND_EXTERNAL_MODEL


def provenance_for(kind: str, *, narrated: bool) -> tuple[str, str]:
    """The legend for an answer that was ACTUALLY produced this way. Returns ``(kind, line)``.

    ``narrated=False`` collapses to built-in **whatever the configuration says**, because that is
    what happened: the model's text was discarded (or never arrived), and every word on screen came
    from the engine. This is the same honesty the fallback signal already carries — D-070 tells the
    reader the answer fell back; the legend tells them what wrote the one they got.
    """
    effective = kind if narrated else KIND_BUILT_IN
    return effective, PROVENANCE_COPY[effective]


def is_local_url(url: str) -> bool:
    """True if the URL points at this device (localhost), so nothing leaves it."""
    u = (url or "").lower()
    return any(h in u for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "://::1"))


async def resolve_posture() -> tuple[str, str]:
    """The posture this device is ACTUALLY in, and the kind of intelligence that follows from it.

    Returns ``(posture_key, kind)``.

    ⚠ READ FROM ``get_settings()``, NEVER FROM THE ``.env`` FILE. Settings is the EFFECTIVE
    resolution — the same object `get_ai_provider()` constructs the live provider from — so what
    this returns is what is actually answering. Reading the file instead is Finding 6: under a
    systemd ``Environment=`` or a container ``-e`` the file and the process disagree, and every
    surface built from the file then describes a provider that is not running.

    NO-EGRESS IS CHECKED FIRST AND OVERRIDES THE CONFIGURED PROVIDER (R-22 amendment, owner
    2026-07-20, option (b)). No-egress means zero outbound calls INCLUDING LOOPBACK, so a
    configured local provider is not answering either — ``egress_client`` refuses before it looks
    at any URL. Reporting an on-device model here would describe a local AI that is not running.
    """
    from app.core.config import get_settings
    from app.core.egress import egress_allowed

    s = get_settings()

    if not await egress_allowed():
        posture = "no_egress"
    elif not s.ai_enabled or s.ai_provider == "disabled":
        posture = "disabled"
    elif s.ai_provider == "openai_compatible" and s.openai_base_url:
        posture = "local_openai" if is_local_url(s.openai_base_url) else "remote"
    else:  # hailo / ollama — a local endpoint by construction
        posture = "local_npu"

    return posture, POSTURE_KIND[posture]
