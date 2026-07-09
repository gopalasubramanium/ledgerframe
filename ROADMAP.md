# ROADMAP.md — LedgerFrame Parked Items

**The rule: nothing on this list is built without a plan file in `docs/plans/`.**
These are accumulated breadcrumbs from the v2 decision audit — deliberately *not*
v2 work. Each entry is parked until a plan file covering it exists. Some carry
explicit gates or conditions (below) that a plan file must additionally satisfy.
Source: `docs/audit/DECISIONS.md` (D-001–D-080). Entries mirror that file's
merges — the historical-FX item is a single merged entry (D-020 + D-076).

---

| # | Item | Origin | Conditions / gates | Status |
|---|------|--------|--------------------|--------|
| R-1 | Optional passphrase mode (8–64 chars) | D-002 | — (PIN remains an access lock, not data-at-rest protection) | parked |
| R-2 | User-requestable transaction currencies | D-006 | Must be FX-validated — a currency may exist in the master only if the FX service can translate it | parked |
| R-3 | Domicile for fund-tax display | D-007 | Reintroduces a domicile field beyond the single authoritative `listing_country` | parked |
| R-4 | Instrument notes | D-015 | Follows the drop of the general `Note` table; per-record note fields cover the current need | parked |
| R-5 | Opt-in AI chat history | D-016 | Opt-in only; default remains ephemeral (Product Guarantee 6 — no stored AI conversations) | parked |
| R-6 | `spec` (specific-lot) cost-basis method | D-018 | Extends the per-account fifo/average selector | parked |
| R-7 | Corporate-actions audit: spin-offs, symbol changes as first-class recordings | D-019 | Audit whether other corporate actions need first-class recording; splits/bonuses already engine-covered | parked |
| R-8 | Historical FX series (enables trade-date backfill + per-date realised totals) | D-020, D-076 | Merged entry. Native-currency stays the filing-grade output; base-currency realised totals stay explicitly indicative with caveats preserved | parked |
| R-9 | Insurance cash value: opt-in inclusion in Net worth | D-039 | Opt-in only; default remains permanently excluded in v2, stated visibly on Insurance and Net worth pages | parked |
| R-10 | App-wide Detail level | D-040 | Gated on per-page specs (v2 scopes Detail level to Home only) | parked |
| R-11 | User-defined scenario shocks | D-058 | Gated on a proper plan file; "scenario, never a forecast" preserved | parked |
| R-12 | Revisit AI validator strictness | D-070 | Only if fallback frequency proves high in practice; the validation contract may not weaken (Product Guarantee 7) | parked |
| R-13 | Per-lane provider priority editing | D-072 | Only on demonstrated need; no user-editable provider priority in v2 (visibility yes, editability no) | parked |
| R-14 | FD accrued-interest valuation | D-073 | First post-v2 feature. Plan file **must cover day-count conventions, compounding variants, maturity handling, and provenance labelling of calculated values**. `calculated_accrual` retained in the ValuationMethod vocabulary but no v2 lane emits it | parked |
| R-15 | User-configurable review thresholds | D-084 | The v2 defaults are owner-set (D-084: runway 3 months, goal 180 days, the rest as audited); this makes them user-editable. Each still a named constant with a rationale | parked |

---

## Themes

### v2.1 — "accounting precision" (D-088)

The first coherent post-v2 milestone bundles three parked items that together
sharpen the ledger's accounting fidelity. They are grouped for sequencing only —
**each still requires its own plan file** before any is built, and each keeps its
individual gate:

| In the theme | Item | Individual gate (unchanged) |
|---|---|---|
| R-6 | `spec` (specific-lot) cost-basis method | extends the per-account fifo/average selector |
| R-8 | Historical FX series (trade-date backfill + per-date realised totals) | native currency stays filing-grade; base totals stay explicitly indicative |
| R-14 | FD accrued-interest valuation | plan file must cover day-count, compounding, maturity, and provenance labelling of calculated values |

All other R-items remain independent parked breadcrumbs, not part of this theme.

---

## Not on this list (recorded, but not ROADMAP)

- **SaaS/PaaS hardening layer** (D-001) — a future proprietary layer, recorded
  in an ADR rather than here. v2 core must not make choices that preclude it,
  but it is out of scope for v2 core and is not a parked ROADMAP item.
