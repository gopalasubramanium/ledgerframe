import { test, expect } from "@playwright/test";
import { API } from "./smoke-target.mjs";

// ⚠ DEV-ONLY smoke. §12cf1-3 — THE EDITOR DIALOGS ARE COMPACT: no dead bands.
//
// The defect: `.cf__field` carried `flex: 1 1 10rem` inside a COLUMN flex container, so every field
// STRETCHED vertically — the Name field was 160px tall to hold a label and a 40px input, and the
// dialog was full of empty space. A field is a label + ONE control (+ an optional hint); it may not
// be taller than that.

for (const theme of ["light", "dark"] as const) {
  for (const width of [1366, 1440]) {
    for (const [btn, what] of [
      [/add income or expense/i, "income/expense"],
      [/add contribution/i, "contribution"],
      [/add goal/i, "goal"],
    ] as [RegExp, string][]) {
      test(`editor is compact · ${what} · ${width} · ${theme}`, async ({ page }) => {
        await page.request.put(`${API}/settings`, { data: { values: { first_run_complete: "1" } } });
        await page.setViewportSize({ width, height: 900 });
        await page.goto("/#/cash-flow");
        await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
        await page.getByRole("button", { name: btn }).first().click();
        const dlg = page.getByRole("dialog");
        await expect(dlg).toBeVisible();

        const report = await dlg.evaluate((d) => {
          const fields = [...d.querySelectorAll(".cf__field")] as HTMLElement[];
          const bad: string[] = [];
          for (const f of fields) {
            const h = f.getBoundingClientRect().height;
            const control = f.querySelector("input, select, button, .lf-field") as HTMLElement | null;
            const ch = control?.getBoundingClientRect().height ?? 0;
            // A field is a label + one control (+ an optional hint). Anything much taller is a
            // stretched box: an empty band the user reads as a hole in the form.
            if (ch > 0 && h > ch * 2.4) bad.push(`${f.textContent?.trim().slice(0, 14)}: ${Math.round(h)}px around a ${Math.round(ch)}px control`);
          }
          const body = d.querySelector(".lf-dialog__body") as HTMLElement;
          const last = fields[fields.length - 1]?.getBoundingClientRect();
          const tail = last ? body.getBoundingClientRect().bottom - last.bottom : 0;
          return { bad, tail: Math.round(tail), fieldCount: fields.length };
        });

        expect(report.fieldCount, "the form rendered").toBeGreaterThan(2);
        expect(report.bad, "no field is a stretched empty band").toEqual([]);
        // No dead band under the last field either.
        expect(report.tail, "no dead space between the last field and the dialog footer").toBeLessThanOrEqual(48);
      });
    }
  }
}
