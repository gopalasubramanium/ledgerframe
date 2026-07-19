# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fixed information-only disclaimer — ONE definition, product-wide.

Commitment 2 (`PRODUCT-SPEC.md` §3) promises that *"every AI answer ends with the
fixed information-only disclaimer"*. **"Fixed" is a claim about identity across
paths**, and identity is not something a repeated literal can promise: before this
module the sentence was **13 separate literals** across `app/ai/`, `app/schemas/`,
`app/api/` and `app/services/` (AI-surfaces plan §0-C). They agreed by coincidence,
not by construction — one edit to one of them and the Commitment would have been
false with every test still green.

Two of those 13 made the point concretely:

- `app/schemas/ai.py`'s ``AIAnswer.disclaimer`` default looked canonical and governed
  **nothing the user ever sees** — the streaming path yields raw dicts, never that model.
- `app/services/briefing.py`'s idempotence check tested the **substring**
  ``"not financial advice"``, not the sentence, so an edit to the sentence would have
  left the check silently matching the old one.

**This module is the only place the sentence may be written.** Every other site imports
``DISCLAIMER``. That closure is enforced, not requested — `tests/unit/test_disclaimer_
closure.py` scans `app/` for the literal and fails on any second copy, and separately
asserts that **every terminal ``done`` event of the answer stream carries it**. Both
halves are needed: the scan alone would pass vacuously if the sentence vanished
entirely (CLAUDE.md — a guard is pinned against going blind).

⚠ **This is the product-level disclaimer (D-106 kind (b)) and nothing else.** The
**scoped caveats** — ``_REPORTING_CAPTION = "Reporting only, not advice."``
(`app/services/reports_pack.py`), and the per-figure caveats served by `review.py`,
`insurance.py`, `analytics.py` — are **D-106 kind (a): part of the figure**. `IA:425-440`
rules that Legal *"does not own, absorb, shorten, or centralise them"* and that removing
one is an **honesty regression** (AC-L6). **Do not consolidate them here.** This module
centralises the one sentence that was always meant to be one sentence.
"""

from __future__ import annotations

DISCLAIMER = "Information only, not financial advice."
"""The fixed information-only disclaimer (Commitment 2). Never rewrite in place."""

__all__ = ["DISCLAIMER"]
