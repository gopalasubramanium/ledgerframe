import { test, expect } from "@playwright/test";

// §12po2-1 — REVIEWCARD ROW INTEGRITY (owner re-verify: 17 attention items broke the Net worth row
// and displaced the Portfolio card beside it).
//
// This is a COMPONENT defect, not a page's: ReviewCard rendered EVERY section it was handed, so its
// height was a function of the DATA. Any placement could therefore be torn apart by a bad week. The
// card is now CONTAINED at the component level (a capped, internally-scrolled list — the
// `--table-max-h` posture), so no placement can break its row no matter how many items arrive.
//
// The fixture is the point: 17 items. A guard fed 3 items proves nothing about the defect the owner
// saw — the assertion must reproduce the OWNER-SEEN geometry (§13).
const MANY = Array.from({ length: 17 }, (_, i) => ({
  area: "Policy",
  title: `Attention item number ${i + 1} with a fairly long title that wraps`,
  severity: i % 2 ? "Info" : "Review",
}));

const WIDTHS = [1366, 1440];

async function mockReview(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/portfolio/review*", (r) =>
    r.fulfill({ json: { as_of: "2026-07-14", count: MANY.length, items: MANY, disclaimer: "reporting only" } }),
  );
}

for (const width of WIDTHS) {
  test(`ReviewCard is contained and never breaks its row · net worth · ${width}px`, async ({ page }) => {
    await mockReview(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/#/net-worth");
    const card = page.locator('[data-card="review"] .lf-review');
    await expect(card).toBeVisible({ timeout: 15_000 });

    const report = await page.evaluate(() => {
      const cell = document.querySelector('[data-card="review"]') as HTMLElement;
      const card = cell.querySelector(".lf-review") as HTMLElement;
      const cardBox = card.getBoundingClientRect();
      // Siblings that share the card's grid ROW (they start at the same y).
      const sibs = [...document.querySelectorAll(".nw > *, .lf-page > *")] as HTMLElement[];
      const rowMates = sibs
        .filter((s) => s !== cell && Math.abs(s.getBoundingClientRect().top - cell.getBoundingClientRect().top) < 8)
        .map((s) => ({ cls: s.className, h: Math.round(s.getBoundingClientRect().height) }));
      return {
        cardH: Math.round(cardBox.height),
        cellH: Math.round(cell.getBoundingClientRect().height),
        overflowsCell: cardBox.bottom > cell.getBoundingClientRect().bottom + 1,
        rowMates,
      };
    });

    // The card may not grow past the cell the layout gave it — that is what displaced Portfolio.
    expect(report.overflowsCell, "the ReviewCard must not overflow its grid cell").toBe(false);
    // And it must not be unboundedly tall: 17 items rendered raw made it ~3x a normal card.
    expect(report.cardH, `card height with 17 items (${report.cardH}px)`).toBeLessThanOrEqual(560);
  });
}

test("ReviewCard offers the '+N more' route to the canonical page when it caps", async ({ page }) => {
  await mockReview(page);
  await page.setViewportSize({ width: 1366, height: 900 });
  await page.goto("/#/net-worth");
  const card = page.locator('[data-card="review"] .lf-review');
  await expect(card).toBeVisible({ timeout: 15_000 });
  // The full list lives ONLY on Review (P-1) — the card says how many it is not showing, and links.
  await expect(card.getByText(/\+\d+ more/)).toBeVisible();
});
