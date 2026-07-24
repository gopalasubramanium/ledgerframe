# R-58 — the `settings.key` check-then-insert race at the four filed sites

**Charter:** `ROADMAP.md` R-58 (RD-9 Amendment 9, from the F10 census) — that row is the charter and
carries the census, the order, the severity statement, and the fix shape. This file does not re-derive
it; it reconciles the census against the live tree, enumerates intake as a §-LEDGER at plan time, and
records dispositions at close (TEMPLATE §8 / `ai-surfaces.md` §19-K).

**Shape:** `SELECT Setting → if absent, session.add(Setting(...)) → flush()` on `settings.key`. Two
concurrent callers both read absent, both insert; the loser dies on
`sqlite3.IntegrityError: UNIQUE constraint failed: settings.key`, 500ing a request that did nothing
wrong. **Backend-only concurrency milestone: no served surfaces, no copy, no frontend.**

**Fences (charter §5):** no new surfaces, no copy, no settings semantics changes — the fix changes who
WINS a race, never what a winner writes. Any repair wanting to change behaviour beyond claim-vs-collide
STOPS and reports. `demo.py` joins only per the §2.4 evidence.

---

## §0. SURVEY — VERIFY-FIRST (re-entry reconciliation, 2026-07-24)

HEAD `c7c1efd`, tree clean. Census line numbers had drifted; reconciled **by shape**, not by line:

| Census (ROADMAP) | Live | Shape | Note |
|---|---|---|---|
| `briefing.py:201-207` | **201-207** (exact) | generic `_set(session, key, value)` upsert | widest blast radius — every caller present + future |
| `feeds.py:72-78` | **69-78** (SELECT 71-73, add 77, flush 78) | `set_feed_urls` upsert on `news_feeds` | drift −3 |
| `settings.py:131-135` | **130-136** (loop), insert branch 131-135 | PUT loop over `patch.values.items()` | **verb is `PUT /api/v1/settings`**, not PATCH — the body model is `SettingsPatch`; census said "PATCH loop" |
| `system.py:617-621` | **678-682** | reset writes `SEED_FLAG_KEY` | **drifted ~60 lines** — a legal-consent comment block (612-634) was inserted between the census and now |
| `seed/demo.py:327` | **327** (exact) | unconditional `add(Setting(SEED_FLAG_KEY,"1"))`, NO select | adjacent variant, not the shape |

**The primitive it reuses:** `app/services/market.py:1181` `_claim_marker(session, key) -> bool` — insert a
`Setting` inside `session.begin_nested()` (a SAVEPOINT), absorb the loser's `IntegrityError`, return
whether WE inserted. Its 5th internal caller is the F10 site at `market.py:1382-1391`, which already uses
the exact target shape (`if marker: marker.value = … else: await _claim_marker(…)` — SELECT-first,
update-if-present, claim-on-absent). **`_claim_marker` hardcodes `value = now().isoformat()`**, so the
promotion must generalise `value` to a parameter; `_claim_marker` then becomes a thin timestamp wrapper so
its behaviour — and the F10 tests (`tests/integration/test_history_cache_race.py`) — stay green UNMODIFIED,
which is itself the evidence the promotion is behaviour-preserving.

**Placement:** `app/db/claim.py` (new), function `claim_setting(session, key, value) -> bool`, importing
only `app.models.Setting`. This mirrors `app/db/upsert.py` — the established home for cross-service
persistence primitives — and is cycle-free (`app.db` is a leaf; services/routes already import from it).

**Alternative considered — NOT taken (recorded honestly):** `app/db/upsert.py` already offers a
dialect-aware native `INSERT … ON CONFLICT DO UPDATE`, which would fix the four value-bearing upsert sites
race-free with last-write-wins semantics and no savepoint. It is **not** taken because (a) the charter
explicitly prescribes the F10 `_claim_marker` savepoint primitive and requires unifying all FIVE sites —
including the F10 *claim* site whose contract is presence-not-value — under ONE shape, which
`on_conflict_do_update` (a value-refreshing upsert) does not cleanly express for a claim marker; and (b)
reusing the already-tested F10 primitive is the lower-risk path the charter chose. Flagged for the
architect at the verdicts HARD STOP in case a native upsert is preferred.

---

## §-LEDGER — intake enumerated at plan time (may not claim CLOSED while any row lacks a disposition)

| # | Type | Item | Disposition |
|---|---|---|---|
| **I-1** | Scope §2.1 | **Promote `_claim_marker` → shared `app/db/claim.py claim_setting(session, key, value)`**; F10 site migrates (5th caller); `_claim_marker` becomes a timestamp wrapper; F10 tests stay green **unmodified**. | **DONE `c4bafc8`.** `app/db/claim.py::claim_setting` created (leaf; imports only `app.models`). `market._claim_marker` is now a thin wrapper delegating to it with `datetime.now(UTC).isoformat()`; the F10 site (`market.py` `get_history_cached`) and `_repair_once_per_install` call it unchanged. **F10 tests (`test_history_cache_race.py`) pass UNMODIFIED** — the behaviour-preserving evidence. Unused `IntegrityError` import removed from `market.py`. |
| **I-2** | Scope §2.2 | **Site 1 — `briefing.py` `_set()` FIRST** (generic helper, widest blast radius). Insert branch delegates to `claim_setting`; update-if-present branch unchanged. | **DONE `c4bafc8`.** `_set` keeps SELECT-first + update-if-present (with its `flush`); the absent branch delegates to `claim_setting`. Retires the race for every `_set` caller (both `BRIEFING_KEY` and `BRIEFING_TS_KEY`). |
| **I-3** | Scope §2.3 | **Site 2 — `feeds.py` `set_feed_urls`** (`news_feeds`). Same transform. | **DONE `c4bafc8`.** Absent branch → `claim_setting(session, FEEDS_SETTING_KEY, value)`. |
| **I-4** | Scope §2.3 | **Site 3 — `settings.py` PUT loop** (user-triggered). Per-key insert branch delegates to `claim_setting`; AuditEvent + final flush unchanged. | **DONE `c4bafc8`.** Per-key absent branch → `claim_setting`; the AuditEvent add + single final `flush` are untouched. **Note:** verb reconciled — `PUT /api/v1/settings` (body model `SettingsPatch`), not "PATCH". |
| **I-5** | Scope §2.3 | **Site 4 — `system.py` reset** (`SEED_FLAG_KEY`). Same transform. **Posture recorded:** the preceding `table.delete()` loop takes the write lock and serialises concurrent resets, so the route-level race is latent-not-live; fix applied for uniformity ("sites cannot drift"), RED covered by the primitive's deterministic collision test, route test pins reach. | **DONE `c4bafc8`.** Absent branch → `claim_setting(session, SEED_FLAG_KEY, "1")`; trailing `flush` kept. Route-level race serialised by the preceding deletes (posture recorded in the code comment + the test docstring); `test_reset_reaches_the_seed_flag_insert` is the blindness pin (a reset REACHES the flag insert), the deterministic primitive test carries the SHAPE's RED. |
| **I-6** | Scope §2.4 | **Adjacent — `demo.py:327` ANSWERED, not assumed** (can it run twice concurrently?). | **ANSWERED — does NOT join the fix.** Sole production caller: the boot lifespan `app/main.py:120-124`, gated on `settings.demo_seed` (**default `False`**, `config.py:68`); every other caller is a **sequential** test call on one session (no concurrency). It can be *entered* twice only by two processes booting with `demo_seed=true` on a shared DB — and even then (a) `seed_demo_data`'s flag SELECT (`demo.py:112-114`) + Transaction-count guard (`115-117`) + the seed writes before 327 (first flush `demo.py:124` takes the write lock) make the second seeder normally return before reaching 327, and (b) in the residual window the loser's `IntegrityError` is **caught by the sole caller's startup `try/except`** (`main.py:127-129` → "demo seed skipped"), a boot log line, **never a request 500**. The defect's HARM is structurally unreachable here; and 327 is an *unconditional* insert (no SELECT — not the check-then-insert shape), so converting it would change the seed contract for zero harm-reduction. **Record, don't fix** — the charter's "adjacent, not a fifth site" confirmed. |
| **I-7** | Scope §3 | **Test spec per site:** RED-first concurrent repro + blindness-pin reach assertion + deliberate posture. | **DONE `c4bafc8`** (`tests/integration/test_settings_key_claim_race.py`). **Deterministic RED (reliable):** `test_claim_setting_absorbs_a_losing_insert_deterministically` — a winner commits the key; the raw `add+flush` loser RAISES `IntegrityError` (fix-independent, documents the shape); `claim_setting` ABSORBS it, returns False, leaves the winner's value untouched, and leaves the session USABLE (a subsequent write succeeds — the property a bare flush cannot give). **Per-site concurrent HTTP tests** (briefing/feeds/settings gather N=10; reset reach) each assert no-500 + a **blindness-pin reach assertion** (target key row exists). **Fail-first evidence:** the real `IntegrityError: UNIQUE constraint failed: settings.key` was captured live on `settings-put` pre-fix. **Flakiness recorded (F10 characteristic, `ai-surfaces`/r63 I-6):** the *route-level* RED is context/timing-dependent — it reproduced on `settings-put` in full-file context but not in isolation, and briefing/feeds did not reproduce it via naive gather (event-loop/pool-state sensitivity). The **reliable** RED is therefore the deterministic primitive test (the exact code all four sites now run on the absent branch); the HTTP tests are the watched-to-work + reach layer, deterministically GREEN post-fix. Not a barrier harness (F10 precedent used plain gather + recorded flake). |
| **I-8** | Scope §3.4 | **Isolation-portability note:** savepoint-claim is isolation-portable in design; Postgres untested (charter caveat) — carry the note, don't expand scope. | **CARRIED (note only).** `begin_nested()` (SAVEPOINT) + `IntegrityError` absorption is isolation-portable in design; the `identity.py:117-130` sibling handles the same on the Postgres-capable `OperationalError` path too. Postgres remains untested (whole-suite caveat, `02-DATA-MODEL §2.2`); Postgres widens the race window but the primitive's contract is unchanged. No scope expansion. |

---

## BUILD PHASES (backend-first, fail-first each — RED on the real cause before GREEN)

1. **Promote (I-1).** Add `app/db/claim.py`. Rewrite `market._claim_marker` as a wrapper. Run F10 tests → must stay green unmodified.
2. **Sites 1→4 (I-2..I-5), in charter order.** Each: SELECT-first + update-if-present unchanged; absent branch → `claim_setting`.
3. **Tests (I-7).** Deterministic primitive collision test (place-then-collide: raw `add+flush` RAISES = RED shape; `claim_setting` ABSORBS + returns False + session survives = GREEN; absent → True + inserts = reach). Per-site HTTP concurrent tests (asyncio.gather N, no-500 + reach assertion), posture chosen to expose the race. RED captured against pre-fix code first.
4. **Disposition demo.py (I-6)** with call-graph + trigger evidence.
5. **Verdicts.** SOLO pair both orders on final code; reconciliation itemised. **HARD STOP with full report** (architect review before RATIFICATION §6 ritual).

## Baselines (charter §4)

- Backend **2182 passed / 16 skipped**, seed **6363**. Frontend untouched (checkable via diff).
