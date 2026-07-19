import { apiGet } from "./client";

// Help catalogue reader — page-help §3a. The KB is SERVED (page-help §9-2: served is canonical for
// the PAGE; the bundled `mocks/glossary.ts` stays canonical for the [Help] popover, which must open
// instantly and offline). The page renders these strings VERBATIM and computes nothing.
//
// The route has TWO shapes (§9-12, found by typing it): the full catalogue, and a ranked search.
// Both are pinned in the frozen contract as `anyOf[HelpResponse, HelpSearchResponse]`.
//
// `what`/`why`/`improves` ride Terms entries ONLY and are ABSENT (not null) elsewhere — the
// endpoint sets `response_model_exclude_unset`, so `k in entry` is the honest test, not `!= null`.

export interface HelpEntry {
  id: string;
  category: string;
  title: string;
  body: string;
  what?: string;
  why?: string;
  improves?: string;
}

export interface HelpResponse {
  categories: string[];
  entries: HelpEntry[];
}

export interface HelpSearchResponse {
  query: string;
  entries: HelpEntry[];
}

/** The whole catalogue, grouped by the served category order. */
export function helpContent() {
  return apiGet<HelpResponse>("/help");
}

/** Ranked entries for a natural-language query (server-side; max 6). */
export function helpSearch(q: string) {
  return apiGet<HelpSearchResponse>(`/help?q=${encodeURIComponent(q)}`);
}
