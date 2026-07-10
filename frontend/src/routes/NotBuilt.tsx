import { EmptyState } from "../components/ui";
import "./NotBuilt.css";

// Shell fallback for routes that are navigable (redirect targets, direct URLs) but
// whose page isn't built yet. Honest per Product Guarantee 3 — never a blank screen,
// always a reason. The sidebar only surfaces built pages, so this is reached only by
// a redirect (e.g. /snapshot → /net-worth before Net worth ships) or a typed URL.
export function NotBuilt() {
  return (
    <div className="lf-notbuilt">
      <EmptyState
        message="This page isn't built yet"
        reason="It arrives in a later milestone. Use the sidebar to reach a page that's ready."
      />
    </div>
  );
}
