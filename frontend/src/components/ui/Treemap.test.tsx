import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { Treemap } from "./Treemap";
import type { TreemapNode } from "../../mocks/types";

afterEach(cleanup);

const NODES: TreemapNode[] = [
  { label: "AAPL", value: 100, tone: "gain", magnitudePct: 1.2, href: "#/instrument/AAPL" },
  { label: "VOO", value: 60, tone: "loss", magnitudePct: 0.5, href: "#/instrument/VOO" },
];

// page-heatmap ND-7 (§5 amendment) — a node with href becomes a keyboard-operable link.
test("nodes with href render a keyboard-operable link to their entity (D-098)", () => {
  const { container } = render(<Treemap nodes={NODES} squarified />);
  const links = container.querySelectorAll<HTMLAnchorElement>(".lf-treemap__link");
  expect(links.length).toBe(2);
  const hrefs = [...links].map((a) => a.getAttribute("href"));
  expect(hrefs).toContain("#/instrument/AAPL");
  // Accessible name is the tile label (labels are aria-hidden; the link carries the name).
  expect([...links].map((a) => a.getAttribute("aria-label"))).toContain("AAPL");
});

test("Space activates a focused tile (Enter is native to the anchor)", () => {
  const { container } = render(<Treemap nodes={NODES} squarified />);
  const link = container.querySelector<HTMLAnchorElement>(".lf-treemap__link")!;
  const clickSpy = vi.spyOn(link, "click").mockImplementation(() => {});
  fireEvent.keyDown(link, { key: " " });
  expect(clickSpy).toHaveBeenCalledTimes(1);
});

test("nodes without href or readout are non-interactive (back-compatible)", () => {
  const plain: TreemapNode[] = NODES.map((n) => ({ label: n.label, value: n.value, tone: n.tone, magnitudePct: n.magnitudePct }));
  const { container } = render(<Treemap nodes={plain} squarified />);
  expect(container.querySelectorAll(".lf-treemap__link").length).toBe(0);
  expect(container.querySelectorAll(".lf-treemap__hot").length).toBe(0);
});

// page-heatmap §12hm1-1 (§5 amendment) — the hover/focus readout.
const READOUT: TreemapNode[] = [
  { label: "AAPL", value: 100, tone: "gain", magnitudePct: 1.2, href: "#/instrument/AAPL", readout: { value: "SGD 1,000.00", change: "+1.20%" } },
  { label: "Home", value: 60, tone: "flat", readout: { value: "SGD 600.00", change: null, note: "No prior close to compare." } },
];

test("the readout is empty until a tile is hovered or focused (no layout shift, no stray copy)", () => {
  const { container } = render(<Treemap nodes={READOUT} squarified />);
  const tip = container.querySelector(".lf-treemap__tip")!;
  expect(tip.textContent).toBe("");
  // The live region exists up front so keyboard users hear the change (AllocationDonut precedent).
  expect(tip.getAttribute("aria-live")).toBe("polite");
});

test("HOVER renders the served display strings verbatim — the component formats nothing", () => {
  const { container } = render(<Treemap nodes={READOUT} squarified />);
  fireEvent.mouseEnter(container.querySelector(".lf-treemap__hot")!);
  const tip = container.querySelector(".lf-treemap__tip")!;
  expect(tip.textContent).toContain("AAPL");
  expect(tip.textContent).toContain("SGD 1,000.00"); // served, not formatted here
  expect(tip.textContent).toContain("+1.20%");
  expect(tip.textContent).toContain("Today’s change"); // D-025 — the only term for this metric
  fireEvent.mouseLeave(container.querySelector(".lf-treemap__hot")!);
  expect(tip.textContent).toBe("");
});

test("keyboard FOCUS shows the same readout — never hover-only (WCAG 1.4.13)", () => {
  const { container } = render(<Treemap nodes={READOUT} squarified />);
  const hots = container.querySelectorAll(".lf-treemap__hot");
  expect(hots.length).toBe(2); // a tile with only a readout is still focusable
  fireEvent.focus(hots[0]);
  expect(container.querySelector(".lf-treemap__tip")!.textContent).toContain("AAPL");
  fireEvent.blur(hots[0]);
  expect(container.querySelector(".lf-treemap__tip")!.textContent).toBe("");
});

test("a missing Today's change renders an em dash + the reason, never a fabricated 0% (Guarantee 3)", () => {
  const { container } = render(<Treemap nodes={READOUT} squarified />);
  const home = [...container.querySelectorAll(".lf-treemap__hot")].find((h) => h.getAttribute("aria-label") === "Home")!;
  fireEvent.mouseEnter(home);
  const text = container.querySelector(".lf-treemap__tip")!.textContent!;
  expect(text).toContain("—");
  expect(text).toContain("No prior close to compare.");
  expect(text).not.toContain("0.00%");
});
