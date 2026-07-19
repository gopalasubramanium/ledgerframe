import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./Help.css";
import { Button, EmptyState, PageHeader, Skeleton, TextInput } from "../components/ui";
import { helpContent } from "../api/help";
import type { HelpEntry, HelpResponse } from "../api/help";
import { HelpProse } from "./helpMarkup";

// Help (System group). page-help §9-3, REBUILT to §9-bis after the 0a rejection.
//
// The page OWNS the knowledge base and NOTHING else: it describes what a page is FOR and what a
// term MEANS, and never restates a figure, a procedure, or a definition another page owns (P-1).
// It carries no money — by construction, so D-105 is N/A for figures (§2); every OTHER state
// (empty, error, no-results) still ships a served string.
//
// WHAT THE 0a REJECTION CHANGED (§9-bis-0). The old page was a FILTERED FLAT STACK — one Segmented
// category filter over three stacked sections, prose in a 78ch column, and a search that only
// answered on submit. It passed every guard it had and was rejected BY LOOKING, because the
// landing is a CATALOGUE SURFACE: the user arrives to FIND a topic, not to read a document
// top-to-bottom. A narrow measure makes a catalogue longer to scan for no benefit.
//
// So the measure MOVED rather than being repealed (§9-bis-0): the page is full-width, and the 78ch
// reading cap now applies INSIDE an expanded entry body, where the user genuinely is reading prose.
// Scanning and reading are different jobs and the layout serves whichever is happening.
//
// ⚠ SUPERSEDED 2026-07-19 (§9-bis-11(b), owner). The 78ch cap is now RETIRED ENTIRELY: entry
// bodies use the FULL responsive width and carry TYPOGRAPHIC STRUCTURE instead — headings, bold,
// italic, lists, spacing — served in a CONSTRAINED MARKUP SUBSET (`app/services/help_markup.py`,
// rendered by `./helpMarkup`). Structure gives the eye its return points, which is the job the
// measure was doing, without stranding a narrow column inside a wide entry. The two paragraphs
// above are kept as the record of what was tried first.
//
// THREE SECTIONS, AND ONLY THREE (§9-bis-1): Orientation · Pages · Glossary. About is GONE from
// Help — it is a card in Settings → System now (§9-bis-6).
//
// §9-3 CRITERION — ONE CANONICAL ANCHOR PER TOPIC. Searching REPLACES the sections rather than
// rendering matches above them: two renderings would mean two elements carrying `id="term-xirr-twr"`
// and a deep link would land on whichever the DOM happened to put first. One entry, one anchor.
//
// §9-3 DEEP LINKS UNDER HASHROUTER. The route itself lives in the hash (`#/help`), so a second
// `#fragment` is not addressable and the browser performs NO native anchor scroll. The topic
// travels as a QUERY param (`?topic=`) and the page scrolls to it in an effect — an honest
// mechanism rather than one that looks native and silently does nothing.

const ORIENTATION = "Orientation";
const PAGES = "Pages";
const GLOSSARY = "Glossary";

/** Read `?q=` / `?topic=` out of the HASH route's own query string. */
function hashParams(search: string, hash: string): URLSearchParams {
  // Under HashRouter the query lives inside the hash (`#/help?q=x`); `location.search` is empty.
  // useLocation() already splits it, but fall back to parsing the raw hash for a first paint from
  // a pasted URL.
  if (search) return new URLSearchParams(search);
  const i = hash.indexOf("?");
  return new URLSearchParams(i >= 0 ? hash.slice(i) : "");
}

// --- Type-ahead ranking, CLIENT-SIDE (§9-bis-4) ----------------------------------------------- //
// The whole catalogue arrives in one read, so ranking per keystroke costs nothing and keeps working
// under no-egress. Pinned strictly to Help content — this never searches holdings or the market.
//
// The ranker mirrors the server's shape deliberately: question scaffolding does not score (it is in
// nearly every query and distinguishes nothing), and COVERAGE outranks tier weight, so an entry
// answering the whole question beats one answering a fragment of it prominently.
const STOPWORDS = new Set(
  ("what whats how why when where which who does did the this that these those and but for with " +
    "from into about are was were you your yours can could should would there here have has had " +
    "its not all any more most some such than then they them their").split(" "),
);

function terms(q: string): string[] {
  return (q.toLowerCase().match(/[a-z0-9]+/g) ?? []).filter(
    (t) => t.length > 1 && !STOPWORDS.has(t),
  );
}

/** Every authored string on an entry, so a match on an input, option or example counts too. */
function haystack(e: HelpEntry): { title: string; keys: string; rest: string } {
  const flat = (v: unknown): string =>
    Array.isArray(v) ? v.filter((x) => typeof x === "string").join(" ") : typeof v === "string" ? v : "";
  return {
    title: e.title.toLowerCase(),
    keys: (e.keywords ?? "").toLowerCase(),
    rest: [e.body, e.what, e.why, e.improves, e.example, e.interpret, e.inputs, e.options, e.outputs]
      .map(flat)
      .join(" ")
      .toLowerCase(),
  };
}

function rank(entries: HelpEntry[], query: string): HelpEntry[] {
  const ts = terms(query);
  if (!ts.length) return [];
  const scored: { e: HelpEntry; covered: number; tier: number }[] = [];
  for (const e of entries) {
    const { title, keys, rest } = haystack(e);
    const hay = `${title} ${keys} ${rest}`;
    const covered = ts.filter((t) => hay.includes(t)).length;
    if (!covered) continue;
    const tier =
      ts.filter((t) => title.includes(t)).length * 3 +
      ts.filter((t) => keys.includes(t)).length * 2 +
      ts.filter((t) => rest.includes(t)).length;
    scored.push({ e, covered, tier });
  }
  scored.sort((a, b) => b.covered - a.covered || b.tier - a.tier);
  return scored.map((s) => s.e);
}

// --- The expandable entry (PROPOSED DS pattern: content Accordion, §9-bis-8) -------------------- //
// Ruled at §9-bis-8: the tokens.css DECLINED is scoped to SIDEBAR NAVIGATION, whose concern is
// hiding navigable DESTINATIONS. A help entry is CONTENT DISCLOSURE — the title stays visible when
// collapsed and nothing navigable is hidden — so the concern is not triggered. Built on a native
// <button aria-expanded> pair rather than <details>/<summary>, because the open state has to be
// driven from the URL (`?topic=`) and <details> fights a controlled open state.
function Entry({
  entry,
  open,
  targeted,
  onToggle,
  onLink,
  onTopic,
  registerRef,
}: {
  entry: HelpEntry;
  open: boolean;
  targeted: boolean;
  onToggle: () => void;
  onLink: () => void;
  onTopic: (id: string) => void;
  registerRef: (el: HTMLElement | null) => void;
}) {
  const panelId = `${entry.id}-panel`;
  return (
    <article
      className={`help__entry${open ? " is-open" : ""}${targeted ? " is-target" : ""}`}
      id={entry.id}
      ref={registerRef}
    >
      <div className="help__entryhead">
        <button
          type="button"
          className="help__entrytoggle"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
        >
          <span className="help__chevron" aria-hidden="true" />
          <span className="help__entrytitle">{entry.title}</span>
          {entry.level && <span className="help__level">{entry.level}</span>}
        </button>
        {/* §9-bis-7, option (b): quiet until wanted. Revealed on hover/focus of the entry, and
            always reachable by keyboard — `.help__topiclink` is never `display:none`, so it stays
            in the tab order and a keyboard user is not shown a shorter page than a mouse user. */}
        {/* The visible word is "Link", not the title: repeating the title beside the title reads as
            a duplicate heading, and gave two controls in one row the same accessible name. The
            title rides the aria-label instead, so a screen-reader user hears WHICH topic the link
            copies without the page saying it twice. */}
        <button
          type="button"
          className="help__topiclink"
          onClick={onLink}
          title="Link to this topic"
          aria-label={`Link to this topic — ${entry.title}`}
        >
          Link
        </button>
      </div>

      <div className="help__panel" id={panelId} role="region" hidden={!open}>
        {/* §9-bis-11(b) — the body now uses the FULL responsive entry width; the 78ch cap of
            §9-bis-0 is retired (see Help.css). Structure, not a narrow column, is what makes a
            long entry readable — and the structure is SERVED, in a constrained subset the
            accuracy guards strip before checking, so formatting can never hide a claim. */}
        <div className="help__measure">
          <HelpProse text={entry.body} />

          {entry.links && (
            <p className="help__links">
              {entry.links.map((l) => (
                <button
                  key={l.topic}
                  type="button"
                  className="help__jump"
                  onClick={() => onTopic(l.topic)}
                >
                  {l.label}
                </button>
              ))}
            </p>
          )}

          {/* Section 2 — what the user fills in, may choose, sees, and how to read it. Every
              `outputs` item NAMES a figure and never states one: Help is a pointer, never a second
              home for a number (IA law). */}
          {entry.inputs && (
            <section className="help__block">
              <h4 className="help__blocktitle">What you fill in</h4>
              <ul className="help__list">
                {entry.inputs.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </section>
          )}
          {entry.options && (
            <section className="help__block">
              <h4 className="help__blocktitle">What you can choose</h4>
              <ul className="help__list">
                {entry.options.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </section>
          )}
          {entry.outputs && (
            <section className="help__block">
              <h4 className="help__blocktitle">What you see</h4>
              <ul className="help__list">
                {entry.outputs.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </section>
          )}
          {entry.interpret && (
            <section className="help__block">
              <h4 className="help__blocktitle">How to read it</h4>
              <HelpProse text={entry.interpret} />
            </section>
          )}

          {/* Section 3 — the glossary triad. Absent (not null) on entries that do not carry it. */}
          {"what" in entry && (
            <dl className="help__triad">
              <dt>What it is</dt>
              <dd><HelpProse text={entry.what ?? ''} /></dd>
              <dt>Why it matters</dt>
              <dd><HelpProse text={entry.why ?? ''} /></dd>
              <dt>What improves it</dt>
              <dd><HelpProse text={entry.improves ?? ''} /></dd>
            </dl>
          )}

          {/* §9-bis-3 — STATIC and marked. The marker is part of the served string, so it travels
              wherever the content goes; the chip repeats it visually rather than replacing it. */}
          {entry.example && (
            <section className="help__block help__example">
              <h4 className="help__blocktitle">
                Worked example <span className="help__samplechip">Illustrative sample</span>
              </h4>
              <HelpProse text={entry.example} />
            </section>
          )}
        </div>
      </div>
    </article>
  );
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
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const entryRefs = useRef<Record<string, HTMLElement | null>>({});

  const load = useCallback(() => {
    setCatalogue(undefined);
    helpContent().then((r) => setCatalogue(r.ok ? r.data : null));
  }, []);

  // The catalogue loads once and stays — it is authored entries, not a growing dataset. That is
  // also what makes the client-side type-ahead honest: there is nothing further to fetch.
  useEffect(() => { load(); }, [load]);

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

  const entries = useMemo(() => catalogue?.entries ?? [], [catalogue]);
  const query = draft.trim();
  const searching = query.length > 0;
  const results = useMemo(() => (searching ? rank(entries, query) : []), [searching, entries, query]);

  // A deep link opens the entry it names — landing on a collapsed title would be a link that
  // appears not to have worked.
  useEffect(() => {
    if (topic) setOpen((o) => ({ ...o, [topic]: true }));
  }, [topic]);

  // Deep link: scroll the named topic into view once it is on screen. HashRouter gives us no native
  // anchor behaviour, so this effect IS the mechanism (§9-3).
  useEffect(() => {
    if (!topic) return;
    const el = entryRefs.current[topic];
    // Optional-call: jsdom has no layout engine and does not implement scrollIntoView, so an
    // unguarded call throws under unit test while working fine in a browser.
    el?.scrollIntoView?.({ block: "center", behavior: "auto" });
  }, [topic, entries, searching]);

  const openTopic = useCallback(
    (id: string) => {
      setDraft("");
      setOpen((o) => ({ ...o, [id]: true }));
      setUrl({ topic: id });
    },
    [setUrl],
  );

  const section = useCallback(
    (name: string) => entries.filter((e) => e.category === name),
    [entries],
  );

  const renderEntry = (e: HelpEntry) => (
    <Entry
      key={e.id}
      entry={e}
      open={!!open[e.id]}
      targeted={topic === e.id}
      onToggle={() => setOpen((o) => ({ ...o, [e.id]: !o[e.id] }))}
      onLink={() => setUrl({ topic: e.id })}
      onTopic={openTopic}
      registerRef={(el) => { entryRefs.current[e.id] = el; }}
    />
  );

  return (
    <div className="lf-page help">
      <PageHeader
        title="Help"
        subtitle="Start with Orientation, look up a page, or find a term. Every figure stays on the page that owns it."
      />

      {/* Type-ahead: results appear AS YOU TYPE (§9-bis-4). No submit button — there is nothing to
          submit to. Escape and Clear both return to the catalogue. */}
      <div className="help__search">
        <TextInput
          aria-label="Search help"
          value={draft}
          onChange={setDraft}
          placeholder="Search help — try “XIRR”, “drift”, or “import”"
        />
        {searching && <Button onClick={() => setDraft("")}>Clear</Button>}
      </div>

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
            action={<Button onClick={load}>Retry</Button>}
          />
        </div>
      )}

      {/* SEARCHING — results replace the sections (one anchor per topic), grouped by section so a
          hit's kind is visible without reading it. */}
      {catalogue && searching && (
        results.length === 0 ? (
          <div className="lf-card">
            <EmptyState
              message={`No help entry matches “${query}”`}
              reason="Try a different word — Help covers each page and the terms it uses, and nothing else. It does not search your holdings or the market."
            />
          </div>
        ) : (
          <div className="help__results">
            <p className="help__resultcount" role="status">
              {results.length === 1 ? "1 entry" : `${results.length} entries`} matching “{query}”
            </p>
            {[ORIENTATION, PAGES, GLOSSARY].map((name) => {
              const hits = results.filter((e) => e.category === name);
              if (!hits.length) return null;
              return (
                <section className="lf-card help__section" key={name}>
                  <h2 className="lf-card__title">{name}</h2>
                  <div className="lf-card__body help__stack">{hits.map(renderEntry)}</div>
                </section>
              );
            })}
          </div>
        )
      )}

      {/* THE CATALOGUE — full width, minimal surface, high detail on expand. */}
      {catalogue && !searching && (
        <>
          <section className="lf-card help__section" aria-labelledby="help-orientation">
            <h2 className="lf-card__title" id="help-orientation">Orientation</h2>
            <p className="lf-card__lead">
              What the platform is for, and how the pages work together.
            </p>
            <div className="lf-card__body help__stack">{section(ORIENTATION).map(renderEntry)}</div>
          </section>

          <section className="lf-card help__section" aria-labelledby="help-pages">
            <h2 className="lf-card__title" id="help-pages">Pages</h2>
            <p className="lf-card__lead">
              One entry per page — what you fill in, what you can choose, what you see, and how to
              read it.
            </p>
            {/* PROPOSED DS pattern: topic CardGrid. Minimal surface, high detail on expand. */}
            <div className="lf-card__body help__grid">{section(PAGES).map(renderEntry)}</div>
          </section>

          <section className="lf-card help__section" aria-labelledby="help-glossary">
            <h2 className="lf-card__title" id="help-glossary">Glossary</h2>
            <p className="lf-card__lead">
              The words, from the basics upward. Each carries a worked example built from
              illustrative figures — never your own.
            </p>
            <div className="lf-card__body help__grid">{section(GLOSSARY).map(renderEntry)}</div>
          </section>
        </>
      )}
    </div>
  );
}
