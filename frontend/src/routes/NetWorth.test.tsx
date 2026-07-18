import { afterEach, expect, test, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../theme/ThemeProvider";
import { DisplayProvider } from "../theme/DisplayProvider";
import { RefdataProvider } from "../refdata/RefdataProvider";

// Populated defaults; individual tests override a reader with mockResolvedValueOnce.
vi.mock("../api/portfolio", () => ({
  getPortfolioSummary: vi.fn(async () => ({
    ok: true,
    data: {
      base_currency: "SGD", total_value: 819848.4, gross_assets: 1239848.4, liabilities: -420000,
      cash_and_deposits: 25000, cost_basis: 711738.95, unrealised_pl: 108109.45, day_change: 296.84,
      total_return_pct: 15.19, has_stale: true, stale_count: 11,
      allocation_by_class: {}, allocation_by_currency: {}, allocation_by_sector: {},
      top_gainers: [], top_losers: [],
    },
  })),
  getPerformance: vi.fn(async () => ({
    ok: true,
    data: {
      base_currency: "SGD", benchmark_symbol: "SPY",
      series: [{ ts: "2025-01-01", value: 100 }, { ts: "2025-06-01", value: 110 }],
      benchmark: [], stats: null,
    },
  })),
  getPortfolioStats: vi.fn(async () => ({
    ok: true,
    data: { base_currency: "SGD", metrics: [
      { label: "Time-weighted return (TWR)", value: 8.4, kind: "pct", term_id: "term-xirr-twr" },
    ] },
  })),
}));

vi.mock("../api/net-worth", () => ({
  getNetWorthHistory: vi.fn(async () => ({
    ok: true,
    data: { history: [
      { ts: "2025-01-01T00:00:00Z", assets: 1000000, liabilities: 400000, net_worth: 600000, currency: "SGD" },
      { ts: "2025-06-01T00:00:00Z", assets: 1239848, liabilities: 420000, net_worth: 819848, currency: "SGD" },
    ] },
  })),
  getNetWorthStatement: vi.fn(async () => ({
    ok: true,
    data: {
      base_currency: "SGD",
      rows: [
        { asset_class: "property", value: 980000 },
        { asset_class: "equity", value: 234848.4 },
        { asset_class: "cash", value: 25000 },
        { asset_class: "liability", value: -420000 },
      ],
      gross_assets: 1239848.4, liabilities: -420000, net_worth: 819848.4,
    },
  })),
  getLiquidity: vi.fn(async () => ({
    ok: true,
    data: {
      base_currency: "SGD", gross_assets: 1239848.4,
      rungs: [
        { key: "immediate", label: "Immediate (cash & listed)", value: 259848, pct: 21, cumulative_pct: 21 },
        { key: "illiquid", label: "Illiquid (property & private)", value: 980000, pct: 79, cumulative_pct: 100 },
      ],
      liquid_pct: 21, liabilities: -420000, disclaimer: "Indicative liquidity by asset type.",
    },
  })),
  getRunway: vi.fn(async () => ({
    ok: true,
    data: {
      base_currency: "SGD", liquid: 259848, monthly_expense: 3000, monthly_income: 600,
      net_monthly_burn: 2400, runway_months: 8.5, runway_date: "2027-03-01",
      status: "finite", note: "At your recorded recurring net burn, your liquid assets would last this long.",
      disclaimer: "Indicative — liquid assets ÷ your recorded recurring net burn.",
    },
  })),
  getInsurance: vi.fn(async () => ({ ok: true, data: { base_currency: "SGD", count: 0, total_cash_value: 0, total_cash_value_display: "0.00" } })),
  // §12 step 7: coverage preflight — default all-covered so it stays hidden for the other tests.
  getCoverage: vi.fn(async () => ({
    ok: true,
    data: { base_currency: "SGD", instruments: [], total: 2, covered_count: 2, all_covered: true,
      coverage_label: "History is complete for every holding." },
  })),
  getReview: vi.fn(async () => ({
    ok: true,
    // §12rv1-5 — the shared review reader serves display-cased severity ("Review"/"Info").
    data: { as_of: "2026-07-11", count: 1, items: [
      { area: "Data", title: "7 holdings have stale prices — refresh", severity: "Review" },
      { area: "Data", title: "4 holdings have incomplete details", severity: "Info" },
    ] },
  })),
}));

vi.mock("../api/client", async (orig) => ({
  ...(await orig<typeof import("../api/client")>()),
  apiGet: vi.fn(async () => ({ ok: false, error: "no refdata in test" })),
}));

import { NetWorth } from "./NetWorth";
import { getNetWorthHistory, getInsurance, getCoverage } from "../api/net-worth";

function renderPage() {
  return render(
    <ThemeProvider>
      <DisplayProvider>
        <RefdataProvider>
          <MemoryRouter initialEntries={["/net-worth"]}>
            <NetWorth />
          </MemoryRouter>
        </RefdataProvider>
      </DisplayProvider>
    </ThemeProvider>,
  );
}

afterEach(cleanup);

test("KPI strip shows the four D-054 figures", async () => {
  const { container } = renderPage();
  await screen.findByText("Cash & deposits");
  const kpis = within(container.querySelector('[data-card="kpis"]') as HTMLElement);
  expect(kpis.getByText("Net worth")).toBeTruthy();
  expect(kpis.getByText("Gross assets")).toBeTruthy();
  expect(kpis.getByText("Liabilities")).toBeTruthy();
  expect(kpis.getByText("Cash & deposits")).toBeTruthy();
});

test("composition statement includes a NEGATIVE liability row and a reconciling Net worth total (ND-4)", async () => {
  const { container } = renderPage();
  await screen.findByText("Composition by class");
  await waitFor(() => {
    const stmt = container.querySelector('[data-card="statement"]') as HTMLElement;
    // Class labels resolve via the offline refdata registry (never a raw enum key).
    expect(stmt.textContent).toMatch(/Liability/);
    // The statement's Net worth total is a <tfoot> row (shares the column grid, §12b1-2).
    expect(stmt.querySelector(".lf-table__foot--emph")?.textContent).toMatch(/Net worth/);
    // Liability value renders negative.
    expect(stmt.textContent).toMatch(/-420,000/);
  });
});

test("liquidity ladder renders rungs + the Liquid share line (D-036)", async () => {
  renderPage();
  await screen.findByText("Liquidity ladder");
  expect(await screen.findByText("Immediate (cash & listed)")).toBeTruthy();
  expect(await screen.findByText(/Liquid \(Immediate \+ Short\) = 21\.0% of gross assets/)).toBeTruthy();
});

test("runway shows the finite figure + the honest basis label (ND-9)", async () => {
  const { container } = renderPage();
  await screen.findByText("Cash runway");
  await waitFor(() => {
    expect(container.textContent).toMatch(/8\.5/);
    expect(container.textContent).toMatch(/Basis: liquid assets ÷ recurring monthly net burn/);
  });
});

test("fresh instance: empty net-worth history shows the honest EmptyState + Build-history trigger, never a fabricated curve (ND-1 / R-43 §9-2)", async () => {
  vi.mocked(getNetWorthHistory).mockResolvedValueOnce({ ok: true, data: { history: [] } });
  renderPage();
  expect(await screen.findByText("No history yet")).toBeTruthy();
  expect(await screen.findByText(/Build the Net-worth trend from your price history/i)).toBeTruthy();
  // The empty state carries the "Build history" backfill trigger (§9-2), not just a passive message.
  expect(await screen.findByRole("button", { name: /Build history/i })).toBeTruthy();
});

test("insurance exclusion line is OMITTED with zero policies (ND-5)", async () => {
  const { container } = renderPage();
  await screen.findByText("Liquidity ladder");
  await waitFor(() => expect(container.querySelector(".nw__exclusion")).toBeNull());
});

test("insurance exclusion line shows the verbatim wording when ≥1 policy (D-039/D-081, ND-5)", async () => {
  vi.mocked(getInsurance).mockResolvedValueOnce({ ok: true, data: { base_currency: "SGD", count: 2, total_cash_value: 15000, total_cash_value_display: "15,000.00" } });
  renderPage();
  expect(await screen.findByText(/Insurance cash value \(excluded\):/)).toBeTruthy();
  expect(await screen.findByText("15,000.00")).toBeTruthy();   // the SERVED display string, verbatim (D-105)
  expect(await screen.findByText(/see Insurance/)).toBeTruthy();
});

test("§12 step 7 (F-1): the served coverage preflight renders uncovered holdings verbatim", async () => {
  // A partial-coverage summary → the trigger surfaces which holdings still need history (D-105).
  vi.mocked(getCoverage).mockResolvedValueOnce({
    ok: true,
    data: {
      base_currency: "SGD", total: 2, covered_count: 1, all_covered: false,
      coverage_label: "History covers 1 of 2 holding(s) — Build history to fill the rest.",
      instruments: [
        { instrument_id: 1, symbol: "TSLA", name: "Tesla", asset_class: "equity",
          price_earliest: "2019-01-01", price_latest: "2026-07-18", price_days: 1900,
          needs_fx: true, fx_currency: "USD", fx_earliest: "1999-01-04", fx_latest: "2026-07-17",
          covered: true, summary: "Prices 2019-01-01→2026-07-18; USD FX 1999-01-04→2026-07-17" },
        { instrument_id: 2, symbol: "BTC", name: "Bitcoin", asset_class: "crypto",
          price_earliest: null, price_latest: null, price_days: 0,
          needs_fx: true, fx_currency: "USD", fx_earliest: null, fx_latest: null,
          covered: false, summary: "No price history yet — run Build history to acquire it" },
      ],
    },
  });
  renderPage();
  // The served label + the uncovered holding's served summary are rendered verbatim.
  expect(await screen.findByText("History covers 1 of 2 holding(s) — Build history to fill the rest.")).toBeTruthy();
  expect(await screen.findByText("No price history yet — run Build history to acquire it")).toBeTruthy();
  // The covered holding (TSLA) is NOT listed — only the gaps are surfaced.
  expect(screen.queryByText("Tesla")).toBeNull();
});
