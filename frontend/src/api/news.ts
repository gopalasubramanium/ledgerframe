import { apiGet, apiSend } from "./client";

// News (Markets-group home) readers — page-news §3a. Canonical home for the briefing + grouped
// headlines (D-037/D-068). The briefing is a SERVED display string (deterministic; AI narration is
// deferred, ND-1) — rendered verbatim. Headlines are SERVED, sanitised, deduped, grouped (ND-3/ND-12).
// Under no-egress the readers make zero outbound calls and flag `no_egress` (ND-2) — the page shows an
// honest reason, never fabricated headlines.

export interface BriefingResp {
  text: string;
  generated_at: string | null;
}

export interface GroupedNewsItem {
  headline: string;
  source: string;
  url: string | null;
  published_at: string | null;
  symbols: string[];
  relevance?: number;
}
export interface NewsGroup {
  name: string;
  items: GroupedNewsItem[];
}
export interface GroupedNewsResp {
  groups: NewsGroup[];
  total: number;
  no_egress: boolean;
}

export const getBriefing = () => apiGet<BriefingResp>("/briefing");
export const getGroupedNews = () => apiGet<GroupedNewsResp>("/news/grouped");

// Per-card refresh (batch 1, ND-8 REVERSAL). Both are EGRESS — the ND-2 guard governs under no-egress
// (the buttons render honestly disabled, never a no-op spinner). Briefing regenerate is `require_auth`
// ([S]); headlines refresh is just a re-GET of the live reader (no auth, no new endpoint).
export const refreshBriefing = () => apiSend<{ text: string }>("/briefing/refresh", "POST");

// No-egress state (ND-2) — gates the refresh buttons. Same shape as Pricing Health's reader.
const TRUTHY = new Set(["1", "true", "yes", "on"]);
export const getNoEgress = async (): Promise<boolean> => {
  const r = await apiGet<{ stored?: Record<string, string> }>("/settings");
  return r.ok ? TRUTHY.has((r.data.stored?.privacy_mode ?? "").toLowerCase()) : false;
};
