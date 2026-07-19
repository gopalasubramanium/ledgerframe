// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ReactNode } from "react";
import "./badges.css";

/** Semantic tone. Colour is NEVER the sole signal — the label always carries the meaning (WCAG). */
export type StatusChipTone = "neutral" | "attention" | "positive" | "negative";

export interface StatusChipProps {
  /**
   * The SERVED display string, rendered verbatim (D-005) — never a raw enum key.
   * MANDATORY: a chip's meaning is never carried by colour alone (WCAG 1.4.1). `ReactNode` so a
   * chip may carry a link (Pricing Health's "add in Settings") — it is still always a visible label.
   */
  label: ReactNode;
  tone?: StatusChipTone;
  /** Optional trailing count, e.g. "Delayed · 3". */
  count?: number;
  title?: string;
  /**
   * Dead-affordance treatment — the chip names something real that is NOT active here (e.g. a
   * priority-chain provider this instance holds no key for). Same ratified dimming as a disabled
   * `Segmented` option (`--text-tertiary` + 0.5 opacity, DESIGN-SYSTEM §5). The MEANING must still
   * be carried by the served label (WCAG 1.4.1) — dimming annotates it, never replaces it.
   */
  muted?: boolean;
}

/**
 * StatusChip — THE status/severity chip (DESIGN-SYSTEM §5.3 amendment, page-policy §9-15).
 *
 * Extracted at the THIRD recurrence of the same page-local pattern (Pricing Health's `ph__chip`,
 * Review's `rv__chip`, and Policy's band chip), per the centralization rule the Segmented extraction
 * set: *per-instance copies of a standard are the defect*. Both page-local copies are migrated onto
 * this component; neither remains.
 *
 * The label is MANDATORY and always rendered: a chip's meaning may never be carried by colour alone.
 */
export function StatusChip({ label, tone = "neutral", count, title, muted }: StatusChipProps) {
  return (
    <span className={`lf-statuschip lf-statuschip--${tone}${muted ? " lf-statuschip--muted" : ""}`} title={title}>
      {label}
      {count !== undefined && <span className="lf-statuschip__count">· {count}</span>}
    </span>
  );
}
