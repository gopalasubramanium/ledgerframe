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

export interface HelpTopicLink {
  topic: string;
  label: string;
}

export interface HelpEntry {
  id: string;
  category: string;
  title: string;
  body: string;
  keywords?: string;
  // Glossary (Section 3)
  what?: string;
  why?: string;
  improves?: string;
  example?: string;
  level?: string;
  // Pages (Section 2)
  inputs?: string[];
  options?: string[];
  outputs?: string[];
  interpret?: string;
  // Orientation (Section 1) — pointers into Section 2, never figures.
  links?: HelpTopicLink[];
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

/** Ranked entries for a natural-language query (server-ranked; max 6).
 *
 * NOT what the page's type-ahead uses (§9-bis-4). The page ranks CLIENT-SIDE over the bundle
 * `helpContent()` already returned: the whole catalogue arrives in one read on a local-first
 * appliance, so per-keystroke ranking costs nothing, needs no debounce-to-server, and keeps working
 * with no-egress on — none of which a per-keystroke request can claim.
 *
 * This reader stays because it has its own consumers: `GET /help?q=` as an addressable URL, and the
 * AI's grounded fact pack. The honest cost, stated rather than glossed: two rankers now exist and
 * could drift apart. They answer to different consumers and each is tested on its own side.
 */
export function helpSearch(q: string) {
  return apiGet<HelpSearchResponse>(`/help?q=${encodeURIComponent(q)}`);
}
