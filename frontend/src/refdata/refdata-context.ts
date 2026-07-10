import { createContext, useContext } from "react";

// Fixed vocabularies from GET /refdata (D-005) — the canonical source of vocab
// VALUES. Null until loaded (or if the fetch fails); consumers fall back to the
// labelled registry so the UI degrades gracefully offline.
export type Vocabs = Record<string, string[]>;

export const RefdataContext = createContext<Vocabs | null>(null);

export function useRefdataVocabs(): Vocabs | null {
  return useContext(RefdataContext);
}
