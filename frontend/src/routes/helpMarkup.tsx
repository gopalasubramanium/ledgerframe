// SPDX-License-Identifier: AGPL-3.0-or-later
//
// Renderer for the CONSTRAINED SERVED MARKUP MODEL (page-help §9-bis-11(b)).
// The authoritative definition of the subset is `app/services/help_markup.py`; this file must
// stay in step with it, and `tests/unit/test_help_markup.py` pins the pairing (on the Python
// side, because that is the side that can read both files).
//
// NO `dangerouslySetInnerHTML`, ANYWHERE. That is the whole safety argument and it is structural,
// not a policy: this parser emits React ELEMENTS, so there is no code path along which a served
// string could become markup. A sanitiser tries to enumerate badness and loses eventually; a
// builder that cannot express HTML has nothing to enumerate.
//
// WHY THIS IS ROUTE-LOCAL AND NOT A DS PRIMITIVE. It renders through DS typography tokens, but it
// is used on exactly one surface. The house rule is to extract at the THIRD recurrence (the
// `Segmented` / `StatusChip` precedent) — extracting at the first would put a component in the
// library on speculation. If a second and third surface ever need served prose, this is the thing
// to lift.

import type { ReactNode } from 'react';

const HEADING = '## ';
const LIST = '- ';

type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'para'; text: string }
  | { kind: 'list'; items: string[] };

/** Split served prose into blocks. Unknown line shapes are PARAGRAPH TEXT, never dropped —
 *  silently discarding a line the author wrote is the one failure mode a content renderer must
 *  not have. */
function parseBlocks(src: string): Block[] {
  const blocks: Block[] = [];
  let para: string[] = [];
  let list: string[] = [];

  const flushPara = () => {
    if (para.length) blocks.push({ kind: 'para', text: para.join(' ') });
    para = [];
  };
  const flushList = () => {
    if (list.length) blocks.push({ kind: 'list', items: list });
    list = [];
  };
  const flush = () => {
    flushPara();
    flushList();
  };

  for (const raw of (src ?? '').split('\n')) {
    const line = raw.trim();
    if (!line) {
      flush();
    } else if (line.startsWith(HEADING)) {
      flush();
      blocks.push({ kind: 'heading', text: line.slice(HEADING.length) });
    } else if (line.startsWith(LIST)) {
      flushPara();
      list.push(line.slice(LIST.length));
    } else {
      flushList();
      para.push(line);
    }
  }
  flush();
  return blocks;
}

/** Inline emphasis → `<strong>` / `<em>`. Returns an array of nodes, never a string of HTML. */
function renderInline(text: string, keyPrefix = 'i'): ReactNode[] {
  const out: ReactNode[] = [];
  // One pass, bold before italic, so `**a**` is never mistaken for two italic markers.
  const pattern = /\*\*(.+?)\*\*|(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)/gs;
  let last = 0;
  let m: RegExpExecArray | null;
  let n = 0;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] !== undefined) {
      out.push(<strong key={`${keyPrefix}-b${n}`}>{m[1]}</strong>);
    } else {
      out.push(<em key={`${keyPrefix}-i${n}`}>{m[2]}</em>);
    }
    last = m.index + m[0].length;
    n += 1;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/**
 * Served prose, rendered with its typographic structure.
 *
 * Emits a `<div>` wrapper, never a `<p>`: this renders inside a `<dd>` (the glossary triad) as
 * well as standalone, and a `<p>` containing block children is invalid HTML that browsers
 * silently restructure — which would break the DS spacing in a way no test asserting text
 * content would ever notice.
 */
export function HelpProse({ text, className }: { text: string; className?: string }) {
  const blocks = parseBlocks(text);
  return (
    <div className={`help__prose${className ? ` ${className}` : ''}`}>
      {blocks.map((b, i) => {
        if (b.kind === 'heading') {
          return (
            <h5 className="help__prosehead" key={`h${i}`}>
              {renderInline(b.text, `h${i}`)}
            </h5>
          );
        }
        if (b.kind === 'list') {
          return (
            <ul className="help__proselist" key={`l${i}`}>
              {b.items.map((item, j) => (
                <li key={`l${i}-${j}`}>{renderInline(item, `l${i}-${j}`)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p className="help__prosepara" key={`p${i}`}>
            {renderInline(b.text, `p${i}`)}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Inline-only served markup, for text that ALREADY sits in its own element.
 *
 * `inputs` / `options` / `outputs` render as `<li>` rows the page owns; they carry emphasis on the
 * affordance label but no block structure, so wrapping them in {@link HelpProse} would nest a
 * paragraph inside a list item and add block spacing to a one-line row. Caught by the 3a pre-pass,
 * which found those 54 labels rendering as literal `**Quote source**` — the strings were formatted
 * and the renderer was only wired to the prose fields.
 */
export function HelpInline({ text }: { text: string }) {
  return <>{renderInline(text)}</>;
}
