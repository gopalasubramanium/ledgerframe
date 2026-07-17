// News RSS feeds editor (page-settings §12st-3 / ND-6). Feeds MANAGEMENT lives in Settings (the
// §9-3 ruling); News stays display-only. PUT is require_auth ([S]-gated); Test is egress and
// returns empty under no-egress (Guarantee 5). The editor is a Dialog + multi-URL TextInput + Test
// — the ratified Accounts-dialog pattern, no new component.
import { apiGet, apiSend } from "./client";

export interface FeedTestResult {
  url: string;
  ok: boolean;
  count: number;
  error: string | null;
  status: number | null;
}

export async function getFeeds(): Promise<{ feeds: string[]; defaults: string[] } | null> {
  const r = await apiGet<{ feeds: string[]; defaults: string[] }>("/news/feeds");
  return r.ok ? r.data : null;
}

export async function putFeeds(
  feeds: string[],
): Promise<{ ok: true; feeds: string[] } | { ok: false; error: string }> {
  const r = await apiSend<{ ok?: boolean; feeds?: string[] }>("/news/feeds", "PUT", { feeds });
  return r.ok ? { ok: true, feeds: r.data.feeds ?? feeds } : { ok: false, error: r.error };
}

export async function testFeeds(): Promise<FeedTestResult[] | null> {
  const r = await apiGet<{ results: FeedTestResult[] }>("/news/feeds/test");
  return r.ok ? r.data.results : null;
}
