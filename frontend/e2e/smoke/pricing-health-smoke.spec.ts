import { test, expect } from "@playwright/test";

// ⚠ DEV-ONLY smoke (see playwright.smoke.config.ts). Phase-3a scripted pre-pass for Pricing Health —
// drives the LIVE app + real backend on seeded demo, checks the POPULATED page (diagnostics +
// confidence + the banner↔page reconciliation + refresh/correct-source + no config controls +
// overflow), and captures console errors. NOT wired into `npm run check`/CI. Run (from frontend/):
//   npx playwright test --config e2e/smoke/playwright.smoke.config.ts pricing-health-smoke

const WIDTHS = [320, 375, 900, 1366];
const consoleErrors: string[] = [];

test.describe.serial("pricing health pre-pass (live)", () => {
  test("drive the populated /pricing-health + assert diagnostics, reconciliation, D-072, overflow, 0 errors", async ({ page }) => {
    page.on("console", (m) => m.type() === "error" && consoleErrors.push(`[console] ${m.text()}`));
    page.on("pageerror", (e) => consoleErrors.push(`[pageerror] ${e.message}`));

    // PART 0: clear the first-run gate SERVER-SIDE so the page (not the overlay) is tested.
    await page.request.put("http://127.0.0.1:8321/api/v1/settings", { data: { values: { first_run_complete: "1" } } });

    // PART 1: diagnostics populated + confidence card ------------------------------------------
    await page.goto("/#/pricing-health");
    await expect(page.getByRole("heading", { name: "Pricing Health", exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Portfolio confidence" })).toBeVisible();
    const rows = page.locator('[data-card="diagnostics"] .lf-table tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 15_000 });
    const rowCount = await rows.count();
    console.log("PART 1 — diagnostics rows:", rowCount);
    expect(rowCount, "per-holding diagnostics populated").toBeGreaterThan(0);
    // by-band table + status-count strip present (ND-6).
    await expect(page.locator(".ph__bandtable")).toBeVisible();
    expect(await page.locator('[data-card="confidence"] .ph__chip').count(), "status/band chips render").toBeGreaterThan(0);

    // PART 2: banner ↔ page stale-count RECONCILIATION (ND-1, LIVE) -----------------------------
    const pageStale = Number((await page.getByTestId("ph-stale-count").textContent()) ?? "-1");
    const summary = await (await page.request.get("http://127.0.0.1:8321/api/v1/portfolio/summary")).json();
    console.log("PART 2 — page is_stale count:", pageStale, "· summary.stale_count (banner source):", summary.stale_count);
    expect(pageStale, "page stale count reconciles with the StaleBanner source").toBe(summary.stale_count);

    // PART 3: D-072 — routing chain is READ-ONLY; NO provider-priority config on the page --------
    // Open a Details dialog and confirm the routing chain has no form controls (chips only).
    await page.getByRole("button", { name: /Actions for/ }).first().click();
    await page.getByText("Details", { exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Routing")).toBeVisible();
    await expect(dialog.getByText(/Priority chain \(read-only\)/)).toBeVisible();
    expect(await dialog.locator(".ph__chain select, .ph__chain input").count(), "routing chain is read-only (no controls)").toBe(0);
    await page.keyboard.press("Escape");
    // No provider-priority editing anywhere on the page (D-072). The only select is the correct-source
    // MasterSelect, which lives inside its own dialog (closed now) — so the base page has none.
    expect(await page.locator('[data-card="diagnostics"] select, [data-card="confidence"] select').count(), "no priority config controls").toBe(0);

    // PART 4: Correct-source dialog opens with a served MasterSelect (per-instrument correction) --
    await page.getByRole("button", { name: /Actions for/ }).first().click();
    await page.getByText("Correct source", { exact: true }).click();
    await expect(page.getByRole("dialog").getByText(/per-instrument correction/)).toBeVisible();
    await expect(page.getByRole("dialog").locator("select")).toBeVisible(); // MasterSelect
    await page.keyboard.press("Escape");

    // PART 5: identifier-duplicate banner — honest (shown only when count > 0) -------------------
    const dupCount = (await (await page.request.get("http://127.0.0.1:8321/api/v1/system/identifier-duplicates")).json()).count;
    const dupBannerCount = await page.locator(".ph__dupbanner").count();
    console.log("PART 5 — identifier duplicates:", dupCount, "· banner shown:", dupBannerCount);
    expect(dupBannerCount, "dup banner present iff duplicates exist").toBe(dupCount > 0 ? 1 : 0);

    // PART 6: progressive loading — every card resolved OUT of skeleton --------------------------
    await expect(page.locator(".lf-skeleton"), "no card stuck in skeleton").toHaveCount(0);

    // PART 7: NO horizontal overflow on the POPULATED page at every breakpoint × both themes ------
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      for (const w of WIDTHS) {
        await page.setViewportSize({ width: w, height: 900 });
        await page.waitForTimeout(120);
        const over = await page.evaluate(() => {
          const doc = document.documentElement;
          const content = document.querySelector(".lf-shell__content");
          return { doc: doc.scrollWidth - doc.clientWidth, content: content ? content.scrollWidth - content.clientWidth : 0 };
        });
        console.log(`PART 7 — overflow ${theme} ${w}px:`, JSON.stringify(over));
        expect(over.doc, `doc overflow ${theme} ${w}`).toBeLessThanOrEqual(1);
        expect(over.content, `content overflow ${theme} ${w}`).toBeLessThanOrEqual(1);
      }
    }

    console.log("\n===== CONSOLE ERRORS (" + consoleErrors.length + ") =====\n" + (consoleErrors.join("\n") || "(none)") + "\n===== END =====\n");
    expect(consoleErrors, "zero console errors on the populated page").toHaveLength(0);
  });
});
