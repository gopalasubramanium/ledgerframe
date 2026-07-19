import { test, expect } from "@playwright/test";
import { API } from "./smoke-target.mjs";

// ⚠ DEV-ONLY smoke (see playwright.smoke.config.ts). Phase-3a scripted pre-pass for the Settings
// page — drives the app + real backend named by smoke-target.mjs on the demo-seeded instance across all
// four D-069 tabs, both themes, all breakpoints: containment (no horizontal overflow), 0 console
// errors, and captures the §12st ratification-condition screenshots + the danger Reset control. NOT
// wired into `npm run check`/CI. Run (from frontend/):
//   npx playwright test --config e2e/smoke/playwright.smoke.config.ts settings-smoke
//
// It exercises the PIN set flow (§12st-1) to capture the enabled Reset + the D-103 fresh-PIN
// ConfirmDialog, but NEVER confirms a reset (demo data untouched). The harness driver restores the
// instance to PIN-free afterward (reset.py mechanism).
//
// §14st-1 (owner, Phase-3b walk 2026-07-18): a "Data feeds" tab — feed/provider config (market data
// provider, write-only API key, ND-6 feeds) lives there.
// §14st-2 (owner re-walk 2026-07-18): a SIXTH "AI" tab — the read-only served AI-config line MOVES out
// of System to its own AI tab; System loses it.
// §9-bis-11(c) (owner, 2026-07-19) — a SEVENTH "About" tab (D-069 amendment #3), REVERSING the
// §9-bis-6 ruling that had made About a card inside System. SEVEN tabs — General · Appearance ·
// Privacy · Data feeds · AI · System · About. System keeps the access/appliance controls (root helper, PIN, auto-lock, Allow LAN,
// Reset data); the "AI never persists" statement stays in Privacy.


// ⚠ SMOKE_API IS NOT OPTIONAL WHEN RUNNING ISOLATED (page-help §9-bis-11, Step F).
// `SMOKE_BASE` redirects only the BROWSER. Every `page.request.*` call below talks to the API
// DIRECTLY, bypassing the frontend proxy — so with the port hardcoded, an "isolated" pre-pass
// sends its writes to the OWNER'S LIVE BACKEND while the browser drives the spare-port instance.
// That happened during this milestone's re-run. Nothing was written, because the owner's instance
// was PIN-locked and answered 401 to everything — the isolation held by LUCK, not by design.
// Run isolated as:  SMOKE_BASE=http://127.0.0.1:5199 SMOKE_API=http://127.0.0.1:8399 npx playwright …
const OUT = "e2e/smoke/artifacts";
const WIDTHS = [320, 375, 900, 1366];
const THEMES = ["light", "dark"] as const;
const TABS = ["general", "appearance", "privacy", "data-feeds", "ai", "system", "about"] as const;
const TEST_PIN = "090909";
const consoleErrors: string[] = [];

test.describe.serial("settings pre-pass (live)", () => {
  test.beforeAll(() => {
    consoleErrors.length = 0;
  });

  test("containment + 0 console errors across seven tabs × both themes × breakpoints", async ({ page }) => {
    page.on("console", (m) => m.type() === "error" && consoleErrors.push(`[console] ${m.text()}`));
    page.on("pageerror", (e) => consoleErrors.push(`[pageerror] ${e.message}`));

    // Clean state: first-run complete so the PAGE is tested (not the overlay).
    await page.request.put(`${API}/settings`, { data: { values: { first_run_complete: "1" } } });

    for (const theme of THEMES) {
      await page.emulateMedia({ colorScheme: theme });
      for (const tab of TABS) {
        await page.goto(`/#/settings?tab=${tab}`);
        await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });
        // The tab strip is present and the requested tab is the live panel.
        await expect(page.getByRole("tabpanel")).toBeVisible();
        for (const w of WIDTHS) {
          await page.setViewportSize({ width: w, height: 900 });
          await page.waitForTimeout(120);
          const ov = await page.evaluate(() => {
            const doc = document.documentElement;
            const content = document.querySelector(".lf-shell__content");
            return { doc: doc.scrollWidth - doc.clientWidth, content: content ? content.scrollWidth - content.clientWidth : 0 };
          });
          expect(ov.doc, `doc overflow ${theme}/${tab}/${w}px`).toBeLessThanOrEqual(1);
          expect(ov.content, `content overflow ${theme}/${tab}/${w}px`).toBeLessThanOrEqual(1);
        }
      }
    }
    console.log(`SETTINGS smoke — console errors: ${consoleErrors.length}`, consoleErrors);
    expect(consoleErrors, "zero console/page errors across the settings pre-pass").toEqual([]);
  });

  // ⚑ THE FULL-WIDTH GEOMETRY GUARD (DS §3 standing rule, RATIFIED 2026-07-19; page-help §9-bis-14).
  //
  // "Prose in content surfaces is full-width responsive by default; a fixed reading measure exists
  // only where explicitly ratified, per surface."
  //
  // WHY THIS GUARD HAD TO BE WRITTEN AT ALL. A measure cap is invisible to every other gate in this
  // file. It overflows nothing, throws nothing, and photographs beautifully — the containment sweep
  // above ran 320/375/900/1366 × both themes over an About capped at 62ch and reported ZERO
  // problems, because it asks "does anything break?" and a cap breaks nothing. It just refuses half
  // the page. This is the second time the same drift shipped (§9-bis-9(b) retired a 78ch cap on
  // Help; About reintroduced it at 62ch three days later), and a defect class only a human can see
  // is closed by a guard, not by remembering.
  //
  // IT MEASURES THE REAL RENDERED BOX, NOT THE MECHANISM. Asserting `max-width: none` would be a
  // different and weaker test: `max-width` is one of many ways to be narrow (a width, a flex-basis,
  // an inline-size, a grid track, a centred margin), and the owner-visible defect is "the text stops
  // short of the page", not "a particular property is set". So it compares the prose container's
  // rendered width against its PARENT'S CONTENT BOX, at a WIDE viewport — the only place a cap is
  // visible at all. At 320px every one of these fills its parent whether or not a cap exists, which
  // is exactly why the narrow sweep could never have caught this.
  test("About prose is FULL-WIDTH — the DS §3 standing rule, measured at a wide viewport", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto(`/#/settings?tab=about`);
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".set__about")).toBeVisible();

    const geo = await page.evaluate(() => {
      const inner = (el: Element) => {
        const cs = getComputedStyle(el);
        // The PARENT'S CONTENT BOX — its border box less its own padding. Comparing against
        // `clientWidth` alone would silently forgive a parent that pads the prose into a column.
        return el.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      };
      const rows: { name: string; width: number; avail: number }[] = [];
      const push = (name: string, el: Element | null) => {
        if (!el || !el.parentElement) return;
        rows.push({ name, width: el.getBoundingClientRect().width, avail: inner(el.parentElement) });
      };
      push("set__about", document.querySelector(".set__about"));
      document.querySelectorAll(".set__beatbody").forEach((el, i) => push(`beatbody[${i}]`, el));
      push("tagline", document.querySelector(".set__tagline"));
      return rows;
    });

    expect(geo.length, "the About prose containers were not found — the guard measured nothing").toBeGreaterThan(4);
    for (const r of geo) {
      // 1px of tolerance for sub-pixel layout, and nothing more. A ratified measure would show up
      // here as a large, deliberate shortfall (62ch ≈ 600px inside a ~1250px box), never as 2px.
      expect(
        r.avail - r.width,
        `${r.name} stops ${Math.round(r.avail - r.width)}px short of its parent's content box ` +
          `(${Math.round(r.width)}px in ${Math.round(r.avail)}px) — DS §3 says prose is full-width ` +
          `responsive unless a measure is explicitly ratified for this surface`,
      ).toBeLessThanOrEqual(1);
    }
    await page.screenshot({ path: `${OUT}/about-fullwidth-1600.png`, fullPage: true });
  });

  test("tab screenshots — each of the seven tabs, both themes", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    for (const theme of THEMES) {
      await page.emulateMedia({ colorScheme: theme });
      for (const tab of TABS) {
        await page.goto(`/#/settings?tab=${tab}`);
        await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });
        await page.waitForTimeout(200);
        await page.screenshot({ path: `${OUT}/settings-${tab}-${theme}.png`, fullPage: true });
      }
    }
  });

  test("General serves long_term_days verbatim (D-105) + protected long-term copy (D-077)", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.goto(`/#/settings?tab=general`);
    const days = page.getByLabel("Long-term threshold in days");
    await expect(days).toHaveValue("365");
    // Neutral framing — no jurisdiction presets, not tax advice (D-077/Guarantee 4).
    await expect(page.getByText(/neutral organisation split/i)).toBeVisible();
  });

  test("Privacy — derived state statement VERBATIM + token empty state (§9-9)", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.goto(`/#/settings?tab=privacy`);
    await expect(page.getByLabel("No-egress mode")).toBeVisible();
    // Empty token register (usable from zero).
    await expect(page.getByText("No API tokens yet")).toBeVisible();
    await page.screenshot({ path: `${OUT}/settings-privacy-detail.png`, fullPage: true });
  });

  test("Data feeds §14st-1 — the write-only provider key (§12st-2) + the ND-6 feeds editor (§12st-3)", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(`/#/settings?tab=data-feeds`);
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });

    // §14st-1 — the market-data provider now lives on the Data feeds tab.
    await expect(page.getByLabel("Market data provider")).toBeVisible();
    // §12st-2 — the write-only key field never echoes a value (an honest "set, hidden" state).
    await expect(page.getByLabel("Provider API key (write-only)")).toBeVisible();
    await page.screenshot({ path: `${OUT}/settings-data-feeds.png`, fullPage: true });

    // §12st-3 — the ND-6 feeds editor Dialog (the ratified Accounts-dialog pattern) — on Data feeds now.
    await page.getByRole("button", { name: /Edit feeds/ }).click();
    await expect(page.getByRole("dialog", { name: "News feeds" })).toBeVisible();
    await page.screenshot({ path: `${OUT}/settings-feeds-dialog.png` });
    await page.getByRole("button", { name: "Cancel" }).click();
  });

  test("AI §14st-2 — the read-only served AI-config line MOVED here + the deferral note", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(`/#/settings?tab=ai`);
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });
    // §12st-4 / §14st-2 — the READ-ONLY served AI-config line now lives on its own AI tab.
    await expect(page.getByText(/^AI is (on|off)/)).toBeVisible();
    // The static deferral note — model management stays with AI-surfaces (D-067/D-068).
    await expect(page.getByText(/Model management lives with the AI surfaces/i)).toBeVisible();
    await page.screenshot({ path: `${OUT}/settings-ai.png`, fullPage: true });
  });

  test("System §12st + the danger Reset control (D-103) + the §9-10 degradation", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 900 });
    await page.emulateMedia({ colorScheme: "light" });
    // This harness assumes a RESET (PIN-free) demo-seeded instance, like every smoke here. If a prior
    // run left the test PIN set, clear it first (reset.py / null pin_hash) before re-running.
    await page.goto(`/#/settings?tab=system`);
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible({ timeout: 15_000 });
    const pinAlreadySet = await page.getByText("PIN: set").isVisible().catch(() => false);

    // §14st-2 — the AI-config line MOVED to the AI tab; System no longer carries it.
    await expect(page.getByText(/^AI is (on|off)/)).toHaveCount(0);
    // §14st-1 — provider/key MOVED to Data feeds; System no longer carries them.
    await expect(page.getByLabel("Provider API key (write-only)")).toHaveCount(0);
    // §9-10 — the root helper is absent on this instance → Allow LAN is disabled (not dead) with a note.
    // Allow LAN is an ACCESS control and STAYS in System (§14st-1).
    await expect(page.getByText(/optional root helper/i)).toBeVisible();
    await expect(page.getByLabel("Allow LAN access")).toBeDisabled();
    // §12st-1 — the PIN card + the danger Reset. On a no-PIN instance it is DISABLED (the honest
    // D-103 state: an irreversible wipe is impossible on an unprotected install).
    const reset = page.getByRole("button", { name: /Reset data/ });
    await expect(reset).toHaveClass(/lf-btn--danger/);
    if (!pinAlreadySet) {
      await expect(page.getByText("PIN: not set")).toBeVisible();
      await expect(reset).toBeDisabled();
      await page.screenshot({ path: `${OUT}/settings-system-degraded.png`, fullPage: true });
    }

    // §12st-1 — set a PIN if one isn't set, so the ENABLED danger Reset + the D-103 fresh-PIN
    // ConfirmDialog can be captured (never confirmed — demo data untouched).
    if (!pinAlreadySet) {
      await page.getByRole("button", { name: /Set PIN/ }).click();
      await page.getByLabel("New PIN").fill(TEST_PIN);
      await page.getByRole("dialog").getByRole("button", { name: /Set PIN/ }).click();
    }
    await expect(page.getByText("PIN: set")).toBeVisible({ timeout: 10_000 });
    await expect(reset).toBeEnabled();
    await page.screenshot({ path: `${OUT}/settings-system-pin-set.png`, fullPage: true });

    await reset.click();
    const confirm = page.getByRole("dialog", { name: "Reset all data?" });
    await expect(confirm).toBeVisible();
    await expect(confirm.getByText(/Enter your PIN/i)).toBeVisible(); // D-103 fresh purge-PIN
    await page.screenshot({ path: `${OUT}/settings-reset-confirm.png` });
    await confirm.getByRole("button", { name: "Cancel" }).click(); // NEVER confirm — data untouched
  });
});
