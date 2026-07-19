# Vendored assets — provenance register

*Hand-maintained. **This file is the opposite of `LICENSES.md`**, and the distinction is the
reason it exists.*

`LICENSES.md` and `NOTICE` are **GENERATED** (`scripts/license_audit.py`; `write_notice()` rewrites
`NOTICE` wholesale), and they audit **DEPENDENCIES** — which, as `NOTICE` says in as many words,
*"LedgerFrame does not vendor or redistribute … a source install fetches them from their own
registries."*

A **vendored asset is the opposite case**: a file that IS committed to this repository and IS
redistributed with it. Neither generated file has anywhere to put one, and hand-editing either
would be silently erased on the next regeneration. So vendored assets are recorded here.

> **Created 2026-07-19** (page-help §9-bis-11, Settings → About). The author photo below is the
> **first** vendored asset in the repository; before it, every third-party artifact was a
> dependency fetched at install time.

## Register

| Asset | Source | Provided by | Vendored | sha256 (first 16) |
|---|---|---|---|---|
| `frontend/src/assets/author-gs.jpg` | `gs.jpg`, `github.com/gopalasubramanium/me` | **The owner** (his own repository, his own likeness) | 2026-07-19 | `a8833cc529f3f70a` |

### `author-gs.jpg` — the author photo on Settings → About

- **THE PRODUCT NEVER FETCHES IT AT RUNTIME.** It is imported as a build asset and served from the
  local bundle. This is not a preference: a local-first appliance that advertises **no telemetry
  and no egress** cannot reach out to `github.com` to draw a face, and a remote `<img>` would leak
  a request every time the About tab opened — under no-egress, it would leak or fail visibly. The
  3a pre-pass asserts, from the page's own request log, that **no network request leaves for it**.
- **Processed before committing, and the processing is part of the record:** cropped
  head-and-shoulders from the 1280×1148 original and resized to **256×256** (it renders as a ~64px
  round avatar; a full-frame portrait would be a smudge at that size), re-encoded at quality 86 →
  **11.6 KB**.
- **EXIF STRIPPED.** The original carried camera/software metadata (a Picasa tag). A product whose
  entire posture is *your data stays on your machine* should not ship personal metadata into a
  public repository as a side effect of showing a photograph. The vendored file has **zero** EXIF
  entries.

> ### ⚠ NEEDS DECISION — the owner's, not this file's
> **Under what terms is the photograph licensed?** The repository ships under
> **AGPL-3.0-or-later**, and every source file carries that SPDX header — but a **photograph of a
> person is not source code**, and the owner may well not intend to place his own likeness under a
> licence that grants everyone the right to redistribute and modify it.
>
> **This file deliberately does not answer that.** Stating a licence for the owner's likeness on
> his behalf would be fabricating a legal position, which is exactly the kind of claim the
> adjudication convention exists to prevent (*"whether a flagged licence is compatible … is an
> **owner/counsel** decision, not a script's"* — `LICENSES.md`). Recorded in `CURRENT.md` under
> **Needs decision**. What IS established: the owner supplied the file, from his own repository,
> for this use.
