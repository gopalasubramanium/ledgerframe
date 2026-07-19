#!/usr/bin/env node
/*
 * PRIMITIVE-OWNERSHIP CHECK (CLAUDE.md hard rule; DESIGN-SYSTEM §6).
 *
 * "Every user input uses a component from src/components/ui/. Raw <input>,
 * <select>, or ad-hoc styling is forbidden."
 *
 * That rule has been in CLAUDE.md and in DESIGN-SYSTEM §6 since the design-system
 * milestone, and until this file existed it was enforced by NOBODY. The Acceptance
 * Gate shipped a hand-rolled `<input type="checkbox">` (page-legal §11-E2) and
 * passed a full `npm run check`, a green 1713-test suite, a Playwright pre-pass and
 * a written review — because every one of those asks whether the thing WORKS, and
 * none of them asks whether it is the SANCTIONED CONTROL. A hard rule without a
 * guard is a request.
 *
 * WHAT THIS CHECKS: no raw `<input type="checkbox">` anywhere in the app. The
 * checkbox is the type that had no primitive, so it is the type that drifted; the
 * scope is deliberately the one that was violated rather than a speculative sweep
 * over every input type (the other raw `<input>`s in this tree are all INSIDE their
 * own primitives — TextInput, MoneyInput, DateInput, FileInput, LockScreen's PIN —
 * which is exactly where a raw element is supposed to live).
 *
 * THE ALLOW-LIST IS ONE FILE, and that is the point of the rule: the primitive owns
 * the native element so every consumer inherits its label association, its keyboard
 * behaviour, its focus ring and its disabled state, instead of re-deriving them and
 * getting one of them wrong.
 *
 * Extending this to `<select>` / other input types is a deliberate act with a
 * ratified primitive behind it, not a regex someone widens on a hunch.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(root, "src");

// The primitive that OWNS the native checkbox. Nothing else may hold one.
const OWNER = "src/components/ui/Checkbox.tsx";

const SCAN_EXT = new Set([".ts", ".tsx"]);
const SKIP_SUFFIX = [".test.ts", ".test.tsx"];

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

// Comments are stripped: a comment that mentions the forbidden markup (this file's
// own header, or FileInput's "no raw <input>" note) is documentation, not a control.
// NEWLINES ARE PRESERVED. The first version of this guard deleted them and reported
// AcceptanceGate.tsx:87 for a violation on line 90 — a guard that names the wrong line
// sends the reader to innocent code and teaches them to distrust it.
function stripComments(src) {
  const blank = (m) => "\n".repeat((m.match(/\n/g) ?? []).length);
  return src.replace(/\/\*[\s\S]*?\*\//g, blank).replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

// `<input ... type="checkbox" ...>` across line breaks, which is how it is actually
// written in this codebase — the attribute sat three lines below the tag in the gate.
const RAW_CHECKBOX = /<input\b[^>]*\btype\s*=\s*["{']?checkbox/g;

const findings = [];
let scanned = 0;

for (const file of walk(SRC)) {
  const rel = relative(root, file);
  const ext = file.slice(file.lastIndexOf("."));
  if (!SCAN_EXT.has(ext)) continue;
  if (SKIP_SUFFIX.some((s) => file.endsWith(s))) continue;
  if (rel === OWNER) continue;

  scanned++;
  const src = stripComments(readFileSync(file, "utf8"));
  for (const m of src.matchAll(RAW_CHECKBOX)) {
    findings.push({ rel, line: src.slice(0, m.index).split("\n").length });
  }
}

// If the primitive ever disappears, this guard would "pass" by having nothing left to
// protect. Pin it, so a blind guard fails loudly instead of quietly (the lesson from
// the token check's --text-primary pin).
try {
  const owner = readFileSync(join(root, OWNER), "utf8");
  if (!/type\s*=\s*"checkbox"/.test(owner)) throw new Error("no native checkbox in the primitive");
} catch (e) {
  console.error(
    `\n✗ Primitive check is BLIND: ${OWNER} is missing or no longer owns a native\n` +
      `  checkbox (${e.message}). The guard would pass by protecting nothing.\n`,
  );
  process.exit(1);
}

if (findings.length > 0) {
  console.error(
    `\n✗ Raw checkbox input: ${findings.length} occurrence(s) outside the Checkbox primitive.\n` +
      `  CLAUDE.md hard rule / DESIGN-SYSTEM §6 — every user input uses a component from\n` +
      `  src/components/ui/. Use <Checkbox> so label association, keyboard, focus ring and\n` +
      `  disabled state come from one place instead of being re-derived per surface.\n`,
  );
  for (const f of findings) console.error(`  ${f.rel}:${f.line}`);
  console.error("");
  process.exit(1);
}

console.log(
  `✓ Primitive check: no raw checkbox input in ${scanned} source file(s) ` +
    `(the Checkbox primitive owns the native element).`,
);
