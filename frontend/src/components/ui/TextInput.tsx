import "./inputs.css";

// Plain free-text entry (DESIGN-SYSTEM §5.1, amended 2026-07-10 — Holdings
// page-build): the sanctioned control for name-like free text that is NOT a
// money/date/quantity/categorical field (e.g. manual-asset label, tag entry,
// free-text names). Wraps the native input internally so §6's "no raw <input>"
// rule holds. NOT for categorical data — use MasterSelect for those.
export interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  maxLength?: number;
  onEnter?: () => void;
  "aria-label": string;
}

export function TextInput({
  value,
  onChange,
  placeholder,
  disabled,
  maxLength,
  onEnter,
  "aria-label": ariaLabel,
}: TextInputProps) {
  return (
    <span className={`lf-field lf-field--block${disabled ? " lf-field--disabled" : ""}`}>
      <input
        className="lf-field__input"
        type="text"
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        maxLength={maxLength}
        aria-label={ariaLabel}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={
          onEnter
            ? (e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onEnter();
                }
              }
            : undefined
        }
      />
    </span>
  );
}
