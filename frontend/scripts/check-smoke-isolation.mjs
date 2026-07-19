#!/usr/bin/env node
// SMOKE ISOLATION GUARD — smoke specs never hardcode the owner's live ports.
//
// The near-miss (2026-07-19, page-help §9-bis-11 Step F): 20 smoke specs hardcoded 127.0.0.1:8321.
// `SMOKE_BASE` redirects only the browser, so an "isolated" pre-pass drove the spare-port frontend
// while its `page.request.*` writes went to the OWNER'S LIVE BACKEND. One Settings spec would have
// SET A PIN on an unlocked live install. It held by luck (a 401), not by design.
//
// This guard makes the fix grep-provable: no live port literal may appear in any smoke driver.
// Targets are resolved ONLY through e2e/smoke/smoke-target.ts, which is itself fail-closed.
//
//   node scripts/check-smoke-isolation.mjs

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const SMOKE_DIR = join(ROOT, "e2e/smoke");

// The owner's live dev stack. These literals are what must never appear.
const LIVE_PORTS = ["8321", "5173"];

// The ONLY files permitted to name a live port: the fail-closed resolver (it must know what to
// refuse), this guard, and the owner's pristine .env snapshot used by reset.py.
const ALLOWLIST = new Set(["smoke-target.mjs", ".env-snapshot"]);

const DRIVER_RE = /\.(spec\.ts|mjs|ts)$/;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      out.push(...walk(p));
    } else if (DRIVER_RE.test(name) && !ALLOWLIST.has(name)) {
      out.push(p);
    }
  }
  return out;
}

const violations = [];
for (const file of walk(SMOKE_DIR)) {
  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, i) => {
    for (const port of LIVE_PORTS) {
      if (line.includes(`:${port}`)) {
        violations.push({ file: relative(ROOT, file), line: i + 1, port, text: line.trim() });
      }
    }
  });
}

if (violations.length > 0) {
  console.error("\n✗ SMOKE ISOLATION — hardcoded live port(s) in smoke drivers:\n");
  for (const v of violations) {
    console.error(`  ${v.file}:${v.line}  (live port ${v.port})`);
    console.error(`    ${v.text.slice(0, 120)}`);
  }
  console.error(
    `\n  ${violations.length} violation(s). A smoke driver must never name the owner's live stack —\n` +
      "  import { API, BASE } from './smoke-target' (fail-closed) instead. Comments included: a\n" +
      "  documented port becomes a copy-pasted port.\n",
  );
  process.exit(1);
}

console.log(`✓ smoke isolation — no hardcoded live ports across ${walk(SMOKE_DIR).length} smoke driver(s)`);
