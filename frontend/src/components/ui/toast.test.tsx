import { afterEach, expect, test } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { ToastProvider } from "./ToastProvider";
import { useToast } from "./toast-context";

afterEach(() => cleanup());

// A tiny harness that exposes show() so a test can fire it imperatively.
let fire: (msg: string, tone?: "info" | "warning") => void = () => {};
function Harness() {
  const toast = useToast();
  fire = (message, tone) => toast.show(tone ? { message, tone } : { message });
  return null;
}

// §14dr-6 — dedupe at the toast standard: the SAME message while still visible must
// not stack a second (or third) identical toast. Fail-first RED: today show()
// appends unconditionally, so three identical calls render three toasts.
test("identical messages while visible do not stack (dedupe)", () => {
  render(
    <ToastProvider>
      <Harness />
    </ToastProvider>,
  );
  act(() => {
    fire("Saved.");
    fire("Saved.");
    fire("Saved.");
  });
  expect(screen.getAllByText("Saved.")).toHaveLength(1);
});

// A genuinely different message (or tone) is still its own toast — dedupe must not
// swallow distinct notifications.
test("distinct messages and tones still show separately", () => {
  render(
    <ToastProvider>
      <Harness />
    </ToastProvider>,
  );
  act(() => {
    fire("Saved.");
    fire("Refreshed 3 of 5.");
    fire("Saved.", "warning"); // same text, different tone → distinct
  });
  expect(screen.getByText("Refreshed 3 of 5.")).toBeInTheDocument();
  expect(screen.getAllByText("Saved.")).toHaveLength(2);
});
