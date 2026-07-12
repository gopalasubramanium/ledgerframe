import { Link } from "react-router-dom";
import "./news.css";
import { EmptyState } from "./EmptyState";

// Extracted from the Instrument Detail news list (the recurring-pattern rule, page-news ND-5): a list
// of headlines, each an EXTERNAL link opening in a new tab + a `source · relative-time` meta line, with
// optional per-symbol links to InstrumentDetail. Headlines render as PLAIN TEXT (React escapes; the
// backend also sanitises untrusted feeds — ND-12) and are clamped with an ellipsis so a long headline
// never forces overflow. Shared by News (grouped) and InstrumentDetail (scoped).
export interface NewsListItem {
  headline: string;
  source: string;
  url?: string | null;
  published_at: string | null;
  symbols?: string[];
}

export interface NewsListProps {
  items: NewsListItem[];
  /** Show per-symbol links to InstrumentDetail (grouped News); off for the scoped instrument view. */
  showSymbols?: boolean;
  emptyMessage?: string;
  emptyReason?: string;
}

/** Relative age of a served timestamp ("3h ago"). Display-only client formatting — NOT money. */
function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

export function NewsList({
  items,
  showSymbols = false,
  emptyMessage = "No recent news",
  emptyReason = "No headlines right now.",
}: NewsListProps) {
  if (items.length === 0) return <EmptyState message={emptyMessage} reason={emptyReason} />;
  return (
    <ul className="lf-newslist">
      {items.map((n, i) => (
        <li className="lf-newslist__item" key={`${n.url ?? n.headline}-${i}`}>
          {n.url ? (
            <a className="lf-newslist__head" href={n.url} target="_blank" rel="noreferrer noopener">
              {n.headline}
            </a>
          ) : (
            <span className="lf-newslist__head lf-newslist__head--plain">{n.headline}</span>
          )}
          <span className="lf-newslist__meta">
            {n.source}
            {n.published_at ? ` · ${relativeTime(n.published_at)}` : ""}
            {showSymbols && n.symbols && n.symbols.length > 0 ? (
              <>
                {" · "}
                {n.symbols.map((s, j) => (
                  <span key={s}>
                    {j > 0 ? " " : ""}
                    <Link className="lf-newslist__sym" to={`/instrument/${encodeURIComponent(s)}`}>{s}</Link>
                  </span>
                ))}
              </>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}
