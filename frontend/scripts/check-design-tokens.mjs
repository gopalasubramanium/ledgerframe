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

console.log("✓ Design-token check: no raw hex/px outside the token layer.");
