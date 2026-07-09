# MASTER-DATA.md — LedgerFrame v2 Controlled Vocabularies & Masters

**Normative.** This file is the single register of every controlled vocabulary
and reference master in v2. CLAUDE.md hard rule: every categorical field
references this file; no free-text enums. D-005 completeness rule: **every
vocabulary must appear here with its complete seed value list — no vocabulary is
confirmed without its values.** Vocabularies whose authoritative values live in
application code that is **not present in this repository** are marked
`EXTRACTION REQUIRED` and listed in [§9 Blocked extractions](#9-blocked-extractions);
they are deliberately left unfilled rather than guessed.

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

**EXTRACTION REQUIRED fixed vocabularies** (values in un-extracted service code
— see §9): `Account.kind` (`ACCOUNT_KINDS`, DEF-3), `Instrument.asset_subclass`
(DEF-2), `InsurancePolicy.policy_type` / `premium_frequency` (`POLICY_TYPES`,
`FREQUENCIES`, DEF-4), `EstateDocument.category` / contact roles
(`DOC_CATEGORIES`, `CONTACT_ROLES`, DEF-5). Each is a fixed vocabulary by D-010;
only its value list is pending.

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

**Seed = `EXTRACTION REQUIRED` (DEF-1).** The seed is the **union** of three
divergent legacy lists — `config.SUPPORTED_CURRENCIES` (9, the base-eligible
set), `refdata.ts` `CURRENCIES` (14), and the PortfolioEditor inline list (22) —
**each member re-validated against the FX-translatability rule**; members the FX
service cannot translate are dropped, not carried. The base-eligible flag is set
`true` for the 9 `SUPPORTED_CURRENCIES` members and `false` for the remainder
that survive validation. The three source lists are in application code not
present in this repo; the concrete codes cannot be enumerated here (§9).

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
| **Sector** (D-009) | `instruments.sector` | GICS-like seed list — `EXTRACTION REQUIRED` **authorship** (DEF-6, §9) | by name |
| **Tag** (D-011) | `holding_tag.tags` (JSON list, keyed by `account_id` + `holding_key`) | none | **case-insensitive**, cap **16 tags/holding** |

**Institution (D-008).** One master, FK'd from both `accounts.institution` and
`insurance_policy.insurer`. Estate `estate_document.related_to` stays **free
text by design** (architectural invariant — the estate register deliberately
does not FK into other tables; do not "normalise" it).

**Sector (D-009).** User-extensible, seeded GICS-like. The seed list is
authorship (not code extraction) and is not yet written — DEF-6.

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

The application source is **not present in this repository** (docs-only). The
following vocabularies have their authoritative values in service-layer code that
cannot be read here; per the SHARED RULES they are **not guessed**. Each must be
extracted verbatim from the named source before it is "confirmed" and before the
dependent spec/UI is built. References are the DEF items in DECISIONS.md.

| ID | Vocabulary / master | Authoritative source | Partial info available | Blocks |
|----|---------------------|----------------------|------------------------|--------|
| DEF-1 | **Currency master seed** | `config.SUPPORTED_CURRENCIES` (9, base-eligible) ∪ `refdata.ts CURRENCIES` (14) ∪ PortfolioEditor inline (22), FX-validated | Counts (9/14/22); the 9 are base-eligible; defaults seen: SGD, USD | Currency master (§3); base-currency picker |
| DEF-2 | **`asset_subclass`** | Instrument taxonomy code usage | Known members (incomplete): `etf, reit, mutual_fund, derivative` — routing reads `derivative` | Instrument taxonomy (§2); Add flow (D-049) |
| DEF-3 | **`Account.kind` (`ACCOUNT_KINDS`)** | `app/services/accounts.py` | Known members (incomplete): `brokerage` (default), `manual` (auto-created) | Account form (D-064) |
| DEF-4 | **`policy_type` / `premium_frequency` (`POLICY_TYPES`, `FREQUENCIES`)** | Insurance service (`/insurance/meta`) | Defaults seen: `other` (policy_type), `annual` (premium_frequency) | Insurance form (D-062) |
| DEF-5 | **`category` / contact roles (`DOC_CATEGORIES`, `CONTACT_ROLES`)** | Estate service (`/estate/meta`); `estate_contact.relationship` **folds into roles** and the separate field is dropped (D-010) | Default seen: `other` (category) | Estate forms (D-063) |
| DEF-6 | **Sector master seed (GICS-like)** | Authorship (not extraction) | — | Sector picker (D-009) |

DEF-7 (Review threshold constants) is not master data; it belongs to the Review
page spec (D-059).

---

**Derived from:** `docs/audit/02-DATA-MODEL.md`, `docs/audit/06-UI-AND-TERMINOLOGY-AUDIT.md`
§(a), and `docs/audit/DECISIONS.md`. Decision IDs applied: D-005, D-006, D-007,
D-008, D-009, D-010, D-011, D-012, D-013, D-018, D-049, D-055, D-064, D-073, and
the DEFERRED table (DEF-1..DEF-6). Where the audit flagged free-text fields that
"should" reference masters (02 §4), DECISIONS.md's verdicts govern the choice of
fixed-vocabulary vs extensible-master.

## Needs decision

None outstanding as product decisions — all vocabularies received a verdict in
DECISIONS.md. The open items are **mechanical extractions/authorship** (DEF-1..DEF-6,
§9), blocked solely because the application source is not in this repository.
Resolve by running the extraction against the codebase (or committing the code
here) and filling the seed lists in §2/§3/§6 in place.
