import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { apiGet } from "../api/client";
import { RefdataContext } from "./refdata-context";
import type { Vocabs } from "./refdata-context";

// Fetches GET /refdata once and provides the fixed vocabularies to MasterSelect
// (D-005 — the frontend carries no vocabulary of its own). On failure the value
// stays null and MasterSelect falls back to the labelled registry.
export function RefdataProvider({ children }: { children: ReactNode }) {
  const [vocabs, setVocabs] = useState<Vocabs | null>(null);

  useEffect(() => {
    let live = true;
    apiGet<Vocabs>("/refdata").then((r) => {
      if (live && r.ok) setVocabs(r.data);
    });
    return () => {
      live = false;
    };
  }, []);

  return (
    <RefdataContext.Provider value={vocabs}>{children}</RefdataContext.Provider>
  );
}
