import { test, expect } from "@playwright/test";

// §12cf1-1 — THE TABLE HEADER PAINTS EDGE-TO-EDGE (platform-wide component defect).
//
// The header fill stopped short of the right border: `scrollbar-gutter: stable` reserves a strip that
// the <table> does not cover, so the top-right corner showed the CARD through the gap — filled on the
// left (where the header's own background follows the radius), empty on the right.
//
// There WAS a fix attempt — a box-shadow on `.lf-table__th:last-child` spanning `--scrollbar-size`.
// It can never work: the shadow is painted INTO the scrollbar gutter of the very container that
// CLIPS it (`.lf-table__scroll { overflow: auto }`). Measuring said "the shadow is there"; the
// rendered pixels said otherwise. The pixels win — so this guard asserts PIXELS.
//
// It samples the header band at its middle and at the far right (inside the gutter). Both must be
// the same colour. One component, no page-local patches — so it runs on several pages.
// ⚠ MEASURED IN THE GALLERY. The CI e2e suite runs with NO BACKEND, so the product pages render
// EMPTY tables — there is no header to sample and the guard timed out (green against a dev backend,
// red in the suite). A specimen only proves what it exercises, and a component guard must not depend
// on a page having data: the gallery's Cash flow specimen always has rows.
const PAGES = [
  { name: "kitchen-sink · cash flow specimen", hash: "#/kitchen-sink" },
];

for (const theme of ["light", "dark"] as const) {
  for (const p of PAGES) {
    test(`table header fills its corner · ${p.name} · ${theme}`, async ({ page }) => {
      // The specimen frame is 1440 wide — the viewport must be wider, or its right edge (the very
      // thing under test) sits outside the screenshot. (The home-grid guard does the same.)
      await page.setViewportSize({ width: 1600, height: 1000 });
      await page.goto(`/${p.hash}`);
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      const wrap = page.locator(".ks__viewport--scroll .lf-table-wrap").first();
      await wrap.waitFor({ state: "visible", timeout: 15_000 });
      await wrap.scrollIntoViewIfNeeded();   // the specimen sits below the fold in the gallery
      // ⚠ SETTLE BEFORE SAMPLING PIXELS. A pixel guard that shoots while the table is still filling
      // (or before the theme attribute has repainted) compares two frames of a moving picture — it
      // went green alone and red under parallel load, which is a racing GUARD, not a racing product.
      await wrap.locator("tbody tr").first().waitFor({ state: "visible", timeout: 15_000 });
      await page.waitForFunction((t) => document.documentElement.getAttribute("data-theme") === t, theme);
      await page.waitForTimeout(250);
      const box = (await wrap.boundingBox())!;

      // Sample the header band in its MIDDLE and inside the reserved GUTTER — both well clear of the
      // rounded border, whose antialiasing would otherwise bleed into the patch and make the guard
      // flake (it did: the first version sat 7px from the edge and failed ~1 run in 3).
      // The gutter is `--scrollbar-size` (10px) wide, just inside the 1px border.
      const y = box.y + 14;                       // mid-header, clear of the top border/radius
      const mid = await page.screenshot({ clip: { x: box.x + box.width / 2, y, width: 3, height: 3 } });
      const right = await page.screenshot({ clip: { x: box.x + box.width - 8, y, width: 3, height: 3 } });

      expect(
        right.equals(mid),
        "the header band must reach the right border — the gutter strip may not show the card through it",
      ).toBe(true);
    });
  }
}
