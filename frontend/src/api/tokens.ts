// API-token card (page-settings Privacy tab; D-069 / §9-8). Create/list/revoke go through
// /tokens, which is require_session — a read-only API token can neither mint nor revoke tokens
// (403). The raw token is returned ONCE at creation and never retrievable after (tokens.py).
import { apiGet, apiSend } from "./client";

export interface TokenMeta {
  id: number;
  name: string;
  prefix: string;
  /** ISO timestamp or null; rendered as a served string (D-105). A never-used token → null → em dash. */
  created_at: string | null;
  last_used_at: string | null;
}

export interface CreatedToken {
  id: number;
  name: string;
  prefix: string;
  /** The raw token — shown exactly once at creation; never re-read. */
  token: string;
  note: string;
}

export async function listTokens(): Promise<TokenMeta[] | null> {
  const r = await apiGet<{ tokens: TokenMeta[] }>("/tokens");
  return r.ok ? r.data.tokens : null;
}

export async function createToken(
  name: string,
): Promise<{ ok: true; token: CreatedToken } | { ok: false; error: string }> {
  const r = await apiSend<CreatedToken>("/tokens", "POST", { name });
  return r.ok ? { ok: true, token: r.data } : { ok: false, error: r.error };
}

/** Revoke a token — require_session (§9-8): the SESSION, not a fresh PIN. D-103 binds only the
 *  destructive purge; a revoked token is re-creatable, so revoke does not take a fresh PIN. */
export async function revokeToken(
  id: number,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const r = await apiSend<{ ok?: boolean }>(`/tokens/${id}`, "DELETE");
  return r.ok ? { ok: true } : { ok: false, error: r.error };
}
