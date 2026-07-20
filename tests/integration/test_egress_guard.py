# SPDX-License-Identifier: AGPL-3.0-or-later
"""release-readiness Part B/2 — Guarantee 5: no-egress means ZERO outbound calls.

FAIL-FIRST, and the RED had to be **real**: each test below configures a **LIVE provider** (not the
mock), turns no-egress **on**, and then asserts that **no HTTP client is ever constructed**. Against
the unguarded baseline the client *was* constructed and the call went out — that is the defect, and
these tests reproduced it before the guard landed.

The gap, precisely (verified by enumerating every call site of the old gate): ``no_egress_enabled``
was consulted from **news, briefing, markets-news and version-check only**. The market price
providers (kite · eodhd · coingecko · amfi · yahoo · external), the **ECB FX feed**, and **both AI
providers** never asked. Under ``privacy_mode`` they still went out.

It *looked* fine because a no-egress user usually also runs ``market_provider=mock`` — a
**configuration coincidence, not a guard**. Guarantee 5 is an absolute, so a guarantee that holds by
accident does not hold.

The structural test is the one that matters most: it makes the defect **unrepeatable**. A new
provider physically cannot forget to check, because constructing an ``httpx.AsyncClient`` outside the
one gate is a test failure.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

from app.core.egress import EgressBlocked

APP = Path(__file__).resolve().parents[2] / "app"


# --- The structural guard: there is exactly ONE way to get an HTTP client -----------------------


def test_no_module_may_construct_an_http_client_outside_the_egress_gate() -> None:
    """The choke point, enforced.

    A guard you must remember to call is a guard you will eventually forget — which is exactly how
    six provider paths ended up ignoring Guarantee 5. So the client cannot be built anywhere else.
    """
    offenders: list[str] = []
    for path in APP.rglob("*.py"):
        if path.name == "egress.py":
            continue  # the gate itself is the one place that may construct one
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\bhttpx\.(AsyncClient|Client)\s*\(", line):
                offenders.append(f"{path.relative_to(APP.parent)}:{i}")
    assert not offenders, (
        "these construct an HTTP client without passing the no-egress gate "
        f"(use app.core.egress.egress_client): {offenders}"
    )


# --- Behavioural: a LIVE provider, no-egress on, and the client is never built -------------------


@pytest.fixture
async def no_egress(app_client):
    """Turn no-egress ON exactly the way a user does — through the real settings endpoint."""
    r = await app_client.put("/api/v1/settings", json={"values": {"privacy_mode": "1"}})
    assert r.status_code == 200


@pytest.fixture
def forbid_http(monkeypatch):
    """Explode if anything so much as CONSTRUCTS an HTTP client.

    Not "asserts no request was sent" — *no client at all*. Under no-egress there must be no socket,
    no DNS lookup, and no timeout to wait out.
    """
    constructed: list[str] = []

    class Tripwire:
        def __init__(self, *a, **kw):
            constructed.append("httpx.AsyncClient")
            raise AssertionError(
                "an HTTP client was CONSTRUCTED while no-egress is on — Guarantee 5 says zero "
                "outbound calls"
            )

    monkeypatch.setattr(httpx, "AsyncClient", Tripwire)
    return constructed


async def _blocked(coro) -> bool:
    """The call must be refused by the gate, not by a network error."""
    try:
        await coro
    except EgressBlocked:
        return True
    return False


async def test_price_provider_coingecko_makes_no_call(no_egress, forbid_http) -> None:
    from app.providers.market.coingecko import fetch_prices

    assert await _blocked(fetch_prices(["bitcoin"]))
    assert not forbid_http, "the client was constructed"


async def test_price_provider_amfi_makes_no_call(no_egress, forbid_http) -> None:
    from app.providers.market.amfi import fetch_nav_all

    assert await _blocked(fetch_nav_all())
    assert not forbid_http


async def test_fx_feed_ecb_makes_no_call(no_egress, forbid_http) -> None:
    """The ECB FX feed was fully unguarded — FX is egress like any other."""
    from app.providers.market.ecb import fetch_ecb_daily

    assert await _blocked(fetch_ecb_daily())
    assert not forbid_http


async def test_ai_provider_makes_no_call(no_egress, forbid_http) -> None:
    """A remote LLM is still a network call — and it is the one carrying your figures.

    NOTE the assertion here is deliberately different. `health()` never raises by contract: it
    *reports*. So the invariant is not "EgressBlocked escaped" — it is "no client was constructed,
    and the provider says it is unavailable instead of pretending". That is the honest outcome
    (Guarantee 3): a withheld answer with a reason, never a guessed one.
    """
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m")
    status = await p.health()

    assert not forbid_http, "the client was constructed"
    assert status.available is False, "no-egress must not be reported as a healthy AI provider"


async def test_ai_chat_makes_no_call(no_egress, forbid_http) -> None:
    """The CHAT path — the one that would actually ship your figures off the device.

    (`list_models()` is deliberately not used here: it returns a static list and makes no call, so it
    would have been a test that could never have been red.)
    """
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider
    from app.schemas.ai import AIRequest, ChatMessage

    p = OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m")
    req = AIRequest(messages=[ChatMessage(role="user", content="what is my net worth")])

    gen = p.chat(req)
    blocked = False
    try:
        await gen.__anext__()
    except EgressBlocked:
        blocked = True
    finally:
        await gen.aclose()  # close it explicitly, or the refusal resurfaces at GC as an unraisable

    assert blocked, "the chat path went out over the network while no-egress was on"
    assert not forbid_http, "the client was constructed"


async def test_egress_is_allowed_again_when_no_egress_is_OFF(app_client) -> None:
    """The guard must not become a permanent kill-switch: with the toggle OFF, egress proceeds.

    Without this, a green suite could just mean "nothing calls out any more" — which would pass every
    other test in this file for entirely the wrong reason.
    """
    from app.core.egress import egress_allowed

    assert await egress_allowed() is True

    await app_client.put("/api/v1/settings", json={"values": {"privacy_mode": "1"}})
    assert await egress_allowed() is False


# --- BOTH providers refuse with the SAME TYPE, and neither retries ------------------------------
#
# AI-surfaces §0-E found the gap: `openai_compatible` deliberately re-raised `EgressBlocked`
# before its retry, with the reason written out — *"No-egress is a REFUSAL, not a transient
# failure … retrying it would be the very thing Guarantee 5 forbids."* `hailo_ollama` had no
# such case: its `except Exception` swallowed the refusal into `RuntimeError(str(exc))`.
#
# No call was made either way, so the behaviour was already safe. **The TYPE is the honesty.**
# Commitment 3 turns on telling *"you turned this off"* apart from *"it broke"*, and a caller
# holding a `RuntimeError` cannot tell them apart — so the Ask panel could not render a refusal
# as the product's posture WORKING rather than as an error. These tests hold both providers to
# the same contract so they cannot drift apart again.


async def _chat_raises(provider) -> Exception | None:
    from app.schemas.ai import AIRequest, ChatMessage

    req = AIRequest(messages=[ChatMessage(role="user", content="hi")])
    try:
        async for _ in provider.chat(req):
            pass
    except Exception as exc:  # noqa: BLE001 — the TYPE is what this test is about
        return exc
    return None


async def test_openai_compatible_chat_propagates_EgressBlocked_untyped_never_retried(
    no_egress, forbid_http
) -> None:
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m")
    exc = await _chat_raises(p)

    assert isinstance(exc, EgressBlocked), (
        f"openai_compatible turned a no-egress refusal into {type(exc).__name__}: {exc}. "
        "A refusal must keep its type all the way to the caller."
    )
    assert not forbid_http, "the client was constructed — the refusal came too late"


async def test_hailo_chat_propagates_EgressBlocked_untyped_never_retried(
    no_egress, forbid_http
) -> None:
    """The §0-E gap, closed.

    The model is passed explicitly: with no model configured, `chat()` calls `_select_model()`
    → `list_models()`, which catches every exception and returns `[]`, so `chat()` returns
    before it ever reaches the gate. That path is honest (no model → no answer) but it is not
    the one under test, and a test that never reached the gate would prove nothing.
    """
    from app.providers.ai.hailo_ollama import HailoOllamaProvider

    p = HailoOllamaProvider(base_url="http://127.0.0.1:8000", model="m")
    exc = await _chat_raises(p)

    assert isinstance(exc, EgressBlocked), (
        f"hailo turned a no-egress refusal into {type(exc).__name__}: {exc}. This was the "
        "§0-E gap: `except Exception` swallowed EgressBlocked into RuntimeError, losing the "
        "distinction between 'you turned this off' and 'it broke' — the exact distinction "
        "Commitment 3 turns on."
    )
    assert not forbid_http, "the client was constructed — the refusal came too late"


async def test_the_two_providers_refuse_identically(no_egress, forbid_http) -> None:
    """Pinned against drift: the guard above is per-provider, so it cannot see disagreement.

    Two tests that each pass in isolation can still describe two different products. This
    asserts the property that actually matters — a caller cannot tell the providers apart by
    how they refuse.
    """
    from app.providers.ai.hailo_ollama import HailoOllamaProvider
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider

    a = await _chat_raises(OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m"))
    b = await _chat_raises(HailoOllamaProvider(base_url="http://127.0.0.1:8000", model="m"))

    assert type(a) is type(b) is EgressBlocked, (
        f"the providers refuse differently: openai_compatible→{type(a).__name__}, "
        f"hailo→{type(b).__name__}. No-egress means the same thing on both."
    )


# --- The SERVED posture: no-egress overrides the configured provider ---------------------------
#
# R-22 AMENDMENT (owner 2026-07-20, option (b)): no-egress means zero outbound calls INCLUDING
# LOOPBACK, so a configured LOCAL provider is not answering either. `/ai/grounding-status` must
# say so. Reporting "On-device — portfolio facts stay on this device" while no-egress is on would
# describe a local AI that is not running, on the one surface built to be honest about posture.


async def test_grounding_status_reports_no_egress_and_overrides_the_provider(no_egress, app_client):
    body = (await app_client.get("/api/v1/ai/grounding-status")).json()

    assert body["no_egress"] is True, (
        "grounding-status does not report no-egress. The client cannot tell a SWITCHED-OFF AI "
        "from a BROKEN one without it, and those are opposites: one is the product doing exactly "
        "what it promised (Commitment 3)."
    )
    assert body["remote"] is False, "no outbound calls are possible, so nothing is remote"
    assert body["mode"] == "deterministic", (
        f"mode is {body['mode']!r} under no-egress. Per the R-22 amendment the device is not "
        "running a local model either — deterministic is what it is actually doing."
    )
    assert "no-egress" in body["privacy_label"].lower(), (
        f"the served privacy label does not name the posture: {body['privacy_label']!r}"
    )


async def test_grounding_status_does_not_claim_no_egress_when_it_is_off(app_client):
    """Pinned against going blind: a hardcoded True would satisfy the test above."""
    body = (await app_client.get("/api/v1/ai/grounding-status")).json()
    assert body["no_egress"] is False, (
        "grounding-status reports no-egress while the toggle is OFF — the posture label would "
        "tell the user the device makes no outbound calls when it may be about to make one."
    )


async def test_health_reports_REFUSED_BY_POSTURE_not_a_connection_error(no_egress, forbid_http):
    """FINDING 2 from the 0a specimen (owner ruled it in-scope by extension of (f)).

    Under no-egress the specimen found `/ai/grounding-status` serving this as `last_error`:

        "cannot connect to http://…/v1 — verify it's reachable from the device running
         LedgerFrame (try: curl …)"

    **Nothing failed to connect. The product refused to call it.** Phase 0.5 fixed exactly this
    confusion inside `chat()` with the typed `EgressBlocked` re-raise; `health()` → `list_models()`
    still swallowed it into the generic connection-diagnosis path, and `last_error` SERVED that to
    the client. A served string that misdescribes the product's own posture is the class this
    milestone exists to close — and it would send the first operator who read it hunting a network
    fault that does not exist.

    `health()` still does not RAISE — that contract is unchanged and deliberate
    (`test_ai_provider_makes_no_call` above depends on it): it REPORTS, and now it reports the
    right thing. Driven at the PROVIDER, which is where the defect lives; the route simply serves
    whatever `health().detail` says.
    """
    from app.providers.ai.hailo_ollama import HailoOllamaProvider
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider

    for provider in (
        OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m"),
        HailoOllamaProvider(base_url="http://127.0.0.1:8000", model="m"),
    ):
        status = await provider.health()
        detail = (status.detail or "").lower()

        assert status.available is False, f"{provider.name}: no-egress is not a healthy provider"
        for wrong in ("cannot connect", "verify it's reachable", "connection refused",
                      "no route", "timed out", "cannot resolve", "no models listed"):
            assert wrong not in detail, (
                f"{provider.name}: under no-egress health() blames the NETWORK ({wrong!r}): "
                f"{status.detail!r}\n"
                "Nothing failed to connect — no client was ever constructed. This is the posture "
                "working, and saying otherwise sends the reader after a fault that does not exist."
            )
        assert "no-egress" in detail, (
            f"{provider.name}: health() does not name the posture: {status.detail!r}"
        )
    assert not forbid_http, "a client was constructed while reporting health under no-egress"


async def test_health_still_diagnoses_a_REAL_connection_failure_when_egress_is_on(app_client):
    """Pinned against going blind: reporting 'no-egress' unconditionally would satisfy the above.

    With egress ON and nothing listening, the connection diagnosis is genuinely useful and must
    survive. The fix must narrow the posture message to the posture, not replace the diagnosis.
    """
    from app.providers.ai.openai_compatible import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(base_url="http://127.0.0.1:9/v1", api_key="k", model="m")
    status = await p.health()

    assert status.available is False
    assert "no-egress" not in (status.detail or "").lower(), (
        f"a real connection failure was reported as a posture refusal: {status.detail!r}"
    )
    assert status.detail, "a real failure must still carry a diagnosable reason"
