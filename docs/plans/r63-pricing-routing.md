# R-63 — Pricing routing reliability (fix the chain once and for all)

> **⚡ PRE-RELEASE, RD-9 Amendment 11.** Owner ruling at the R-54 close (2026-07-23):
> *"data is the core of this platform, can't leave it so loose" / "needs to be fixed once
> and for all."* **Investigation-first — a hard gate.** Phase A (read-only live diagnosis)
> is DONE and its findings ARE the survey core of §0. This file runs §0 → §9 and **STOPS**
> at §9 for the chat one-pass. No code has changed and none changes until §9 is ruled.
>
> Cross-refs: `docs/audit/05-PROVIDERS-AND-ROUTING.md` · `data-feed-routing.md` (R-38) ·
> `page-pricing-health.md` · `page-settings.md` · `docs/reference/alpha_vantage_claude_code_reference.md`
> (committed this session, `b88adbe`) · `ROADMAP.md` R-63 · `release-readiness.md` RD-9 Amdt 11.

---

## 0. SURVEY

### 0-A. Phase A — READ-ONLY LIVE DIAGNOSIS (evidence, 2026-07-23)

**Method (boundaries honoured):** live logs read in place; the live DB **copied** to a temp
path and inspected read-only (copy since deleted); settings/keys **loaded, never printed**;
one instrumented **5-call** AlphaVantage probe with real egress (the owner's own key), each
call's raw envelope captured. Live stack/data never written, never restarted. AV free/premium
entitlement labels cross-checked against the committed reference doc.

**⛳ THE ROOT CAUSE (dominant, affects every AV symbol): an entitlement-envelope PARSE mismatch.**
`external.py:124` injects `entitlement=delayed` on **every** AV call (added at F-4). With that
parameter, AlphaVantage returns the quote under a **decorated top-level key** —
`"Global Quote - DATA DELAYED BY 15 MINUTES"` — but `external.py:191` reads only
`data.get("Global Quote", {})`. It therefore gets `{}` on **every** entitled response, raises
`"empty quote (unknown symbol or rate limited)"`, and returns `UNAVAILABLE`. **The price is in
the response the whole time, under a key the parser never looks for.** The key IS entitled to
delayed data (AV served it); this is a parsing defect, not an entitlement or quota failure.

**Probe results (5 calls, all HTTP 200, no throttle):**

| # | Call | Result | Reading |
| --- | --- | --- | --- |
| 1 | TSLA GLOBAL_QUOTE **entitlement=delayed** (what the code sends) | key = `"Global Quote - DATA DELAYED BY 15 MINUTES"`; `data["Global Quote"]` = **absent** | **the bug, reproduced** |
| 2 | TSLA GLOBAL_QUOTE **no entitlement** | `{"Global Quote": {…}}`, price **378.93** | works without the param |
| 3 | **SBICARD.BSE** GLOBAL_QUOTE no entitlement | price **644.75** | `.BSE` **exonerated** |
| 4 | RELIANCE.BSE GLOBAL_QUOTE no entitlement (control) | price **1303.65** | `.BSE` class works |
| 5 | ZZZZINVALID GLOBAL_QUOTE no entitlement | `{"Global Quote": {}}` | AV's genuine-empty envelope |

**Live-log corroboration** (`~/.ledgerframe-data/logs/ledgerframe.log`): every AV symbol —
TSLA, AAPL, MSFT, NVDA, SPY, QQQ, GLD, SBICARD.BSE, AARK — logs the **identical**
`"AV quote unavailable … empty quote (unknown symbol or rate limited)"` (lines 13440–13651).
One line (13605) caught a genuine transient throttle: *"Burst pattern detected … no more than 5
requests per second."* — a **secondary** contributor during a 19-symbol serial blast, not the
dominant cause.

**Live-DB corroboration** (read-only copy): the three symptom instruments (TSLA id 22,
AARK id 27, SBICARD.BSE id 29) have **no `quotes` row at all** — so `get_cached_quote` returns
`source="none"`, the frontend appends `(corrected)` because a `source_override='alphavantage'`
is set (`PricingHealth.tsx:216`), and the valuation falls to cost → `ESTIMATED_VALUE`
(`portfolio.py:510`) → confidence base 40 − 15 (`"no source could price it"`) = **25/low**
(`confidence.py`), which is exactly what the owner sees. `routing_matrix` has `equity→* =
alphavantage` and `etf→US = alphavantage`; `privacy_mode=false` (egress on). CoinGecko (BTC,
65762) and AMFI (the fund) — both **keyless** — have real cached prices. **Only the
key-gated AV lane is dark.** (Aside for §9-i: TSLA has a **duplicate instrument** — id 22 with
the override, id 23 without; noted, not central.)

**Fan-out vs budget:** the refresh universe is holdings **plus** the market-overview default
set (`markets.py:26`: SPY/QQQ/DIA/EWJ/FEZ/EWU/EWH/INDA/EWS/… ≈ 16 ETF proxies). One pass fires
**19 AV calls**; AV free tier is **25/day** (reference §1). The owner's key returns *delayed*
data (a premium market-data entitlement), so it is not the 25/day free tier — but the per-second
burst guard still trips on a serial blast. Free-first ordering (f) would keep the money-free
lanes (yahoo/coingecko/amfi) carrying the load regardless.

### 0-B. The five investigation questions — answered, evidence-cited

- **(i) What does AV actually return, and is "premium" verified?** AV returns **valid delayed
  quote data** for every symbol tried, under the decorated envelope key when `entitlement=delayed`
  is sent. The key **is** entitled to 15-min-delayed market data (verified live, probe #1). The
  Settings **"premium"** label is **config-claimed and coarse**: the adapter's own `av_tier`
  (`external.py:116`) learns tier **only from INDEX_DATA** responses (a *different* premium
  product the key may lack), never from quotes — so it can read "unknown/free" while quotes are
  fully entitled. Two different "premium" notions are conflated.
- **(ii) Which path collapses distinct failures into one "none"?** Three layers, compounding:
  (1) `external.py:207-216` — one `except Exception` funnels **parse-miss, unknown-symbol,
  throttle (`RateLimited`), HTTP error** all into a single `UNAVAILABLE` quote with the message
  `"empty quote (unknown symbol or rate limited)"`; the `RateLimited` text is discarded.
  (2) `refresh_quote_detailed` (`market.py:684-691`) reports a generic `no_data` /
  *"unsupported on this provider, or limit hit"*. (3) `get_cached_quote` (`market.py:733-739`)
  stores/returns `source="none"` when no row exists; the UI appends `(corrected)`.
- **(iii) Why no fall-through to yahoo — does an override pin & remove the net?** **There is no
  fetch-time net at all.** `refresh_quote_detailed` only ever fetches from the **single active
  provider** (`get_provider()` = `alphavantage`); the `priority_chain` is a **display/ownership
  decision, never an execution fallback** — no code walks it to try the next provider. The
  `override` branch (`router.py:338-344`) does pin the head and return immediately with no
  capability revalidation, but even without an override the matrix/active-provider path fetches
  only AV. **Yahoo is never instantiated or called** (zero yahoo lines in the logs). So the
  shipped sentence — *"routing falls through to the default lane"* — describes a fallthrough that
  exists in the **decision** of which provider is *named*, never in the **execution** of fetching.
- **(iv) Why eodhd(no key) at priority 1 — skip or stall?** Neither. `DEFAULT_PRIORITY`
  (`router.py:150`) is a policy constant; `route()` selects the **active provider** when it is in
  the chain (`router.py:411`); `eodhd` is only **annotated `(no key)` for display**
  (`_chain_detail`) and is **never fetched**, because the chain is not walked at fetch time. It
  neither skips nor stalls — it is decorative.
- **(v) Why do stale chips never clear?** The three symbols have **no quote row**; each refresh
  gets `UNAVAILABLE` (price None) → the code correctly refuses to write a null price
  (`market.py:684`) → returns the (empty) cache → valuation falls to cost (`ESTIMATED_VALUE`).
  Nothing ever advances the state because the only lane tried (AV) always parse-fails. The chip is
  permanent until a real price lands, which never happens on the AV lane as shipped.
- **(vi) The `.BSE` suspect.** **Exonerated.** SBICARD.BSE and RELIANCE.BSE both return real
  prices without entitlement (probe #3, #4). The `.BSE` symbols failed only because the
  envelope-parse bug hits **all** symbols equally, and the message *"empty quote (unknown symbol
  or rate limited)"* invited the wrong suspicion — which is itself finding (b): the collapsed
  message misdirected the diagnosis.

### 0-C. Code census — the routing/provider layer (what a fix touches)

- `app/providers/market/external.py` — the AV adapter. **Root-cause site** (`:124` entitlement
  inject, `:191` fragile parse, `:207` failure collapse). History parse (`_find_time_series`) is
  already key-tolerant; quote parse is not.
- `app/providers/market/router.py` — pure `route()`; `DEFAULT_PRIORITY`, `CAPABILITIES`,
  `ChainEntry`, override/matrix/active precedence. Decides **ownership**, not execution.
- `app/services/market.py` — `refresh_quote_detailed` (single-provider fetch; **no chain
  walk**), `route_for_instrument`, `_refetch_route_mismatched` (coingecko-only), `get_cached_quote`.
- `app/services/confidence.py` — score/band/factors (drives the 25/low the owner sees).
- `app/api/v1/routes/portfolio.py` — `/portfolio/pricing-health` (the diagnostics surface).
- `app/providers/market/{yahoo,coingecko,amfi,eodhd,kite,ecb,csv,mock}.py` — the lanes a real
  fallback would fetch from. `yahoo` is keyless and `_ALL`-class — the natural free-first net.
- Frontend: `frontend/src/routes/PricingHealth.tsx`, `Settings.tsx` (the routing sentence
  `:1417-1418`), `RoutingMatrixMockup.tsx`.
- Specs: `GLOSSARY.md:138` (Routing matrix promise), `:118` (Source/Provider/Routing split),
  `:103` (Data confidence). No failure-state taxonomy terms exist yet (GLOSSARY-first in §9).

### 0-D. Survey inputs (a)–(g) — where each lands

- **(a)** rule pins HEAD, never removes the net → §9-1 (override semantics) + the **execution
  fallback** that must exist first (§0-B iii). *The sentence is false today for a deeper reason
  than an override: there is no fetch-time net at all.*
- **(b)** failure taxonomy (throttled/unmapped/errored/empty ≠ one "none"), surfaced in Pricing
  Health → §9-2 + §9-3 (served vocabulary, GLOSSARY-first).
- **(c)** per-symbol empty honesty (`.BSE`) → folded into (b); the class itself is exonerated, but
  the *genuine* empty (probe #5) must read differently from a parse-miss.
- **(d)** provider preflight (`is_available`-shaped) + **provider doctor** on Pricing Health → §9-4.
  *A doctor would have caught "AV returns 200 but we parse empty" on day one.*
- **(e)** cache staleness honesty for forming bars → §9-5.
- **(f)** **FREE-FIRST** chain ordering (owner ruling 2026-07-23) → §9-6. Money is a routing cost
  dimension; core function never requires payment. Yahoo/coingecko/amfi are keyless.
- **(g)** leverage the configured provider's full value → §0-E (ROADMAP candidates, **never R-63
  scope**).

### 0-E. (g) — AV capabilities beyond pricing (ROADMAP-row candidates, NOT R-63 scope)

From the committed reference: `NEWS_SENTIMENT` (FREE), `OVERVIEW`/`INCOME_STATEMENT`/`EARNINGS`
(FREE fundamentals), `DIVIDENDS`/`SPLITS` (FREE corporate actions), `SYMBOL_SEARCH` (FREE, would
sharpen mapping). Listed for the owner as future rows; **R-63 fixes pricing routing only.**

---

## 1. IDENTITY

R-63 is a **cross-cutting reliability fix**, not a new page. Primary owners: the AV adapter and
the refresh/execution path; secondary deltas on two **accepted** surfaces — **Pricing Health**
(new diagnostics: failure taxonomy + provider doctor) and **Settings → Data feeds** (the routing
sentence must become true). Both accepted-surface changes ship under the **guard-REDs-an-accepted-
surface rite** (CLAUDE.md): a dated delta note in each page's plan file + that page's pre-pass
re-run, in the same delta — **not** a close-report footnote.

## 2. OWNERSHIP TABLE (canonical homes — INFORMATION-ARCHITECTURE)

- Per-instrument routing **decision** → `route()` (internal) · surfaced read-only on **Pricing
  Health**. · Provider config/keys → **Settings → Data feeds**. · Failure taxonomy vocabulary →
  **GLOSSARY** (one home) then served. · Provider-doctor result → **Pricing Health** (read-only).
  No figure duplicated; other pages link.

## 3. API SURFACE

- **3a. Consumed (frozen contract):** `GET /portfolio/pricing-health` (extend rows with typed
  failure state), Settings routing-matrix endpoints (unchanged shape).
- **3b. Contract deltas (BUILD BACKEND-FIRST — approval owed at §9):**
  - a typed **failure-state** field on each pricing-health row (enum, not free text);
  - a **provider-doctor** read endpoint (per-provider verdict, redacted — key presence + a live
    known-symbol resolve, never the key);
  - possibly a `route_source`/execution-trace addition so "what the router did next" is honest.
  *Exact shapes drafted after §9 rules the taxonomy and doctor scope.*

## 4. COMPONENTS

Every user input via `src/components/ui/`. The provider-doctor surface is **read-only**
diagnostics (Badge/Table/status chips already in the DS). No raw inputs. Any new affordance the
ratified inventory lacks → listed in §9 before build.

## 5. VOCABULARIES

Failure-state terms are **categorical** → MASTER-DATA + GLOSSARY-first (§9-3). No free-text enums.
Candidate internal states (naming ruled at §9): `parse_error` · `throttled` · `unmapped` ·
`errored` · `empty` · `no_key` · `unsupported`. User-facing wording is a **separate** GLOSSARY
decision (copy hygiene: name a fact, never an endpoint).

## 6. DECISIONS IN FORCE

- GLOSSARY:138 Routing-matrix promise (*"falls back to its normal source exactly as before"*) —
  R-63 must make it **true**, not reword it away.
- Source/Provider/Routing split (D-028); Data-confidence penalties (GLOSSARY:103); no-egress
  Guarantee 5 (a fallback must **never** make a call under no-egress); F-4 entitlement=delayed
  (its intent — request delayed data — stays; its **parse** must tolerate the entitled envelope).
- Commitments: never fabricate a number; money math backend-only.

## 7. ACCEPTANCE CRITERIA (seed — completed after §9)

- [ ] TSLA / SBICARD.BSE / AARK price on the live chain (fail-first: a test that RED-reproduces
  the decorated-envelope parse-miss, then greens).
- [ ] Distinct failure states render distinctly on Pricing Health (throttled ≠ empty ≠ unmapped).
- [ ] A pinned rule never removes the fallback net — an execution fallback exists and is proven
  (fail-first: AV forced to fail, yahoo serves the price).
- [ ] Provider doctor gives per-provider verdicts, **redacted**, and would have caught this bug.
- [ ] Free-first ordering holds; no core price requires a paid key.
- [ ] **Blindness pins** on every new guard (a guard that protects nothing must fail loudly).
- [ ] Help Currency Law: Pricing Health + Settings routing copy deltas shipped, or guard-
  corroborated "no impact".
- [ ] Accepted-surface rite discharged for Pricing Health **and** Settings (dated delta note +
  pre-pass re-run each).

## 8. BUILD PHASES (seed — gated on §9)

0 survey (this file) → **§9 one-pass STOP** → 1 backend: envelope parse + failure taxonomy +
execution fallback (fail-first each) → 2 provider doctor + preflight → 3 free-first ordering →
4 Pricing Health + Settings surface deltas (accepted-surface rite) → walk → close. Both suite
verdicts (ordered AND randomized, declared seeds); UTF-8-safe edits; NO PUSH; KB-sync from diff.

---

## 9. NEEDS DECISION — **STOP. Owner one-pass before any code.**

Phase A is diagnosis; every item below is a normative choice the fix's shape depends on. Intake
rows for §0-A/§0-B findings enter the §-ledger at build time (TEMPLATE §8 / ai-surfaces §19-K).

**§9-0 — The root-cause fix (near-mechanical, but confirm the shape).** The dominant failure is
the decorated-envelope parse-miss. Two shapes: **(A)** make the quote parser tolerant of the
`"Global Quote*"` key family (mirrors `_find_time_series`), keeping `entitlement=delayed`; **(B)**
stop sending `entitlement=delayed` for `GLOBAL_QUOTE` (probe #2 shows the plain key works) and
send it only where it demonstrably helps. *Recommendation: (A) — the key IS entitled to delayed
(fresher) data, so keep requesting it and parse it correctly; (B) would silently drop 15-min-
delayed for end-of-day.* **Owner: A, B, or both (tolerant parse + audit every `entitlement` use)?**

**§9-1 — Override semantics: pin-head vs pin-only.** Today an override *pins and returns*
(`router.py:344`). Under (a) a rule must pin the chain's **head** and keep the net. **Ruling
needed:** does an explicit per-instrument override (i) pin the head then fall through on failure
(recommended — makes the sentence true), or (ii) remain an absolute pin (and then the shipped
sentence must be reworded for overrides specifically)? Same question for a **matrix** cell.

**§9-2 — The failure-state taxonomy.** Confirm the distinct states to name and surface:
`parse_error` · `throttled` · `unmapped` · `errored` · `empty` · `no_key` · `unsupported`
(vs collapsing to "none"). Which are **user-facing** on Pricing Health vs internal-only?

**§9-3 — Served vocabulary (GLOSSARY-first).** Each user-facing failure state needs an exact
GLOSSARY term before it is served (Help Currency Law). **Owner ratifies wording** — e.g.
"throttled" → *"the provider is rate-limiting; will retry"* vs "empty" → *"the provider had no
price for this symbol"*. Draft copy proposed at build; owner rules the words.

**§9-4 — Provider doctor: scope.** A live-chain test on Pricing Health with per-provider
verdicts, **redacted** (key **presence**, reachability, a known-symbol end-to-end resolve — never
the key, never a real holding's value). **Ruling:** on-demand button only, or also a preflight
that gates routing? How many egress calls may it spend (budget honesty)? Which known symbol per
provider lane?

**§9-5 — Cache staleness honesty for forming bars (e).** A still-forming bar / intra-session
quote is not a settled price. **Ruling:** surface "forming" distinctly from "stale", or fold into
the existing Stale state? (Interacts with R-42 intraday.)

**§9-6 — Free-first chain ordering (f, owner-ruled intent).** Reorder `DEFAULT_PRIORITY` so
free/keyless sources (yahoo, coingecko, amfi, ecb) sit **before** key-gated/paid (eodhd,
alphavantage, kite) — *within* capability. **Ruling needed:** the exact per-lane order. E.g.
`us_equity: [yahoo, alphavantage, eodhd, csv, manual]` (free yahoo leads) vs today's
`[eodhd, alphavantage, yahoo, csv, manual]`. Does a user-set matrix cell / override **override**
free-first (yes — explicit user intent wins, but still keeps the net per §9-1)?

**§9-7 — Provider doctor on an accepted page = the rite.** Pricing Health is accepted; adding the
doctor + taxonomy is a delta on it. Confirm the **guard-REDs-an-accepted-surface rite** applies
(dated delta note in `page-pricing-health.md` + a Pricing Health pre-pass re-run) and equally to
`page-settings.md` for the routing-sentence change. (Standing convention; confirming, not asking
permission to skip.)

**§9-8 — Symbol-mapping ownership per provider.** Should each provider own its symbol mapping
(e.g. AV `SYMBOL_SEARCH`, the `.BSE` suffix convention) explicitly, or stay in the shared
`currency_for_symbol`/identifier layer? Scope guard: mapping *correctness* is in R-63; a full
mapping subsystem is **not**.

**§9-9 — Call-budget honesty surfaced.** Rate-limit awareness (the 5/sec burst, any daily cap)
should be **visible**, not hidden. **Ruling:** surface a per-provider budget/last-throttle note on
Pricing Health, or keep internal with only the failure-state chip? (The one caught "Burst pattern"
line argues for at least a "throttled — will retry" surface.)

**§9-10 — Scope fence for (g).** Confirm AV's non-pricing capabilities (news, fundamentals,
corporate actions, symbol-search) are **ROADMAP candidates only** (§0-E), explicitly **out** of
R-63. Recommended: yes — one lane fixed well beats scope creep.

**§9-i (housekeeping, not normative):** the duplicate TSLA instrument (id 22 / id 23) — fold a
dedupe into R-63, or file separately? Flagging; owner's call.

**Sign-off to start build:** §9 has no open blocker · §3b deltas approved · the fail-first RED
for the parse-miss is written first.
