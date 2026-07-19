import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { Help } from "./Help";

// page-help Phase 1. The page renders SERVED strings verbatim and computes nothing, so these tests
// are about STRUCTURE and HONESTY, not content — content accuracy is guarded backend-side by
// tests/unit/test_help_content_accuracy.py, against the nav model and the glossary.

const CATALOGUE = {
  categories: ["Pages", "Terms", "About"],
  entries: [
    { id: "page-net-worth", category: "Pages", title: "Net worth", body: "Your headline and liquidity." },
    { id: "page-policy", category: "Pages", title: "Policy", body: "Targets, bands and drift." },
    {
      id: "term-data-confidence",
      category: "Terms",
      title: "Data confidence",
      body: "A 0-100 score.",
      what: "What it is.",
      why: "Why it matters.",
      improves: "What improves it.",
    },
    { id: "guarantee", category: "About", title: "What LedgerFrame will never do", body: "It never places a trade." },
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

test("renders the served catalogue grouped in the served category order", async () => {
  renderAt();
  expect(await screen.findByRole("heading", { name: "Pages" })).toBeTruthy();
  const sections = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(sections).toEqual(["Pages", "Terms", "About"]);
  expect(screen.getByRole("heading", { name: "Net worth" })).toBeTruthy();
});

test("the glossary triad renders for Terms entries and NOT for others", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Data confidence" });
  // The triad rides Terms only; a Pages entry must not render an empty label set.
  expect(screen.getAllByText("What it is").length).toBe(1);
  expect(screen.getAllByText("Why it matters").length).toBe(1);
});

test("a topic has exactly ONE anchor — no duplicate homes (§9-3)", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Net worth" });
  expect(document.querySelectorAll("#page-net-worth").length).toBe(1);
});

test("search REPLACES the catalogue rather than rendering a second copy (§9-3)", async () => {
  mockFetch((url) =>
    url.includes("?q=")
      ? { body: { query: "drift", entries: [CATALOGUE.entries[1]] } }
      : { body: CATALOGUE },
  );
  renderAt("/help?q=drift");
  await screen.findByRole("heading", { name: "Policy" });
  // Only the hit is on screen, and it still has exactly one anchor.
  expect(screen.queryByRole("heading", { name: "Net worth" })).toBeNull();
  expect(document.querySelectorAll("#page-policy").length).toBe(1);
});

test("a no-match search shows a reason, never a blank (Guarantee 3)", async () => {
  mockFetch((url) =>
    url.includes("?q=") ? { body: { query: "zzz", entries: [] } } : { body: CATALOGUE },
  );
  renderAt("/help?q=zzz");
  expect(await screen.findByText(/No help entry matches/)).toBeTruthy();
  expect(screen.getByText(/Try a different word/)).toBeTruthy();
});

test("an endpoint failure shows an honest reason and a retry, not a half page", async () => {
  mockFetch(() => ({ status: 500, body: { detail: "boom" } }));
  renderAt();
  expect(await screen.findByText("Help is unavailable")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
});

test("a ?topic= deep link marks the entry it meant", async () => {
  renderAt("/help?topic=term-data-confidence");
  await screen.findByRole("heading", { name: "Data confidence" });
  await waitFor(() =>
    expect(document.querySelector("#term-data-confidence")?.className).toContain("is-target"),
  );
});

test("the category filter narrows to the served category", async () => {
  renderAt();
  await screen.findByRole("heading", { name: "Net worth" });
  await userEvent.click(screen.getByRole("button", { name: "Terms" }));
  expect(screen.queryByRole("heading", { name: "Net worth" })).toBeNull();
  expect(screen.getByRole("heading", { name: "Data confidence" })).toBeTruthy();
});
