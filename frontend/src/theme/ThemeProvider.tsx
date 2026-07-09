import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  nextChoice,
  readStoredChoice,
  resolveTheme,
  THEME_STORAGE_KEY,
} from "./theme";
import type { ThemeChoice } from "./theme";
import { ThemeContext } from "./theme-context";

function applyResolvedTheme(choice: ThemeChoice): void {
  document.documentElement.setAttribute("data-theme", resolveTheme(choice));
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(() =>
    readStoredChoice(),
  );

  // Reflect the choice onto <html data-theme> so tokens re-resolve.
  useEffect(() => {
    applyResolvedTheme(choice);
    if (choice === "system") return;
    localStorage.setItem(THEME_STORAGE_KEY, choice);
  }, [choice]);

  // While on `system`, follow OS changes live.
  useEffect(() => {
    if (choice !== "system") return;
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyResolvedTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  const setChoice = useCallback((c: ThemeChoice) => setChoiceState(c), []);
  const cycle = useCallback(
    () => setChoiceState((c) => nextChoice(c)),
    [],
  );

  const value = useMemo(
    () => ({ choice, resolved: resolveTheme(choice), setChoice, cycle }),
    [choice, setChoice, cycle],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}
