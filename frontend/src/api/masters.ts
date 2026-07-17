// Instrument masters — the reference lists the Add-flow picker searches (§14dr-13).
// v1 Settings carried AMFI/CoinGecko sync affordances (01-FEATURE-INVENTORY:191); v2
// dropped the UI without a recorded deferral. The backend sync engines never left —
// these clients wire the existing require_auth POST /{master}/refresh triggers +
// GET /{master}/status readers to the Settings → Data feeds "Masters" card.
//
// `synced_at` is the served last-synced timestamp (null = never synced — the honest
// empty). Sync is opt-in network (Guarantee 5: nothing fetched under no-egress — the
// endpoint 502s honestly, surfaced as a served error, never fabricated progress).
import { apiGet, apiSend } from "./client";

/** One master row for the card. Counts + synced_at are served; the frontend computes nothing. */
export interface MasterState {
  key: "amfi" | "coingecko";
  /** User-facing name of what this master backs in the picker. */
  label: string;
  /** How many entries the master holds (schemes / coins). 0 = never synced. */
  count: number;
  /** ISO timestamp of the last sync, or null when never synced. */
  synced_at: string | null;
}

interface AmfiStatus {
  schemes: number;
  priced: number;
  as_of: string | null;
  synced_at: string | null;
}
interface CoingeckoStatus {
  coins: number;
  mapped: number;
  synced_at: string | null;
}

export async function getMasters(): Promise<MasterState[] | null> {
  const [a, c] = await Promise.all([
    apiGet<AmfiStatus>("/amfi/status"),
    apiGet<CoingeckoStatus>("/coingecko/status"),
  ]);
  if (!a.ok || !c.ok) return null;
  return [
    { key: "amfi", label: "Mutual funds (AMFI)", count: a.data.schemes, synced_at: a.data.synced_at },
    { key: "coingecko", label: "Crypto (CoinGecko)", count: c.data.coins, synced_at: c.data.synced_at },
  ];
}

type SyncResult = { ok: true; count: number } | { ok: false; error: string };

/** Trigger a sync of one master (opt-in network). Returns the served post-sync count. */
export async function syncMaster(key: "amfi" | "coingecko"): Promise<SyncResult> {
  const path = key === "amfi" ? "/amfi/refresh" : "/coingecko/refresh";
  const r = await apiSend<{ schemes?: number; coins?: number }>(path, "POST");
  if (!r.ok) return { ok: false, error: r.error };
  const count = key === "amfi" ? (r.data.schemes ?? 0) : (r.data.coins ?? 0);
  return { ok: true, count };
}
