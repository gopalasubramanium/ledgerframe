# OPEN QUESTIONS

Ambiguous, contradictory, or product-decision-shaped items a human (the owner) must resolve
before the ground-up rebuild. Grouped by theme. Each references where it surfaced.

## Data model & master data

1. **Consolidate master data?** Currencies, asset classes, countries, and the `*_meta` vocab
   sets are duplicated across backend enums, `refdata.ts`, `policyTemplates.ts`, and inline lists
   (3 divergent currency lists alone; see 06/08). Should the rebuild introduce **DB reference
   tables / a single shared schema** driving both layers, or keep client lists? Which fields become
   FK-constrained (asset class, currency, sector, country, institution, insurer, policy type,
   document category, relationship/role, tags)?
2. **Institution / platform master?** `accounts.institution`, `insurance_policy.insurer`,
   `estate_contact` names are free text. Do you want a deduped institution/platform master?
3. **Dead tables — keep, wire, or drop?** `ProviderConfig`, `Note`, `AIConversation`/`AIMessage`,
   `DashboardConfig`/`DashboardRotationItem` are defined but effectively unused (08 §1). Were any of
   these intended features (notes on instruments, persisted AI chat history, server-side dashboard
   config)? Drop or build?
4. **`domicile_country` vs `listing_country` vs `country`** — three country-ish fields on
   `Instrument`; only listing/country are read. Which is authoritative for region/tax logic?

## Unfinished / schema-only features

5. **Cost-basis method (`average`)** — the engine supports it and it's tested, but there is **no UI
   to set `accounts.cost_basis_method`**. Ship a per-account selector? Add the deferred `spec`
   (specific-lot) method?
6. **Mergers** — `resolve_mergers` handles A→B lot transfer, but the transaction form has **no
   `merger` type** and `TXN_TYPES` (frontend) omits it. Should users be able to record mergers in
   the UI? If so, define the input (target instrument + ratio) — currently ratio rides in the
   `price` field and target in `related_instrument_id`.
7. **Trade-date FX** — captured only for same-day trades; historical trades are permanently NULL.
   Is the secondary "trade-date FX realised total" (with excluded-events count) the right UX, or
   should the rebuild fetch a historical FX series to backfill?

## Presentation / UX

8. **Simple/Expert scope** — the toggle only changes **Home** (and is set in Settings); every other
   page ignores it. Should Simple mode meaningfully declutter all pages, or should the toggle be
   scoped/removed? Default is `expert`.
9. **Orphaned pages in nav** — Reports, Reports Pack, and Pricing Health are not in the sidebar
   (only reachable via in-page links). Add them to nav (or under a Portfolio submenu)?
10. **"Net worth" vs "Total value"** — the same computed figure (`value_portfolio.total_value`) is
    labelled "Total value" on Portfolio and "Net worth" on Snapshot. Liabilities are already
    negative, so they coincide. Should these be distinct concepts (gross value vs net worth), and
    should assets/liabilities be broken out consistently?
11. **Canonical home for duplicated data** — 01/06 list ~12 pieces of information shown on 3-6 pages
    each (value, allocation, movers, briefing, headlines, drift, runway, review…). Confirm the
    recommended canonical homes (06 §c) or specify your own; decide whether other pages should link
    rather than recompute.
12. **Insurance cash value excluded from net worth** — deliberate (isolated register). Confirm this
    stays, or offer an opt-in to include it.

## AI

13. **AI chat persistence** — chat is streamed and not saved. Do you want conversation history
    (which would use `AIConversation`/`AIMessage`)? Any retention/privacy constraints?
14. **AI validator strictness** — the grounded validator can reject legitimate answers (heuristic
    number/ticker matching) and fall back to the template. Acceptable, or tune? Any appetite for a
    stricter/looser posture?

## Security & deployment

15. **Target exposure** — is the rebuild still single-user local-appliance, or does it need to
    support LAN/multi-user/internet? This determines whether TLS, CSRF tokens, per-user isolation,
    password (vs 4-digit PIN), and a secret manager are in scope (see 07 gaps).
16. **PIN policy** — keep 4-digit numeric PIN, or allow/require stronger secrets? Offline
    brute-force of a stolen encrypted DB is the residual risk.
17. **App writes its own `.env` and runs a sudo helper** — acceptable for an owner-operated
    appliance. Should the rebuild keep in-app provider/key editing and system controls, or move
    secrets/ops to an out-of-band channel?

## Provider / routing

18. **Provider priority policy** (`DEFAULT_PRIORITY`) is hard-coded per lane. Should users be able
    to customise source priority (beyond the per-instrument override)?
19. **Bond/deposit/retirement valuation** — lanes route to `statement`/`accrual`/`manual`, but the
    `calculated_accrual` method and statement-import are not obviously implemented end-to-end.
    Confirm intended behaviour for FDs/bonds (accrued interest calc) and retirement accounts.
20. **`ecb_fx` as an FX source** — reference-only, never a trading quote; confirm it should never
    price a holding, only translate.

## Reporting / tax

21. **Base-currency realised total at "today's FX"** is explicitly not-for-filing. Is a per-date FX
    reconstruction desired for accurate tax reporting, or is native-currency-only sufficient?
22. **Statements / cost-of-ownership** are "for your accountant, not tax advice". Confirm no
    jurisdiction-specific tax logic is ever added (the product guarantee says never).

## Housekeeping

23. **Stray files in repo root** — `2026-06-28…txt`, `2026-06-30…txt`, `09-Jul-2026` look like
    working notes/transcripts. Intentional, or should they be removed/gitignored?
24. **`verify_token` / commented `_carry_forward` / no-op `account` fetch** (08 §1) — confirm these
    are safe to delete in the rebuild.

<!-- AUDIT COMPLETE -->
