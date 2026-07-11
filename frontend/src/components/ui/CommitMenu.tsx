import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "./inputs.css";
import "./firstrun.css"; // reuse the portaled .lf-combo__menu / .lf-combo__opt styles

// Internal helper for Select / MasterSelect's `onCommit` mode (first-run F3, walk batch 2).
// A button + portaled listbox that fires `onCommit` on EVERY pick — INCLUDING re-selecting
// the value already shown. A native <select> emits no `change` event for a same-value pick,
// so confirming a pre-filled suggestion (choose SGD when SGD is suggested) is impossible with
// it. This is NOT a new public primitive: Select/MasterSelect delegate here when a caller
// needs commit-on-pick semantics; every categorical field still goes through MasterSelect.
export interface CommitMenuOption {
  value: string;
  label: string;
}

export interface CommitMenuProps {
  options: CommitMenuOption[];
  value: string;
  onCommit: (value: string) => void;
  disabled?: boolean;
  "aria-label": string;
}

export function CommitMenu({ options, value, onCommit, disabled, "aria-label": ariaLabel }: CommitMenuProps) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find((o) => o.value === value)?.label ?? value ?? "";

  useLayoutEffect(() => {
    if (open && btnRef.current) setRect(btnRef.current.getBoundingClientRect());
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      // The menu is PORTALED outside btnRef — treat clicks inside it as inside too.
      const inside = btnRef.current?.contains(t) || menuRef.current?.contains(t);
      if (!inside) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pick = (v: string) => {
    onCommit(v); // fires for EVERY pick, incl. re-selecting the current value (the F3 fix)
    setOpen(false);
  };

  return (
    <span className={`lf-field lf-field--block${disabled ? " lf-field--disabled" : ""}`}>
      <button
        ref={btnRef}
        type="button"
        className="lf-field__select lf-commit__trigger"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
      >
        {selectedLabel || "Select…"}
      </button>
      {open &&
        rect &&
        createPortal(
          <div
            ref={menuRef}
            className="lf-combo__menu"
            role="listbox"
            aria-label={ariaLabel}
            style={{ position: "fixed", top: rect.bottom + 4, left: rect.left, width: rect.width }}
          >
            {options.map((o) => (
              <button
                key={o.value}
                type="button"
                role="option"
                aria-selected={o.value === value}
                className={`lf-combo__opt${o.value === value ? " is-active" : ""}`}
                onClick={() => pick(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </span>
  );
}
