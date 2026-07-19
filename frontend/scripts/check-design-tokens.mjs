#!/usr/bin/env node
/*
 * Design-token drift check (ADR-0002, design-system-build.md Phase A).
 *
 * The token layer is the SINGLE source of truth for every colour/size/space.
 * Components must resolve values through CSS custom properties — never a raw
 * hex colour or a hardcoded px size. This check fails (exit 1) if any component
 * source contains one, so CI enforces the rule mechanically.
 *
 * Allowed to hold raw values (the token layer only):
 *   - src/theme/tokens.css        (the token definitions)
 *   - src/theme/tokens/**         (split token files, if any)
 *
 * Tolerated everywhere (not "sizes in a component"):
 *   - px inside an @media (...) breakpoint prelude
 *   - unitless 0, and non-px units (rem/em/%/vh/vw/fr/ch/ms/s/deg)
 *   - hex inside comments (stripped before scanning)
 *
 * CHECK 2 — EVERY REFERENCED TOKEN MUST EXIST (page-help §9-bis-14 delta 2).
 *
 * Check 1 above enforces "resolve through a custom property, never a raw value". It says nothing
 * about whether the property you named is REAL — `var(--text-muted)` satisfies it perfectly, and
 * `--text-muted` does not exist. That is how 23 undefined-token references shipped across
 * Help.css and Settings.css: --text-muted, --text-sm, --text-xl, --text, --focus, --text-md,
 * --text-xs.
 *
 * A `var()` with no fallback and no definition is INVALID AT COMPUTED-VALUE TIME. The declaration
 * is DROPPED and the property inherits — silently:
 *   - `color: var(--text-muted)`  → prose meant to be muted rendered at full primary contrast.
 *   - `font-size: var(--text-sm)` → text rendered at its parent's size.
 *   - `outline: var(--focus-width) solid var(--focus)` → the WHOLE shorthand is invalid, so Help's
 *     accordion toggle, topic link and jump link had NO keyboard focus ring at all. An
 *     accessibility defect, which is what proves the class is not cosmetic.
 *
 * Nothing caught it for weeks: unit suites assert text and structure (jsdom does not even load
 * these stylesheets), and the Playwright pre-passes assert containment and console errors — a
 * dropped declaration overflows nothing and logs nothing. `var(--x, fallback)` is deliberate and
 * is NOT flagged.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(root, "src");

const ALLOW_FILE = new Set(["src/theme/tokens.css"]);
const ALLOW_DIR = "src/theme/tokens";

const SCAN_EXT = new Set([".css", ".ts", ".tsx"]);
const SKIP_SUFFIX = [".test.ts", ".test.tsx"];
const SKIP_DIR = new Set(["test"]);

const HEX = /#[0-9a-fA-F]{3,8}\b/g;
// A px length: a number immediately followed by px, not part of an identifier.
const PX = /(?<![\w.#])-?\d*\.?\d+px\b/g;

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (SKIP_DIR.has(entry)) continue;
      out.push(...walk(full));
    } else {
      out.push(full);
    }
  }
  return out;
}

function stripNoise(src, ext) {
  let s = src;
  // Block comments (CSS + JS/TS).
  s = s.replace(/\/\*[\s\S]*?\*\//g, "");
  // Line comments (JS/TS), preserving protocol-relative `://`.
  if (ext !== ".css") s = s.replace(/(^|[^:])\/\/[^\n]*/g, "$1");
  // @media / @container breakpoint preludes may carry px legitimately.
  s = s.replace(/@(?:media|container)[^{]*\{/g, "{");
  return s;
}

const findings = [];

for (const file of walk(SRC)) {
  const rel = relative(root, file);
  const ext = file.slice(file.lastIndexOf("."));
  if (!SCAN_EXT.has(ext)) continue;
  if (SKIP_SUFFIX.some((s) => file.endsWith(s))) continue;
  if (ALLOW_FILE.has(rel) || rel.startsWith(ALLOW_DIR)) continue;

  const raw = readFileSync(file, "utf8");
  const cleaned = stripNoise(raw, ext);
  const lines = cleaned.split("\n");

  lines.forEach((line, i) => {
    for (const [re, label] of [
      [HEX, "raw hex colour"],
      [PX, "hardcoded px size"],
    ]) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(line)) !== null) {
        findings.push({ rel, line: i + 1, label, text: m[0] });
      }
    }
  });
}

// --- CHECK 2: every var(--x) referenced without a fallback is actually defined ----------------
// Custom properties supplied at runtime from TSX (`style={{ "--tx": … }}`) are legitimately absent
// from the CSS. They are ENUMERATED rather than pattern-matched, so adding one is a deliberate act
// a reviewer sees — not something a regex quietly starts forgiving.
const RUNTIME_SET = new Set([
  "--tx", "--ty", "--tw", "--th", // Treemap tile geometry (Treemap.tsx)
  "--bar", "--swatch",            // KitchenSink specimen boards
  "--toast-ms",                   // Toast countdown duration (Toast.tsx)
]);

const cssFiles = walk(SRC).filter((f) => f.endsWith(".css"));
const defined = new Set();
for (const f of cssFiles) {
  for (const m of readFileSync(f, "utf8").matchAll(/^\s*(--[A-Za-z0-9-]+)\s*:/gm)) defined.add(m[1]);
}
// If the token layer ever stops being parsed this check would "pass" by finding nothing to
// complain about. Pin a token that must exist so a blind guard fails loudly instead of quietly.
if (!defined.has("--text-primary")) {
  console.error("\n✗ Token check is BLIND: the token layer was not parsed (no --text-primary).\n");
  process.exit(1);
}

const undef = [];
for (const f of cssFiles) {
  const src = readFileSync(f, "utf8");
  for (const m of src.matchAll(/var\(\s*(--[A-Za-z0-9-]+)\s*\)/g)) {
    if (defined.has(m[1]) || RUNTIME_SET.has(m[1])) continue;
    undef.push({ rel: relative(root, f), line: src.slice(0, m.index).split("\n").length, name: m[1] });
  }
}

if (undef.length > 0) {
  console.error(
    `\n✗ Undefined design tokens: ${undef.length} reference(s) to a custom property that does not exist.\n` +
      `  Each is INVALID AT COMPUTED-VALUE TIME — the declaration is dropped and the property\n` +
      `  inherits, silently. Inside an outline/border/font shorthand it kills the WHOLE\n` +
      `  declaration (this is how Help shipped with no focus ring).\n` +
      `  Use a real token from src/theme/tokens.css, or give the var an explicit fallback.\n`,
  );
  for (const u of undef) console.error(`  ${u.rel}:${u.line}  var(${u.name})`);
  console.error("");
  process.exit(1);
}

if (findings.length > 0) {
  console.error(
    `\n✗ Design-token drift: ${findings.length} raw value(s) outside the token layer.\n` +
      `  Every colour/size in a component must resolve to a token variable ` +
      `(src/theme/tokens.css). See ADR-0002.\n`,
  );
  for (const f of findings) {
    console.error(`  ${f.rel}:${f.line}  ${f.label}: ${f.text}`);
  }
  console.error("");
  process.exit(1);
}

console.log(
  `✓ Design-token check: no raw hex/px outside the token layer; ` +
    `all ${defined.size} referenced tokens defined.`,
);
