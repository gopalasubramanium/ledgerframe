# 07 — Security Posture

Threat model: a **single-user, local-first** appliance (default bind `127.0.0.1:8321`,
`app/core/config.py:45`). Security hardens the step-up to LAN exposure; it is **not** designed
for multi-user or internet exposure as-is (see Gaps).

## Current measures

### Authentication & sessions
- **Local PIN**, Argon2 hashed (`core/security.py:24`, `PasswordHasher()` defaults; `needs_rehash`
  supported). Min 4 chars (`PinPayload` 4-32).
- **Signed session tokens** (`itsdangerous.URLSafeTimedSerializer`, salt `ledgerframe-session`),
  time-limited to `autolock_minutes` (default 15). Cookie `lf_session` httponly, `samesite=strict`,
  `secure=False` (loopback), `max_age = autolock*60` (`auth.py:51`).
- **Token revocation** (`services/sessions.py`): per-token via `jti` blacklist (`RevokedToken`,
  set on `/auth/lock`); revoke-all via `users.tokens_valid_after` bump on **any PIN set/change**.
- **Read gate** (`deps.require_read_auth`, wired router-wide `main.py:193`): when a PIN is set,
  all `/api/v1` GET/HEAD require a valid session or read-only API token; auth routes stay open.
- **Mutation gate** (`require_auth`): no-PIN local → open; API token on a mutation → 403.
- **PIN-required gate** (`require_pin`): irreversible actions (`purge-deleted`) require a PIN to
  **exist** (403 otherwise) + valid session.
- **First-PIN takeover protection** (`auth.py:78`): when LAN-exposed, the first PIN may only be set
  from loopback; changing an existing PIN needs a valid token.

### Brute-force & rate limiting
- In-process per-IP limiter (`core/ratelimit.py`): exponential backoff after 5 failures
  (1,2,4,8,16s…), hard 15-min lockout after 10. 429 + `Retry-After`. Audit events
  `unlock_failed` / `rate_limited`.
- AI request limiter: `ai_max_requests_per_minute` (default 20) in-process (`ai/grounding.py:29`).

### Scoped API tokens (read-only)
- `core/security.generate_api_token`: `lft_` + 256-bit random; **only SHA-256 stored** (`ApiToken.
  token_hash`), raw shown once. Usable on **GET/HEAD only** (403 on any mutation, `deps.py:53`).
  Cannot manage tokens or purge (require_session/require_pin reject tokens). `last_used_at`
  throttled writes.

### Secrets handling
- Secrets live in **`.env` / environment only, never the DB** (config docstring, `Setting`/
  `ProviderConfig` explicitly "never holds secrets"). Kite credentials env-only (`config.py:62`).
- `envfile.apply_env` writes `.env` (chmod 0600) + updates `os.environ` (pydantic ranks env above
  file). API keys are **write-only** in the API (`has_api_key` boolean returned, never the value;
  `/system/ai-config`, `/system/data-source`).
- **Secret-key enforcement** (`main.py:85`): weak/placeholder/<32-char secret = warning on
  loopback, **hard refusal to start** when LAN-exposed.

### Network / headers
- Loopback bind by default; `0.0.0.0` only when `allow_lan` (and a PIN is required, `deps.py:96`).
- **Security headers** (ASGI middleware, `main.py:42`): `X-Content-Type-Options nosniff`,
  `X-Frame-Options DENY`, `Referrer-Policy no-referrer`, `Permissions-Policy` (geo/cam off, mic self),
  strict **CSP** (`default-src 'self'`, `script-src 'self'`, `style-src 'self' 'unsafe-inline'`,
  `img-src 'self' data:`, `connect-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`).
- **CORS** only in `env=development` (Vite origins) with credentials; production is same-origin.
- `/metrics` gated to loopback or a valid session (`require_metrics_access`).
- `security.txt` served (RFC 9116, `main.py:175`).

### Admin surface hardening
- `/system/admin` runs a **fixed allow-list** of actions/args (`system.py:24`) via
  `sudo -n /usr/local/sbin/ledgerframe-admin` — never free-form shell; requires auth; 120s timeout.
- **Kite**: read-only market data only; no order/trading endpoints exist; status never returns
  credentials.

### Backups
- SQLite online-backup snapshot; optional **`age` encryption** on device before write
  (recipient from config); chmod 0600; SHA-256 digest recorded; rotation (`backup_keep`).
- Restore: **path-traversal guards** (`_safe_backup_path`, `_safe_identity_path` must stay under
  backups/data dir), refuses overwrite without `force`, keeps a pre-restore safety copy.

### AI safety (see 05)
- Untrusted news sanitised (`sanitize_untrusted` — injection-phrase stripping, HTML strip).
- Model output **buffered & validated before display** (`validate_grounded_answer`): blocks
  recommendations, secret-like strings, unsupported numbers/tickers/quotes, real-time claims.
- Off-device transmission only via `openai_compatible` + non-loopback URL, surfaced in UI.

### Input validation
- Pydantic schemas on every write; CSV cells sanitised against formula injection
  (`csv_import.sanitize_cell`); manual-holding meta whitelisted per asset type
  (`portfolio.py:_META_KEYS`); source override validated (`validate_source_override`);
  tags capped (≤16), targets (≤200), field length caps throughout.

## Gaps / hardening needed before multi-user or internet exposure

| # | Gap | Detail | Severity |
|---|-----|--------|----------|
| 1 | **No multi-user model** | Single global PIN + single `User` row; no per-user data isolation, no roles. Entity is ownership metadata, not access control. | High (for multi-user) |
| 2 | **Cookie `secure=False`** | `auth.py:51` — fine on loopback, but over LAN/HTTP the session cookie can be sniffed. No HTTPS/TLS layer in-app. | High (LAN/remote) |
| 3 | **No CSRF token** | Mutations rely on same-site cookie + bearer; `samesite=strict` mitigates, but a strict CSRF token is absent. Bearer path + CORS-in-dev widen this. | Medium |
| 4 | **Rate limiter is in-process** | `ratelimit`/AI limiter reset on restart and are per-process (not shared across workers). A multi-process deploy weakens brute-force protection. | Medium |
| 5 | **App can write its own `.env` and run `sudo` helper** | `envfile` + `/system/admin` mean an authenticated session can change provider/keys and trigger privileged actions. Acceptable for owner-appliance; dangerous if auth is bypassed. | Medium |
| 6 | **PIN entropy** | 4-digit numeric PIN is low entropy; Argon2 + lockout mitigate online guessing, but a stolen DB + weak PIN is brute-forceable offline (Argon2 slows, doesn't stop). No PIN complexity policy. | Medium |
| 7 | **No auth on read when no PIN set** | By design the app is fully open (read + write) on a no-PIN local install. A user who enables LAN without setting a PIN is blocked from mutations but first-PIN rule is the only guard. | Medium |
| 8 | **Secrets reachable by process** | API keys in env/`.env` (0600) are readable by the app user and any code-exec bug; no OS keyring/secret manager. | Medium |
| 9 | **AI validator is heuristic** | Regex-based; a determined jailbreak or a number that coincidentally matches `_sig3` could slip a fabricated claim. Defence-in-depth only. | Low |
| 10 | **`/system/version-check` egress** | Outbound HTTPS to GitHub (best-effort). Minor info leak (IP) if privacy-sensitive; not gated by a "no network" mode. | Low |
| 11 | **No audit of reads** | `AuditEvent` covers auth/mutation/security/system, not data reads; no tamper-evidence on the audit log itself. | Low |
| 12 | **Dependency risk** | httpx, argon2-cffi, itsdangerous, sqlalchemy, fastapi, `age` binary (external). No SBOM/pin-audit surfaced here; verify pinned versions & CVE scanning in CI. | Review |
| 13 | **Restore trusts backup content** | A restored DB is trusted wholesale (only SHA-256 self-consistency + traversal checks); a malicious/corrupt backup file replaces the live DB. | Low |
| 14 | **CORS credentials in dev** | `allow_credentials=True` with fixed localhost origins in development only — ensure never enabled in production builds. | Low |

## Notes for the rebuild
- Preserve: env-only secrets, write-only key API, PIN Argon2 + lockout + revocation, CSP/headers,
  admin allow-list, backup encryption + traversal guards, AI validate-before-show.
- Add for exposure: TLS + `secure` cookies, CSRF tokens, shared/durable rate limiting, optional
  password (not just PIN), per-user isolation if multi-user, secret manager integration.

<!-- AUDIT COMPLETE -->
