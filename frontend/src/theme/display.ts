// Per-device display axes beyond theme (D-078): density, high-contrast, and
// reduced-motion. All are localStorage-backed and never server-persisted. Each
// is applied as a resolved data-attribute on <html> so tokens.css re-resolves.

export type Density = "comfortable" | "compact";
export type ContrastPref = "system" | "high" | "normal";
export type MotionPref = "system" | "reduced" | "full";

export type ResolvedContrast = "normal" | "high";
export type ResolvedMotion = "full" | "reduced";

export const DENSITY_KEY = "lf.density";
export const CONTRAST_KEY = "lf.contrast";
export const MOTION_KEY = "lf.motion";

function mql(query: string): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia(query).matches
  );
}

export function resolveContrast(pref: ContrastPref): ResolvedContrast {
  if (pref === "high") return "high";
  if (pref === "normal") return "normal";
  return mql("(prefers-contrast: more)") ? "high" : "normal";
}

export function resolveMotion(pref: MotionPref): ResolvedMotion {
  if (pref === "reduced") return "reduced";
  if (pref === "full") return "full";
  return mql("(prefers-reduced-motion: reduce)") ? "reduced" : "full";
}

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  if (typeof localStorage === "undefined") return fallback;
  const v = localStorage.getItem(key);
  return (allowed as readonly string[]).includes(v ?? "") ? (v as T) : fallback;
}

export function readDensity(): Density {
  return read(DENSITY_KEY, ["comfortable", "compact"] as const, "comfortable");
}
export function readContrastPref(): ContrastPref {
  return read(CONTRAST_KEY, ["system", "high", "normal"] as const, "system");
}
export function readMotionPref(): MotionPref {
  return read(MOTION_KEY, ["system", "reduced", "full"] as const, "system");
}
