// Backend health probe. Proves the FE↔BE seam without building any real page.
// The dev server proxies /health to the backend (vite.config.ts); production
// serves same-origin. Response shape from app/main.py: { status, version }.

export interface HealthOk {
  state: "ok";
  version: string;
}
export interface HealthUnreachable {
  state: "unreachable";
  detail: string;
}
export type HealthResult = HealthOk | HealthUnreachable;

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResult> {
  try {
    const res = await fetch("/health", { signal });
    if (!res.ok) {
      return { state: "unreachable", detail: `HTTP ${res.status}` };
    }
    const body = (await res.json()) as { status?: string; version?: string };
    if (body.status !== "ok") {
      return { state: "unreachable", detail: `status: ${body.status ?? "?"}` };
    }
    return { state: "ok", version: body.version ?? "unknown" };
  } catch (err) {
    const detail = err instanceof Error ? err.message : "network error";
    return { state: "unreachable", detail };
  }
}
