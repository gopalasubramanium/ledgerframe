import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./Help.css";
import { Button, EmptyState, PageHeader, Segmented, Skeleton, TextInput } from "../components/ui";
import { helpContent, helpSearch } from "../api/help";
import type { HelpEntry, HelpResponse } from "../api/help";

// Help (System group, Settings template — DESIGN-SYSTEM §3 names Help explicitly). page-help §9-3.
//
// The page OWNS the knowledge base and NOTHING else: it describes what a page is FOR and what a
// term MEANS, and never restates a figure, a procedure, or a definition another page owns
// (P-1). It carries no money — by construction, so D-105 is N/A here (§2).
//
// §9-3 CRITERION — ONE CANONICAL ANCHOR PER TOPIC, no duplicate homes. That is why searching
// REPLACES the catalogue rather than rendering a second copy of matching entries above it: two
// renderings would mean two elements carrying `id="term-xirr-twr"`, and a deep link would land on
// whichever the DOM happened to put first. One entry, one anchor, always.
//
// §9-3 DEEP LINKS UNDER HASHROUTER. The route itself lives in the hash (`#/help`), so a second
// `#fragment` is not addressable the way it is on a path router and the browser performs NO native
// anchor scroll. The topic therefore travels as a QUERY param (`?topic=term-xirr-twr`) and the page
// scrolls to it in an effect — an honest mechanism rather than one that looks native and silently
// does nothing. Search state travels the same way (`?q=`), so any view is a shareable URL.

const ALL = "all";

/** Read `?q=` / `?topic=` out of the HASH route's own query string. */
function hashParams(search: string, hash: string): URLSearchParams {
  // Under HashRouter the query lives inside the hash (`#/help?q=x`); `location.search` is empty.
  // useLocation() already splits it, but fall back to parsing the raw hash for a first paint from
  // a pasted URL.
  if (search) return new URLSearchParams(search);
  const i = hash.indexOf("?");
  return new URLSearchParams(i >= 0 ? hash.slice(i) : "");
}

export function Help() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useMemo(
    () => hashParams(location.search, window.location.hash),
    [location.search],
  );
  const urlQuery = params.get("q") ?? "";
  const topic = params.get("topic");

  const [catalogue, setCatalogue] = useState<HelpResponse | null | undefined>(undefined);
  const [draft, setDraft] = useState(urlQuery);
  const [results, setResults] = useState<HelpEntry[] | null | undefined>(undefined);
  const [category, setCategory] = useState(ALL);
  const entryRefs = useRef<Record<string, HTMLElement | null>>({});

  // The catalogue loads once and stays — it is 47 authored entries, not a growing dataset.
  useEffect(() => {
    helpContent().then((r) => setCatalogue(r.ok ? r.data : null));
  }, []);

  // Search is SERVER-SIDE (`?q=`, ranked, max 6) — the page never re-ranks or filters the prose.
  useEffect(() => {
    if (!urlQuery) {
      setResults(undefined);
      return;
    }
    let live = true;
    setResults(undefined);
    helpSearch(urlQuery).then((r) => {
      if (live) setResults(r.ok ? r.data.entries : null);
    });
    return () => {
      live = false;
    };
  }, [urlQuery]);

  // Keep the box in step when the URL changes underneath us (back button, a pasted link).
  useEffect(() => setDraft(urlQuery), [urlQuery]);

  const setUrl = useCallback(
    (next: { q?: string; topic?: string }) => {
      const p = new URLSearchParams();
      if (next.q) p.set("q", next.q);
      if (next.topic) p.set("topic", next.topic);
      const qs = p.toString();
      navigate(qs ? `/help?${qs}` : "/help");
    },
    [navigate],
  );

  const searching = urlQuery.length > 0;
  const categories = useMemo(() => catalogue?.categories ?? [], [catalogue]);

  const shown = useMemo<HelpEntry[]>(() => {
    if (searching) return results ?? [];
    const all = catalogue?.entries ?? [];
    return category === ALL ? all : all.filter((e) => e.category === category);
  }, [searching, results, catalogue, category]);

  // Deep link: scroll the named topic into view once it is on screen. HashRouter gives us no
  // native anchor behaviour, so this effect IS the mechanism (§9-3).
  useEffect(() => {
    if (!topic) return;
    const el = entryRefs.current[topic];
    // Optional-call: jsdom has no layout engine and does not implement scrollIntoView, so an
    // unguarded call throws under unit test while working fine in a browser.
    el?.scrollIntoView?.({ block: "center", behavior: "auto" });
  }, [topic, shown]);

  const grouped = useMemo(() => {
    const order = categories.length ? categories : [];
    return order
      .map((c) => ({ category: c, entries: shown.filter((e) => e.category === c) }))
      .filter((g) => g.entries.length > 0);
  }, [categories, shown]);

  return (
    <div className="lf-page help">
      <PageHeader
        title="Help"
        subtitle="What each page is for, and what the words mean. Every figure stays on the page that owns it."
      />

      <div className="help__search">
        <TextInput
          aria-label="Search help"
          value={draft}
          onChange={setDraft}
          onEnter={() => setUrl({ q: draft.trim() })}
          placeholder="Search help — try “what is XIRR” or “how do I set a target allocation”"
        />
        <Button onClick={() => setUrl({ q: draft.trim() })}>Search</Button>
        {searching && (
          <Button onClick={() => setUrl({})}>
            Clear
          </Button>
        )}
      </div>

      {!searching && categories.length > 0 && (
        <div className="help__filter">
          <Segmented
            aria-label="Filter help by category"
            value={category}
            onChange={setCategory}
            options={[
              { value: ALL, label: "All" },
              ...categories.map((c) => ({ value: c, label: c })),
            ]}
          />
        </div>
      )}

      {catalogue === undefined && (
        <div className="lf-card">
          <Skeleton lines={6} />
        </div>
      )}

      {catalogue === null && (
        <div className="lf-card">
          <EmptyState
            message="Help is unavailable"
            reason="The help catalogue could not be loaded."
            action={<Button onClick={() => { setCatalogue(undefined); helpContent().then((r) => setCatalogue(r.ok ? r.data : null)); }}>Retry</Button>}
          />
        </div>
      )}

      {searching && results === undefined && (
        <div className="lf-card">
          <Skeleton lines={4} />
        </div>
      )}

      {searching && results !== undefined && shown.length === 0 && (
        <div className="lf-card">
          <EmptyState
            message={`No help entry matches “${urlQuery}”`}
            reason={
              results === null
                ? "The search could not be run."
                : "Try a different word — the catalogue covers each page and the terms it uses."
            }
          />
        </div>
      )}

      {catalogue && grouped.map((group) => (
        <section className="lf-card help__section" key={group.category}>
          <h2 className="lf-card__title">{group.category}</h2>
          <div className="lf-card__body">
            {group.entries.map((e) => (
              <article
                className={`help__entry${topic === e.id ? " is-target" : ""}`}
                key={e.id}
                id={e.id}
                ref={(el) => {
                  entryRefs.current[e.id] = el;
                }}
              >
                <h3 className="help__entrytitle">{e.title}</h3>
                <p className="help__body">{e.body}</p>
                {/* The triad rides Terms entries only, and is ABSENT (not null) elsewhere. */}
                {"what" in e && (
                  <dl className="help__triad">
                    <dt>What it is</dt>
                    <dd>{e.what}</dd>
                    <dt>Why it matters</dt>
                    <dd>{e.why}</dd>
                    <dt>What improves it</dt>
                    <dd>{e.improves}</dd>
                  </dl>
                )}
                <p className="help__link">
                  <Button onClick={() => setUrl({ q: urlQuery || undefined, topic: e.id })}>
                    Link to this topic
                  </Button>
                </p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
