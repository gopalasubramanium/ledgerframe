import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  CONTRAST_KEY,
  DENSITY_KEY,
  MOTION_KEY,
  readContrastPref,
  readDensity,
  readMotionPref,
  resolveContrast,
  resolveMotion,
} from "./display";
import type { ContrastPref, Density, MotionPref } from "./display";
import { DisplayContext } from "./display-context";

export function DisplayProvider({ children }: { children: ReactNode }) {
  const [density, setDensityState] = useState<Density>(() => readDensity());
  const [contrastPref, setContrastPrefState] = useState<ContrastPref>(() =>
    readContrastPref(),
  );
  const [motionPref, setMotionPrefState] = useState<MotionPref>(() =>
    readMotionPref(),
  );

  const contrast = resolveContrast(contrastPref);
  const motion = resolveMotion(motionPref);

  // Stamp resolved axes onto <html> so tokens.css re-resolves.
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-density", density);
    root.setAttribute("data-contrast", contrast);
    root.setAttribute("data-motion", motion);
  }, [density, contrast, motion]);

  // Persist per-device.
  useEffect(() => localStorage.setItem(DENSITY_KEY, density), [density]);
  useEffect(
    () => localStorage.setItem(CONTRAST_KEY, contrastPref),
    [contrastPref],
  );
  useEffect(() => localStorage.setItem(MOTION_KEY, motionPref), [motionPref]);

  // While either follows the OS, re-resolve on OS pref changes.
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const contrastMq = window.matchMedia("(prefers-contrast: more)");
    const motionMq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const root = document.documentElement;
    const sync = () => {
      root.setAttribute("data-contrast", resolveContrast(contrastPref));
      root.setAttribute("data-motion", resolveMotion(motionPref));
    };
    contrastMq.addEventListener("change", sync);
    motionMq.addEventListener("change", sync);
    return () => {
      contrastMq.removeEventListener("change", sync);
      motionMq.removeEventListener("change", sync);
    };
  }, [contrastPref, motionPref]);

  const setDensity = useCallback((d: Density) => setDensityState(d), []);
  const toggleDensity = useCallback(
    () =>
      setDensityState((d) => (d === "comfortable" ? "compact" : "comfortable")),
    [],
  );
  const setContrastPref = useCallback(
    (c: ContrastPref) => setContrastPrefState(c),
    [],
  );
  const setMotionPref = useCallback((m: MotionPref) => setMotionPrefState(m), []);

  const value = useMemo(
    () => ({
      density,
      contrastPref,
      motionPref,
      contrast,
      motion,
      setDensity,
      toggleDensity,
      setContrastPref,
      setMotionPref,
    }),
    [
      density,
      contrastPref,
      motionPref,
      contrast,
      motion,
      setDensity,
      toggleDensity,
      setContrastPref,
      setMotionPref,
    ],
  );

  return (
    <DisplayContext.Provider value={value}>{children}</DisplayContext.Provider>
  );
}
