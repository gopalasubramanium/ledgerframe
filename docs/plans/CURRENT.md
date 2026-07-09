# CURRENT — Active Plan

The spec-generation sequence is defined in `docs/plans/spec-generation.md`
(ROADMAP pre-task + specs 1–6). This file tracks live status. The next session
starts from files, not memory.

## DONE

- **ROADMAP.md** (repo root) — all 14 parked items (R-1..R-14) extracted from
  DECISIONS.md, historical-FX merged (D-020 + D-076), header rule stated
  (nothing built without a plan file in `docs/plans/`). SaaS/PaaS (D-001)
  recorded as ADR-note, not a ROADMAP item.
- **docs/specs/GLOSSARY.md** — canonical term definitions; Deprecated-terms
  table (term → replacement → decision ID); Net worth formula; both movers
  pairs with the which-list rule; three-layer freshness structure; Source /
  Provider / Routing split; Product Guarantees block verbatim.
- **docs/specs/MASTER-DATA.md** — D-005 hybrid architecture (fixed vocabs via
  /refdata + DB CHECK vs user-extensible masters via DB tables, frontend zero
  copies); every fully-decided fixed vocabulary with complete seed values;
  currency master + FX-translatability rule; country/region model; institution,
  sector, tag masters + admin screens; migration dispositions. (DEF backfill
  since completed — see below; only DEF-2/DEF-6 authoring items remain.)
- **docs/specs/INFORMATION-ARCHITECTURE.md** — IA principles P-1..P-8 + Reports
  Pack exception verbatim; full page map (page/route/nav group/purpose); per-page
  canonical ownership tables (Owns / Summarises-with-reader / Links); navigation
  spec (D-043 groups, /snapshot redirect, /global removed, rotation eligibility);
  Home Simple/Full composition + ticker strip (D-046/D-047); feature-verdict
  appendix (Batches 7–9) + a killed/dropped safeguard appendix.
- **docs/specs/PRODUCT-SPEC.md** — what LedgerFrame is + who it's for; deployment
  posture (loopback default, LAN+PIN, VPN/Tailscale, SaaS out-of-scope-not-
  precluded); Product Guarantees verbatim; deliberate-semantics register (honesty
  features, architectural invariants, calculation honesty invariants incl.
  never-overwrite-NAV, honest-NULL FX, no-FK isolation); Review threshold
  named-constants table w/ rationale (D-059, values from 04 §13); scope principle
  (D-065/P-7); first-run checklist (D-045); Settings Privacy section (D-069).
- **docs/specs/DESIGN-BRIEF.md** — the Rebuild Playbook design brief, committed
  verbatim so the design source never leaves the repo again.
- **docs/specs/DESIGN-SYSTEM.md** — principles (numbers-first, semantic-only
  colour, typographic hierarchy, provenance-first); design tokens (slate palette
  light/dark, type scale 12/13/14/16/20/28, spacing, density comfortable/compact)
  — concrete values PROPOSED, to ratify at kitchen-sink review; four page
  templates + per-page mapping; full component inventory (props + usage rules);
  the compose-components hard rule; house-SVG chart policy + D-053 treemap/ECharts
  escape hatch; WCAG-AA / keyboard / reduced-motion / high-contrast a11y baseline.
- **INFORMATION-ARCHITECTURE.md amended** — Cash flow route resolved to
  `/cash-flow` (D-022 principle), `/planning` redirects; Needs-decision item
  cleared.
- **docs/specs/SECURITY-BASELINE.md** — threat model (D-001); D-004 gap
  disposition table (all 14 → fixed-in-v2 / accepted-with-ADR); PIN policy
  (D-002, access-lock-not-encryption + disk-encryption guidance); sudo helper
  install-time opt-in + allow-list + graceful degradation (D-003); normative AI
  validation contract (D-071) + visible fallback (D-070); ingress/egress
  symmetry (P-8/D-075/D-060); no-egress toggle semantics + Privacy state
  statement; positive privacy guarantees (D-016, no telemetry, hash-chained
  audit); CI hardening (dep pinning/CVE, durable rate limiter, CORS assertion);
  server-side export sanitisation (D-050); preserved baseline measures.

**All six specs in `spec-generation.md` are now written** (GLOSSARY, MASTER-DATA,
INFORMATION-ARCHITECTURE, PRODUCT-SPEC, DESIGN-SYSTEM, SECURITY-BASELINE) plus
ROADMAP.md and DESIGN-BRIEF.md.

- **DEF backfill DONE** — extracted verbatim from the legacy v1 source
  (`~/Documents/github/LedgerFrame`, read-only reference; app source enters this
  repo later as its own milestone). Filled in place with file:line cites:
  - DEF-1 currency master seed — 22-code union, base-eligible 9 (`config.py:18`),
    +5 (`refdata.ts:8`), +8 (`PortfolioEditor.tsx:22`); FX-translatability noted
    as runtime-validated (no static list). MASTER-DATA §3.
  - DEF-3 `ACCOUNT_KINDS` (7, `accounts.py:24`); DEF-4 `POLICY_TYPES` (10) /
    `premium_frequency` (4, `insurance.py:23-25`); DEF-5 `DOC_CATEGORIES` (9) /
    `CONTACT_ROLES` (5, `estate.py:19-20`). MASTER-DATA §2.
  - DEF-7 Review constants reconciled against `review.py:25-30` — all values
    matched the audit; two proposed names corrected (`_INSURANCE_SOON_DAYS`,
    `_CORP_ACTION_RECENT_DAYS`). PRODUCT-SPEC §5.
  - Sudo allow-list — exact `_ADMIN_ACTIONS` set (`system.py:24-36`).
    SECURITY-BASELINE §4.
- **DEF-2 / DEF-6 AUTHORED** — the two remaining items were authored (PROPOSED,
  ratify at review), so §9 is now empty:
  - DEF-2 `asset_subclass` fixed vocab (6): `crypto, derivative, equity, etf,
    mutual_fund, reit`. Per-value table names each consumer — only `derivative`
    is read by the router (`router.py:131`); crypto/equity/mutual_fund are
    code-assigned display-only; etf/reit PROPOSED per D-009. bond/deposit/
    retirement deliberately excluded (their lanes route by asset_class, not
    subclass). MASTER-DATA §2.
  - DEF-6 sector master: 11 GICS sectors seeded (PROPOSED, user-extensible), with
    the `_SECTOR_MAP` 12→seed migration mapping — Technology→Information
    Technology; Crypto / Index-ETF / Commodities → no map (sector=null, no silent
    merge). MASTER-DATA §6.

## IN-PROGRESS

- (none)

## NEXT

1. **Kitchen-sink / ratification review** — ratify the PROPOSED values: the
   design tokens (DESIGN-SYSTEM §2) and the authored DEF-2/DEF-6 vocabularies
   (MASTER-DATA §2/§6).
2. **App-source milestone** — when the v1 code enters this repo, re-verify the
   backfilled values against it (cites already point at the exact lines).

## Needs decision

All open items are **ratification of authored PROPOSED values** (not blocking):

- **DEF-2 `asset_subclass` (MASTER-DATA §2)** — ratify/amend the 6-value vocab;
  `etf`/`reit` are the two speculative additions (D-009, not in code).
- **DEF-6 sector seed (MASTER-DATA §6)** — ratify the 11 GICS sectors and the
  `_SECTOR_MAP` migration mapping (esp. the 3 no-map values left as `sector=null`).
- **Design tokens (DESIGN-SYSTEM §2)** — ratify PROPOSED palette/type/spacing/
  density; the UI/serif font choice may need an ADR if self-hosting adds a
  dependency.
- ~~Cash flow route~~ — **resolved**: `/cash-flow` canonical, `/planning`
  redirects (D-022 principle applied to D-056).
