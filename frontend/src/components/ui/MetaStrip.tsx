import type { ReactNode } from "react";
import "./metastrip.css";

// Compact label/value metadata strip (DESIGN-SYSTEM §5.2). Dense identity/taxonomy
// metadata that recurs across entity-detail pages (instrument, accounts, policies,
// estate). Desktop: a single row of label-over-value pairs; narrow viewports wrap
// to a tight 2-column grid. Labels are `--text-tertiary` small; values sit below and
// may be plain text or a vocab chip (`lf-chip`). Values are display-only (no math).
export interface MetaItem {
  label: string;
  value: ReactNode;
}
export interface MetaStripProps {
  items: MetaItem[];
}

export function MetaStrip({ items }: MetaStripProps) {
  return (
    <dl className="lf-metastrip">
      {items.map((it, i) => (
        <div className="lf-metastrip__item" key={i}>
          <dt className="lf-metastrip__label">{it.label}</dt>
          <dd className="lf-metastrip__value">{it.value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
