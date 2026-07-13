import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../theme/ThemeProvider";
import { DisplayProvider } from "../theme/DisplayProvider";
import { ToastProvider } from "../components/ui";

const PAGE = {
  ok: true,
  data: {
    base_currency: "SGD",
    net_worth: 795860,
    sections: {
      trust: { confidence: 82, low: 1, stale: 2 },
      policy: { out_of_band: 1, has_targets: true },
      liquidity: { liquid_pct: 20, runway_status: "finite", runway_months: 5 },
      goals: { goals: 1, next_obligation: null, next_12m_total: 0 },
      changed: { day_change: 170, top_mover: "VOO" },
    },
    attention: [
      { area: "data", title: "1 holding has incomplete details", severity: "info" },
      { area: "data", title: "2 holdings have stale prices — refresh", severity: "review" },
      { area: "policy", title: "Equity is under its asset class band", severity: "review" },
      { area: "zzz-unknown", title: "An unmapped area item", severity: "info" },
    ],
    attention_count: 2,
    last_review: { reviewed_at: "2026-07-10", days_ago: 3, next_review_date: "2026-08-01" },
    disclaimer: "reporting only",
  },
};
const HISTORY = {
  ok: true,
  data: { history: [{ id: 1, reviewed_at: "2026-07-10", days_ago: 3, net_worth: 790000, base_currency: "SGD", confidence: 80, drift_flags: 1, attention_count: 2, note: "Rebalanced", next_review_date: "2026-08-01" }] },
};

const getReviewPage = vi.fn(async () => PAGE);
const getReviewHistory = vi.fn(async () => HISTORY);
const markReviewed = vi.fn(async () => ({ ok: true, data: { ok: true, id: 2 } }));
vi.mock("../api/review", () => ({
  getReviewPage: () => getReviewPage(),
  getReviewHistory: () => getReviewHistory(),
  markReviewed: (...a: unknown[]) => markReviewed(...(a as [])),
}));

import { Review } from "./Review";

function renderPage() {
  return render(
    <ThemeProvider>
      <DisplayProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={["/review"]}>
            <Review />
          </MemoryRouter>
        </ToastProvider>
      </DisplayProvider>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("attention items render with a NEUTRAL severity chip (served verbatim) sorted review-first (ND-4)", async () => {
  const { container } = renderPage();
  const table = (await screen.findByText(/2 holdings have stale prices/)).closest("table") as HTMLElement;
  // Severity is the served string, verbatim (no semantic mapping).
  expect(within(table).getAllByText("review").length).toBeGreaterThan(0);
  expect(within(table).getAllByText("info").length).toBeGreaterThan(0);
  const chip = container.querySelector(".rv__chip") as HTMLElement;
  expect(chip.textContent).toMatch(/review|info/);
  // review-first ordering: the first body row is a 'review' item, not the served-first 'info' one.
  const firstRow = table.querySelector("tbody tr") as HTMLElement;
  expect(within(firstRow).getByText("review")).toBeTruthy();
});

test("each area links to its canonical page; an unrecognised area is NOT linked (ND-7)", async () => {
  renderPage();
  await screen.findByText(/2 holdings have stale prices/);
  // Known areas map to their canonical route.
  expect(screen.getByRole("link", { name: "policy" }).getAttribute("href")).toContain("/policy");
  expect(screen.getAllByRole("link", { name: "data" })[0].getAttribute("href")).toContain("/pricing-health");
  // Unrecognised area renders WITHOUT a link — never a guessed route.
  expect(screen.queryByRole("link", { name: "zzz-unknown" })).toBeNull();
  expect(screen.getByText("zzz-unknown")).toBeTruthy();
});

test("empty signal renders the served honest empty, never a fabricated row (Guarantee 3)", async () => {
  getReviewPage.mockResolvedValueOnce({ ok: true, data: { ...PAGE.data, attention: [{ area: "ok", title: "Nothing needs a look right now.", severity: "info" }], attention_count: 0 } });
  renderPage();
  expect(await screen.findByText("Nothing needs a look right now.")).toBeTruthy();
});

test("Mark reviewed: the request body is the entered note + next-review date (ND-8, §7 request-body)", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: "Mark reviewed" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Review note"), "Rebalanced equity");
  fireEvent.change(within(dialog).getByLabelText("Next review date"), { target: { value: "2026-08-01" } });
  await user.click(within(dialog).getByRole("button", { name: "Save" }));
  await waitFor(() => expect(markReviewed).toHaveBeenCalledWith("Rebalanced equity", "2026-08-01"));
});

test("review history renders with the honest last-24 legend", async () => {
  renderPage();
  expect(await screen.findByText("Rebalanced")).toBeTruthy();
  expect(screen.getByText(/last 24 recorded reviews/)).toBeTruthy();
});
