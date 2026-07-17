// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import "./structure.css";

export type ButtonVariant = "default" | "primary" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** The visible text label. MANDATORY — an icon is never a label on its own (WCAG). */
  children: ReactNode;
  /** Optional leading icon (lucide). Sized by `--icon-size` and optically centred with the label. */
  icon?: LucideIcon;
  variant?: ButtonVariant;
  /** §14dr-8 — async-action standard: in-flight state. Disables the button (re-click
   *  guarded), sets `aria-busy`, and shows a PERCEPTIBLE spinner (replacing the leading
   *  icon). The completion signal is the caller's served-outcome toast — never a
   *  silent no-op. Reduced-motion stills the spinner (it stays visible). */
  loading?: boolean;
}

/**
 * Button — THE button, and THE icon+label treatment (DESIGN-SYSTEM §5.4 amendment,
 * page-cash-flow §9-13).
 *
 * Extracted at the THIRD occurrence of the same page-local pattern, per the centralization rule the
 * `Segmented` / `StatusChip` extractions set — and per the trigger page-policy §12po3-1 recorded
 * explicitly ("the 3rd occurrence EXTRACTS the shared treatment"):
 *
 *   1. Review   — "Mark reviewed"  (`.rv__markbtn` + `.rv__markicon`)
 *   2. Policy   — "Set/Edit policy" (`.pol__btn`)
 *   3. Cash flow — "Add obligation / contribution / goal"
 *
 * Both page-local copies are MIGRATED onto this component and DELETED; none remains.
 *
 * The treatment (what the copies each re-derived): a **centred inline-flex row** with a **token
 * gap**, so the icon lands on the label's optical centre instead of baseline-aligning against it.
 * The icon is sized by **`--icon-size`** — `.lf-btn svg` already does this globally, so a per-call
 * `size` prop is a lie about what controls it and is not offered here.
 */
export function Button({ children, icon: Icon, variant = "default", loading = false, disabled, className, ...rest }: ButtonProps) {
  const cls = [
    "lf-btn",
    variant === "primary" ? "lf-btn--primary" : "",
    // `danger` — destructive, irreversible-or-drastic actions ONLY (DESIGN-SYSTEM §5.4 danger-variant
    // amendment). It SIGNALS; protection is ConfirmDialog (+ the D-103 fresh purge-PIN where it applies).
    variant === "danger" ? "lf-btn--danger" : "",
    Icon || loading ? "lf-btn--icon" : "",
    loading ? "lf-btn--loading" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" className={cls} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? (
        <span className="lf-btn__spinner" aria-hidden="true" />
      ) : (
        Icon && <Icon aria-hidden="true" focusable="false" />
      )}
      {children}
    </button>
  );
}
