import "./badges.css";

// Amber chip for the Stale layer (GLOSSARY layer 2). It FLAGS, never hides, the
// value — distinct from ProvenanceBadge (which carries full source·freshness·
// confidence). When not stale it renders nothing. Compact by design so it never
// forces a table into horizontal scroll: the chip reads "Stale · 08 Jul"; the full
// as-of date lives in the tooltip. When `asOf` is not a real timestamp it reads
// just "Stale" (never "Stale · as of <label>" — that double-reads).
export interface StalenessChipProps {
  isStale: boolean;
  /** ISO timestamp the value was as-of (empty/non-date → just "Stale"). */
  asOf: string;
  staleAfter?: number;
}

function parseDate(asOf: string): Date | null {
  const d = new Date(asOf);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function StalenessChip({ isStale, asOf }: StalenessChipProps) {
  if (!isStale) return null;
  const d = parseDate(asOf);
  const short = d ? d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : null;
  const full = d ? d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : null;
  return (
    <span className="lf-stale" title={full ? `Stale · as of ${full}` : "Price is stale"}>
      <span className="lf-stale__glyph" aria-hidden="true">
        ⚠
      </span>
      Stale{short ? ` · ${short}` : ""}
    </span>
  );
}
