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
