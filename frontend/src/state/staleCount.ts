import { useSyncExternalStore } from "react";
import { fetchStaleSummary } from "../api/chrome";

// ONE shared client query for the portfolio stale-price count (page-pricing-health §12ph1-1).
// The StaleBanner (global chrome) and the Pricing Health footnote BOTH read this single cached
// value over `/portfolio/summary` — so a page can never claim "matches the Stale banner" while
// displaying a different, independently-fetched number (the ND-1 reconciliation guarantee). Refresh
// actions call `invalidateStaleCount()` so the banner and the footnote move together.

const POLL_MS = 60_000;

interface StaleState {
  count: number;
  // R-63 F-F/I-13: the holdings total the count ranges over, carried in the SAME snapshot so the
  // Pricing Health card renders "N of M" entirely from this shared value — never M from a separate
  // fetch — and the banner and card cannot disagree even transiently during a refresh.
  total: number;
  loaded: boolean;
}
// A stable reference between changes (useSyncExternalStore requires getSnapshot to be referentially
// stable when nothing changed).
let snapshot: StaleState = { count: 0, total: 0, loaded: false };
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | null = null;
let inFlight = false;

async function load(): Promise<void> {
  if (inFlight) return;
  inFlight = true;
  try {
    const s = await fetchStaleSummary();
    if (s.stale_count !== snapshot.count || s.holdings_count !== snapshot.total || !snapshot.loaded) {
      snapshot = { count: s.stale_count, total: s.holdings_count, loaded: true };
      listeners.forEach((l) => l());
    }
  } finally {
    inFlight = false;
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (listeners.size === 1) {
    void load(); // first subscriber kicks the initial fetch + poll
    timer = setInterval(() => void load(), POLL_MS);
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  };
}

function getSnapshot(): StaleState {
  return snapshot;
}

/** The shared, polled stale-price count (banner + any page read the SAME value). */
export function useStaleCount(): StaleState {
  return useSyncExternalStore(subscribe, getSnapshot);
}

/** Re-fetch now — call after any refresh so the banner + page footnote update together. */
export function invalidateStaleCount(): void {
  void load();
}
