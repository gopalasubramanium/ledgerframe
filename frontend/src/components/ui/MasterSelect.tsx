import { useMemo, useState } from "react";
import "./inputs.css";
import { getMaster, humanize } from "../../mocks/refdata";
import { useRefdataVocabs } from "../../refdata/refdata-context";

// THE select for every categorical field (DESIGN-SYSTEM §5.1 / §6). Fixed-vocab
// VALUES come from GET /refdata (D-005) when a RefdataProvider is present; the
// labelled registry provides display labels + the extensible flag and is the
// graceful offline fallback. Never an inline option list. `allowCreate` is
// honoured only where the master is user-extensible (institution, sector, tag).
export interface MasterSelectProps {
  /** Vocabulary / master id (see mocks/refdata MASTERS). */
  master: string;
  value: string;
  onChange: (value: string) => void;
  allowCreate?: boolean;
  disabled?: boolean;
  "aria-label"?: string;
}

export function MasterSelect({
  master,
  value,
  onChange,
  allowCreate,
  disabled,
  "aria-label": ariaLabel,
}: MasterSelectProps) {
  const def = useMemo(() => getMaster(master), [master]);
  const canCreate = Boolean(allowCreate && def.extensible);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState("");
  const vocabs = useRefdataVocabs();

  // Prefer live /refdata values for this vocabulary (D-005); fall back to the
  // labelled registry offline. Value may be a just-created row not yet in the
  // seed — show it regardless.
  const options = useMemo(() => {
    const live = vocabs?.[master];
    const base = live
      ? live.map((v) => ({ value: v, label: humanize(v) }))
      : def.options;
    if (value && !base.some((o) => o.value === value)) {
      return [...base, { value, label: value }];
    }
    return base;
  }, [vocabs, master, def.options, value]);

  if (creating) {
    return (
      <span className="lf-field lf-field--block">
        <input
          className="lf-field__input"
          autoFocus
          value={draft}
          placeholder={`New ${def.label.toLowerCase()}…`}
          aria-label={`New ${def.label}`}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && draft.trim()) {
              onChange(draft.trim());
              setCreating(false);
              setDraft("");
            } else if (e.key === "Escape") {
              setCreating(false);
              setDraft("");
            }
          }}
        />
      </span>
    );
  }

  return (
    <span
      className={`lf-field lf-field--block${disabled ? " lf-field--disabled" : ""}`}
    >
      <select
        className="lf-field__select"
        value={value}
        disabled={disabled}
        aria-label={ariaLabel ?? def.label}
        onChange={(e) => {
          if (e.target.value === "__create__") {
            setCreating(true);
            return;
          }
          onChange(e.target.value);
        }}
      >
        <option value="" disabled>
          Select {def.label.toLowerCase()}…
        </option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
        {canCreate && <option value="__create__">＋ Create new…</option>}
      </select>
    </span>
  );
}
