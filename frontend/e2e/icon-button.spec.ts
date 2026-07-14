import { test, expect } from "@playwright/test";

// §12po3-1 — ICON-IN-BUTTON SIZING (owner walk, Policy close-out).
//
// The Policy pencil was hardcoded at 16px via lucide's `size` prop — OFF-TOKEN — on a button with no
// flex/gap/centring, so it rode mis-sized and off the label's optical centre.
//
// ⚠ My first version of this guard asserted "icon box == the button's font-size" and it went RED on
// REVIEW — the button the owner has already ACCEPTED. That was me asserting a theory again (§13). The
// ratified treatment is the `--icon-size` TOKEN (18px) with an inline-flex row and a token gap. So the
// guard asserts PARITY WITH THE ACCEPTED PRECEDENT, which is what "conform to Mark-reviewed" means.
//
// This is the 2nd icon+label button (Review · Policy). Per the centralization rule, the 3rd occurrence
// EXTRACTS a shared treatment — recorded in the plan, not pre-emptively built here.
// §9-13 — both buttons are now the RATIFIED `Button` component (`.lf-btn--icon`); the page-local
// copies (.rv__markbtn, .pol__btn) are DELETED. The guard is RETARGETED at the shared class, not
// removed — a migration that drops its guard is a migration that stops being proven.
// ⚠ MEASURED IN THE GALLERY, NOT ON A LIVE PAGE. The CI e2e suite runs with NO BACKEND, so Policy
// renders no action button at all (it has no policy to edit) and this guard TIMED OUT there — green
// locally against a dev backend, red in the suite. A COMPONENT guard must not depend on a page
// having data. The gallery specimen is static, so it can never render zero.
// Review is kept as the live case: its button renders regardless of data.
const BUTTONS = [
  { name: "kitchen-sink · Button specimen", hash: "#/kitchen-sink", selector: ".lf-btn--icon" },
  { name: "review · Mark reviewed", hash: "#/review", selector: ".lf-btn--icon" },
];

for (const theme of ["light", "dark"] as const) {
  for (const b of BUTTONS) {
    test(`icon scales with the button's type · ${b.name} · ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width: 1366, height: 900 });
      await page.goto(`/${b.hash}`);
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      const btn = page.locator(b.selector).first();
      await expect(btn).toBeVisible({ timeout: 15_000 });

      const m = await btn.evaluate((el) => {
        const svg = el.querySelector("svg") as SVGElement;
        const ib = svg.getBoundingClientRect();
        const cs = getComputedStyle(el);
        const bb = el.getBoundingClientRect();
        const token = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--icon-size")) *
          parseFloat(getComputedStyle(document.documentElement).fontSize) / 16 * 16;
        return {
          tokenPx: token,
          iconW: ib.width,
          iconH: ib.height,
          gap: parseFloat(cs.columnGap || "0"),
          display: cs.display,
          iconCentre: ib.top + ib.height / 2,
          btnCentre: bb.top + bb.height / 2,
          label: (el.textContent ?? "").trim(),
        };
      });

      // The icon is the RATIFIED TOKEN size — never a magic pixel value passed per call site.
      expect(Math.abs(m.iconW - m.tokenPx), `icon width ${m.iconW} == --icon-size ${m.tokenPx}`).toBeLessThanOrEqual(1);
      expect(Math.abs(m.iconH - m.tokenPx), `icon height ${m.iconH} == --icon-size ${m.tokenPx}`).toBeLessThanOrEqual(1);
      // Optically centred with the label, with a consistent gap — and the TEXT LABEL IS KEPT.
      expect(Math.abs(m.iconCentre - m.btnCentre), "icon is optically centred with the label").toBeLessThanOrEqual(1.5);
      expect(m.gap, "a consistent gap between icon and label").toBeGreaterThan(0);
      expect(m.display).toContain("flex");
      expect(m.label.length, "the icon rides WITH a text label, never instead of it").toBeGreaterThan(0);
    });
  }
}
