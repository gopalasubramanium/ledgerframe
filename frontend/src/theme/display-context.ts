import { createContext, useContext } from "react";
import type {
  ContrastPref,
  Density,
  MotionPref,
  ResolvedContrast,
  ResolvedMotion,
} from "./display";

export interface DisplayState {
  density: Density;
  contrastPref: ContrastPref;
  motionPref: MotionPref;
  /** Concrete values in effect (system prefs resolved). */
  contrast: ResolvedContrast;
  motion: ResolvedMotion;
  setDensity: (d: Density) => void;
  toggleDensity: () => void;
  setContrastPref: (c: ContrastPref) => void;
  setMotionPref: (m: MotionPref) => void;
}

export const DisplayContext = createContext<DisplayState | null>(null);

export function useDisplay(): DisplayState {
  const ctx = useContext(DisplayContext);
  if (!ctx) throw new Error("useDisplay must be used within <DisplayProvider>");
  return ctx;
}
