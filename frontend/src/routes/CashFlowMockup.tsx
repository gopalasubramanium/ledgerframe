// SPDX-License-Identifier: AGPL-3.0-or-later
import { Plus } from "../icons";
import { Button, DataTable, PageHeader, StatusChip, SummaryHead } from "../components/ui";
import type { Column } from "../components/ui";
import "./CashFlow.css";

// STATIC LAYOUT SPECIMEN — page-cash-flow §9-10 (the GEOMETRY GATE).
//
// Nothing here is wired: it exists so the owner can RATIFY THE GEOMETRY BY LOOKING AT IT, before a
// line of the real page is assembled. The ruling: THREE STACKED SECTIONS (Obligations ·
// Contributions · Goals) + the runway summary card, each table internally capped and scrolled, ONE
// page scroll region.
//
// The data is REAL-SHAPED ON PURPOSE — long lists, long names, multi-currency, a `once` row with no
// monthly rate, a goal with no progress. page-home's lesson: a specimen fed a toy dataset flatters
// the design and the gate lies. Every money figure below is written as the BACKEND WOULD SERVE IT
// (a display string), because that is what the page will render (D-105).

interface ObRow {
  id: number; name: string; kind: string; recurrence: string;
  monthly: string | null; amount: string; next_due: string;
}
interface ConRow {
  id: number; name: string; kind: string; frequency: string;
  monthly: string | null; amount: string; goal: string;
}
interface GoalRow {
  id: number; name: string; target: string; progress: string; remaining: string; when: string;
}

const OBLIGATIONS: ObRow[] = [
  { id: 1, name: "Rent — Tanjong Pagar apartment", kind: "Expense", recurrence: "Monthly", monthly: "4,200.00", amount: "4,200.00", next_due: "1 Aug 2026" },
  { id: 2, name: "Salary", kind: "Income", recurrence: "Monthly", monthly: "12,500.00", amount: "12,500.00", next_due: "25 Jul 2026" },
  { id: 3, name: "Mortgage — Pune flat", kind: "Expense", recurrence: "Monthly", monthly: "1,980.00", amount: "1,980.00", next_due: "5 Aug 2026" },
  { id: 4, name: "Helper salary", kind: "Expense", recurrence: "Monthly", monthly: "780.00", amount: "780.00", next_due: "1 Aug 2026" },
  { id: 5, name: "Utilities", kind: "Expense", recurrence: "Monthly", monthly: "260.00", amount: "260.00", next_due: "12 Aug 2026" },
  { id: 6, name: "Car insurance", kind: "Expense", recurrence: "Annual", monthly: "150.00", amount: "1,800.00", next_due: "3 Mar 2027" },
  { id: 7, name: "Property tax", kind: "Expense", recurrence: "Annual", monthly: "108.33", amount: "1,300.00", next_due: "31 Jan 2027" },
  { id: 8, name: "School fees", kind: "Expense", recurrence: "Quarterly", monthly: "1,166.67", amount: "3,500.00", next_due: "1 Sep 2026" },
  { id: 9, name: "Rental income — Pune flat", kind: "Income", recurrence: "Monthly", monthly: "640.00", amount: "640.00", next_due: "7 Aug 2026" },
  // The `once` row: a REAL future outflow with NO monthly rate. It must read as "—", never "0.00"
  // (D-057 — excluded from the burn is not the same as free).
  { id: 10, name: "Income tax — YA2026 final assessment", kind: "Expense", recurrence: "Once", monthly: null, amount: "18,400.00", next_due: "30 Sep 2026" },
  { id: 11, name: "Annual travel insurance", kind: "Expense", recurrence: "Annual", monthly: "37.50", amount: "450.00", next_due: "14 Jun 2027" },
  { id: 12, name: "Gym membership", kind: "Expense", recurrence: "Monthly", monthly: "95.00", amount: "95.00", next_due: "1 Aug 2026" },
];

const CONTRIBUTIONS: ConRow[] = [
  { id: 1, name: "VWRA — monthly SIP", kind: "Invest", frequency: "Monthly", monthly: "2,000.00", amount: "2,000.00", goal: "Retire by 55" },
  { id: 2, name: "Nifty index SIP (INR)", kind: "Invest", frequency: "Monthly", monthly: "540.00", amount: "35,000.00", goal: "—" },
  { id: 3, name: "CPF top-up", kind: "Invest", frequency: "Annual", monthly: "666.67", amount: "8,000.00", goal: "Retire by 55" },
  { id: 4, name: "Mortgage prepayment", kind: "Prepay", frequency: "Quarterly", monthly: "1,000.00", amount: "3,000.00", goal: "—" },
  { id: 5, name: "Emergency fund top-up", kind: "Invest", frequency: "Monthly", monthly: "500.00", amount: "500.00", goal: "Emergency fund" },
  { id: 6, name: "Year-end bonus lump sum", kind: "Invest", frequency: "Once", monthly: null, amount: "20,000.00", goal: "House deposit" },
  { id: 7, name: "Drawdown for school fees", kind: "Withdraw", frequency: "Quarterly", monthly: "1,166.67", amount: "3,500.00", goal: "—" },
];

const GOALS: GoalRow[] = [
  { id: 1, name: "House deposit", target: "250,000.00", progress: "62.4%", remaining: "94,000.00", when: "in 540 days" },
  { id: 2, name: "Emergency fund — 6 months", target: "45,000.00", progress: "88.1%", remaining: "5,355.00", when: "in 120 days" },
  { id: 3, name: "Retire by 55", target: "2,400,000.00", progress: "31.7%", remaining: "1,639,200.00", when: "in 4,380 days" },
  // A goal with basis "none": NO automatic progress. It must read "—", never "0%" (Guarantee 3 —
  // a goal without a basis is not a goal at zero).
  { id: 4, name: "Sabbatical fund", target: "60,000.00", progress: "—", remaining: "—", when: "—" },
  { id: 5, name: "Kids' university", target: "300,000.00", progress: "12.0%", remaining: "264,000.00", when: "in 3,650 days" },
];

const OB_COLS: Column<ObRow>[] = [
  { key: "name", label: "Name", sortable: true, truncate: true },
  { key: "kind", label: "Kind", sortable: true, render: (r) => <StatusChip label={r.kind} tone="neutral" /> },
  { key: "recurrence", label: "Recurrence", sortable: true },
  { key: "amount", label: "Amount", align: "right", sortable: true },
  { key: "monthly", label: "Monthly equivalent", align: "right", sortable: true, render: (r) => r.monthly ?? "—" },
  { key: "next_due", label: "Next due", align: "right", sortable: true },
];

const CON_COLS: Column<ConRow>[] = [
  { key: "name", label: "Contribution", sortable: true, truncate: true },
  { key: "kind", label: "Kind", sortable: true, render: (r) => <StatusChip label={r.kind} tone="neutral" /> },
  { key: "frequency", label: "Frequency", sortable: true },
  { key: "amount", label: "Amount", align: "right", sortable: true },
  { key: "monthly", label: "Monthly equivalent", align: "right", sortable: true, render: (r) => r.monthly ?? "—" },
  { key: "goal", label: "Towards", sortable: true },
];

const GOAL_COLS: Column<GoalRow>[] = [
  { key: "name", label: "Goal", sortable: true, truncate: true },
  { key: "target", label: "Target", align: "right", sortable: true },
  { key: "progress", label: "Progress", align: "right", sortable: true },
  { key: "remaining", label: "Remaining", align: "right", sortable: true },
  { key: "when", label: "Target date", align: "right", sortable: true },
];

export function CashFlowMockup() {
  return (
    <div className="lf-page cf">
      <PageHeader
        title="Cash flow"
        subtitle="What you owe, what you're putting away, and what you're aiming at. Reporting only — not advice."
      />

      {/* The RUNWAY SUMMARY (§9-3) — Net worth's figures, from Net worth's reader, with the
          canonical-home link in the card header (D-100). Never re-derived here. */}
      <section className="lf-card cf__runway">
        {/* ⚠ The RATIFIED SummaryHead — NOT a hand-rolled ↗. My first pass hand-rolled the anchor with
            `.lf-summarylink` (which is `position: absolute`) inside an unpositioned header, and the
            glyph ESCAPED ITS CARD — the exact defect that killed the first Home build (§12ho1-4).
            The tile-integrity guard caught it. "There are no page-local variants" is the rule, and
            this is why. */}
        <SummaryHead title="Cash runway" to="/net-worth" destination="Net worth" whole />
        <div className="lf-card__body cf__runwaybody">
          <div className="cf__figure">
            <span className="cf__figlabel">Runway</span>
            <span className="cf__figvalue">14.2 months</span>
            <StatusChip label="Finite" tone="attention" />
          </div>
          <div className="cf__figure">
            <span className="cf__figlabel">Net monthly burn</span>
            <span className="cf__figvalue">3,470.00</span>
          </div>
          <div className="cf__figure">
            <span className="cf__figlabel">Monthly expenses</span>
            <span className="cf__figvalue">8,777.50</span>
          </div>
          <div className="cf__figure">
            <span className="cf__figlabel">Monthly income</span>
            <span className="cf__figvalue">13,140.00</span>
          </div>
          <p className="lf-card__footnote">
            Liquid assets ÷ your recorded recurring net burn, at today's FX. Contributions do not
            reduce it.
          </p>
        </div>
      </section>

      {/* THREE STACKED SECTIONS (§9-10). Each table is internally capped + scrolled, so the PAGE
          keeps ONE scroll region no matter how long any one list grows. */}
      <section className="lf-card cf__section">
        <header className="cf__head">
          <h2 className="lf-card__title">Income &amp; expenses</h2>
          <span className="cf__total">Next 12 months · 74,285.00</span>
          <Button icon={Plus} variant="primary">Add income or expense</Button>
        </header>
        <div className="lf-card__body">
          <DataTable<ObRow> caption="Income and expenses" columns={OB_COLS} rows={OBLIGATIONS} />
        </div>
      </section>

      <section className="lf-card cf__section">
        <header className="cf__head">
          <h2 className="lf-card__title">Contributions</h2>
          <span className="cf__total">Planned investing · 5,873.34 / month</span>
          <Button icon={Plus} variant="primary">Add contribution</Button>
        </header>
        <div className="lf-card__body">
          <DataTable<ConRow> caption="Contributions" columns={CON_COLS} rows={CONTRIBUTIONS} />
        </div>
      </section>

      <section className="lf-card cf__section">
        <header className="cf__head">
          <h2 className="lf-card__title">Goals</h2>
          <Button icon={Plus} variant="primary">Add goal</Button>
        </header>
        <div className="lf-card__body">
          <DataTable<GoalRow> caption="Goals" columns={GOAL_COLS} rows={GOALS} />
        </div>
      </section>
    </div>
  );
}
