import { apiGet } from "./client";

// Legal reader — page-legal §3a/§3b. The page's copy is SERVED (§9-3, owner 2026-07-19).
//
// The deciding rationale was the GUARD BAR, not the transport: accuracy guards bind server-side
// corpora, so this copy is held to the same truth bar as Help (`tests/unit/test_legal_accuracy.py`,
// `test_legal_content.py`). A frontend constant would have been cheaper and would have inherited
// nothing — on the one page whose entire job is to be true.
//
// The page renders every string VERBATIM and composes nothing. There is no money on this surface,
// so D-105 is N/A here — and D-105 governs money, never prose (the correction recorded at §9-3).

export interface LegalSection {
  id: string;
  title: string;
  body: string;
}

export interface LegalCommitments {
  title: string;
  intro: string;
  /** The seven Product Commitments, VERBATIM from PRODUCT-SPEC.md §3 — string equality is asserted
   *  server-side (AC-L3). The page renders them in the served order and never renumbers,
   *  reorders, paraphrases or truncates them. */
  items: string[];
}

/** A file that ships with the source.
 *
 *  Deliberately carries NO url, and the omission is the contract (§9-5): a local-first product
 *  cannot link to a hosted licence page, so a pointer NAMES A FILE. There is nowhere in this type
 *  to put a URL, which is how the rule is kept rather than remembered. */
export interface LegalPointer {
  file: string;
  what: string;
}

export interface LegalResponse {
  /** The served markup dialect the prose is written in (`lf-help-markup-1`) — the same subset
   *  Help uses, rendered by the same route-local renderer. Versioned, so a future change to the
   *  subset is a visible contract change rather than a silent reinterpretation. */
  markup: string;
  sections: LegalSection[];
  commitments: LegalCommitments;
  pointers: LegalPointer[];
  /** The single product-level line the Reports Pack renders (§9-4). Served here because Legal
   *  OWNS the string and the Pack RENDERS it — one source, two renderers, asserted byte-for-byte
   *  server-side (AC-L8). The page does not display this field; it is on the response so the two
   *  renderers are provably reading the same bytes. */
  pack_footer: string;
}

/** The whole Legal page. One read, no parameters — the copy is static and never personalised. */
export function legalContent() {
  return apiGet<LegalResponse>("/legal");
}
