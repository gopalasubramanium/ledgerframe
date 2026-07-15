import { apiGet } from "./client";

// Scenarios reader — page-scenarios §3a. Canonical home for the fixed shock set, exposures and the
// liquidity what-ifs (D-058). READ-ONLY — a scenario, never a forecast; no write path.
//
// Every money figure arrives as a SERVED display string (`*_display`, D-105) and is rendered
// verbatim: the page computes and formats NO money. Percentages (`pct_change`) are served numbers
// and formatted client-side. A shock delta is always a LOSS (downside stress) — never a gain.

export interface AssetShock {
  id: string;
  name: string;             // served display string — rendered verbatim
  group: string;            // markets | fx
  exposure: number;
  exposure_display: string;
  delta: number;            // always <= 0
  delta_display: string;
  new_net_worth: number;
  new_net_worth_display: string;
  pct_change: number;       // a percentage — a number, not money
}

export interface Exposures {
  equities: number; equities_display: string;
  crypto: number; crypto_display: string;
  property: number; property_display: string;
  foreign_fx: number; foreign_fx_display: string;
}

export interface IncomeStop {
  monthly_expense: number;
  monthly_expense_display: string;
  /** null when there is no recorded expense to model against — render a reason, never 0. */
  runway_months: number | null;
  note: string;
}
export interface ObligationDue {
  amount: number;
  amount_display: string;
  new_liquid: number;
  new_liquid_display: string;
  covered: boolean;
  note: string;             // §9-10 — "expenses", the user's vocabulary
}
export interface Liquidity {
  liquid: number;
  liquid_display: string;
  runway_months: number | null;
  income_stop: IncomeStop;
  obligation_due: ObligationDue;
}

export interface ScenariosResp {
  base_currency: string;
  net_worth: number;
  net_worth_display: string;
  exposures: Exposures;
  asset_scenarios: AssetShock[];
  liquidity: Liquidity;
  // A10 — a what-if computed on stale/low-confidence values says so (§9-2).
  stale_inputs: number;
  low_confidence_inputs: number;
  inputs_stale: boolean;
  inputs_note: string | null;
  disclaimer: string;       // protected D-058 copy — rendered verbatim
}

export const fetchScenarios = () => apiGet<ScenariosResp>("/portfolio/scenarios");
