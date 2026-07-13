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

test("nodes without href are non-interactive (back-compatible)", () => {
  const plain: TreemapNode[] = NODES.map((n) => ({ label: n.label, value: n.value, tone: n.tone, magnitudePct: n.magnitudePct }));
  const { container } = render(<Treemap nodes={plain} squarified />);
  expect(container.querySelectorAll(".lf-treemap__link").length).toBe(0);
});
