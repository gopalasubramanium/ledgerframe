import { createContext, useContext } from "react";
import type { ResolvedTheme, ThemeChoice } from "./theme";

export interface ThemeState {
  /** The user's selection: light, dark, or system. */
  choice: ThemeChoice;
  /** The concrete theme in effect (system resolved via prefers-color-scheme). */
  resolved: ResolvedTheme;
  /** Set an explicit choice (persisted per-device). */
  setChoice: (choice: ThemeChoice) => void;
  /** Advance the light → dark → system cycle (D-066). */
  cycle: () => void;
}

export const ThemeContext = createContext<ThemeState | null>(null);

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
