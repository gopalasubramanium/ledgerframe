# REVIEW-GUIDE.md — Plain-language review companion

**Who this is for.** You — the owner. You know accounting, portfolios,
insurance, and tax cold. You do **not** need to know anything about software.
This guide translates every material decision in the eight planning documents
into plain English so you can read it *alone*, understand what was decided, and
either **approve** each item or **challenge** it.

**How to read it.** Every item below has three parts:

- **In practice** — one concrete example, with realistic-feeling numbers or a
  moment where the rule helps you, so you can see what it *does*.
- a **decision ID** in brackets (e.g. `[D-039]`) — the permanent label for that
  decision, so you and I can refer to it unambiguously later.
- a **checkbox line**: `[ ] Approve  [ ] Challenge: ______`. Tick one. If you
  challenge, write what you'd change on the line.

**A word on vocabulary.** Where a technical word is unavoidable, it is explained
in parentheses the first time, in this register:

> a **fixed vocabulary** (a dropdown list whose options only change with a
> software release — users can't add to it)
>
> a **user-extensible master** (a dropdown list users *can* add to, like a
> chart-of-accounts list you maintain yourself)

Financial terms (FIFO, cost basis, XIRR, drift, cash value, accrual) are used
as-is — you know them better than I do.

**Authority.** *Nothing in this guide changes the specifications.* It is a
reading aid. Where this guide summarises, the specification is the authoritative
text and wins on any discrepancy. The eight source documents are:

| Short name | File | What it governs |
|---|---|---|
| PRODUCT-SPEC | `docs/specs/PRODUCT-SPEC.md` | What the product is, its promises, protected rules |
| GLOSSARY | `docs/specs/GLOSSARY.md` | The exact words shown to users + their definitions |
| MASTER-DATA | `docs/specs/MASTER-DATA.md` | Every dropdown list and its values |
| INFORMATION-ARCHITECTURE (IA) | `docs/specs/INFORMATION-ARCHITECTURE.md` | Every page and what lives on it |
| DESIGN-SYSTEM | `docs/specs/DESIGN-SYSTEM.md` | The look, the input controls, accessibility |
| SECURITY-BASELINE | `docs/specs/SECURITY-BASELINE.md` | Privacy, the PIN, what leaves the device |
| DESIGN-BRIEF | `docs/specs/DESIGN-BRIEF.md` | The visual intent (institutional, numbers-first) |
| ROADMAP | `ROADMAP.md` (repo root) | Everything deliberately parked for later |

---

## ★ ATTENTION — the ~10 items that most need your judgment

These are the calls where your professional eye matters most: values I
**authored** (invented, because no prior source existed) and marked
**PROPOSED**; the thresholds that decide what the software nags you about; and
the handful of places where a specification **interpreted** a decision rather
than copying it. Everything here also appears in full in the body below — this
is the shortlist to look at first.

> **✔ Round 1 resolved (Batch 12, D-081–D-088).** Your challenges from the first
> read have been recorded as decisions D-081–D-088 in `docs/audit/DECISIONS.md`
> and folded into the specs. Each affected item below now carries a **→ Resolved**
> line. A2 (the 11 GICS sectors) and §3.3 (the v1 removals) were reviewed and
> **affirmed unchanged**.

### A1. The two invented subclass values: `etf` and `reit` `[DEF-2 / D-009]`

The instrument "subclass" list has six values. Four (`crypto`, `derivative`,
`equity`, `mutual_fund`) were read straight out of the existing code. **Two —
`etf` and `reit` — I invented**, because the design calls for them but nothing
in the code assigns them yet. They are display/reporting labels only; no
calculation depends on them.

- **In practice:** you hold a REIT and an S&P 500 ETF. Today both would just
  read "equity". With these values, reporting can show them as their own
  categories.
- **→ Resolved (D-085):** both values kept, with classification guidance —
  **asset class = economic exposure, subclass = wrapper.** A listed REIT is
  therefore `class = property` + `subclass = reit`; the ETF is `class = equity`
  + `subclass = etf`. `[x] Approved with guidance`

### A2. The 11 GICS sectors as the starting sector list `[DEF-6 / D-009]`

There is **no sector list in the existing code** — only an informal
ticker→sector lookup. So I proposed seeding the sector dropdown with the **11
standard GICS sectors**: Energy · Materials · Industrials · Consumer
Discretionary · Consumer Staples · Health Care · Financials · Information
Technology · Communication Services · Utilities · Real Estate. This is a
user-extensible master — you can add your own sectors later.

- **In practice:** when you tag a holding's sector, you pick from these 11
  instead of typing free text. Two of them (Materials, Real Estate) start empty
  because nothing currently maps to them.
- **→ Resolved: affirmed unchanged.** You accepted the 11 GICS sectors as
  written. `[x] Approved`

### A3. The "three-null" sector migration `[DEF-6 / D-009]`

The old informal lookup had 12 values. Nine map cleanly to GICS. **Three do
not** — `Crypto`, `Index / ETF`, and `Commodities` — because they are asset
classes or fund wrappers, **not company sectors**. The decision: when data is
migrated, set each of these three to **blank (null)**, *not* forced into the
nearest sector. (In particular, Commodities is **not** merged into GICS
*Materials*.) Allocation for these is already handled by their asset class.

- **In practice:** your Bitcoin holding will show sector = blank rather than a
  made-up sector. Your gold ETF will not be miscounted as a "Materials company".
- **→ Resolved (D-082):** the null stays in the data (no forced merge), **and**
  sector charts now show an explicit **"Not sector-classified (non-equity)"**
  bucket so those holdings are visible rather than dropped. `[x] Approved with change`

### A4. One rename in that migration: `Technology` → `Information Technology` `[DEF-6]`

The old label "Technology" is renamed to the GICS-canonical "Information
Technology". This is the only *rename* (as opposed to exact match or null) in
the mapping.

- **In practice:** holdings previously under "Technology" appear under
  "Information Technology" after migration. Same holdings, GICS-standard name.
- `[ ] Approve  [ ] Challenge: ______`

### A5. The Review thresholds — what the software decides is "worth a look" `[D-059]`

The Review page raises flags when certain numbers cross a line. Every line is a
**named constant with a one-line rationale**. The values were checked against
the existing code and all matched; I list them in full in §2.9. The ones most
worth your eye:

| Flag fires when… | Threshold | Rationale |
|---|---|---|
| Liquid assets below this share of gross assets | **15%** | below ~1/7 is too thin a cushion |
| Cash runway below this many months | **3 months** ✎ | owner-set floor (D-084) |
| A goal's target date is within | **180 days** ✎ | owner-set half-year notice (D-084) |
| A cash obligation is due within | **30 days** | one month's notice |
| An insurance renewal is within (or overdue) | **30 days** | one month to renew before lapse |
| A split/bonus occurred within | **45 days** | recent corporate action → "verify" |
| `other`-classed holdings exceed | **10%** of gross assets ✎ | over-use of the escape valve → reclassify (D-087) |
| A holding's data-confidence score is below | **50 / 100** | poorly-sourced value deserves attention |
| A market quote is older than | **15 minutes** | flagged stale (NAV/end-of-day use 30 hours) |

- **In practice:** with your 3-month runway floor, if liquid assets ÷ monthly
  net burn falls to 2.8 months, Review flags it.
- **→ Resolved (D-084 / D-087):** you set **runway = 3 months** (was 6) and
  **goal = 180 days** (was 90); the rest keep the audited values. These two now
  *deliberately* differ from the legacy code — noted in the spec's audit trail so
  the mismatch is honest, not an error (this affects Spot-check 1 below). A new
  **`other`-over-use signal (10%)** was added (D-087). Making these thresholds
  user-editable is parked as R-15. `[x] Approved with changes`

### A6. The FX / tax posture — the product never does jurisdiction tax `[D-077, D-020, D-076, D-004]`

Three linked stances an accountant should sign specifically:

1. **No jurisdiction tax logic — ever.** The "long-term" holding threshold
   (`long_term_days`) is a plain number *you* set, with **no country presets**.
   Statements and Realised P/L outputs are labelled "for your accountant" — the
   product classifies nothing as taxable.
2. **Trade-date FX is honest-null.** The native→base exchange rate is captured
   at the live rate **only when the trade happens today**. For a backdated
   trade, the rate is honestly left **blank**, never back-filled with today's
   rate. The trade-date-FX realised total is shown with an **"excluded-events
   count"** so you can see how many legs couldn't get an honest rate.
3. **Native currency is the filing-grade number.** Realised P/L is exact in the
   instrument's own currency; the base-currency total is explicitly *indicative*
   (today's FX) or trade-date-FX-with-caveat — never presented as exact.

- **In practice:** you sell a US stock bought 2 years ago in your INR-base
  ledger. The USD realised gain is exact and filing-grade; the INR figure is
  marked indicative; and because the buy was backdated, that leg is counted in
  the "excluded from trade-date total" tally rather than converted at a
  wrong-but-convenient rate.
- **→ Resolved: affirmed unchanged.** The FX/tax posture stands as written.
  `[x] Approved`

### A7. Insurance cash value is excluded from the Net worth *total* `[D-039, D-081]`

The surrender/cash value of a policy is **excluded from the headline Net worth
total** in v2. It is stated visibly on the Insurance page and appears as a
labelled line on the Net worth page.

- **In practice:** you have a whole-life policy with ₹8L cash value. Net worth's
  headline does not include it.
- **→ Resolved (D-081):** you asked that the amount be **shown, not just named**.
  The Net worth line now reads *"Insurance cash value (excluded): ₹8,00,000 —
  see Insurance"* — the figure is visible but still excluded from the total.
  (Opt-in *inclusion* stays parked — R-9.) `[x] Approved with change`

### A8. The currency list — 22 codes, only 9 usable as base currency `[D-006, DEF-1]`

The currency dropdown is seeded with **22 currency codes**, merged and
de-duplicated from three divergent legacy lists. Of these, **only 9** may be
chosen as your **base/reporting** currency (SGD, USD, INR, EUR, GBP, JPY, AUD,
CNY, HKD); the other 13 are valid only as a *transaction* currency. The
governing rule: a currency exists in the list **only if the FX service can
actually translate it** — checked live, not from a frozen list.

- **In practice:** you can record a trade in Thai baht (THB) but you cannot set
  THB as your reporting currency; the base-currency picker offers only the 9.
- `[ ] Approve  [ ] Challenge: ______`

### A9. Cost-basis method: `fifo` or `average` only; specific-lot is parked `[D-018]`

Each account carries a cost-basis method, chosen from exactly **two** options in
v2: **FIFO** or **average**. Specific-lot (`spec`) identification is deliberately
**not** a v2 option; it is parked (R-6).

- **In practice:** you set a brokerage account to FIFO and a fund account to
  average. You cannot hand-pick lots on a sale in v2.
- **→ Resolved (D-088):** specific-lot stays out of v2, but it is now bundled
  with historical FX and FD accrual into a named **v2.1 "accounting precision"**
  theme (§6) — a clear first post-v2 milestone rather than a loose parked item.
  `[x] Approved, sequenced to v2.1`

### A10. Region is *derived* from listing country into six buckets `[D-007, D-083]`

There is no editable "region" field. Region is computed from an instrument's
listing country into **six buckets (D-083): India · Singapore · US · Europe ·
APAC · Other** (full listing-country membership table in MASTER-DATA §4). "Other"
is the catch-all for any country not on the Europe or APAC lists.

- **In practice:** a London-listed stock now falls into **Europe** and a
  Tokyo-listed stock into **APAC**, instead of both collapsing to "Global".
- **→ Resolved (D-083):** the four-bucket model was **expanded to six** at your
  request, with a full country→region mapping table authored in the spec.
  `[x] Approved with change`

### A11. Two interpretations you should bless (specs went beyond copying) `[D-022/D-056, DEF-7]`

Two places where a spec made a *judgment call* rather than transcribing a
decision:

- **The "Cash flow" page's address was chosen, not given.** The page was renamed
  from "Planning" to "Cash flow"; the specification then *decided* its web
  address should be `/cash-flow` (matching the name), keeping the old `/planning`
  address working as a redirect. `[D-022 principle applied to D-056]`
- **Two threshold names were corrected against the code.** Two of the Review
  constants had been proposed under wrong names; checking the real code corrected
  them to `_INSURANCE_SOON_DAYS` and `_CORP_ACTION_RECENT_DAYS`. Values were
  unchanged. `[DEF-7]`
- **In practice:** these don't change any number you see; they're recorded here
  only because they were interpretation, not transcription, and you should know
  where that happened.
- `[ ] Approve  [ ] Challenge: ______`

---

# 1. What the product promises users — and never does

LedgerFrame is a **single-user, local wealth-reporting appliance**: it runs on
your own machine, consolidates your (and your household's) holdings into one
private picture, and **reports** — it does not act. `[D-001]`

## 1.1 The seven Product Guarantees (the promises)

These are copied **verbatim** into the app's Legal page, the glossary, and the
README. They are the load-bearing promises.

**G1 — No trades.** The platform never places or executes a trade. There are no
"order" connections at all; even the market-data link (Kite) is read-only.
`[Guarantee 1]`
- **In practice:** there is literally no button, anywhere, that could buy or sell
  on your behalf. It is a ledger, not a broker.
- `[ ] Approve  [ ] Challenge: ______`

**G2 — No advice.** Never gives buy/sell/hold, tax, or financial advice. Every
AI answer ends with a fixed *"Information only, not financial advice."* line.
`[Guarantee 2]`
- **In practice:** ask the built-in assistant "should I sell my HDFC?" and it
  will refuse to answer as advice and show facts instead, with the disclaimer.
- `[ ] Approve  [ ] Challenge: ______`

**G3 — No fabrication.** Never invents a price, headline, or figure. When inputs
are insufficient it shows **"—" (a dash) with a reason**, never a made-up number.
`[Guarantee 3]`
- **In practice:** if a fund's NAV is unavailable today, the value cell shows
  "—" and tells you *why* ("mapping required"), rather than guessing a price.
- `[ ] Approve  [ ] Challenge: ______`

**G4 — No jurisdiction tax logic, ever.** The long-term threshold is a neutral
number you set; no country presets. Tax outputs are "for your accountant."
`[Guarantee 4 / D-077]` (see A6)
- **In practice:** the software will never tell you a gain is "long-term
  taxable" under any country's rules — it gives you the dated lots and lets you
  (the accountant) apply the law.
- `[ ] Approve  [ ] Challenge: ______`

**G5 — No egress (opt-in).** With the "no-egress" switch on, the device makes
**zero** outbound network calls — including the update check, news feeds, and
version banner. `[Guarantee 5 / D-004]`
- **In practice:** flip one switch and the appliance is network-silent; it will
  still show cached data, honestly marked as stale.
- `[ ] Approve  [ ] Challenge: ______`

**G6 — No stored AI conversations.** Your questions to the assistant and its
answers are **never saved**. `[Guarantee 6 / D-016]`
- **In practice:** you ask a question about your portfolio; when you close the
  panel, there is no transcript kept anywhere.
- `[ ] Approve  [ ] Challenge: ______`

**G7 — The validation contract never weakens.** The rules that keep the AI
honest (§5.3) may be *improved* but may never be *loosened*. `[Guarantee 7 / D-071]`
- **In practice:** a future version can add checks; it is contractually barred
  from removing them.
- `[ ] Approve  [ ] Challenge: ______`

## 1.2 The protected "honesty features" (copy that can't be quietly removed)

These bits of on-screen wording were *deliberately* added to prevent a
misleading impression. They are protected: a future cleanup may not delete them.
`[PRODUCT-SPEC §4a]`

**H1 — "Not a Sharpe ratio" disclaimer.** The "return ÷ volatility" figure is
explicitly labelled **not** a Sharpe ratio (because no risk-free rate is
subtracted). `[D-030]` — *In practice:* stops anyone reading the ratio as a true
risk-adjusted Sharpe. `[ ] Approve  [ ] Challenge: ______`

**H2 — Real-index vs ETF-proxy badge.** On world indices, a badge marks whether
you're seeing a real index or an ETF standing in for it. `[D-051]` — *In
practice:* you know whether "S&P 500" is the actual index or the SPY proxy.
`[ ] Approve  [ ] Challenge: ______`

**H3 — "Reporting, never a trade instruction."** Policy drift reports a gap; it
never names or implies a trade. `[D-055]` — *In practice:* "equity is 4% over
band" — never "sell equity". `[ ] Approve  [ ] Challenge: ______`

**H4 — Contributions don't reduce runway.** A planned contribution builds wealth
and is shown as a monthly-equivalent; it is **never subtracted** from cash
runway. `[D-057]` — *In practice:* deciding to invest ₹50k/month doesn't make
your emergency runway look shorter. `[ ] Approve  [ ] Challenge: ______`

**H5 — One-off ("once") obligations excluded from burn.** Lumpy one-time
outflows are excluded from the *recurring* net burn used for runway. `[D-057]` —
*In practice:* a one-time ₹5L tax payment doesn't distort your monthly burn rate.
`[ ] Approve  [ ] Challenge: ______`

**H6 — Honest-NULL trade-date FX + excluded-events count.** (See A6.) `[D-020,
D-076]` — *In practice:* backdated trades honestly show no trade-date rate and
are counted, not converted at today's rate. `[ ] Approve  [ ] Challenge: ______`

**H7 — Insurance cash-value exclusion lines.** Now a **valued** line — the amount
is shown on Net worth but excluded from the total (see A7). `[D-039, D-081]`
`[x] Approved with change`

**H8 — Visible AI-fallback signal.** When an AI answer fails the honesty checks,
you see *"AI answer didn't pass grounding checks — showing facts directly."*
`[D-070]` — *In practice:* you always know when you're seeing raw facts instead
of the assistant's prose. `[ ] Approve  [ ] Challenge: ______`

## 1.3 What the product is *not* (deployment posture)

**P1 — Runs on your machine, reachable only by you.** By default it listens only
to the same computer ("loopback"). To reach it from another device on your home
network you must set a **PIN** first. `[D-001, D-002]`
- **In practice:** out of the box, nothing on your network — let alone the
  internet — can open your ledger; you opt in to LAN access with a PIN.
- `[ ] Approve  [ ] Challenge: ______`

**P2 — Not built for the public internet.** No web-server TLS, no multi-user
accounts in v2. Remote access is meant to be done by joining the machine's
private network (VPN / Tailscale), not by exposing it online. `[D-001, D-004]`
- **In practice:** you'd reach it from the office the way you'd reach a home NAS
  — over a private tunnel, not a public web address.
- `[ ] Approve  [ ] Challenge: ______`

**P3 — Adds no new financial capabilities.** v2 rebuilds what already exists on a
sounder footing. Any genuinely *new* financial feature is out of scope and goes
to the ROADMAP. `[D-065, P-7]`
- **In practice:** v2 will look and behave like a cleaner version of what you
  have; it won't sprout, say, an FD interest-accrual calculator (that's parked —
  R-14).
- `[ ] Approve  [ ] Challenge: ______`

---

# 2. How money is counted

Every rule here affects a number you will actually see. **All money math happens
in the backend using exact `Decimal` arithmetic; the screen never computes a
financial value — it only displays what the backend computed.** `[PRODUCT-SPEC
§4b]`

## 2.1 The one headline: Net worth `[D-021]`

```
Net worth    = Gross assets − Liabilities
Gross assets = Σ (positive holdings' current market value, in base currency, at today's FX)
Liabilities  = Σ (liability-class holdings, counted negative)
```

**Net worth is the only headline total.** "Gross assets" and "Liabilities"
appear only as labelled components, never as competing headlines. Retired words:
"Total value", "Portfolio value" — both are ambiguous and are banned from the UI.
- **In practice:** your ₹3.2cr of assets minus a ₹90L mortgage reads as **Net
  worth ₹2.3cr**, with Gross assets and Liabilities shown beneath — never a bare
  "portfolio value" that hides the mortgage.
- `[ ] Approve  [ ] Challenge: ______`

## 2.2 Liabilities count negative; gross-asset denominators `[calc honesty]`

A liability-class holding counts **negative** toward Net worth. And every share
/ weight calculation — allocation weight, concentration, drift — divides by
**gross assets** (positive holdings only), so a mortgage cannot distort your
allocation percentages.
- **In practice:** adding a ₹90L mortgage lowers Net worth by ₹90L but does
  **not** make your "equity is 60% of the portfolio" figure lurch — the
  denominator is gross assets, not net.
- `[ ] Approve  [ ] Challenge: ______`

## 2.3 Cost basis, and the two P/L figures `[GLOSSARY; D-026, D-076]`

- **Cost basis** = quantity × FIFO average cost (native currency → base).
- **Unrealised P/L** = current market value − cost basis, on holdings still held.
  ("Paper gain" is a banned colloquialism — the glossary may explain it, the UI
  won't use it.)
- **Realised P/L** = sale proceeds − FIFO-matched cost of the parcels sold.
  **Native currency is exact (filing-grade).** The base-currency total is shown
  either at today's FX (marked indicative) **or** at trade-date FX with an
  excluded-events count (see A6). The report is headed **"Realised P/L report"**
  — "Realised gains" is a retired heading.
- **In practice:** you sold half a position; the report shows the exact realised
  P/L in the stock's own currency and a clearly-*indicative* base-currency
  companion figure, never conflating the two.
- `[ ] Approve  [ ] Challenge: ______`

## 2.4 Today's change, returns, and the risk metrics `[GLOSSARY]`

- **Today's change** — the day's change in value; the *only* term for this
  concept (retired: "Today" alone, "day change").
- **Total return** — cumulative % vs cost basis, since inception.
- **XIRR** — money-weighted return (IRR of dated cash flows); shows "Not
  applicable" on thin history rather than a misleading number.
- **TWR** — time-weighted return (external flows removed), for benchmark
  comparison.
- **Return / volatility** — 1Y return ÷ 1Y volatility, **explicitly not a
  Sharpe** (H1).
- **Return attribution** — per-holding contribution rolled up to class/sector,
  **with an explicit residual** so that *Σ contributions + residual = the
  headline return*, by construction (nothing silently doesn't add up).
- **Sharpe and Sortino are deliberately excluded** (they need a risk-free rate
  the product won't assume).
- **Short histories (D-086):** below a minimum-history threshold, only the
  **cumulative (non-annualized) return** is shown — no annualized/CAGR figure and
  no 1-year trailing return/volatility. **XIRR appears only from that threshold
  upward** (below it, "Not applicable"). This stops a two-week-old position from
  showing a wild annualized number.
- **In practice:** a position you opened three weeks ago shows its plain
  cumulative return, not a misleading "+380% annualized"; your attribution
  table's parts still sum exactly to the headline via the labelled "residual".
- **→ Resolved (D-086):** your challenge — no annualized figures on thin history
  — is now a calculation-honesty invariant. `[x] Approved`

## 2.5 Costs are shown as two blocks, never blended `[D-048, D-029]`

- **Recorded fees** — actual commissions + taxes from your ledger (a hard
  currency fact).
- **Ongoing cost (expense ratio)** — a *forward estimate* = expense ratio ×
  current value.

These are **never combined into one number**; they sit as two blocks on a card
that may be titled "Costs".
- **In practice:** ₹12,400 of recorded brokerage this year and a *separate*
  estimated ₹31,000/yr of fund expense ratios — you never see them fused into one
  misleading "total cost".
- `[ ] Approve  [ ] Challenge: ______`

## 2.6 Income and yield `[GLOSSARY]`

- **Income** = dividends + interest recorded in the ledger, base currency at
  today's FX.
- **Income yield** = recorded income ÷ current gross assets (trailing,
  backward-looking).
- **In practice:** ₹1.8L of dividends+interest over the trailing window against
  ₹3.2cr gross assets reads as a ~0.56% trailing income yield — clearly labelled
  backward-looking, not a forecast.
- `[ ] Approve  [ ] Challenge: ______`

## 2.7 Liquidity ladder and cash runway `[D-036, D-054]`

- **Liquidity ladder** — holdings grouped by time-to-cash: **Immediate / Short /
  Locked / Illiquid**.
- **Liquid** = Immediate + Short rungs.
- **Cash runway** = liquid assets ÷ recurring net burn (expenses − income). Its
  status can be *no data / positive / finite*.
- Contributions don't reduce it (H4); one-off obligations are excluded from the
  burn (H5).
- **In practice:** ₹48L liquid ÷ ₹4L/month recurring net burn = a **12-month
  runway**; a one-off ₹5L outflow next month doesn't shorten that headline.
- `[ ] Approve  [ ] Challenge: ______`

## 2.8 FX honesty `[D-020, D-074, D-076]`

- **Trade-date FX** is captured live **only when the trade date is today**; a
  backdated trade honestly has none (see A6).
- **Reference FX (ECB)** — EUR-based reference rates are used **only** as a
  translation fallback, **never as a trading quote**.
- The current-FX realised total and the trade-date-FX total are kept **separate**
  and never mixed; a leg with no valid same-currency trade-date rate is
  **excluded, not silently converted** at today's rate.
- **In practice:** the appliance never dresses up an ECB reference rate as a
  live market quote, and never blends "today's FX" and "trade-date FX" into one
  total.
- `[ ] Approve  [ ] Challenge: ______`

## 2.9 The Review thresholds — every value, with its reason `[D-059]`

The Review page turns your data into a "what needs a look" feed. Each trigger is
a **named constant with a one-line rationale**, and the values were reconciled
against the existing code (`app/services/review.py:25-30`); all matched. (This is
A5, in full.)

| Constant | Value | Fires when | Why this number |
|---|---|---|---|
| `_LIQUID_THIN_PCT` | 15% | liquid share of gross assets below 15% | below ~1/7 is too thin a cushion |
| `_RUNWAY_LOW_MONTHS` | **3** ✎ | runway below 3 months | owner-set floor (D-084; was 6) |
| `_GOAL_SOON_DAYS` | **180** ✎ | goal target date within 180 days | owner-set half-year notice (D-084; was 90) |
| `_OBLIGATION_SOON_DAYS` | 30 | an obligation due within 30 days | one month's notice |
| `_INSURANCE_SOON_DAYS` | 30 | insurance renewal within 30 days (or overdue) | one month to renew before lapse |
| `_CORP_ACTION_RECENT_DAYS` | 45 | split/bonus within 45 days → "verify" | recent corporate action warrants a check |
| `_OTHER_CLASS_OVERUSE_PCT` | **10%** ✎ | `other`-classed holdings exceed ~10% of gross assets | over-use of the escape valve → reclassify (D-087, new) |
| low-confidence band | < 50 | a holding's confidence score under 50/100 | poorly-sourced value deserves attention |
| `LEDGERFRAME_STALE_AFTER_SECONDS` | 900 (15 min) | a market quote older than 15 min | flagged stale (NAV/EOD use a 30-hour threshold) |
| policy band / concentration | per-policy | out-of-band buckets; positions over your `max_position_pct` | uses *your own* bands — no fixed number |

Each signal is wrapped so that one failing check never breaks the whole feed.
- **In practice:** these lines are the entire "nagging" logic.
- **→ Resolved (D-084 / D-087):** you set **runway = 3 months** and **goal = 180
  days** (marked ✎), keeping the rest as audited, and added the **`other`
  over-use (10%)** signal. The two changed defaults deliberately diverge from the
  legacy code — see the note in Spot-check 1. User-editable thresholds are parked
  as **R-15**. `[x] Approved with changes`

## 2.10 "None, not fabricated" and "never overwrite NAV" `[calc honesty]`

- **None, not fabricated.** Where inputs are insufficient (XIRR, TWR,
  attribution, FX, a % change when the prior value is zero), the answer is
  `None` / "—" **with a reason** — never a made-up number.
- **Never overwrite an official value.** A manually-entered value, an official
  NAV, or a statement valuation is **never** overridden by staleness logic; only
  live market *quotes* degrade to a "Stale cached value" label.
- **Data confidence** is a 0–100 score: a base score by valuation method, minus
  itemised penalties (stale −20, needs-mapping −15, unavailable −15),
  value-weighted at the portfolio level.
- **In practice:** you hand-key a flat's value at ₹1.4cr; no staleness rule will
  ever quietly replace or "expire" that figure, and its confidence score shows
  *why* it's rated as it is.
- `[ ] Approve  [ ] Challenge: ______`

---

# 3. What users see, and where

**The governing rule (P-1):** every piece of information has **ONE canonical
page** where it is authoritative and fully explained. Other pages may show a
*summary* — produced by the *same* backend calculation, linked back — but may
**never** recompute it or add a figure the canonical page doesn't show. Home
owns nothing; it is entirely summaries. `[P-1, D-031]`

## 3.1 The pages and their groups `[D-043]`

The sidebar has six fixed groups (not reorderable). Each page below has its route
(web address) and its one-line job.

| Group | Page | Address | What it is |
|---|---|---|---|
| **Overview** | Home | `/` | Dashboard of linked summaries; owns nothing |
| **Wealth** | Net worth | `/net-worth` | *Canonical* for Net worth, gross/liabilities, trend, liquidity ladder, runway |
| | Portfolio | `/portfolio` | *Canonical* for investment analytics (P/L, allocation, performance, attribution) |
| | Holdings | `/holdings` | The management surface: add/edit holdings, transactions, imports |
| | Accounts | `/accounts` | Manage accounts + the Entity (ownership) list |
| **Markets** | Markets | `/markets` | *Canonical* for quotes, indices, gainers/losers, watchlists |
| | Heatmap | `/heatmap` | Treemap picture of your holdings |
| | News | `/news` | *Canonical* for the briefing + grouped headlines |
| **Planning** | Review | `/review` | *Canonical* for the "what needs a look" feed + mark-reviewed history |
| | Policy | `/policy` | *Canonical* for target allocation + drift (computed live) |
| | Cash flow | `/cash-flow` | Goals, Obligations, Contributions (renamed from "Planning") |
| | Scenarios | `/scenarios` | Deterministic what-if shocks — a scenario, never a forecast |
| | Insurance | `/insurance` | Protection register; cash value excluded from Net worth |
| | Estate | `/estate` | Will/executor, contacts, document readiness |
| **Reports** | Reports | `/reports` | Statements, Realised P/L report, tax lots; server-side exports |
| | Pricing Health | `/pricing-health` | *Canonical* for where each price came from + confidence |
| **System** | Settings | `/settings` | Configuration (4 tabs incl. Privacy + API tokens) |
| | Help | `/help` | Searchable knowledge base |
| | Legal | `/legal` | License, disclaimers, the Product Guarantees |

Two surfaces are reachable by link only, not in the sidebar: the **Reports Pack**
(`/reports/pack`, a print/export artifact) and **Instrument Detail**
(`/instrument/:symbol`, a filtered view of a single holding). `[D-038, D-041, P-3]`
- **In practice:** if you want to know "where did this price come from and how
  confident is it?", there is exactly one place — Pricing Health — and every
  other page links to it rather than answering differently.
- `[ ] Approve  [ ] Challenge: ______`

## 3.2 A few canonical-home calls worth noting `[D-032..D-039, D-054]`

- **Net worth page owns** the composition-by-class table (an itemised statement
  including liabilities). This is deliberately **not** the same as Portfolio's
  allocation-weight (which excludes liabilities and uses gross-asset
  denominators). Two different questions, two different homes. `[D-033]`
- **The Net worth composition *donut* was dropped**; that page now leads with a
  KPI strip (Net worth / Gross assets / Liabilities / Cash & deposits). `[D-054]`
- **Portfolio owns** the performance chart with benchmark picker — it lives
  *only* there, not duplicated onto Net worth or Home. `[D-035]`
- **In practice:** you won't find two subtly-different "allocation" numbers on
  two pages; the composition statement (with the mortgage) is on Net worth, the
  weight analysis (without it) is on Portfolio.
- `[ ] Approve  [ ] Challenge: ______`

## 3.3 What was deliberately removed from v1, and why `[IA Appendix B]`

| Removed / changed | Why | Decision |
|---|---|---|
| **Persona onboarding** ("what kind of investor are you?") | The product does not profile its user; replaced by a plain first-run checklist | D-045 |
| **Home top-holdings widget + 3 separate market rows** | Replaced by one compact quote-card row; less clutter | D-046 |
| **Net worth composition donut** | Redundant with the KPI strip + composition table | D-054 |
| **Markets region-news blocks** | Removed; Markets links to the News page's region groups instead | D-051 |
| **App-wide "Simple/Expert" toggle** | Kept, but scoped to Home only — it was confusing as a global switch | D-040 |
| **Nav-customization control** | Removed; the sidebar order is now fixed and guessable | D-043 |
| **The `/global` page** | Removed with no redirect (its content moved) | D-042 |
| **Stored AI chat, dashboard-config tables, provider-config table** | Dropped; config lives in settings/`.env`, AI is ephemeral | D-014/16/17 |
| **Frontend copies of dropdown lists** | Retired; the frontend now gets every list from one backend source | D-005/D-049 |

- **In practice:** the app you get back is deliberately *quieter* than v1 — fewer
  widgets, no "tell us about yourself" step, one place for each fact.
- **→ Resolved: affirmed unchanged.** You reviewed the v1 removals and accepted
  them as written. `[x] Approved`

## 3.4 How you enter data — the input controls `[DESIGN-SYSTEM §5, §6]`

A hard rule: **every input on screen is a purpose-built control** — there are no
raw text boxes for money, dates, or categories. Money uses a currency-aware
**MoneyInput** (2 decimal places, right-aligned, never computes anything);
quantities, percentages, and dates each have their own control; instruments are
chosen with a typeahead **picker** (no more free-text symbols, no silent
auto-creation of instruments); and **every dropdown is driven by the master
lists in §4**, never an inline hand-typed list.
- **In practice:** you can't accidentally type "12,00,0" into a money box or
  invent a stray sector by typo — the controls constrain entry to valid, exact
  values.
- `[ ] Approve  [ ] Challenge: ______`

---

# 4. The dropdown lists (controlled vocabularies)

This is where wrong values become wrong choices your users are forced into, so
read the actual values. There are **two kinds**:

- a **fixed vocabulary** (dropdown whose options change only with a software
  release; served from one backend source, enforced in the database) — no admin
  screen; and
- a **user-extensible master** (dropdown you *can* add to via an admin screen).

## 4.1 Fixed vocabularies (users cannot add to these) `[MASTER-DATA §2]`

| List | Where used | Values |
|---|---|---|
| **Transaction type** | on every transaction | `buy, sell, dividend, interest, deposit, withdrawal, fee, split, bonus, merger, transfer` (11) |
| **Asset class** | instruments & holdings | `equity, etf, mutual_fund, bond, cash, fixed_deposit, commodity, crypto, property, private, retirement, liability, other` (13) |
| **Asset subclass** ★ | instruments (display) | `crypto, derivative, equity, etf, mutual_fund, reit` (6) — see A1; `etf`/`reit` are PROPOSED |
| **Liquidity profile** | instruments | `listed, redeemable, locked, illiquid, manual` (5) |
| **Entity kind** | ownership entities | `self, spouse, trust, company, other` (5) |
| **Goal basis** | goals | `net_worth, liquid, none` (3) |
| **Obligation recurrence** | obligations | `once, monthly, quarterly, annual` (4) |
| **Obligation kind** | obligations | `expense, income` (2) |
| **Contribution frequency** | contributions | `monthly, quarterly, annual, once` (4) |
| **Contribution kind** | contributions | `invest, withdraw, prepay` (3) |
| **Will status** | estate profile | `none, draft, executed, needs_update` (4) |
| **Estate-document status** | estate docs | `present, missing, outdated` (3) |
| **Valuation method** | provenance | `market_quote, official_nav, broker_quote, manual_valuation, statement_import, calculated_accrual, estimated_value, fx_reference, unavailable` (9) |
| **Entitlement status** | provenance | `real-time, delayed, end-of-day, cached, unavailable` (5) |
| **Policy target dimension** | policy | `asset_class, currency, region` (3) |
| **Identifier type** | instrument IDs | `isin, cusip, figi, sedol, amfi_code, kite_token, coingecko_id, provider_symbol` (8) |
| **Cost-basis method** | accounts | `fifo, average` (2) — see A9; `spec` is parked |
| **Account kind** | accounts | `brokerage, bank, retirement, wallet, property, manual, other` (7) |
| **Insurance policy type** | insurance | `term_life, whole_life, health, critical_illness, disability, personal_accident, property, motor, travel, other` (10) |
| **Insurance premium frequency** | insurance | `monthly, quarterly, annual, single` (4) — note `single`, **not** `once` |
| **Estate-document category** | estate docs | `will, insurance, property, loan, identity, bank, tax, medical, other` (9) |
| **Estate-contact roles** | estate contacts | `nominee, beneficiary, executor, emergency, guardian` (5) |

Points worth an accountant's eye:
- **Insurance premium frequency uses `single`** (a paid-once policy), which is
  *deliberately different* from Contribution frequency's `once`. Don't conflate
  them. `[DEF-4]`
- **Two valuation methods (`calculated_accrual`, `statement_import`) stay in the
  list but no v2 process produces them** — retained for data already tagged that
  way. `[D-073]`
- **The product never claims `real-time` for its own data** — that value exists
  only to record what a *source* claims. `[D-027]`
- **`other` is kept everywhere as the honest escape valve (D-087)** — a user is
  never forced into a wrong specific value; if none fits, `other` is legitimate.
- **In practice:** every value above is what a user will be forced to pick from.
- **→ Resolved (D-087):** `other` is retained across the fixed vocabularies, and
  a Review signal now flags when `other`-classed holdings exceed **10%** of gross
  assets — the escape valve stays, with a gentle nudge to reclassify if
  over-used. `[x] Approved with addition`

## 4.2 User-extensible masters (users *can* add to these) `[MASTER-DATA §6]`

| Master | Used for | Starting values | Rules |
|---|---|---|---|
| **Institution** | brokers/banks/insurers | *empty* (you populate it) | merge dedupes variants ("DBS" vs "DBS Bank"); can't delete while referenced |
| **Sector** ★ | instrument sector | the **11 GICS sectors** (PROPOSED — see A2) | can add more; can't delete while referenced |
| **Tag** | labels on holdings | *empty* | case-insensitive-unique; **max 16 tags per holding**; rename cascades |
| **Currency** | trade/base currency | the **22-code seed** (see A8) | seed-managed under the FX-translatability rule; user-additions parked (R-2) |

- **In practice:** Institution and Tag start empty and grow as you use the app;
  Sector arrives pre-filled with the 11 GICS sectors you can extend; Currency is
  managed (not freely added to) in v2.
- `[ ] Approve  [ ] Challenge: ______`

## 4.3 The country/region model and timezone `[D-007, D-013]`

- **Country** — the single authoritative field is `listing_country`, an ISO-3166
  two-letter code, seeded from the published ISO standard (a standard, not an
  authored list). The old free-text `country` and `domicile_country` fields are
  **dropped**; legacy values are mapped to ISO codes with a **manual review list
  for anything that can't be mapped — no silent best-guess**.
- **Region** — *derived* into **six** buckets (India / Singapore / US / Europe /
  APAC / Other), with a full country→region mapping table; see A10. `[D-083]`
- **Timezone** — a proper IANA timezone dropdown (seeded from the maintained `tz`
  database standard), replacing free-text entry.
- **In practice:** you'll pick "IN" from a standard country list, and the app
  derives "India"; a London listing derives "Europe", a Tokyo listing "APAC"; any
  old free-text country it can't confidently map is put on a review list rather
  than guessed.
- **→ Resolved (D-083):** region expanded from four buckets to six.
  `[x] Approved with change`

---

# 5. Privacy & security, in plain terms

## 5.1 What the appliance does and doesn't send over the internet `[D-004, §7]`

Normally the appliance reaches out only for the things it needs: market quotes,
FX reference rates, news feeds, and an occasional version check. **The no-egress
switch turns all of that off** — with it on, the device makes **zero** outbound
calls (quotes, FX, feeds, version check, and update banner all suppressed), and
cached data is shown **honestly marked as stale**, never faked. The Settings →
Privacy section shows the current state as a plain sentence, e.g. *"This device
makes no network calls."*
- **In practice:** going on a privacy-sensitive footing is one switch; you keep
  seeing your last-known numbers, clearly labelled as of when they were fetched.
- `[ ] Approve  [ ] Challenge: ______`

## 5.2 What the PIN really protects `[D-002, D-003]`

- The PIN is **numeric, minimum 6 digits**, hashed with Argon2, with escalating
  lockout after repeated failures (backoff after 5, a hard 15-minute lockout
  after 10).
- **The PIN is an access lock, not encryption.** It gates access to a *running*
  app; it does **not** encrypt the database file. Someone who steals the database
  file off disk can attempt an offline brute-force (Argon2 slows this, doesn't
  stop it).
- **Therefore, confidentiality of the stored ledger relies on OS disk
  encryption** (FileVault / LUKS / BitLocker) — this is stated plainly in the app
  and first-run guidance.
- **In practice:** the PIN stops someone walking up to your running kiosk; it is
  **not** what protects the file if the laptop is stolen — full-disk encryption
  is. Both are needed, and the app says so.
- `[ ] Approve  [ ] Challenge: ______`

## 5.3 What the AI is allowed to say `[D-070, D-071 — the validation contract]`

Every AI answer (chat, briefing, instrument explainers) passes through **one**
pipeline with these non-negotiable checks. The AI **never computes money and
never calls a data provider** — the deterministic engine is the only source of
numbers, and the facts (with source · timestamp · staleness) are shown **before**
the answer.

1. Output is **buffered and validated before any of it is shown** (never streamed
   raw); internal "reasoning" is stripped.
2. **Every significant money/% number must trace to a supplied fact** (years
   1900–2100 exempted). Ungrounded numbers fail.
3. **Unknown tickers are rejected** — a ticker must appear in the facts or your
   question.
4. **Advice, "real-time/live" claims, and secret-like strings are hard-rejected.**
5. **Any quoted 25+ character string (a headline) must appear verbatim** in the
   facts.
6. **On any failure the AI's text is discarded** and a deterministic, fact-only
   answer is shown, ending with *"Information only, not financial advice."*

False rejections are the **accepted cost** — the fallback is a correct
fact-based answer, and you always see the visible signal (H8) when it happens.
This contract **may be strengthened but never weakened** (G7).
- **In practice:** the assistant physically cannot slip in a number that isn't
  in your data, quote a headline that wasn't published, or tell you to sell — if
  it tries, you get the facts instead, flagged.
- `[ ] Approve  [ ] Challenge: ______`

## 5.4 Other privacy/security posture worth noting `[§8–§11]`

- **No telemetry or analytics** of any kind. `[§8]`
- **AI conversations are never stored** (G6); off-device AI (if you configure a
  remote model) is always surfaced with an always-visible privacy-mode label.
- **The audit log is tamper-evident** (hash-chained) and **never contains
  secrets**. `[D-004 #11]`
- **API keys are write-only** — once entered they can't be read back out (only a
  "key is set" yes/no); secrets live in a locked-down `.env` file (permissions
  0600), never in the database. `[D-003]`
- **All exports are generated on the server**, and every exported cell is
  sanitised so a crafted value can't become a live spreadsheet formula. `[D-050,
  P-5]`
- **The privileged "System" controls degrade gracefully** — if the optional
  admin helper isn't installed, those controls are simply hidden with an
  explanation, never half-working. `[D-003]`
- **In practice:** you can hand this appliance to a family member without
  worrying it phones home, keeps chat logs, or leaks an API key back onto the
  screen.
- `[ ] Approve  [ ] Challenge: ______`

---

# 6. Parked for later — the ROADMAP on one page

**The rule: nothing on this list is built without a written plan file first.**
These are deliberate deferrals, not to-dos for v2. `[ROADMAP.md]`

| # | Parked item | Condition / gate | From |
|---|---|---|---|
| R-1 | Optional passphrase mode (8–64 chars) | PIN stays an access lock, not encryption | D-002 |
| R-2 | User-requestable transaction currencies | must be FX-validated (translatable or not admitted) | D-006 |
| R-3 | Domicile field for fund-tax display | reintroduces a field beyond `listing_country` | D-007 |
| R-4 | Instrument notes | after the general Note table was dropped | D-015 |
| R-5 | Opt-in AI chat history | opt-in only; default stays ephemeral (G6) | D-016 |
| R-6 | `spec` (specific-lot) cost-basis method | extends the fifo/average selector (see A9) | D-018 |
| R-7 | Corporate-actions audit (spin-offs, symbol changes) | splits/bonuses already covered | D-019 |
| R-8 | Historical FX series (enables trade-date backfill + per-date realised) | native currency stays filing-grade; base stays indicative | D-020, D-076 |
| R-9 | Insurance cash value: opt-in inclusion in Net worth | opt-in only; default stays excluded (see A7) | D-039 |
| R-10 | App-wide Detail level | gated on per-page specs (v2 scopes it to Home) | D-040 |
| R-11 | User-defined scenario shocks | gated on a plan file; "scenario, never a forecast" preserved | D-058 |
| R-12 | Revisit AI validator strictness | only if false-rejections prove frequent; contract may not weaken (G7) | D-070 |
| R-13 | Per-lane provider priority editing | only on demonstrated need; no user-editable priority in v2 | D-072 |
| R-14 | **FD accrued-interest valuation** (first post-v2 feature) | plan file **must** cover day-count conventions, compounding, maturity, and provenance labelling | D-073 |
| R-15 | **User-configurable review thresholds** ✎ | the v2 defaults (§2.9) become user-editable; each still a named constant with a rationale | D-084 |

**The v2.1 "accounting precision" theme (D-088).** Three of the parked items —
**R-6 (specific-lot cost basis)**, **R-8 (historical FX series)**, and **R-14 (FD
accrued-interest valuation)** — are now bundled as the first coherent post-v2
milestone, "accounting precision". They are grouped for sequencing only; each
still needs its own plan file before it is built.

**Recorded but not on the ROADMAP:** a future **SaaS/PaaS** (multi-user, hosted)
layer is noted as a design constraint — v2 must not preclude it — but is a
separate proprietary layer, not a parked v2 item. `[D-001]`
- **In practice:** the v2.1 theme gives the FD-accrual, historical-FX, and
  specific-lot items you cared about a clear home and running order — the first
  thing built after v2 ships.
- **→ Resolved (D-088):** ROADMAP restructured into the v2.1 theme; R-15 added
  for user-configurable thresholds. `[x] Approved with change`

---

# 7. How the numbers can be trusted (the audit trail)

Think of the specifications as a set of **working papers**. The discipline used
throughout is exactly the one you'd expect of a working paper: **every value that
came from the existing system cites the precise source file and line it was
copied from**, so any figure can be traced back to its origin and re-verified.
Three tiers of trust are used, and each value is tagged:

- **Extracted (verbatim).** Copied directly from the existing code, with a
  `file:line` citation. Example: the currency list, the account kinds, the sudo
  action list, the Review thresholds. These are as trustworthy as the source
  code — and the citation lets you check.
- **Standard.** The value *is* a published external standard, not an opinion:
  ISO-3166 country codes, IANA timezones, the 11 GICS sectors' names.
- **Authored (PROPOSED).** No prior source existed, so a value was *proposed* and
  is marked **PROPOSED**, to be ratified at review. Only two things are in this
  tier: the `etf`/`reit` subclass values (A1) and the sector seed + migration
  (A2/A3). These are exactly the items on the ATTENTION list, so nothing invented
  escapes your eye.

**The chain, end to end:** a decision in `docs/audit/DECISIONS.md` → a spec that
implements it and cites either that decision ID or a `file:line` source →
(for extracted values) the legacy code line itself. You can walk any figure back
along that chain.

## Three spot-checks you can do yourself

Each takes about two minutes and needs nothing but a text viewer.

**Spot-check 1 — the Review thresholds trace honestly, including your two
overrides.**
1. Open `docs/specs/PRODUCT-SPEC.md` and scroll to **§5 "Review signal
   thresholds"**.
2. Read the paragraph headed **"Value provenance (honest audit trail)"** just
   under the table. It lists the legacy code values (`_RUNWAY_LOW_MONTHS = 6`,
   `_GOAL_SOON_DAYS = 90`, etc.) and then states that **D-084 deliberately set two
   of them away from the code**: runway to **3** and goal to **180**.
3. **What you should see:** in the table above, `_RUNWAY_LOW_MONTHS = 3` and
   `_GOAL_SOON_DAYS = 180` (each tagged `(D-084)`), while every *other* value
   still matches the legacy code, and `_OTHER_CLASS_OVERUSE_PCT = 10` is tagged
   `(D-087)`. This is the model working as intended: the two owner-set values
   *should* differ from the code, and the spec says so out loud. A disagreement
   that is **not** explained by a D-084/D-087 tag would be the finding.

**Spot-check 2 — the currency list is a real union of three legacy lists.**
1. Open `docs/specs/MASTER-DATA.md` and scroll to **§3 "Currency master"**
   (around lines 145–165).
2. Read the seed table: **9** base-eligible codes from `config.py:18`, **+5** from
   `refdata.ts:8`, **+8** from `PortfolioEditor.tsx:22`.
3. **What you should see:** 9 + 5 + 8 = **22 unique codes**, with exactly the 9
   `SUPPORTED_CURRENCIES` marked base-eligible and the other 13 not — matching A8
   above. The text should also say FX-translatability is checked *live*, not from
   a frozen list.

**Spot-check 3 — the privileged action list is copied verbatim, not invented.**
1. Open `docs/specs/SECURITY-BASELINE.md` and scroll to **§4** (around lines
   93–114).
2. Read the "Action allow-list (exact, extracted)" table; it cites
   `app/api/v1/routes/system.py:24-36`.
3. **What you should see:** exactly **10 actions** (`status, restart,
   restart-worker, doctor, backup, update, lan, voice, ai, kiosk`), with only
   `lan/voice/ai/kiosk` taking an `on`/`off` argument and the rest taking none —
   and the statement that **no free-form input ever reaches the shell**. This is
   the security surface; it should read as a short, fixed, closed list.

---

# 8. Sign-off summary (one page)

**What approving this guide means.** You are approving the *specifications* it
summarises — the product's promises, how every visible number is counted, the
page structure, the dropdown values, and the privacy/security posture — as the
basis for building v2. The specifications remain the authoritative text; this
guide is only your reading lens.

**What is settled by your approval:**
- The seven Product Guarantees and the protected honesty features (§1).
- Every money-counting rule, including Net worth composition, the two P/L
  figures, FX honesty, the cost split, and the Review thresholds (§2).
- The page map, canonical homes, and the v1 removals (§3).
- Every dropdown list and its values (§4).
- The privacy posture, PIN semantics, and the AI validation contract (§5).
- The parked-items list (§6).

**What remains open (deliberately):**
1. **Design-token ratification** — the exact palette, fonts, spacing, and density
   metrics in DESIGN-SYSTEM §2 are marked *PROPOSED* and get ratified at the
   **kitchen-sink review** (when the component library is built and can be seen).
   These are look-and-feel working values, not numbers you'd audit.
2. **The two authored vocabularies** — the `etf`/`reit` subclass values (A1) and
   the 11-sector seed + migration (A2/A3) — are *PROPOSED* and ratified at that
   same review. Your ATTENTION-section decisions feed directly into it.
3. **The UI/serif font choice** — if self-hosting a font adds a software
   dependency, it needs a short architecture note (ADR) first; the fallback
   fonts keep everything shippable meanwhile.

**What happens next:**
1. **Round 1 is complete.** Your challenges from the first read are resolved as
   **Batch 12 (D-081–D-088)** in `docs/audit/DECISIONS.md` and folded into the
   specs; each affected item above carries a **→ Resolved** line. Any further
   challenge you mark starts a round 2, folded back the same way.
2. The **kitchen-sink review** ratifies the still-PROPOSED design tokens and the
   authored vocabularies (the `etf`/`reit` values now carry D-085 classification
   guidance; the sector seed was affirmed).
3. **Backend copy-in** — the existing v1 code enters this repository as its own
   milestone, and every *extracted* value here is re-verified against it (the
   `file:line` citations already point at the exact lines to check). Note the two
   D-084 review defaults are owner-set and *expected* to differ from the code.

**Overall sign-off:**

`[ ] I approve the specifications as summarised, subject to my per-item notes above.`

`[ ] I approve with the challenges noted; please revise and re-circulate.`

`[ ] I do not approve; see notes.`

Signed: ________________________   Date: ____________

---

*This guide summarises `docs/specs/{PRODUCT-SPEC, GLOSSARY, MASTER-DATA,
INFORMATION-ARCHITECTURE, DESIGN-SYSTEM, SECURITY-BASELINE, DESIGN-BRIEF}.md` and
`ROADMAP.md`. Where it summarises, those documents are authoritative. It changes
no specification.*
