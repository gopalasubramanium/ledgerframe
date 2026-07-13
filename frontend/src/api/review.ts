import { apiGet, apiSend } from "./client";

// Review (Planning-group home) readers — page-review §3a. Canonical home for review verdicts + the
// attention list, Mark-reviewed (with history), reporting only (D-038). Every value is a SERVED display
// value; the page performs no money math. `/review` is the D-030 rename of `/review/centre` (ND-2); its
// `attention[]` is `review_report.items`, the same reader `/portfolio/review` (ReviewCard) uses — the
// counts reconcile by construction (ND-3).

export interface ReviewAttentionItem {
  area: string;
  title: string;
  severity: string; // served display value — {review, info} (rendered verbatim, neutral; ND-4)
}
export interface ReviewSections {
  trust: { confidence: number; low: number; stale: number };
  policy: { out_of_band: number; has_targets: boolean };
  liquidity: { liquid_pct: number; runway_status: string; runway_months: number | null };
  goals: { goals: number; next_obligation: string | null; next_12m_total: number };
  changed: { day_change: number; top_mover: string | null };
}
export interface ReviewLastReview {
  reviewed_at: string;
  days_ago: number;
  next_review_date: string | null;
}
export interface ReviewPageResp {
  base_currency: string;
  net_worth: number;
  sections: ReviewSections;
  attention: ReviewAttentionItem[];
  attention_count: number;
  last_review: ReviewLastReview | null;
  disclaimer: string;
}
export interface ReviewHistoryRow {
  id: number;
  reviewed_at: string;
  days_ago: number;
  net_worth: number;
  base_currency: string;
  confidence: number;
  drift_flags: number;
  attention_count: number;
  note: string | null;
  next_review_date: string | null;
}
export interface ReviewHistoryResp {
  history: ReviewHistoryRow[];
}

export const getReviewPage = () => apiGet<ReviewPageResp>("/review");
export const getReviewHistory = () => apiGet<ReviewHistoryResp>("/review/history");
// Mark-reviewed (ND-8) — records a ReviewLog snapshot; require_auth ([S], as served).
export const markReviewed = (note?: string, nextReviewDate?: string) =>
  apiSend<{ ok: boolean; id: number }>("/review/log", "POST", {
    note: note || null,
    next_review_date: nextReviewDate || null,
  });
