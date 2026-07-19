import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { Legal } from "./Legal";

// page-legal Phase 1 (§9 ruled by the owner in chat, 2026-07-19).
//
// These tests are about STRUCTURE and HONESTY, not content — deliberately, and the same way
// Help.test.tsx is. Legal's copy is SERVED, so its accuracy is guarded where it lives:
// `tests/unit/test_legal_content.py` (AC-L3 verbatim, AC-L5 the NEVER list),
// `test_legal_accuracy.py` (AC-L7 the Help truth bar), `test_scoped_caveats.py` (AC-L6). That
// split is §9-3's whole rationale in practice: asserting the wording here instead would put the
// page's truth in a test that only knows what the fixture told it.
//
// So what is asserted here is what only the page can be wrong about: that it renders every served
// section, renders the Commitments VERBATIM and in order, distinguishes loading from failure, and
// never turns a file pointer into a link.

const PAGE = {
  markup: "lf-help-markup-1",
  sections: [
    { id: "position", title: "Disclaimer", body: "LedgerFrame reports; **it does not act**." },
    {
      id: "scoped-caveats",
      title: "The limits on each figure",
      body: "Individual figures carry their own limits, stated where the figure is shown.",
    },
    { id: "licence", title: "Licence", body: "Released under the **AGPL-3.0-or-later** licence." },
    {
      id: "jurisdiction",
      title: "No jurisdiction tax logic",
      body: "LedgerFrame contains **no tax logic for any country**.",
    },
  ],
  commitments: {
    title: "Product Commitments",
    intro: "These seven are what the product will never do.",
    items: [
      "**No trades.** LedgerFrame never places or executes trades.",
      "**No advice.** Never gives buy/sell/hold, tax, or financial advice.",
      "**No fabrication.** Never fabricates a price, headline, or figure.",
      "**No jurisdiction tax logic — ever** (D-077).",
      "**No egress (opt-in)** (D-004).",
      "**No stored AI conversations** (D-016).",
      "**The validation contract never weakens** (D-071).",
    ],
  },
  pointers: [
    { file: "LICENSE", what: "The full text of the licence." },
    { file: "docs/audit/LICENSES.md", what: "The licence of every dependency. Generated." },
  ],
  pack_footer: "Reporting only.",
};

function mockFetch(impl: (url: string) => { status?: number; body: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const { status = 200, body } = impl(String(input));
      return new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
      });
    }),
  );
}

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/legal"]}>
      <Routes>
        <Route path="/legal" element={<Legal />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
  mockFetch(() => ({ body: PAGE }));
});

test("AC-L1 — /legal renders real contents, not the unbuilt fallback", async () => {
  renderAt();
  expect(await screen.findByRole("heading", { name: "Legal", level: 1 })).toBeTruthy();
  expect(document.querySelector(".lf-notbuilt")).toBeNull();
  expect(screen.queryByText(/isn't built yet/)).toBeNull();
});

test("renders every SERVED section, in the served order — the page picks nothing", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Disclaimer" });
  const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  // The four IA-owned contents, plus the pointers card. A section dropped server-side must
  // disappear here; a section added must appear, without a frontend change.
  expect(headings).toEqual([
    "Disclaimer",
    "The limits on each figure",
    "Licence",
    "No jurisdiction tax logic",
    "Product Commitments",
    "Where to find the full record",
  ]);
});

test("AC-L3 — the Commitments render VERBATIM, all seven, in the served order", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Product Commitments" });
  const items = Array.from(document.querySelectorAll(".legal__commitment"));
  expect(items).toHaveLength(7);
  // Markup markers are RENDERED (bold), not shown, so the text compare strips them the same way
  // the server-side guard does. What is asserted is that the page neither reorders, renumbers,
  // paraphrases nor truncates what it was given.
  const texts = items.map((li) => li.textContent);
  expect(texts[0]).toContain("No trades.");
  expect(texts[6]).toContain("The validation contract never weakens");
  PAGE.commitments.items.forEach((g, i) => {
    expect(texts[i]).toBe(g.replace(/\*\*/g, ""));
  });
});

test("the Commitments are an ORDERED list — the numbering is part of what they are", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Product Commitments" });
  expect(document.querySelector("ol.legal__commitments")).not.toBeNull();
});

test("§9-5 — a file pointer is a NAME, never a link (a local-first page must work offline)", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Where to find the full record" });
  const pointers = document.querySelector(".legal__pointers") as HTMLElement;
  expect(pointers.querySelectorAll("a")).toHaveLength(0);
  expect(screen.getByText("docs/audit/LICENSES.md")).toBeTruthy();
});

test("the LOAD-FAILURE state names the failure, offers retry, and does NOT reassure", async () => {
  mockFetch(() => ({ status: 500, body: { detail: "boom" } }));
  renderAt();
  expect(await screen.findByText("Legal is unavailable")).toBeTruthy();
  // The one thing still true with the server unreachable: the licence ships in the source tree.
  expect(screen.getByText(/ships with the source, in the LICENSE file/)).toBeTruthy();
  // A Legal page that cannot load its terms must never imply the terms are fine.
  expect(screen.queryByRole("heading", { name: "Product Commitments" })).toBeNull();
  expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
});

test("Retry re-reads, and a page that failed once can still come good", async () => {
  let attempt = 0;
  mockFetch(() => (attempt++ === 0 ? { status: 500, body: {} } : { body: PAGE }));
  renderAt();
  await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("heading", { name: "Product Commitments" })).toBeTruthy();
  expect(screen.queryByText("Legal is unavailable")).toBeNull();
});

test("loading and failure are DIFFERENT states — 'not yet' never renders as 'unavailable'", async () => {
  // A never-resolving read: the page must sit in the loading state, not fall through to the
  // failure copy. Two different facts, and a page about honesty should not conflate them.
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
  renderAt();
  expect(await screen.findByRole("heading", { name: "Legal", level: 1 })).toBeTruthy();
  expect(document.querySelector(".lf-skeleton")).not.toBeNull();
  expect(screen.queryByText("Legal is unavailable")).toBeNull();
});
