import { apiGet, apiSend } from "./client";

// Net worth (overview) readers — page-net-worth §3a. All figures are SERVED display values;
// the page performs no money math (P-1/D-031). Types mirror the verified payloads (§10/§11).

// Net-worth trend — persisted snapshots. Each point carries served provenance (backfilled |
// live | manual, R-43 §9-1) and a §9-5 carried-forward flag + served reason; a fresh instance
// with no history shows the "Build history" trigger (ND-1 / R-43 §9-2).
export interface NetWorthPoint {
  ts: string;
  assets: number;
  liabilities: number;
  net_worth: number;
  currency: string;
  source?: "backfilled" | "live" | "manual";
  carried_forward?: boolean;
  reason?: string | null;
}
export interface NetWorthHistoryResp {
  history: NetWorthPoint[];
}

// R-43 §9-2/§9-6 — the backfill trigger, its served progress, and snapshot-now.
export interface BackfillStatus {
  running: boolean;
  ok: boolean;
  failed: boolean;
  done: number;
  total: number;
  current: string | null;
  message: string;
}
export const startBackfill = () => apiSend<{ ok: boolean; running: boolean; message: string }>("/net-worth/backfill", "POST");
export const getBackfillStatus = () => apiGet<BackfillStatus>("/net-worth/backfill-status");
export const takeSnapshot = () => apiSend<{ ok: boolean; ts: string; net_worth: number }>("/net-worth/snapshot", "POST");

// Signed per-class STATEMENT (page-net-worth ND-4, D-033). Distinct from allocation:
// assets positive, liabilities negative, `net_worth` reconciles to the headline.
export interface StatementRow {
  asset_class: string;
  value: number;
}
export interface StatementResp {
  base_currency: string;
  rows: StatementRow[];
  gross_assets: number;
  liabilities: number;
  net_worth: number;
}

// Liquidity ladder (D-036). Served rung labels (D-005 zero-copy).
export interface LiquidityRung {
  key: string;
  label: string;
  value: number;
  pct: number;
  cumulative_pct: number;
}
export interface LiquidityResp {
  base_currency: string;
  gross_assets: number;
  rungs: LiquidityRung[];
  liquid_pct: number;
  liabilities: number;
  disclaimer: string;
}

// Cash runway (D-036/D-057). Honest states: no_data / positive / finite.
export interface RunwayResp {
  base_currency: string;
  liquid: number;
  monthly_expense: number;
  monthly_income: number;
  net_monthly_burn: number;
  runway_months: number | null;
  runway_date: string | null;
  status: "no_data" | "positive" | "finite";
  note: string;
  disclaimer: string;
}

// Insurance valued exclusion line (D-039/D-081) — only the served display total + count are used here.
// `count` is ACTIVE policies only (page-insurance §9-10, Amendment A), agreeing with the cash-value total.
export interface InsuranceResp {
  base_currency: string;
  count: number;
  total_cash_value: number;
  total_cash_value_display: string; // served display string (D-105) — rendered verbatim, no client math
}

// Review summary (D-038) — the same reader the (unbuilt) Review page will own; P-1 summary only.
export interface ReviewItem {
  area: string;
  title: string;
  severity: string; // review | info | …
}
export interface ReviewResp {
  as_of: string;
  count: number;
  items: ReviewItem[];
}

export const getNetWorthHistory = () => apiGet<NetWorthHistoryResp>("/net-worth/history");
export const getNetWorthStatement = () => apiGet<StatementResp>("/net-worth/statement");
export const getLiquidity = () => apiGet<LiquidityResp>("/portfolio/liquidity");
export const getRunway = () => apiGet<RunwayResp>("/portfolio/runway");
export const getInsurance = () => apiGet<InsuranceResp>("/insurance");
export const getReview = () => apiGet<ReviewResp>("/portfolio/review");
