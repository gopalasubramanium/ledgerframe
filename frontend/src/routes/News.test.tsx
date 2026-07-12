import { afterEach, expect, test, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../theme/ThemeProvider";
import { DisplayProvider } from "../theme/DisplayProvider";
import { ToastProvider } from "../components/ui";

const BRIEFING = {
  ok: true,
  data: {
    text: "Your portfolio 100,000.00 SGD, today +500.00 SGD. Information only, not financial advice.",
    generated_at: "2026-07-13T00:00:00Z",
  },
};
const GROUPED = {
  ok: true,
  data: {
    groups: [
      { name: "My holdings", items: [{ headline: "Apple steadies as the market digests rate expectations", source: "BBC", url: "https://example.com/a", published_at: "2026-07-13T00:00:00Z", symbols: ["AAPL"] }] },
      { name: "India", items: [{ headline: "Rupee firms <script>alert(1)</script> on strong inflows", source: "Reuters", url: "https://example.com/b", published_at: "2026-07-12T00:00:00Z", symbols: [] }] },
    ],
    total: 2,
    no_egress: false,
  },
};

const getBriefing = vi.fn(async () => BRIEFING);
const getGroupedNews = vi.fn(async () => GROUPED);
const getNoEgress = vi.fn(async () => false);
const refreshBriefing = vi.fn(async () => ({ ok: true, data: { text: "Refreshed briefing. Information only, not financial advice." } }));
vi.mock("../api/news", () => ({
  getBriefing: () => getBriefing(),
  getGroupedNews: () => getGroupedNews(),
  getNoEgress: () => getNoEgress(),
  refreshBriefing: () => refreshBriefing(),
}));

import { News } from "./News";

function renderPage() {
  return render(
    <ThemeProvider>
      <DisplayProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={["/news"]}>
            <News />
          </MemoryRouter>
        </ToastProvider>
      </DisplayProvider>
    </ThemeProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  getNoEgress.mockResolvedValue(false);
});

test("briefing renders the SERVED deterministic text; the card carries NO AI copy (ND-1)", async () => {
  const { container } = renderPage();
  expect(await screen.findByText(/Information only, not financial advice/)).toBeTruthy();
  expect(container.textContent ?? "").not.toMatch(/\bAI\b|narrat|artificial intelligence/i);
});

test("headline buckets render as segmented tabs; one group visible at a time (§12nw1-2)", async () => {
  const user = userEvent.setup();
  renderPage();
  // Tabs for each SERVED bucket (labels verbatim).
  expect(await screen.findByRole("button", { name: /My holdings/ })).toBeTruthy();
  expect(screen.getByRole("button", { name: /India/ })).toBeTruthy();
  // The first bucket is active → its headline + symbol link show; India's is not yet visible.
  expect(screen.getByText(/Apple steadies/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "AAPL" }).getAttribute("href")).toContain("/instrument/AAPL");
  expect(screen.queryByText(/Rupee firms/)).toBeNull();
  // Switch buckets → India's headline appears.
  await user.click(screen.getByRole("button", { name: /India/ }));
  await waitFor(() => expect(screen.getByText(/Rupee firms/)).toBeTruthy());
});

test("a headline containing markup renders as INERT plain text (ND-12 sanitisation)", async () => {
  const user = userEvent.setup();
  renderPage();
  await user.click(await screen.findByRole("button", { name: /India/ }));
  const el = await screen.findByText(/Rupee firms/);
  expect(el.textContent).toContain("<script>alert(1)</script>");
  expect(el.querySelector("script")).toBeNull();
});

test("external headline links open in a new tab with a safe rel (ND-5)", async () => {
  renderPage();
  const link = await screen.findByRole("link", { name: /Apple steadies/ });
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toContain("noreferrer");
});

test("per-card refresh: 'Refresh briefing' regenerates ([S]-gated, ND-8 reversal §12nw1-3)", async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByText(/Information only/);
  await user.click(screen.getByRole("button", { name: "Refresh briefing" }));
  await waitFor(() => expect(refreshBriefing).toHaveBeenCalled());
});

test("no-egress renders the refresh buttons DISABLED with an honest title (ND-2 governs refresh)", async () => {
  getNoEgress.mockResolvedValue(true);
  renderPage();
  const btn = await screen.findByRole("button", { name: "Refresh briefing" });
  await waitFor(() => expect((btn as HTMLButtonElement).disabled).toBe(true));
  expect(btn.getAttribute("title")).toMatch(/no-egress is on/i);
});

test("no-egress headlines render an honest reason, never fabricated (ND-2)", async () => {
  getGroupedNews.mockResolvedValueOnce({ ok: true, data: { groups: [], total: 0, no_egress: true } });
  renderPage();
  expect(await screen.findByText(/no-egress is on/)).toBeTruthy();
});

test("empty headlines show a configure-feeds reason (honest empty)", async () => {
  getGroupedNews.mockResolvedValueOnce({ ok: true, data: { groups: [], total: 0, no_egress: false } });
  renderPage();
  expect(await screen.findByText(/No headlines right now/)).toBeTruthy();
});
