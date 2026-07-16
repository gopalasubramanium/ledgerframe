// SPDX-License-Identifier: AGPL-3.0-or-later
import "./brand.css";

export interface BrandMarkProps {
  /**
   * Square size. Default `1.25em` so, dropped beside text, the mark tracks the
   * adjacent wordmark's cap height (the §5.4 icon-sizing discipline — never a
   * per-call lie about what controls it; here it IS the mark's own metric).
   */
  size?: string | number;
  className?: string;
}

/**
 * BrandMark — the LedgerFrame platform mark, "the double rule" (DESIGN-SYSTEM §Brand, P-4).
 *
 * A rounded square frame containing one entry line and a right-aligned DOUBLE RULE — the
 * bookkeeping mark drawn under a verified final balance. The frame and entry are `currentColor`
 * (they inherit the surrounding text colour, so the mark works in both themes with zero
 * overrides); the double rule is the platform ACCENT token (`var(--accent)`, themed).
 *
 * The mark is DECORATIVE (`aria-hidden`): the wordmark beside it is the accessible name, so a
 * lockup reads as one "LedgerFrame", never "graphic LedgerFrame". Geometry is fixed — never
 * distorted, never recoloured beyond currentColor + the accent (§Brand usage rule).
 */
export function BrandMark({ size = "1.25em", className }: BrandMarkProps) {
  return (
    <svg
      className={className ? `lf-brandmark ${className}` : "lf-brandmark"}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      {/* Frame — the rounded ledger boundary. */}
      <rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" strokeWidth="2" />
      {/* One entry line. */}
      <path d="M7.5 9 h9" stroke="currentColor" strokeWidth="2" />
      {/* The double rule under a verified final balance — drawn in the platform accent. */}
      <path d="M10.5 13.75 h6" stroke="var(--accent)" strokeWidth="2" />
      <path d="M10.5 16.25 h6" stroke="var(--accent)" strokeWidth="2" />
    </svg>
  );
}
