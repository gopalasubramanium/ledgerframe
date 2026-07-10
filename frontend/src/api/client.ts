// Thin fetch helper. Same-origin in production; the Vite dev proxy forwards
// /api and /health to the backend (vite.config.ts). Never throws for a non-2xx —
// callers get a typed Result so pages can render honest error states.

export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number };

const BASE = "/api/v1";

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<Result<T>> {
  try {
    const res = await fetch(`${BASE}${path}`, init);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* non-JSON error body */
      }
      return { ok: false, error: detail, status: res.status };
    }
    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "network error" };
  }
}

export function apiGet<T>(path: string): Promise<Result<T>> {
  return request<T>(path);
}

export function apiSend<T>(
  path: string,
  method: "POST" | "PUT" | "DELETE" | "PATCH",
  body?: unknown,
): Promise<Result<T>> {
  return request<T>(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiUpload<T>(path: string, file: File): Promise<Result<T>> {
  const form = new FormData();
  form.append("file", file);
  return request<T>(path, { method: "POST", body: form });
}

/** Trigger a server-side file download (P-5 — the client never builds the file). */
export function apiDownload(path: string): void {
  const a = document.createElement("a");
  a.href = `${BASE}${path}`;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}
