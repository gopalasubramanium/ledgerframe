# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE SETTINGS AI TAB TELLS THE TRUTH — Finding 6, owner-ruled (a) 2026-07-20.

AI-surfaces §13-C / §14-3.

WHAT THE 0a WALK FOUND, at the line ABOVE the note the pre-pass was checking. The tab read:

    "AI is on — provider hailo, model (default)."

while ``/ai/grounding-status``, on the same instance at the same moment, served
``openai_compatible`` / ``stub-narrator`` — and that was the provider actually answering.

MECHANISM: ``/system/ai-config`` built its answer from ``read_env()`` — the repo-root ``.env``
FILE — while ``/ai/grounding-status`` built its answer from ``get_settings()``, the EFFECTIVE
resolution. **Pydantic settings let OS environment override ``.env``**, so the CONFIGURED provider
(what the file says) and the EFFECTIVE provider (what the process runs) are two sources of truth
for one fact, and they diverge whenever OS env is set — under a systemd ``Environment=`` or a
container ``-e``, in production, silently.

⚠ THIS DRIVE INDUCED THE DIVERGENCE, and the record says so. OS-env overrides are exactly how the
isolated pre-pass harness configures itself, so the walk did not prove the owner's install is
misreporting. **What it proved is that the two CAN disagree and the tab cannot tell** — while
`page-settings.md` §15st-1's ratified note promises *"this line reflects the served configuration
only."* Under an override that sentence was false.

THE FIX IS A RULING, NOT A REPAIR, which is why it waited for the owner: choosing between *report
the CONFIGURED value* and *report the EFFECTIVE value* decides what the tab is FOR. The owner ruled
**(a) — serve the effective settings, what is running.**
"""

from __future__ import annotations

import pytest


async def _config(app_client) -> dict:
    r = await app_client.get("/api/v1/system/ai-config")
    assert r.status_code == 200
    return r.json()


async def _grounding(app_client) -> dict:
    r = await app_client.get("/api/v1/ai/grounding-status")
    assert r.status_code == 200
    return r.json()


# --- The env-override case that induced the disagreement --------------------------------------- #


async def test_ai_config_reports_the_provider_the_process_actually_runs(app_client, tmp_path,
                                                                        monkeypatch):
    """SEEN RED: `.env` says hailo, OS env says openai_compatible, the tab said 'hailo'.

    This is the exact shape of the 0a divergence, reproduced deliberately: a ``.env`` FILE holding
    one provider while the OS environment — which pydantic settings let win — holds another.
    """
    import app.core.envfile as envfile
    from app.core.config import reload_settings

    env_file = tmp_path / ".env"
    env_file.write_text(
        "LEDGERFRAME_AI_ENABLED=true\n"
        "LEDGERFRAME_AI_PROVIDER=hailo\n"
        "LEDGERFRAME_AI_MODEL=from-the-file\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(envfile, "ENV_PATH", env_file)

    # The OS environment — a systemd `Environment=`, a container `-e`, or this harness — wins.
    monkeypatch.setenv("LEDGERFRAME_AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LEDGERFRAME_OPENAI_BASE_URL", "http://127.0.0.1:8402/v1")
    monkeypatch.setenv("LEDGERFRAME_AI_MODEL", "actually-running")
    reload_settings()
    try:
        cfg = await _config(app_client)
        assert cfg["provider"] == "openai_compatible", (
            f"the AI tab reports provider {cfg['provider']!r} from the .env FILE while the process "
            f"is running 'openai_compatible'. §15st-1 promises this line reflects the served "
            f"configuration; a tab that names a provider which is not answering breaks that "
            f"promise (Finding 6, ruled (a))."
        )
        assert cfg["model"] == "actually-running", (
            f"model reported as {cfg['model']!r} — the file's value, not the running one."
        )
    finally:
        reload_settings()


async def test_the_tab_and_the_ask_panel_cannot_disagree(app_client):
    """ONE FACT, ONE SOURCE. The two surfaces that describe how an answer is produced must agree.

    This is the guard for the RULE rather than for the symptom: it does not care which provider is
    configured, only that the Settings tab and the Ask panel's posture are resolved from the same
    place. Two surfaces working the same fact out separately is what Finding 6 was.
    """
    cfg = await _config(app_client)
    ground = await _grounding(app_client)

    assert cfg["remote"] == ground["remote"], (
        f"the Settings AI tab says remote={cfg['remote']} while the Ask panel says "
        f"remote={ground['remote']} — two sources of truth for where the user's data goes."
    )
    assert cfg["no_egress"] == ground["no_egress"]
    assert cfg["kind"] == ground["kind"]


# --- The tab describes the configuration in the RULED VOCABULARY -------------------------------- #


async def test_the_tab_summary_is_served_not_composed(app_client):
    """§0-C — the panel/tab composes no self-describing string.

    A sentence about what the device is doing with the user's data, assembled in the browser, is a
    second source of truth for a claim the product makes about itself. That is the defect this
    milestone exists to undo; it must not be reintroduced on the tab that describes the AI.
    """
    cfg = await _config(app_client)
    assert cfg.get("summary"), "the AI tab's sentence must be SERVED, not composed client-side"
    assert isinstance(cfg["summary"], str) and len(cfg["summary"]) > 20


async def test_the_summary_names_a_kind_of_intelligence(app_client):
    """The tab says WHICH KIND is active, in the owner's vocabulary (§14-2)."""
    from app.ai.vocabulary import KIND_LABEL

    cfg = await _config(app_client)
    assert cfg["kind"] in KIND_LABEL, f"unknown kind {cfg['kind']!r}"
    named = [k for k, label in KIND_LABEL.items() if label.lower() in cfg["summary"].lower()]
    assert named or "built-in" in cfg["summary"].lower(), (
        f"the tab summary names no kind of intelligence: {cfg['summary']!r}. "
        f"§14-3 requires it to say WHICH kind is active."
    )


async def test_the_summary_states_the_data_locality_consequence(app_client):
    """§14-3 half 2 — naming the kind is not enough; the tab states what it MEANS for the data."""
    cfg = await _config(app_client)
    low = cfg["summary"].lower()
    # The consequence is stated in whichever direction is TRUE for the active kind — "no data
    # leaves this device" / "data leaves this device" / "nothing is sent anywhere". A guard that
    # demanded one phrasing would force the built-in states to borrow the remote states' idiom.
    assert ("leave" in low or "leaves" in low or "sent to" in low or "sent anywhere" in low), (
        f"the tab summary states no data-locality consequence: {cfg['summary']!r}. "
        f"Which kind is active is only useful to a reader who is told what it means for "
        f"their data (§14-3)."
    )


async def test_the_tab_never_shows_the_retired_vendor_word(app_client):
    """§14-2 — 'hailo' is retired as a USER-FACING word.

    ⚠ Scoped to the SUMMARY deliberately. The `provider` field still carries the internal id, and
    must: it is the value the config API round-trips, and the owner's `.env` keeps working because
    of it. What is retired is the word a USER READS.
    """
    cfg = await _config(app_client)
    assert "hailo" not in cfg["summary"].lower(), (
        f"the retired vendor word is in served user-facing copy: {cfg['summary']!r}. "
        f"GLOSSARY.md's deprecated table gives 'On-device model (Ollama-compatible)'."
    )


# --- Anti-blind pins ---------------------------------------------------------------------------- #


def test_every_posture_maps_to_a_kind():
    """Coverage: a new posture branch that forgets its kind reds here rather than KeyError-ing in
    production. Same shape as the posture-copy coverage assertion (§12-3)."""
    from app.api.v1.routes.ai import POSTURE_COPY
    from app.ai.vocabulary import POSTURE_KIND

    assert set(POSTURE_COPY) == set(POSTURE_KIND), (
        f"posture branches without a declared kind: {set(POSTURE_COPY) ^ set(POSTURE_KIND)}"
    )


@pytest.mark.parametrize("kind", ["built_in", "on_device_model", "external_model"])
def test_every_kind_has_a_label_and_a_data_locality_answer(kind: str):
    """A kind with no label or no declared locality would silently borrow another kind's."""
    from app.ai.vocabulary import KIND_IS_REMOTE, KIND_LABEL

    assert KIND_LABEL.get(kind)
    assert kind in KIND_IS_REMOTE


def test_every_posture_the_product_can_reach_has_a_tab_sentence():
    """The tab's lookup is `AI_TAB_COPY[posture if posture in AI_TAB_COPY else kind]`, so every
    posture must resolve — by its own key or by its kind — or the tab KeyErrors in production.

    ⚠ TWO BUILT-IN POSTURES, TWO SENTENCES, DELIBERATELY. `no_egress` and `disabled` are the same
    KIND and are NOT interchangeable copy: one is a switch the user chose, the other is a switch
    they can choose. Telling a user who turned no-egress on that their AI is "off" would read as a
    misconfiguration rather than the product doing exactly what they asked.
    """
    from app.ai.vocabulary import POSTURE_KIND
    from app.api.v1.routes.system import AI_TAB_COPY

    unreachable = [
        posture for posture, kind in POSTURE_KIND.items()
        if posture not in AI_TAB_COPY and kind not in AI_TAB_COPY
    ]
    assert not unreachable, f"postures with no served tab sentence: {unreachable}"
    assert len(set(AI_TAB_COPY.values())) == len(AI_TAB_COPY), (
        "two postures serve the SAME tab sentence — the tab would describe different states "
        "identically, which is the failure this copy exists to prevent."
    )
