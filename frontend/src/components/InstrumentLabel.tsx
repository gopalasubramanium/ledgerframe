// SPDX-License-Identifier: AGPL-3.0-or-later
import { Link } from "react-router-dom";
import "./InstrumentLabel.css";

// §14dr-19 (owner reversal of dr-16): the ONE symbol+name display pattern, symbol
// prominent + name secondary — promoted from the Holdings identity subtext so every
// surface (Portfolio movers/attribution, Home movers/gainers-losers, Transactions)
// renders it identically, never a per-instance copy. Name is hidden when it is null
// or equals the symbol (the served payloads already null it in that case). A
// composition of a Link + spans, not a new ui/ primitive.
export function InstrumentLabel({
  symbol,
  name,
  fallback,
  link = true,
}: {
  symbol?: string | null;
  name?: string | null;
  fallback?: string | null;
  link?: boolean;
}) {
  const sym = symbol || fallback || "—";
  const showName = name && name !== symbol && name !== sym;
  return (
    <span className="lf-instr">
      {link && symbol ? (
        <Link className="lf-instr__sym lf-instr__link" to={`/instrument/${encodeURIComponent(symbol)}`}>
          {sym}
        </Link>
      ) : (
        <span className="lf-instr__sym">{sym}</span>
      )}
      {showName && <span className="lf-instr__name">{name}</span>}
    </span>
  );
}
