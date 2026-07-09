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
  sector, tag masters + admin screens; migration dispositions. Blocked
  extractions (DEF-1..DEF-6) flagged, not guessed — app source absent from repo.
- **docs/specs/INFORMATION-ARCHITECTURE.md** — IA principles P-1..P-8 + Reports
  Pack exception verbatim; full page map (page/route/nav group/purpose); per-page
  canonical ownership tables (Owns / Summarises-with-reader / Links); navigation
  spec (D-043 groups, /snapshot redirect, /global removed, rotation eligibility);
  Home Simple/Full composition + ticker strip (D-046/D-047); feature-verdict
  appendix (Batches 7–9) + a killed/dropped safeguard appendix.

## IN-PROGRESS

- (none)

## NEXT

Remaining specs, one per session, in `docs/plans/spec-generation.md` order:
1. docs/specs/PRODUCT-SPEC.md
2. docs/specs/DESIGN-SYSTEM.md
3. docs/specs/SECURITY-BASELINE.md

## Needs decision

- **App source not in repo → DEF-1..DEF-6 blocked.** MASTER-DATA.md §9 lists
  six vocabularies whose authoritative values live in service-layer code that
  is not committed here (currency union, asset_subclass, ACCOUNT_KINDS,
  POLICY_TYPES/FREQUENCIES, DOC_CATEGORIES/CONTACT_ROLES, sector seed). They
  are left unfilled per the no-guessing rule. To resolve: commit the app code
  here (or run the extraction against it) and fill the seed lists in place.
  These are mechanical, not product decisions.
- **Cash flow route (D-056).** Page renamed Planning → Cash flow, but whether
  the route becomes `/cash-flow` (with redirect) or stays `/planning` is not
  decided. See INFORMATION-ARCHITECTURE.md "Needs decision". Product decision.
