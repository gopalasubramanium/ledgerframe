import { useId, type ReactNode } from "react";
import { Check } from "lucide-react";
import "./inputs.css";

// PROPOSED (DESIGN-SYSTEM §5.1 amendment, page-legal §11-J). The sanctioned boolean
// CONSENT control — the ratified inventory had a Switch (a setting you change) and no
// checkbox (a statement you affirm), which is how the Acceptance Gate came to hand-roll
// a raw <input type="checkbox">. See §6: the primitive owns the native element.
//
// The native input is kept and visually replaced, NOT reimplemented on a <button> the way
// Switch is. A checkbox that carries consent is submitted, announced and operated by
// machinery this component does not own — assistive tech, autofill, the space key, the
// form itself — and the native element is the only thing that gets all of it right by
// construction. Switch can afford a button because `role="switch"` has no native element;
// a checkbox has one, so borrowing it is the cheaper AND the more correct choice.
//
// NO COPY LIVES HERE. `label` is whatever the caller passes; on the Acceptance Gate that
// is a SERVED string (page-legal §9-3/§9-8), because the sentence a person is recorded as
// having agreed to is held to the server-side accuracy bar.
export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** The visible, clickable label. Omit only when `aria-label` names the control instead. */
  label?: ReactNode;
  disabled?: boolean;
  "aria-label"?: string;
  "aria-describedby"?: string;
}

export function Checkbox({
  checked,
  onChange,
  label,
  disabled,
  "aria-label": ariaLabel,
  "aria-describedby": describedBy,
}: CheckboxProps) {
  const id = useId();

  return (
    <span className={`lf-checkbox${disabled ? " is-disabled" : ""}`}>
      {/* The real control: focusable, space-operable, announced as a checkbox. It is made
          transparent and laid over the drawn box rather than `display:none`d — a hidden
          input is not focusable, which would take the keyboard away from the one control on
          this surface that a person must operate to proceed. */}
      <input
        id={id}
        className="lf-checkbox__input"
        type="checkbox"
        checked={checked}
        disabled={disabled}
        aria-label={label === undefined ? ariaLabel : undefined}
        aria-describedby={describedBy}
        onChange={(e) => onChange(e.target.checked)}
      />
      {/* The drawn box carries no meaning the input has not already announced. */}
      <span className="lf-checkbox__box" aria-hidden="true">
        <Check className="lf-checkbox__tick" size={14} strokeWidth={3} />
      </span>
      {label !== undefined && (
        <label className="lf-checkbox__label" htmlFor={id}>
          {label}
        </label>
      )}
    </span>
  );
}
