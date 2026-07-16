// SPDX-License-Identifier: AGPL-3.0-or-later
import { apiGet } from "./client";

// Reports domain — page-reports §3. Canonical home for the Statements, Realised P/L and open
// tax-lots readers + their server-side CSV exports (P-5 / D-050). Every figure is a backend-served
// value rendered verbatim by the display formatters (D-105 posture — the frontend computes no money);
// every disclaimer is the served display string, shown on screen AND carried into the export by the
// backend builders (§9-5). No writes on this page (read/export only).

// --- GET /portfolio/statements — income / fees / cash flow (all-years) + realised-vs-unrealised --- //
export interface StatementsByYear {
  year: number;
  dividend: number;
  interest: number;
  total: number;
}
export interface FeesByYear {
  year: number;
  commissions: number;
  taxes: number;
  total: number;
}
export interface CashflowByYear {
  year: number;
  deposits: number;
  withdrawals: number;
  net: number;
}
export interface StatementsReport {
  base_currency: string;
  years: number[];
  year: number;
  income_by_year: StatementsByYear[];
  fees: { commissions: number; taxes: number; total: number; by_year: FeesByYear[] };
  cashflow: { deposits: number; withdrawals: number; net: number; by_year: CashflowByYear[] };
  // §12rp-3: `realised` IS realised_gains_report(year).base_realised_total_current_fx (served at the
  // SAME 2dp precision) — ONE truth with the Realised P/L report's current-FX total. `unrealised` is
  // "open positions, now" (NOT year-scoped). Both served (D-105).
  realised_unrealised: { realised: number; unrealised: number };
  disclaimer: string;
}
export const getStatements = (year?: number | string) =>
  apiGet<StatementsReport>(year ? `/portfolio/statements?year=${year}` : "/portfolio/statements");

// --- GET /portfolio/realised-gains — per-event realised P/L, grouped by native currency ---------- //
export interface RealisedEvent {
  symbol: string;
  name: string;
  sell_date: string;
  acquired_date: string;
  quantity: number;
  proceeds: number;
  cost: number;
  gain: number; // native currency (the group's currency) — §12rp-2 the Currency column names it
  holding_days: number;
  long_term: boolean;
}
export interface RealisedCurrencyGroup {
  currency: string;
  realised_total: number;
  short_term: number;
  long_term: number;
  income: number;
  events: RealisedEvent[];
}
export interface RealisedReport {
  year: number;
  years: number[];
  long_term_days: number; // Amendment J — rendered READ-ONLY (served default, never an input)
  base_currency: string;
  currency_groups: RealisedCurrencyGroup[];
  base_realised_total_current_fx: number; // ONE truth with the Statements Realised stat (§12rp-3)
  base_realised_total_historical_fx: number; // trade-date FX total — the honest divergence (D-020/D-076)
  realised_fx_events_excluded: number; // rendered when NON-ZERO — never hidden
  disclaimer: string;
}
export const getRealisedGains = (year?: number | string) =>
  apiGet<RealisedReport>(year ? `/portfolio/realised-gains?year=${year}` : "/portfolio/realised-gains");

// --- GET /portfolio/tax-lots — open (unsold) lots by FIFO -------------------------------------- //
export interface TaxLot {
  symbol: string;
  name: string;
  acquired_date: string;
  quantity: number;
  unit_cost: number;
  cost: number; // == quantity × unit_cost, SERVED (the frontend never multiplies)
  currency: string; // §12rp-2 precedent — the per-row Currency column the Realised table mirrors
  holding_days: number;
  long_term: boolean;
}
export interface TaxLotsReport {
  long_term_days: number;
  lots: TaxLot[];
  disclaimer: string;
}
export const getTaxLots = () => apiGet<TaxLotsReport>("/portfolio/tax-lots");

// --- server-side export paths (P-5 — apiDownload builds no file client-side) --------------------- //
// The Year scopes the statements + realised exports (§12rp-1 for statements; the realised export was
// always year-scoped). Tax-lots has no year filter (open lots are a point-in-time set).
export const statementsCsvPath = (year: number | string) => `/portfolio/statements.csv?year=${year}`;
export const realisedGainsCsvPath = (year: number | string) =>
  `/portfolio/realised-gains.csv?year=${year}`;
export const taxLotsCsvPath = () => `/portfolio/tax-lots.csv`;
