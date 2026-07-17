// Settings page readers/writers (page-settings Phase 1). The page writes through the CANONICAL
// endpoints only (no second code path): /settings for prefs, /system/* for system config,
// /tokens for the API-token card, /auth/* for the PIN. Every value the page shows is a SERVED
// display string (D-105) — the frontend computes nothing here, and there is no money math.
import { apiGet, apiSend } from "./client";

export interface SettingsDefaults {
  base_currency: string;
  timezone: string;
  market_provider: string;
  supported_currencies: string[];
  /** page-settings §9-1 / Amendment A — the RESOLVED long-term threshold, served so the field
   *  renders it verbatim rather than the frontend carrying a 365 literal. */
  long_term_days: number;
  ai_enabled?: boolean;
  demo_mode?: boolean;
  home_quote_source?: string;
}

export interface SettingsData {
  /** The allow-listed keys actually stored (only those set differ from the served defaults). */
  stored: Record<string, string>;
  defaults: SettingsDefaults;
}

export async function getSettings(): Promise<SettingsData | null> {
  const r = await apiGet<SettingsData>("/settings");
  return r.ok ? r.data : null;
}

/** PUT /settings (require_auth). An unknown key is an honest 400 surfaced as its real message. */
export async function putSettings(
  values: Record<string, string>,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const r = await apiSend<{ ok?: boolean }>("/settings", "PUT", { values });
  return r.ok ? { ok: true } : { ok: false, error: r.error };
}
