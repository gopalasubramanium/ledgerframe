// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "./ConfirmDialog";

// §14dr-23: the purge control's GLOSSARY "Purge" definition is served via a [Help]
// popover INSIDE the ConfirmDialog (helpTerm), not a hover tooltip on a button.
describe("ConfirmDialog helpTerm", () => {
  it("renders a [Help] affordance that reveals the term definition on hover", async () => {
    const user = userEvent.setup();
    render(
      <ConfirmDialog
        open
        title="Permanently delete trashed rows?"
        message="This permanently deletes all trashed holdings and transactions."
        helpTerm="term-purge"
        requirePin
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    const help = screen.getByText("[Help]");
    expect(help).toBeInTheDocument();
    await user.hover(help);
    // The GLOSSARY "Purge" definition surfaces (spelling policed by the parity guard).
    expect(await screen.findByText(/emptying the trash/i)).toBeInTheDocument();
  });

  it("omits the [Help] affordance when no helpTerm is given", () => {
    render(
      <ConfirmDialog open title="Delete?" message="Gone for good." onCancel={vi.fn()} onConfirm={vi.fn()} />,
    );
    expect(screen.queryByText("[Help]")).not.toBeInTheDocument();
  });
});
