# MASTER-DATA.md — LedgerFrame v2 Controlled Vocabularies & Masters

**Normative.** This file is the single register of every controlled vocabulary
and reference master in v2. CLAUDE.md hard rule: every categorical field
references this file; no free-text enums. D-005 completeness rule: **every
vocabulary must appear here with its complete seed value list — no vocabulary is
confirmed without its values.** The DEF backfill extracted the pending
vocabularies verbatim from the legacy v1 source (read-only reference); the two
items still open in [§9](#9-blocked-extractions) (DEF-2 `asset_subclass`, DEF-6
sector seed) require an **authoring decision**, not an extraction — they are
deliberately left unfilled rather than guessed.

---

## 1. Architecture (D-005, "hybrid")

Two mechanisms, no third:

**A. Fixed vocabularies** — code-defined enums.
- Defined once in backend code.
- Served to the frontend via a **single `/refdata` endpoint**. There is no
  second copy anywhere.
- Enforced at the database with **CHECK constraints** (today these fields are
  unconstrained `String` columns — see 02-DATA-MODEL §4; v2 adds the CHECK).
- Not user-editable.

**B. User-extensible masters** — database reference tables.
- Rows live in DB tables; referencing columns are **FK-enforced**.
- Users add/rename/merge rows through an admin screen (§7).

**Frontend carries zero vocabulary copies.** `refdata.ts`, `policyTemplates.ts`,
and every inline list (`CURRENCIES`, `COUNTRIES`, `ASSET_CLASSES`,
`TXN_ASSET_CLASSES`, …) are retired (D-005, D-049). The frontend obtains fixed
vocabularies from `/refdata` and extensible masters from their own endpoints.
The 6-value `TXN_ASSET_CLASSES` subset is deleted; forms use the full 13-value
`AssetClass` from `/refdata` (D-049).

Governing rule for confirmation: a vocabulary is "confirmed" only when its
complete value list is written here. Fixed vocabularies whose values are fully
recorded in DECISIONS.md D-010 or the schema audit are confirmed below (§2);
those whose values live only in un-extracted service code are **not confirmed**
(§9).

---

## 2. Fixed vocabularies (served via `/refdata`, DB CHECK)

Each is code-defined and enumerated in full. "Column(s)" names the storage from
02-DATA-MODEL. Source column: `D-010` = enumerated verbatim in DECISIONS.md
D-010; `02` = from the schema audit.

| Vocabulary | Column(s) | Count | Complete seed values | Source |
|------------|-----------|-------|----------------------|--------|
| **TxnType** | `transactions.type` | 11 | `buy, sell, dividend, interest, deposit, withdrawal, fee, split, bonus, merger, transfer` | D-010 |
| **AssetClass** | `instruments.asset_class`, `holdings.asset_class` | 13 | `equity, etf, mutual_fund, bond, cash, fixed_deposit, commodity, crypto, property, private, retirement, liability, other` | D-010 |
| **liquidity_profile** | `instruments.liquidity_profile` | 5 | `listed, redeemable, locked, illiquid, manual` | D-010 |
| **Entity.kind** | `entities.kind` | 5 | `self, spouse, trust, company, other` | D-010 |
| **Goal.basis** | `goals.basis` | 3 | `net_worth, liquid, none` | D-010 |
| **Obligation.recurrence** | `obligations.recurrence` | 4 | `once, monthly, quarterly, annual` | D-010 |
| **Obligation.kind** | `obligations.kind` | 2 | `expense, income` | D-010 |
| **Contribution.frequency** | `contribution.frequency` | 4 | `monthly, quarterly, annual, once` | D-010 |
| **Contribution.kind** | `contribution.kind` | 3 | `invest, withdraw, prepay` | D-010 |
| **EstateProfile.will_status** | `estate_profile.will_status` | 4 | `none, draft, executed, needs_update` | D-010 |
| **EstateDocument.status** | `estate_document.status` | 3 | `present, missing, outdated` | D-010 |
| **ValuationMethod** | `instruments.valuation_method`, provenance | 9 | `market_quote, official_nav, broker_quote, manual_valuation, statement_import, calculated_accrual, estimated_value, fx_reference, unavailable` | D-010 |
| **EntitlementStatus** | `quotes.entitlement`, provenance | 5 | `real-time, delayed, end-of-day, cached, unavailable` | D-010 |
| **PolicyTarget.dimension** | `policy_targets.dimension` | 3 | `asset_class, currency, region` | 02 §2.8 |
| **InstrumentIdentifier.id_type** | `instrument_identifiers.id_type` | 8 | `isin, cusip, figi, sedol, amfi_code, kite_token, coingecko_id, provider_symbol` | 02 §2.2 |
| **cost_basis_method** | `accounts.cost_basis_method` | 2 (v2) | `fifo, average` (v2 lanes; `spec` is ROADMAP R-6, D-018 — not a v2 value) | D-018 |
| **Account.kind** | `accounts.kind` | 7 | `brokerage, bank, retirement, wallet, property, manual, other` | DEF-3 |
| **InsurancePolicy.policy_type** | `insurance_policy.policy_type` | 10 | `term_life, whole_life, health, critical_illness, disability, personal_accident, property, motor, travel, other` | DEF-4 |
| **InsurancePolicy.premium_frequency** | `insurance_policy.premium_frequency` | 4 | `monthly, quarterly, annual, single` | DEF-4 |
| **EstateDocument.category** | `estate_document.category` | 9 | `will, insurance, property, loan, identity, bank, tax, medical, other` | DEF-5 |
| **EstateContact roles** | `estate_contact.roles` (JSON list) | 5 | `nominee, beneficiary, executor, emergency, guardian` | DEF-5 |

**Notes on specific vocabularies:**
- `TxnType` — the frontend gains `merger` (previously omitted from the 10-value
  client list); the canonical set is the 11 backend values (D-010).
- `ValuationMethod` — `calculated_accrual` and `statement_import` remain in the
  vocabulary but **no v2 lane emits them** (D-073). The values are retained; the
  routing chains do not produce them.
- `EntitlementStatus` — LedgerFrame never claims `real-time` for its own data;
  the value exists to record a source's *claim* (GLOSSARY, D-027).
- `id_type` — the high-confidence subset (globally unique per instrument) is
  `{isin, cusip, figi, sedol, amfi_code, kite_token, coingecko_id}`;
  `provider_symbol` is the non-high-confidence remainder (02 §2.2).

**Notes on the backfilled vocabularies (DEF-3/4/5):**
- `Account.kind` — extracted from `ACCOUNT_KINDS` verbatim (DEF-3 resolved).
- `InsurancePolicy.premium_frequency` — the value set is `..., single` (a
  paid-once policy), **not** `once`; distinct from `Contribution.frequency`
  (`..., once`). Do not conflate them.
- `EstateContact roles` — this is the `CONTACT_ROLES` vocabulary into which the
  former free-text `relationship` field is **folded** (D-010); the separate
  `relationship` field is dropped. Stored as a JSON list on `estate_contact.roles`.
- `estate.py` also confirms `WILL_STATUSES` and `DOC_STATUSES` match the D-010
  values already in the table above (bonus confirmation from the same source).

**Still pending — `Instrument.asset_subclass` (DEF-2, partial; see §9).**
`asset_subclass` has **no enumerated vocabulary in code** — it is a free
`String(40)`. The only values the code actively assigns are `crypto`,
`derivative`, `equity`, `mutual_fund`; **routing only reads `derivative`**.
D-009's asserted "at least `etf`, `reit`" are **not found** as assigned values.
Finalising this fixed vocabulary is therefore an authoring/decision task
(D-009), not a clean extraction — it stays in §9.

---

## 3. Currency master (D-006)

A reference master, not a plain enum, because it carries a flag.

| Column | Meaning |
|--------|---------|
| `code` | ISO-4217 alpha-3 (e.g. SGD, USD). PK. |
| `is_base_eligible` | Boolean. `true` = usable as **base/reporting** currency; the wider set (`false` too) is valid only as a **transaction** currency. |

**FX-translatability rule (governing, D-006):** *a currency may exist in the
master only if the FX service can translate it.* Any candidate that the FX
service cannot translate is not admitted.

**Base-currency picker** draws from `is_base_eligible = true` only
(Settings → base currency). Transaction/holding currency fields draw from the
full master.

**Seed (DEF-1, extracted).** The seed is the **union** of three divergent legacy
lists, deduplicated (`HKD` appears twice in the PortfolioEditor list):

| Group | Codes | `is_base_eligible` | Source |
|-------|-------|--------------------|--------|
| Base-eligible (`config.SUPPORTED_CURRENCIES`, 9) | `SGD, USD, INR, EUR, GBP, JPY, AUD, CNY, HKD` | **true** | `config.py:18` |
| + adds from `refdata.ts CURRENCIES` (14) | `CAD, CHF, AED, MYR, THB` | false | `refdata.ts:8` |
| + adds from PortfolioEditor inline (21 unique) | `KRW, TWD, SEK, NOK, DKK, ZAR, BRL, NZD` | false | `PortfolioEditor.tsx:22` |

**Full seed = 22 unique codes**, `is_base_eligible = true` for exactly the 9
`SUPPORTED_CURRENCIES`, `false` for the other 13.

**FX-translatability validation is operational, not a static list.** The FX
service holds no hard-coded translatable set: `ecb_fx._RATES` is loaded at
runtime from the ECB daily reference feed (`ecb_fx.py:24,71-73`) and `fx.py`
triangulates cross rates through USD with ECB as fallback (`fx.py:51`). So D-006's
rule is enforced **at admission time against the live FX service**, not by a code
constant. The 9 base-eligible codes are FX-supported by definition
(`config.SUPPORTED_CURRENCIES`); the 13 wider codes must be confirmed
translatable when the currency master is seeded (any that the FX service cannot
translate are dropped per D-006, not carried).

**ROADMAP (R-2, D-006):** user-requestable transaction currencies, FX-validated.

---

## 4. Country & region model (D-007)

**`instruments.listing_country` (ISO-3166 alpha-2) is the single authoritative
country field.** Dropped: `instruments.country` (free text) and
`instruments.domicile_country`.

- **Reference table:** the ISO-3166-1 alpha-2 standard seeds the country picker
  (the seed *is* the published ISO-3166 code list — a standard, not a decision
  to author).
- **Region is derived, never stored as a separate vocabulary** (D-007):

  | `listing_country` | Region |
  |-------------------|--------|
  | `IN` | India |
  | `SG` | Singapore |
  | `US` | US |
  | anything else | Global |

  These four region values are the complete `region` vocabulary (used as a
  policy dimension bucket set, D-055/02 §2.8).

**ROADMAP (R-3, D-007):** re-introduce a domicile field for fund-tax display.

---

## 5. Timezone (D-013)

`Settings` timezone becomes an **IANA timezone** select, replacing free-text
entry. The seed is the **IANA Time Zone Database** (`tz` database) name list — a
maintained standard, served to the picker; not a value list authored here.

---

## 6. User-extensible masters (DB reference tables, FK-enforced)

| Master | Referencing columns (FK) | Seed | Uniqueness |
|--------|--------------------------|------|-----------|
| **Institution** (D-008) | `accounts.institution`, `insurance_policy.insurer` | none (starts empty; user-populated) | by name; merge dedupes variants ("DBS" vs "DBS Bank") |
| **Sector** (D-009) | `instruments.sector` | GICS-like seed — **authorship** (DEF-6, §9; no list in code) | by name |
| **Tag** (D-011) | `holding_tag.tags` (JSON list, keyed by `account_id` + `holding_key`) | none | **case-insensitive**, cap **16 tags/holding** |

**Institution (D-008).** One master, FK'd from both `accounts.institution` and
`insurance_policy.insurer`. Estate `estate_document.related_to` stays **free
text by design** (architectural invariant — the estate register deliberately
does not FK into other tables; do not "normalise" it).

**Sector (D-009).** User-extensible, seeded GICS-like. There is **no sector
master or GICS list in the code** — DEF-6 is an **authoring** task, not an
extraction, and remains open (§9). As a starting reference, the ticker→sector
fallback map `_SECTOR_MAP` (`portfolio.py:30-51`) uses these 12 distinct
values: `Technology, Communication Services, Consumer Discretionary, Consumer
Staples, Financials, Energy, Health Care, Industrials, Utilities, Crypto,
Index / ETF, Commodities`. That is a **fallback map, not the authored master**;
the GICS-like seed (e.g. whether to use the 11 GICS sectors and how to treat
Crypto / Commodities / Index-ETF) is the decision DEF-6 records.

**Tag (D-011).** Uniqueness is **case-insensitive**; rename **cascades to all
tagged holdings**; the 16-tags-per-holding cap is retained. `holding_key` is the
instrument symbol or manual-asset label.

**Currency (§3)** is a reference master too, but seed-managed under the
FX-translatability rule rather than freely user-added in v2 (user-requestable
additions are ROADMAP R-2).

---

## 7. Admin-screen requirements (per user-extensible master)

Each extensible master needs an admin surface. Common requirements:

- **Institution** — create, rename, **merge** (fold duplicate into a survivor,
  re-pointing every referencing `accounts.institution` / `insurance_policy.insurer`
  row). **Delete blocked while any row references it** (FK guard); offer merge
  instead.
- **Sector** — create, rename, merge. Delete blocked while any instrument
  references it. Ships pre-seeded (GICS-like, DEF-6).
- **Tag** — create, rename (**cascades** to every tagged holding), **dedupe/merge**
  for case and whitespace variants. Enforce case-insensitive uniqueness and the
  16-per-holding cap at write time.
- **Currency** — view the master and each row's `is_base_eligible`; the
  base-currency picker is restricted to eligible rows. New transaction
  currencies are gated behind the FX-translatability rule (and are ROADMAP R-2).

Fixed vocabularies (§2) have **no admin screen** — they are code-defined and
change only by code + migration.

---

## 8. Migration dispositions (recorded in DECISIONS.md)

| Field / concern | Disposition | Decision |
|-----------------|-------------|----------|
| `instruments.country`, `instruments.domicile_country` (free text) | **Dropped.** `listing_country` (ISO2) is authoritative. | D-007 |
| Legacy free-text country values → ISO2 | Map to ISO-3166 alpha-2 with a **manual review list for unmappables — no silent best-guess.** | D-007 |
| `instruments.asset_category` (free text) | **Dropped.** Migration first moves surviving `asset_category` values **into tags**, then drops the column. | D-009 |
| Tag variants | **Dedupe/merge pass** for case and whitespace variants before enforcing case-insensitive uniqueness. | D-011 |
| Currency lists | Collapse the 3 divergent lists into the one master (§3), each member FX-validated. | D-006 |
| Instrument symbol entry | Free-text symbol entry replaced by an **instrument picker** (typeahead + provider search); explicit "create new instrument" path replaces silent auto-creation; `_get_or_create_instrument` side effects removed from GET paths. | D-012 |
| Bulk imports | Same resolution logic with a **review queue for unresolved symbols** — imports never silently auto-create instruments. | D-012 |
| Account entity assignment | Migration assigns every existing account to a default entity (schema already present, 02 §3 rev. `entities`). | 02 §2.2 |

---

## 9. Blocked extractions

DEF-1, DEF-3, DEF-4, DEF-5 are **resolved** — extracted verbatim from the legacy
v1 source (`~/Documents/github/LedgerFrame`, read-only reference) and filled into
§2/§3 in place (cites in the Derived-from footer). Two items remain open, and
**not** because a value is unreadable — both require a **decision/authoring**, not
an extraction:

| ID | Item | Why still open | Blocks |
|----|------|----------------|--------|
| DEF-2 | **`asset_subclass` fixed vocabulary** | No enum exists in code — `asset_subclass` is a free `String(40)`. Code assigns only `crypto, derivative, equity, mutual_fund` (`amfi.py:75`, `coingecko.py:89`, `kite.py:94,97`, `market.py:417`); routing reads only `derivative` (`router.py:123,131`). D-009's asserted `etf`, `reit` are **not** assigned anywhere. Choosing the final fixed vocab is an **authoring decision** (D-009), not extraction. | Instrument taxonomy (§2); Add flow (D-049) |
| DEF-6 | **Sector master seed (GICS-like)** | No sector master / GICS list in code (only the `_SECTOR_MAP` ticker fallback, `portfolio.py:30-51`). Seed is **authorship** (D-009/DEF-6), not extraction. §6 lists the 12 fallback values as a starting reference. | Sector picker (D-009) |

DEF-7 (Review threshold constants) is not master data; its values live in
PRODUCT-SPEC §5 and were reconciled against `services/review.py` in this backfill.

---

**Derived from:** `docs/audit/02-DATA-MODEL.md`, `docs/audit/06-UI-AND-TERMINOLOGY-AUDIT.md`
§(a), `docs/audit/DECISIONS.md`, and the **legacy v1 source**
(`~/Documents/github/LedgerFrame`, read-only) for the DEF backfill:

- DEF-1 currency union — `app/core/config.py:18` (`SUPPORTED_CURRENCIES`, 9,
  base-eligible); `frontend/src/lib/refdata.ts:8` (`CURRENCIES`, 14);
  `frontend/src/components/PortfolioEditor.tsx:22` (inline list, 21 unique);
  FX-translatability behaviour `app/services/ecb_fx.py:24,71-73`, `app/services/fx.py:51`.
- DEF-3 `ACCOUNT_KINDS` — `app/services/accounts.py:24`.
- DEF-4 `POLICY_TYPES` / `FREQUENCIES` — `app/services/insurance.py:23-25`.
- DEF-5 `DOC_CATEGORIES` / `CONTACT_ROLES` (+ `WILL_STATUSES`, `DOC_STATUSES`
  confirmation) — `app/services/estate.py:19-22`.
- DEF-6 sector reference (`_SECTOR_MAP`) — `app/services/portfolio.py:30-51`.

Decision IDs applied: D-005, D-006, D-007, D-008, D-009, D-010, D-011, D-012,
D-013, D-018, D-049, D-055, D-064, D-073, and the DEFERRED table. Where the audit
flagged free-text fields that "should" reference masters (02 §4), DECISIONS.md's
verdicts govern the choice of fixed-vocabulary vs extensible-master.

## Needs decision

No product decisions outstanding. Two **authoring** items remain (§9): the final
`asset_subclass` fixed vocabulary (DEF-2) and the GICS-like sector seed (DEF-6) —
both now with concrete code-observed values to author from, neither blocked on
missing source.
