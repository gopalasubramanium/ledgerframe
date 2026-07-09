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
  - **Still open (authoring, not extraction):** DEF-2 `asset_subclass` (no enum
    in code; `etf`/`reit` from D-009 not found) and DEF-6 sector seed (GICS-like
    authorship; `_SECTOR_MAP` 12-value reference recorded). MASTER-DATA §9.

## IN-PROGRESS

- (none)

## NEXT

1. **Kitchen-sink review** — ratify the PROPOSED design tokens
   (DESIGN-SYSTEM §2) once the component library is built.
2. **DEF-2 / DEF-6 authoring** — decide the final `asset_subclass` fixed vocab
   and the GICS-like sector seed (both now have code-observed values to author
   from; neither is blocked on missing source).
3. **App-source milestone** — when the v1 code enters this repo, re-verify the
   backfilled values against it (cites already point at the exact lines).

## Needs decision

- **DEF-2 / DEF-6 (authoring, not blocking).** The final `asset_subclass`
  vocabulary and the sector master seed need an authoring decision — see
  MASTER-DATA §9. Not product-blocking; both have concrete starting values.
- **Design token ratification.** PROPOSED palette/type/spacing/density values
  (DESIGN-SYSTEM §2) are working values until the kitchen-sink review; the
  UI/serif font choice may need an ADR if self-hosting adds a dependency.
- **Design token ratification.** The PROPOSED palette/type/spacing/density values
  in DESIGN-SYSTEM §2 are working values until ratified at the kitchen-sink
  review; the UI/serif font choice may need an ADR if self-hosting adds a
  dependency. Not blocking.
- ~~Cash flow route~~ — **resolved**: `/cash-flow` canonical, `/planning`
  redirects (D-022 principle applied to D-056).
