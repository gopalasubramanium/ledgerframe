import { test, expect } from "@playwright/test";

// TILE INTEGRITY (page-home §12ho1-4, strengthened §12ho2-1).
//
// Born from the defect that killed the first Home build: `SummaryHead whole` carried both
// `lf-summaryhead` and `lf-summarylink`, and `.lf-summarylink { position: absolute }` beat
// `.lf-summaryhead { position: relative }` on source order — so every whole-header was torn out of
// its tile and piled in the page's corner. The §12ho1-2 checks COUNTED affordances (8 ↗, 8
// aria-labels, one focusable) — all still true of a header lying in a heap in the wrong corner.
//
// §12ho2-1 — THE GUARD WAS STILL LYING. It ran at ONE width (1366) and compared only whole TILE
// boxes. At 375px the page was visibly garbage — the Today's change figure printed straight through
// the Performance caption, the donut bled through the movers tile — and this suite reported ZERO
// overlaps, because the tiles' boxes did not intersect even while their CONTENTS did. So it now:
//   (a) runs at EVERY breakpoint, phones included (320/375/768/1366/1440);
//   (b) compares the rendered TEXT, not the containers — overlapping text is the actual symptom;
//   (c) still checks the headers' geometry.
// A guard that only looks where the bug was last time is not a guard.

const WIDTHS = [320, 375, 768, 1366, 1440];

const ROUTES = [
  // No backend here, so a live page may honestly render empty/error states instead of its cards.
  // `strict` marks routes that must show the affordance regardless: the kitchen-sink specimens are
  // static, so they can never render zero — and they alone would have caught the original defect.
  // `scope` bounds the TEXT-OVERLAP check. On a product page it is the whole page — nothing may print
  // through anything. The gallery is different: it deliberately renders CHROME specimens (a fixed
  // Sidebar, the banners) stacked over gallery prose, so a page-wide check there measures the gallery's
  // nature, not a defect. It is scoped to the Home specimen, which is what we are actually guarding.
  { name: "kitchen-sink (specimens)", hash: "#/kitchen-sink", strict: true, scope: ".ks__viewport" },
  { name: "home", hash: "#/", strict: false, scope: "body" },
  { name: "net worth", hash: "#/net-worth", strict: false, scope: "body" },
  { name: "portfolio", hash: "#/portfolio", strict: false, scope: "body" },
  { name: "instrument detail", hash: "#/instrument/AAPL", strict: false, scope: "body" },
];

/** Runs in the page: the geometry every tiled layout must satisfy, at whatever width is set. */
function auditPage(scope: string) {
  const heads = [...document.querySelectorAll<HTMLElement>(".lf-summaryhead")];
  const escaped: string[] = [];
  const outside: string[] = [];

  for (const head of heads) {
    const name = (head.textContent ?? "").trim().slice(0, 32);
    // A header is never ripped out of the flow…
    if (getComputedStyle(head).position === "absolute") escaped.push(name);
    // …and it renders within the bounds of the card it heads.
    const tile = head.closest(".lf-card, .hm3__cell");
    if (tile) {
      const h = head.getBoundingClientRect();
      const t = tile.getBoundingClientRect();
      if (h.top < t.top - 2 || h.left < t.left - 2 || h.right > t.right + 2) outside.push(name);
    }
  }

  // The ↗ glyph IS absolutely positioned by design — so it is only correct if its offset parent is
  // the header that owns it.
  for (const link of document.querySelectorAll<HTMLElement>("[data-summarylink]")) {
    const owner = link.closest(".lf-summaryhead, .lf-card, .hm3__cell");
    if (!owner) continue;
    const l = link.getBoundingClientRect();
    const o = owner.getBoundingClientRect();
    if (l.top < o.top - 2 || l.right > o.right + 2 || l.left < o.left - 2 || l.bottom > o.bottom + 2) {
      outside.push(`↗ ${link.getAttribute("aria-label") ?? "?"}`);
    }
  }

  // CONTAINMENT (§12ho3-3) — a card's content stays INSIDE the card. The stale badge on a quote card
  // was hanging out past its right border: the card's box and the badge's box simply did not agree,
  // and nothing checked that they must. Every element that renders inside a card box is bounded by it.
  // (A tile may scroll its own overflow — that is what `overflow` is for — so a scroll container's
  // children are measured against the container's SCROLL extent, not its clipped viewport.)
  const escapees: string[] = [];
  for (const card of document.querySelectorAll<HTMLElement>(".lf-quote, .lf-card, .hm3__cell")) {
    const cs = getComputedStyle(card);
    if (cs.overflowX !== "visible" || cs.overflowY !== "visible") continue; // it clips/scrolls by design
    const c = card.getBoundingClientRect();
    for (const kid of card.querySelectorAll<HTMLElement>("*")) {
      const ks = getComputedStyle(kid);
      if (ks.position === "fixed" || ks.display === "none" || ks.visibility === "hidden") continue;
      if (kid.closest("[role=dialog], [role=tooltip], .lf-popover")) continue;
      // Skip anything sitting inside an INNER scroll/clip container (a D-101 scrolling panel, the
      // quote row's sideways overflow): that content is bounded by ITS container, which is doing its
      // job. Only content that escapes with nothing to catch it is a defect.
      let inner = false;
      for (let a = kid.parentElement; a && a !== card; a = a.parentElement) {
        const as = getComputedStyle(a);
        if (as.overflowX !== "visible" || as.overflowY !== "visible") { inner = true; break; }
      }
      if (inner) continue;
      // Only measure elements that actually paint something of their own.
      if (!kid.textContent?.trim() && kid.tagName !== "SVG" && kid.tagName !== "IMG") continue;
      const k = kid.getBoundingClientRect();
      if (k.width < 1 || k.height < 1) continue;
      if (k.right > c.right + 2 || k.left < c.left - 2 || k.bottom > c.bottom + 2 || k.top < c.top - 2) {
        escapees.push(
          `${(kid.className.toString().split(" ")[0] || kid.tagName)}:"${kid.textContent?.trim().slice(0, 18)}" escapes ${card.className.split(" ")[0]}`,
        );
      }
    }
  }

  // OVERLAPPING TEXT — the symptom the owner actually sees. Take every element that renders its own
  // visible text (a leaf, so a parent box is not blamed for its child), and assert no two of them
  // occupy the same pixels. Text printed through other text is garbage at any width.
  const root = document.querySelector(scope) ?? document.body;
  const leaves: { el: Element; text: string; r: DOMRect }[] = [];
  for (const el of root.querySelectorAll<HTMLElement>("*")) {
    const ownText = [...el.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => (n.textContent ?? "").trim())
      .join(" ")
      .trim();
    if (!ownText) continue;
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none" || Number(s.opacity) === 0) continue;
    // Skip things that are SUPPOSED to sit on top of the page: overlays, popovers, tooltips, the
    // marquee ticker (it scrolls under its own clip), and anything explicitly stacked.
    if (el.closest("[role=dialog], [role=tooltip], .lf-ticker, .lf-toast, .lf-popover, .lf-firstrun")) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    // Skip text that is CLIPPED AWAY by a scroll/hidden ancestor: it has a box, but nobody can see
    // it, so it cannot be "printed through" anything. (Without this the check flags a gallery
    // specimen's clipped overflow as colliding with the section below it — a detector artefact, not
    // a defect. The clipping itself is caught by the no-clip assertions, where it belongs.)
    let clipped = false;
    for (let a = el.parentElement; a && !clipped; a = a.parentElement) {
      const as = getComputedStyle(a);
      if (as.overflow === "visible" && as.overflowX === "visible" && as.overflowY === "visible") continue;
      const ar = a.getBoundingClientRect();
      if (r.bottom <= ar.top + 1 || r.top >= ar.bottom - 1 || r.right <= ar.left + 1 || r.left >= ar.right - 1) {
        clipped = true;
      }
    }
    if (clipped) continue;
    leaves.push({ el, text: ownText.slice(0, 24), r });
  }

  const overlaps: string[] = [];
  for (let i = 0; i < leaves.length; i++) {
    for (let j = i + 1; j < leaves.length; j++) {
      const a = leaves[i];
      const b = leaves[j];
      // Ignore nesting (one contains the other): that is normal composition, not collision.
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      // Require a REAL intersection, not a 1px kiss from rounding.
      const dx = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const dy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (dx > 2 && dy > 2) overlaps.push(`"${a.text}" ⨯ "${b.text}"`);
    }
  }

  return {
    count: heads.length,
    escaped,
    outside,
    overlaps: overlaps.slice(0, 8),
    escapees: [...new Set(escapees)].slice(0, 8),
  };
}

for (const route of ROUTES) {
  for (const width of WIDTHS) {
    test(`tiles hold together · ${route.name} · ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto(`/${route.hash}`);
      await page.waitForSelector(".lf-shell__content > *, .ks", { timeout: 15_000 });
      await page
        .locator(".lf-summaryhead")
        .first()
        .waitFor({ state: "attached", timeout: 5_000 })
        .catch(() => {}); // a backend-less page may legitimately render no summary cards

      const report = await page.evaluate(auditPage, route.scope);

      if (route.strict) {
        expect(report.count, "the specimens must render, or this guard is vacuous").toBeGreaterThan(0);
      }
      expect(report.escaped, "summary headers absolutely positioned out of their tile").toEqual([]);
      expect(report.outside, "summary headers rendering outside their tile's bounds").toEqual([]);
      expect(report.overlaps, "TEXT PRINTED THROUGH OTHER TEXT — the page is garbled here").toEqual([]);
      expect(report.escapees, "content is spilling OUTSIDE the card that contains it").toEqual([]);
    });
  }
}

// The grid specimen (§12ho1-5) — the VIEWPORT-FIT assertion (§12ho1-7, owner's target).
//
// The target is 1440×900 with the REAL-SHAPED dataset, NOT 1366×768: the owner accepted that 1366
// scrolls modestly rather than have content shrunk to fake a fit. So the frame is 1440 × 812 — the
// CONTENT REGION at a 1440×900 screen, i.e. the viewport minus the chrome. The first version of this
// gate framed a bare 1366×768 and so promised the page the chrome's height on top of its own, which is
// how the design got ratified against a box the product does not have.
//
// The specimen is fed REAL-SHAPED data (8 asset classes, 6 quotes) precisely so it cannot flatter
// itself with a tidy demo the way it did last time. 1366 keeps its place in the no-clip / no-overlap
// matrix above — it just no longer has to fit.
test("home grid specimen · fits 1440×900 with real-shaped data, and no tile clips its content", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/#/kitchen-sink");
  await page.locator(".hm3--full").waitFor({ state: "attached", timeout: 15_000 });

  const report = await page.evaluate(() => {
    const frame = document.querySelector(".ks__viewport") as HTMLElement;
    const clipped: string[] = [];
    for (const cell of frame.querySelectorAll<HTMLElement>(".hm3__cell")) {
      const name = cell.className.split(" ").pop() ?? "?";
      if (cell.scrollHeight > cell.clientHeight + 2) clipped.push(`${name} (height)`);
      if (cell.scrollWidth > cell.clientWidth + 2) clipped.push(`${name} (width)`);
    }
    const grid = frame.querySelector(".hm3--full") as HTMLElement;
    return {
      clipped,
      vOverflow: grid.scrollHeight - frame.clientHeight,
      hOverflow: grid.scrollWidth - frame.clientWidth,
    };
  });

  expect(report.clipped, "a tile is hiding its own content to make the layout fit").toEqual([]);
  expect(report.hOverflow, "the grid must never scroll sideways").toBeLessThanOrEqual(0);

  // THE TARGET IS 0 — AND IT IS STILL NOT MET (§12ho3, batch 3). The owner's lever sequence was spent
  // in order — design before content — and it took the LIVE page from 533px of overshoot to 87px at
  // 1440×900. Every lever's real effect was measured, not assumed: the donut ring shrink bought ~0px
  // (the CAPPED LEGEND, not the ring, sets that tile's height), and cutting headlines bought ~0px until
  // density had made News the binding tile in its row — a content cut that buys nothing is pure loss.
  //
  // NOTE the frame under this assertion got 88px STRICTER in the same batch (it now subtracts the
  // shell's own padding, which the page really does lose), so the number below is not comparable to
  // batch 2's: the same ~126px against a much tighter box.
  //
  // It remains a RATCHET, not a pass: the overshoot can never grow, and it drops to 0 the moment the
  // owner spends a further lever. Reporting the number beats asserting a fiction.
  const BUDGET_OVERSHOOT = 130;
  expect(
    report.vOverflow,
    `the grid overshoots the 1440×900 content region by ${report.vOverflow}px (target 0; ratchet ${BUDGET_OVERSHOOT}px — see §12ho2-12)`,
  ).toBeLessThanOrEqual(BUDGET_OVERSHOOT);
});
