import { apiGet } from "./client";

// D-097 — class-aware instrument search for the Add-flow picker. Three honest
// buckets so an autocomplete can never misclassify (see backend /instruments/search).
export interface InstrumentSearchItem {
  id?: number;
  symbol: string;
  name: string;
  asset_class?: string;
  currency?: string;
}
export interface InstrumentSearchResult {
  existing: InstrumentSearchItem[]; // ledger instruments of the picked class
  other_class: InstrumentSearchItem[]; // ledger instruments under a DIFFERENT class
  suggestions: { symbol: string; name: string }[]; // provider search routed by class
}

export const searchInstruments = (q: string, assetClass?: string) => {
  const p = new URLSearchParams({ q });
  if (assetClass) p.set("asset_class", assetClass);
  return apiGet<InstrumentSearchResult>(`/instruments/search?${p.toString()}`);
};
