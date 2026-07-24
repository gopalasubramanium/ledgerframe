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
| **I-1** | Scope §2.1 | **Promote `_claim_marker` → shared `app/db/claim.py claim_setting(session, key, value)`**; F10 site migrates (5th caller); `_claim_marker` becomes a timestamp wrapper; F10 tests stay green **unmodified**. | OPEN |
| **I-2** | Scope §2.2 | **Site 1 — `briefing.py` `_set()` FIRST** (generic helper, widest blast radius). Insert branch delegates to `claim_setting`; update-if-present branch unchanged. | OPEN |
| **I-3** | Scope §2.3 | **Site 2 — `feeds.py` `set_feed_urls`** (`news_feeds`). Same transform. | OPEN |
| **I-4** | Scope §2.3 | **Site 3 — `settings.py` PUT loop** (user-triggered). Per-key insert branch delegates to `claim_setting`; AuditEvent + final flush unchanged. | OPEN |
| **I-5** | Scope §2.3 | **Site 4 — `system.py` reset** (`SEED_FLAG_KEY`). Same transform. **Posture recorded:** the preceding `table.delete()` loop takes the write lock and serialises concurrent resets, so the route-level race is latent-not-live; fix applied for uniformity ("sites cannot drift"), RED covered by the primitive's deterministic collision test, route test pins reach. | OPEN |
| **I-6** | Scope §2.4 | **Adjacent — `demo.py:327` ANSWERED, not assumed** (can it run twice concurrently?). | OPEN |
| **I-7** | Scope §3 | **Test spec per site:** RED-first concurrent repro + blindness-pin reach assertion + deliberate posture. | OPEN |
| **I-8** | Scope §3.4 | **Isolation-portability note:** savepoint-claim is isolation-portable in design; Postgres untested (charter caveat) — carry the note, don't expand scope. | OPEN |

---

## BUILD PHASES (backend-first, fail-first each — RED on the real cause before GREEN)

1. **Promote (I-1).** Add `app/db/claim.py`. Rewrite `market._claim_marker` as a wrapper. Run F10 tests → must stay green unmodified.
2. **Sites 1→4 (I-2..I-5), in charter order.** Each: SELECT-first + update-if-present unchanged; absent branch → `claim_setting`.
3. **Tests (I-7).** Deterministic primitive collision test (place-then-collide: raw `add+flush` RAISES = RED shape; `claim_setting` ABSORBS + returns False + session survives = GREEN; absent → True + inserts = reach). Per-site HTTP concurrent tests (asyncio.gather N, no-500 + reach assertion), posture chosen to expose the race. RED captured against pre-fix code first.
4. **Disposition demo.py (I-6)** with call-graph + trigger evidence.
5. **Verdicts.** SOLO pair both orders on final code; reconciliation itemised. **HARD STOP with full report** (architect review before RATIFICATION §6 ritual).

## Baselines (charter §4)

- Backend **2182 passed / 16 skipped**, seed **6363**. Frontend untouched (checkable via diff).
