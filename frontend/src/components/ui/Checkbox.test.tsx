import { afterEach, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Checkbox } from "./Checkbox";

afterEach(cleanup);

// The primitive's whole justification is that these four behaviours live in ONE place. Each is
// asserted here so that "the gate has a working checkbox" and "the checkbox is correct" stop being
// the same claim — the failure that let a raw input ship (page-legal §11-J).

function Harness({ disabled, label }: { disabled?: boolean; label?: string }) {
  const [checked, setChecked] = useState(false);
  return (
    <Checkbox
      checked={checked}
      onChange={setChecked}
      disabled={disabled}
      label={label ?? "I accept the terms"}
    />
  );
}

test("Checkbox: the label is ASSOCIATED, not merely adjacent — it names the control and ticks it", async () => {
  render(<Harness />);
  // getByRole(name:) resolves through the label association. If htmlFor/id ever broke, the box
  // would still be findable by role but ANONYMOUS — which is what a screen reader would announce.
  const box = screen.getByRole("checkbox", { name: "I accept the terms" });
  expect((box as HTMLInputElement).checked).toBe(false);

  await userEvent.click(screen.getByText("I accept the terms"));
  expect((box as HTMLInputElement).checked).toBe(true);
});

test("Checkbox: operable from the keyboard — Tab reaches it, Space toggles it", async () => {
  render(<Harness />);
  const box = screen.getByRole("checkbox") as HTMLInputElement;

  await userEvent.tab();
  expect(document.activeElement).toBe(box);

  await userEvent.keyboard(" ");
  expect(box.checked).toBe(true);
  await userEvent.keyboard(" ");
  expect(box.checked).toBe(false);
});

test("Checkbox: disabled refuses BOTH the pointer and the keyboard, and is not tabbable", async () => {
  render(<Harness disabled />);
  const box = screen.getByRole("checkbox") as HTMLInputElement;
  expect(box.disabled).toBe(true);

  await userEvent.click(box);
  expect(box.checked).toBe(false);

  // A disabled control must be OUT of the tab order, not merely inert once reached.
  await userEvent.tab();
  expect(document.activeElement).not.toBe(box);
});

test("Checkbox: with no visible label, aria-label names it (and never both)", () => {
  render(<Checkbox checked={false} onChange={() => {}} aria-label="Include closed accounts" />);
  expect(screen.getByRole("checkbox", { name: "Include closed accounts" })).toBeTruthy();
});

test("Checkbox: the drawn box is decorative — the accessible name comes from the label alone", () => {
  const { container } = render(<Harness />);
  // If the drawn box were exposed, the name would double ("I accept the terms I accept the terms")
  // or the tick would announce as an image. It is aria-hidden, so it announces as nothing.
  expect(container.querySelector(".lf-checkbox__box")?.getAttribute("aria-hidden")).toBe("true");
  expect(screen.getByRole("checkbox").getAttribute("aria-label")).toBeNull();
});
