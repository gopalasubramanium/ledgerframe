import { useEffect, useState } from "react";
import { fetchHealth } from "./api/health";
import type { HealthResult } from "./api/health";
import { useTheme } from "./theme/theme-context";
import "./App.css";

const THEME_LABEL: Record<string, string> = {
  light: "Light",
  dark: "Dark",
  system: "System",
};

function HealthRow({ health }: { health: HealthResult | null }) {
  let dot = "boot__dot";
  let text = "checking…";
  if (health?.state === "ok") {
    dot += " boot__dot--ok";
    text = `ok · v${health.version}`;
  } else if (health?.state === "unreachable") {
    dot += " boot__dot--bad";
    text = `unreachable · ${health.detail}`;
  }
  return (
    <div className="boot__row">
      <span className="boot__label">Backend</span>
      <span className="boot__status">
        <span className={dot} aria-hidden="true" />
        <span className="boot__value">{text}</span>
      </span>
    </div>
  );
}

export default function App() {
  const { choice, resolved, cycle } = useTheme();
  const [health, setHealth] = useState<HealthResult | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchHealth(ctrl.signal).then(setHealth);
    return () => ctrl.abort();
  }, []);

  return (
    <div className="boot">
      <div className="boot__card">
        <div>
          <h1 className="boot__title">LedgerFrame</h1>
          <p className="boot__subtitle">
            Frontend scaffold — design system &amp; component library.
          </p>
        </div>

        <HealthRow health={health} />

        <div className="boot__row">
          <span className="boot__label">Theme</span>
          <button
            type="button"
            className="boot__btn"
            onClick={cycle}
            aria-label="Cycle theme: light, dark, system"
          >
            {THEME_LABEL[choice]}
            {choice === "system" ? ` (${resolved})` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}
