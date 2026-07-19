// SPDX-License-Identifier: AGPL-3.0-or-later
// ⚠ DEV-ONLY capture harness — NOT a test, NEVER wired into `npm run check` or CI.
// Renders the Reports Pack print artifact (GET /reports/pack, D-038) on the reset demo seed
// (entities: Household · Rajan Family Trust · Meera Iyer) and captures the Phase-0a
// PRINT-GEOMETRY specimen (reports-pack §7a): on-screen at 1440, and a REAL paginated print
// PDF via Chromium's page.pdf() (which honours @media print + break-before + the running header).
//
// Prereq: the SMOKE_API backend must be serving /reports/pack against the 3-entity
// demo seed. Run from repo root:
//   node frontend/e2e/smoke/capture-pack-specimen.mjs
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { API, API_ORIGIN } from "./smoke-target.mjs";

const URL = `${API_ORIGIN}/reports/pack`;
const OUT = "frontend/e2e/smoke/artifacts";
mkdirSync(OUT, { recursive: true });

const sectionByHeading = (page, name) =>
  page.locator("section.pack-section", { has: page.getByRole("heading", { level: 2, name }) });

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const res = await page.goto(URL, { waitUntil: "networkidle" });
  if (res.status() !== 200) throw new Error(`GET /reports/pack → ${res.status()}`);

  // ---- on-screen captures at 1440 (screen media) ----
  await page.screenshot({ path: `${OUT}/pack-screen-top-1440.png` });
  await sectionByHeading(page, "Cash flow").screenshot({ path: `${OUT}/pack-screen-consolidated-cashflow-1440.png` });
  // The per-entity boundary + the thin entity's empty-section notes (Meera Iyer, 0 accounts).
  await sectionByHeading(page, "Per-entity — Meera Iyer").screenshot({ path: `${OUT}/pack-screen-empty-entity-meera-1440.png` });
  await sectionByHeading(page, "Per-entity — Household").screenshot({ path: `${OUT}/pack-screen-per-entity-household-1440.png` });

  // ---- print-emulation on-screen (light palette + running header visible) ----
  await page.emulateMedia({ media: "print" });
  await page.screenshot({ path: `${OUT}/pack-print-emulated-top-1440.png` });

  // ---- REAL paginated print PDF (the faithful print-geometry capture) ----
  await page.pdf({
    path: `${OUT}/pack-print.pdf`,
    format: "A4",
    printBackground: true,
    margin: { top: "14mm", bottom: "14mm", left: "12mm", right: "12mm" },
  });

  console.log("captured: pack-screen-top / consolidated-cashflow / empty-entity-meera / per-entity-household / print-emulated-top / pack-print.pdf");
} finally {
  await browser.close();
}
