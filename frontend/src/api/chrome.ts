// Chrome status readers: settings (timezone/demo/no-egress) + the stale summary.
// These feed the top bar's Clock/DemoBadge and the StaleBanner. All are status
// summaries — the chrome owns no figures (IA P-1). Every reader degrades to a safe
// empty value so a failed call hides its chrome piece rather than breaking the shell.
import { apiGet } from "./client";

const TRUTHY = new Set(["1", "true", "yes", "on"]);

export interface ChromeSettings {
  timezone: string;
  demo: boolean;
  noEgress: boolean;
}

interface SettingsResponse {
  stored?: Record<string, string>;
  defaults?: { timezone?: string; demo_mode?: boolean };
}

export async function fetchChromeSettings(): Promise<ChromeSettings> {
  const r = await apiGet<SettingsResponse>("/settings");
  if (!r.ok) return { timezone: "UTC", demo: false, noEgress: false };
  const stored = r.data.stored ?? {};
  return {
    timezone: r.data.defaults?.timezone ?? "UTC",
    demo: !!r.data.defaults?.demo_mode,
    noEgress: TRUTHY.has((stored.privacy_mode ?? "").toLowerCase()),
  };
}

export interface StaleSummary {
  has_stale: boolean;
  stale_count: number;
}

export async function fetchStaleSummary(): Promise<StaleSummary> {
  const r = await apiGet<{ has_stale?: boolean; stale_count?: number }>("/portfolio/summary");
  if (!r.ok) return { has_stale: false, stale_count: 0 };
  return { has_stale: !!r.data.has_stale, stale_count: r.data.stale_count ?? 0 };
}

// Global ticker footer (D-047 amendment, §11-17): the user's holdings + world indices.
// Both come from the frozen contract (no contract change) — /portfolio/holdings and
// /markets/global (which exposes index quotes; §11-17 4a). Prices/percents stay strings
// (the frontend never computes money); staleness is carried through per item. Degrades
// safely — a failed reader just contributes nothing.
export interface TickerQuote {
  symbol: string;
  price: string | null;
  changePct: string | null;
  stale?: boolean;
}

const numToStr = (v: unknown): string | null =>
  v === null || v === undefined ? null : String(v);

interface HoldingsResp {
  holdings?: { symbol?: string | null; price?: number | null; day_change_pct?: number | null; is_stale?: boolean }[];
}
interface GlobalResp {
  groups?: { items?: { symbol?: string; label?: string; quote?: { price?: unknown; change_pct?: unknown; is_stale?: boolean } }[] }[];
}

export async function fetchTickerQuotes(): Promise<TickerQuote[]> {
  const [h, g] = await Promise.all([
    apiGet<HoldingsResp>("/portfolio/holdings"),
    apiGet<GlobalResp>("/markets/global"),
  ]);
  const out: TickerQuote[] = [];
  // Holdings first (it's the user's portfolio), then world indices.
  if (h.ok) {
    for (const hv of h.data.holdings ?? []) {
      if (!hv.symbol) continue;
      out.push({
        symbol: hv.symbol,
        price: numToStr(hv.price),
        changePct: numToStr(hv.day_change_pct),
        stale: !!hv.is_stale,
      });
    }
  }
  if (g.ok) {
    for (const grp of g.data.groups ?? []) {
      for (const it of grp.items ?? []) {
        const label = it.label || it.symbol;
        if (!label) continue;
        out.push({
          symbol: label,
          price: numToStr(it.quote?.price),
          changePct: numToStr(it.quote?.change_pct),
          stale: !!it.quote?.is_stale,
        });
      }
    }
  }
  return out;
}
