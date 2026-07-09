# LedgerFrame v2 — Spec Generation Prompts

Run each in Claude Code from the `ledgerframe/` repo root. **One spec per
session.** After each: review it yourself, commit, and replace/upload the
file in project knowledge. If a session hits limits mid-file, start fresh
with: "Continue generating docs/specs/<FILE>. Read what exists, resume from
the first incomplete section."

Every prompt shares the same rules, stated once here and referenced below:

> SHARED RULES: Read CLAUDE.md, docs/audit/DECISIONS.md, and the audit files
> named below. DECISIONS.md is binding — where it amends or overrides an
> audit recommendation, the decision wins. Never invent content not present
> in the audit or decisions. Anything unresolved goes in a "Needs decision"
> section at the end, never guessed. End the file with a "Derived from"
> footer listing the source documents and the decision IDs applied.

---

## 0. ROADMAP.md (quick pre-task)

```
Apply the SHARED RULES. Read docs/audit/DECISIONS.md only.

Write ROADMAP.md (repo root): extract every item marked ROADMAP across all
decisions. One entry per item with: name, originating decision ID(s), any
recorded conditions or gates (e.g. "requires plan file covering day-count
conventions..."), and status "parked". Merge duplicates that DECISIONS.md
already merged (e.g. the historical FX series entry). Add a header stating
the rule: nothing on this list is built without a plan file in docs/plans/.
```

## 1. docs/specs/GLOSSARY.md

```
Apply the SHARED RULES. Sources: audit/09-GLOSSARY.md,
audit/06-UI-AND-TERMINOLOGY-AUDIT.md, DECISIONS.md Batch 4 (D-021..D-030)
plus any terminology set elsewhere (e.g. D-056 "Cash flow", D-062's two
document concepts).

Create docs/specs/GLOSSARY.md:
- One canonical definition per domain term. Where DECISIONS.md resolved a
  conflict, use only the chosen term; list retired synonyms in a
  "Deprecated terms" table (term → replacement → decision ID).
- Include the formula relationships (Net worth = Gross assets − Liabilities).
- Include both movers pairs with the rule for which list type uses which.
- Include the three-layer freshness structure (Entitlement / Stale / Status)
  and the Source/Provider/Routing split.
- Include the "Product Guarantees" block from DECISIONS.md verbatim.
- Definitions must be precise enough to be normative for UI copy.
```

## 2. docs/specs/MASTER-DATA.md

```
Apply the SHARED RULES. Sources: audit/02-DATA-MODEL.md,
audit/06-UI-AND-TERMINOLOGY-AUDIT.md section (a), DECISIONS.md Batch 2
(D-005..D-013) and D-010's enumerated-values requirement.

Create docs/specs/MASTER-DATA.md:
- The D-005-C architecture stated normatively: fixed vocabularies
  (code-defined, served via /refdata, DB CHECK) vs user-extensible masters
  (DB tables). Frontend carries zero vocabulary copies.
- Every vocabulary with its COMPLETE seed value list (no vocabulary is
  specified without its values; source them from the service layer as
  recorded in DECISIONS.md).
- The currency master with is_base_eligible and the FX-translatability rule.
- The country/region model (listing_country authoritative, region derivation).
- Institution master, tag master (case-insensitive uniqueness), sector master.
- Migration dispositions recorded in DECISIONS.md (free-text → ISO2 with
  review list; asset_category → tags; tag dedupe pass).
- Admin-screen requirements for each user-extensible master.
```

## 3. docs/specs/INFORMATION-ARCHITECTURE.md

```
Apply the SHARED RULES. Sources: audit/01-FEATURE-INVENTORY.md,
audit/06 sections (c) and (d), DECISIONS.md Batches 5–9 (D-031..D-069).

Create docs/specs/INFORMATION-ARCHITECTURE.md:
- The general IA principles first, verbatim from DECISIONS.md (canonical-home
  rule + enforcement corollary; "where the answer is explained, not where
  its ingredients are typed"; scoped-views-are-filters; the Reports Pack
  exception; group names guessable from contents).
- The full page map: every page, its route, its nav group (D-043 structure
  with the Planning group / Cash flow page naming), and its purpose in one
  line.
- Per page: the canonical-home table — every piece of information it owns,
  every summary it shows of other pages' information (with the reader it
  must reuse), and its links.
- The navigation spec: sidebar groups and fixed order, route dispositions
  (/snapshot redirect kept, /global removed), rotation eligibility.
- Home composition per D-046/D-047 including Simple/Full layouts.
- Every feature verdict (KEEP/MERGE/SIMPLIFY/KILL) from Batches 7–9 as an
  appendix table with decision IDs, so no killed feature resurfaces
  unnoticed.
```

## 4. docs/specs/PRODUCT-SPEC.md

```
Apply the SHARED RULES. Sources: audit/01-FEATURE-INVENTORY.md,
audit/04-CALCULATION-ENGINE.md, DECISIONS.md throughout.

Create docs/specs/PRODUCT-SPEC.md:
- What LedgerFrame is: single-user, local-first wealth reporting appliance
  (D-001), who it's for, and the deployment posture including the
  VPN/Tailscale remote-access stance and the SaaS-out-of-scope-but-not-
  precluded note.
- The Product Guarantees block (verbatim from DECISIONS.md).
- The deliberate-semantics register: every rule DECISIONS.md marked as
  protected design (contributions don't reduce runway; 'once' obligations
  excluded from burn; estate/insurance no-FK isolation; honest-NULL FX;
  never-overwrite-NAV; insurance cash value excluded from net worth; the
  honesty-features list — not-Sharpe disclaimer, real-vs-ETF-proxy badge,
  visible validator fallback, etc.).
- Review signal thresholds as the named-constants table with per-threshold
  rationale (D-059).
- The scope principle (D-065): no new capabilities; UI for existing
  capabilities that decided features depend on is in scope.
- First-run checklist contents (D-045) and the Settings Privacy section
  (D-069).
```

## 5. docs/specs/DESIGN-SYSTEM.md

```
Apply the SHARED RULES. Additional source: the "Design brief" section of
the Rebuild Playbook (docs/ if committed, else I will paste it).

Create docs/specs/DESIGN-SYSTEM.md:
- Design principles (numbers-first, semantic-only colour, typographic
  hierarchy, provenance as first-class UI).
- Design tokens: full colour palette (light/dark/system), type scale,
  spacing scale, density modes (comfortable/compact per D-045/D-078).
- The four page templates (overview / entity-detail / worklist / settings)
  and which template each page in INFORMATION-ARCHITECTURE.md uses.
- The component library inventory: every component (MoneyInput,
  QuantityInput, PercentInput, DateInput, InstrumentPicker, MasterSelect,
  DataTable, ProvenanceBadge, StalenessChip, TrendStat, AllocationDonut,
  PriceChart, EmptyState, PageHeader, ReviewCard, plus any the feature
  verdicts require — e.g. the treemap per D-053, the quote-card row per
  D-046, the ticker strip scoped to Home Full per D-047) with its props
  surface and usage rules.
- The hard rule from CLAUDE.md restated: pages compose components; raw
  inputs and ad-hoc styling are forbidden.
- Chart layer policy: house SVG only; the D-053 treemap plan with its
  recorded ECharts escape hatch.
- Accessibility baseline: WCAG AA contrast, keyboard navigation,
  reduced-motion and high-contrast settings (D-078 per-device set).
```

## 6. docs/specs/SECURITY-BASELINE.md

```
Apply the SHARED RULES. Sources: audit/07-SECURITY-POSTURE.md,
audit/05-PROVIDERS-AND-ROUTING.md, DECISIONS.md Batches 1 and 10.

Create docs/specs/SECURITY-BASELINE.md:
- Threat model per D-001 (single-user local appliance; LAN opt-in with PIN;
  internet exposure out of scope; VPN/Tailscale as sanctioned remote access).
- The D-004 gap disposition table: each of the 14 gaps → fixed-in-v2 or
  accepted-with-rationale.
- PIN policy (D-002) including the access-lock-not-encryption statement and
  the disk-encryption guidance.
- Sudo helper as documented install-time opt-in with its full action
  allow-list; graceful degradation (D-003).
- The normative AI validation contract (D-071), stated as: implementation
  may improve, the contract may not weaken. Include the visible-fallback
  signal (D-070).
- The ingress/egress symmetry principle (D-075/D-060): one validated path
  out, one sanitised path in; no feature bypasses either.
- No-egress toggle semantics: zero outbound calls including version check
  and feed fetches; Privacy section displays current state as a statement.
- Positive privacy guarantees: AI questions never persisted (D-016);
  no telemetry; hash-chained audit log (in scope, D-004).
- Dependency pinning + CVE scan in CI; rate-limiter durability;
  CORS-credentials production assertion (D-004 fix list).
- Export sanitisation rule: all exports server-side (D-050).
```
