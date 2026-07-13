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
      { id: 1, symbol: "AAPL", asset_class: "equity", market_value: 1000, day_change: 5, day_change_pct: 0.5, is_priced: true, is_stale: false, region: "US", country: "US" },
      { id: 2, symbol: "RELIANCE", asset_class: "equity", market_value: 500, day_change: -3, day_change_pct: -0.6, is_priced: true, is_stale: false, region: "India", country: "IN" },
      { id: 3, symbol: "BTC", asset_class: "crypto", market_value: 300, day_change: 2, day_change_pct: 0.7, is_priced: true, is_stale: false, region: "Other", country: null },
      { id: 4, symbol: null, name: "Home", asset_class: "property", market_value: 2000, day_change: 0, day_change_pct: 0, is_priced: true, is_stale: false, region: "Other", country: null },
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

test("no priced holdings → the honest empty state, never a fabricated tile (Guarantee 3, ND-12)", async () => {
  getHoldings.mockResolvedValueOnce({
    ok: true,
    data: { base_currency: "SGD", holdings: [{ id: 5, symbol: "XYZ", asset_class: "equity", market_value: null, day_change: null, day_change_pct: null, is_priced: false, is_stale: true, region: "US", country: "US" }] },
  });
  renderPage();
  expect(await screen.findByText("No priced holdings to chart.")).toBeTruthy();
});
