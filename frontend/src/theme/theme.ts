// Theme model (DESIGN-SYSTEM §2.1, D-066/D-078). The theme cycle is
// light → dark → system; `system` follows prefers-color-scheme; the choice is
// per-device (localStorage), never server-persisted.

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_CYCLE: readonly ThemeChoice[] = ["light", "dark", "system"];
export const THEME_STORAGE_KEY = "lf.theme";

export function nextChoice(current: ThemeChoice): ThemeChoice {
  const i = THEME_CYCLE.indexOf(current);
  return THEME_CYCLE[(i + 1) % THEME_CYCLE.length];
}

export function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

export function resolveTheme(choice: ThemeChoice): ResolvedTheme {
  if (choice === "system") return systemPrefersDark() ? "dark" : "light";
  return choice;
}

export function readStoredChoice(): ThemeChoice {
  if (typeof localStorage === "undefined") return "system";
  const v = localStorage.getItem(THEME_STORAGE_KEY);
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}
