import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../theme/ThemeProvider";
import { DisplayProvider } from "../theme/DisplayProvider";

// A demo spanning: priced US/India/crypto tiles, a FLAT unlinked property, an UNPRICED holding,
// and a LIABILITY (negative) — the last two must be excluded (ND-3/ND-4).
const HOLDINGS = {
  ok: true,
  data: {
    base_currency: "SGD",
    holdings: [
      { id: 1, symbol: "AAPL", asset_class: "equity", market_value: 1000, market_value_display: "1,000.00", day_change: 5, day_change_pct: 0.5, day_change_pct_display: "+0.50%", is_priced: true, is_stale: false, region: "US", country: "US" },
      { id: 2, symbol: "RELIANCE", asset_class: "equity", market_value: 500, market_value_display: "500.00", day_change: -3, day_change_pct: -0.6, day_change_pct_display: "−0.60%", is_priced: true, is_stale: false, region: "India", country: "IN" },
      { id: 3, symbol: "BTC", asset_class: "crypto", market_value: 300, market_value_display: "300.00", day_change: 2, day_change_pct: 0.7, day_change_pct_display: "+0.70%", is_priced: true, is_stale: false, region: "Other", country: null },
      { id: 4, symbol: null, name: "Home", asset_class: "property", market_value: 2000, market_value_display: "2,000.00", day_change: 0, day_change_pct: null, day_change_pct_display: null, is_priced: true, is_stale: false, region: "Other", country: null },
      { id: 5, symbol: "XYZ", asset_class: "equity", market_value: null, day_change: null, day_change_pct: null, is_priced: false, is_stale: true, region: "US", country: "US" },
      { id: 6, symbol: null, name: "Mortgage", asset_class: "liability", market_value: -800, day_change: 0, day_change_pct: 0, is_priced: true, is_stale: false, region: "Other", country: null },
    ],
  },
};

const getHoldings = vi.fn(async () => HOLDINGS);
vi.mock("../api/holdings", () => ({ getHoldings: () => getHoldings() }));

import { Heatmap } from "./Heatmap";

function renderPage() {
  return render(
    <ThemeProvider>
      <DisplayProvider>
        <MemoryRouter initialEntries={["/heatmap"]}>
          <Heatmap />
        </MemoryRouter>
      </DisplayProvider>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  getHoldings.mockResolvedValue(HOLDINGS);
});

test("charts priced holdings only — unpriced + liabilities excluded; coverage note is honest (ND-3/ND-4)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__cell-rect").length).toBeGreaterThan(0));
  // 6 holdings → 4 tiles (excludes the unpriced XYZ and the -800 liability).
  expect(container.querySelectorAll(".lf-treemap__cell-rect").length).toBe(4);
  expect(screen.getByText(/Showing 4 of 6 holdings — unpriced excluded/)).toBeTruthy();
  expect(screen.getByText(/Assets only — liabilities are excluded/)).toBeTruthy();
  // The liability's label never appears as a tile.
  expect(screen.queryByText("Mortgage")).toBeNull();
});

test("symboled tiles link to InstrumentDetail; the property (no symbol) is not linked (ND-7/D-098)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__link").length).toBeGreaterThan(0));
  const hrefs = [...container.querySelectorAll<HTMLAnchorElement>(".lf-treemap__link")].map((a) => a.getAttribute("href"));
  // 3 symboled priced holdings link; the property has no symbol → no link.
  expect(hrefs.sort()).toEqual(["#/instrument/AAPL", "#/instrument/BTC", "#/instrument/RELIANCE"]);
});

test("region filter narrows to the served region (ND-8, no client region map)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__cell-rect").length).toBe(4));
  fireEvent.change(screen.getByLabelText("Filter by region"), { target: { value: "US" } });
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__cell-rect").length).toBe(1));
  // Only AAPL (US) remains.
  expect(container.querySelector<HTMLAnchorElement>(".lf-treemap__link")?.getAttribute("href")).toBe("#/instrument/AAPL");
});

test("an empty filter combination shows the honest filter-empty state (ND-12)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__cell-rect").length).toBe(4));
  fireEvent.change(screen.getByLabelText("Filter by asset class"), { target: { value: "crypto" } });
  fireEvent.change(screen.getByLabelText("Filter by region"), { target: { value: "India" } });
  expect(await screen.findByText("No holdings match this filter.")).toBeTruthy();
});

// §12hm1-1 — the readout pairs the SERVED money string with the SERVED base currency. The page
// formats nothing: no number here is derived, rounded, or signed on the client.
test("the tile readout renders served display strings + the served base currency (§12hm1-1)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__hot").length).toBe(4));
  const aapl = [...container.querySelectorAll(".lf-treemap__hot")].find((h) => h.getAttribute("aria-label") === "AAPL")!;
  fireEvent.mouseEnter(aapl);
  const text = container.querySelector(".lf-treemap__tip")!.textContent!;
  expect(text).toContain("SGD 1,000.00"); // served base_currency + served market_value_display
  expect(text).toContain("+0.50%"); // served day_change_pct_display, sign included
  expect(text).toContain("Today’s change");
});

test("a holding with no Today's change shows an em dash + reason in the readout, never 0% (Guarantee 3)", async () => {
  const { container } = renderPage();
  await waitFor(() => expect(container.querySelectorAll(".lf-treemap__hot").length).toBe(4));
  // The property is served with a value but NO day_change_pct → honest absence, and (no symbol) it
  // is still focusable, so the readout is reachable by keyboard.
  const home = [...container.querySelectorAll(".lf-treemap__hot")].find((h) => h.getAttribute("aria-label") === "Home")!;
  expect(home.tagName).toBe("DIV"); // not a link — the property has no InstrumentDetail
  fireEvent.focus(home);
  const text = container.querySelector(".lf-treemap__tip")!.textContent!;
  expect(text).toContain("SGD 2,000.00");
  expect(text).toContain("—");
  expect(text).toContain("No prior close to compare.");
});

test("no priced holdings → the honest empty state, never a fabricated tile (Guarantee 3, ND-12)", async () => {
  getHoldings.mockResolvedValueOnce({
    ok: true,
    data: { base_currency: "SGD", holdings: [{ id: 5, symbol: "XYZ", asset_class: "equity", market_value: null, day_change: null, day_change_pct: null, is_priced: false, is_stale: true, region: "US", country: "US" }] },
  });
  renderPage();
  expect(await screen.findByText("No priced holdings to chart.")).toBeTruthy();
});
