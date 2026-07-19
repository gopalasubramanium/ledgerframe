import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { Help } from "./Help";

// page-help Phase 1-bis (the §9-bis rebuild). The page renders SERVED strings verbatim and computes
// nothing, so these tests are about STRUCTURE and HONESTY, not content — content accuracy is
// guarded backend-side by tests/unit/test_help_content_accuracy.py, against the nav model, the
// glossary's deprecated table, and the shipped frontend itself.
//
// The rejected design's tests went with it: there is no category filter to narrow (the three
// sections render as a journey, not as a filtered stack) and no Search button to press (results
// come as you type). Tests were rewritten rather than adapted — an adapted test would still be
// asserting the shape the owner rejected.

const CATALOGUE = {
  categories: ["Orientation", "Pages", "Glossary"],
  entries: [
    {
      id: "orientation-pages",
      category: "Orientation",
      title: "How the pages fit together",
      body: "The pages are layers over one record.",
      links: [{ topic: "page-net-worth", label: "Net worth" }],
    },
    {
      id: "page-net-worth",
      category: "Pages",
      title: "Net worth",
      body: "Your headline and liquidity.",
      inputs: ["Time window — how much of the trend to show"],
      options: ["Time window: 1M · Max"],
      outputs: ["Net worth, Gross assets and Liabilities"],
      interpret: "Net worth is Gross assets minus Liabilities.",
    },
    { id: "page-policy", category: "Pages", title: "Policy", body: "Targets, bands and drift." },
    {
      id: "term-data-confidence",
      category: "Glossary",
      title: "Data confidence",
      body: "A 0-100 score.",
      what: "What it is.",
      why: "Why it matters.",
      improves: "What improves it.",
      level: "Basics",
      example: "Sample — a holding starts at 90 and loses 15 for a stale quote.",
    },
  ],
};

function mockFetch(impl: (url: string) => { status?: number; body: unknown }) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const { status = 200, body } = impl(url);
    return new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  }));
}

function renderAt(path = "/help") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/help" element={<Help />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
  mockFetch(() => ({ body: CATALOGUE }));
});

test("renders the three sections of the journey, in order, and nothing else (§9-bis-1)", async () => {
  renderAt();
  expect(await screen.findByRole("heading", { name: "Orientation" })).toBeTruthy();
  const sections = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(sections).toEqual(["Orientation", "Pages", "Glossary"]);
});

test("About is GONE from Help — it lives in Settings → System now (§9-bis-6)", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Orientation" });
  expect(screen.queryByRole("heading", { name: "About" })).toBeNull();
});

test("an entry title is visible while COLLAPSED, and its body is not (§9-bis-8)", async () => {
  renderAt();
  const toggle = await screen.findByRole("button", { name: /Net worth/, expanded: false });
  // The declination the accordion was ruled against protects NAVIGATION: nothing navigable may be
  // hidden. The title staying visible is precisely what makes this content disclosure instead.
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
  // The body is in the DOM but its panel is `hidden`, which is what keeps it out of the
  // accessibility tree. Asserting the text is absent would be the wrong claim: getByText does not
  // respect `hidden`, so that assertion would pass or fail for reasons unrelated to the design.
  const panel = document.querySelector("#page-net-worth .help__panel") as HTMLElement;
  expect(panel.hidden).toBe(true);
});

test("expanding shows the full inputs / options / outputs / interpret structure", async () => {
  renderAt();
  await userEvent.click(await screen.findByRole("button", { name: /Net worth/, expanded: false }));
  expect(screen.getByText("Your headline and liquidity.")).toBeTruthy();
  expect(screen.getByText("What you fill in")).toBeTruthy();
  expect(screen.getByText("What you can choose")).toBeTruthy();
  expect(screen.getByText("What you see")).toBeTruthy();
  expect(screen.getByText("How to read it")).toBeTruthy();
});

test("a glossary example is marked as an illustrative sample, twice over (§9-bis-3)", async () => {
  renderAt();
  await userEvent.click(await screen.findByRole("button", { name: /Data confidence/, expanded: false }));
  // Once in the SERVED string (so the marking travels to every consumer, including the AI fact
  // pack), and once as a chip for a reader skimming the block.
  expect(screen.getByText(/^Sample — /)).toBeTruthy();
  expect(screen.getByText("Illustrative sample")).toBeTruthy();
});

test("the glossary triad renders for Glossary entries and NOT for others", async () => {
  renderAt();
  await userEvent.click(await screen.findByRole("button", { name: /Data confidence/, expanded: false }));
  expect(screen.getAllByText("What it is").length).toBe(1);
  expect(screen.getAllByText("Why it matters").length).toBe(1);
});

test("an Orientation link opens the Section-2 entry it points at (§9-bis-1)", async () => {
  renderAt();
  await userEvent.click(await screen.findByRole("button", { name: /How the pages fit together/, expanded: false }));
  // The jump pill inside the Orientation body — not the Section-2 toggle that shares its label.
  // Only the toggle carries aria-expanded, so that is what tells them apart.
  const jump = screen
    .getAllByRole("button", { name: "Net worth" })
    .find((b) => !b.hasAttribute("aria-expanded"));
  await userEvent.click(jump!);
  // The pointer landed AND opened — a deep link onto a collapsed title reads as a link that
  // did not work.
  await waitFor(() => expect(screen.getByText("Your headline and liquidity.")).toBeTruthy());
});

test("a topic has exactly ONE anchor — no duplicate homes (§9-3)", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  expect(document.querySelectorAll("#page-net-worth").length).toBe(1);
});

test("type-ahead narrows AS YOU TYPE, with no submit (§9-bis-4)", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  await userEvent.type(screen.getByLabelText("Search help"), "drift");
  await waitFor(() => expect(screen.getByRole("button", { name: /Policy/, expanded: false })).toBeTruthy());
  expect(screen.queryByRole("button", { name: /Data confidence/, expanded: false })).toBeNull();
  // There is nothing to submit to: the ranking is client-side over the bundle already loaded.
  expect(screen.queryByRole("button", { name: "Search" })).toBeNull();
});

test("type-ahead matches MID-WORD and groups hits by section", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  await userEvent.type(screen.getByLabelText("Search help"), "confid");
  await waitFor(() => expect(screen.getByRole("button", { name: /Data confidence/, expanded: false })).toBeTruthy());
  expect(screen.getByRole("heading", { level: 2, name: "Glossary" })).toBeTruthy();
  expect(screen.queryByRole("heading", { level: 2, name: "Pages" })).toBeNull();
});

test("search REPLACES the sections rather than rendering a second copy (§9-3)", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  await userEvent.type(screen.getByLabelText("Search help"), "drift");
  await waitFor(() => expect(screen.queryByRole("button", { name: /Net worth/, expanded: false })).toBeNull());
  expect(document.querySelectorAll("#page-policy").length).toBe(1);
});

test("a no-match search shows a served reason, never a blank (Guarantee 3)", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  await userEvent.type(screen.getByLabelText("Search help"), "zzzz");
  expect(await screen.findByText(/No help entry matches/)).toBeTruthy();
  expect(screen.getByText(/does not search your holdings or the market/)).toBeTruthy();
});

test("an endpoint failure shows an honest reason and a retry, not a half page", async () => {
  mockFetch(() => ({ status: 500, body: { detail: "boom" } }));
  renderAt();
  expect(await screen.findByText("Help is unavailable")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
});

test("a ?topic= deep link marks AND opens the entry it meant", async () => {
  renderAt("/help?topic=term-data-confidence");
  // Expanded, not collapsed: the deep link OPENS what it names.
  await screen.findByRole("button", { name: /Data confidence/, expanded: true });
  await waitFor(() =>
    expect(document.querySelector("#term-data-confidence")?.className).toContain("is-target"),
  );
  expect(screen.getByText("A 0-100 score.")).toBeTruthy();
});

test("'Link to this topic' stays in the tab order — revealed, never removed (§9-bis-7)", async () => {
  renderAt();
  await screen.findByRole("button", { name: /Net worth/, expanded: false });
  // Option (b) is quiet-until-wanted, not absent. `display:none` would hand a keyboard user a
  // shorter page than a mouse user gets.
  const links = screen.getAllByTitle("Link to this topic");
  expect(links.length).toBe(CATALOGUE.entries.length);
  links.forEach((el) => expect((el as HTMLElement).hidden).toBe(false));
});
