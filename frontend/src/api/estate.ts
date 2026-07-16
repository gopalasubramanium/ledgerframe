import { apiGet, apiSend } from "./client";

// Estate readers/writers — page-estate §3a. Canonical home for the will/executor profile
// (singleton), the contacts register (people + roles), and the key-document register
// (D-063 no-FK isolation). PER-ROW CRUD, [S]-gated (ambient PIN session, D-103 — no second
// prompt on save or delete). The whole page loads from ONE reader (`GET /estate`).
//
// There is NO money on this page (§9-3): the readiness figures are COUNTS, not money — no
// `*_display` strings, no base-currency affix. Every categorical (`will_status`, document
// `category`/`status`, contact `roles`) is rendered from the SERVED /refdata `{value,label}`
// label, never a client-side mapping (D-005). A blank optional field is an em dash, never 0.

export interface EstateProfile {
  will_status: string;               // none | draft | executed | needs_update (served vocabulary)
  will_location: string | null;
  executor: string | null;
  last_reviewed: string | null;
  next_review_date: string | null;
  notes: string | null;
}

export interface EstateContact {
  id: number;
  name: string;
  roles: string[];                   // subset of contact_role (served vocabulary)
  phone: string | null;
  email: string | null;
  notes: string | null;
}

export interface EstateDocument {
  id: number;
  title: string;
  category: string;                  // estate_doc_category (served vocabulary)
  location: string | null;
  status: string;                    // present | missing | outdated (served vocabulary)
  review_date: string | null;
  related_to: string | null;         // free text by design (D-063 no-FK)
  notes: string | null;
}

/** Raw COUNTS — never money (§9-3). `will_status` is SERVED but the page does not render it in
 *  the strip (it leads the profile card — §12es-1); it stays here for the shared reader. */
export interface EstateReadiness {
  docs_total: number;
  docs_present: number;
  docs_attention: number;
  will_status: string;
  nominees: number;
  executors: number;
  emergency: number;
}

export interface EstateResp {
  profile: EstateProfile;
  contacts: EstateContact[];
  documents: EstateDocument[];
  readiness: EstateReadiness;
  disclaimer: string;
}

export const fetchEstate = () => apiGet<EstateResp>("/estate");

// --- writes ([S]-gated; ambient PIN session, D-103 — no second prompt on save or delete) ------ //

export interface ProfileIn {
  will_status?: string | null;
  will_location?: string | null;
  executor?: string | null;
  last_reviewed?: string | null;
  next_review_date?: string | null;
  notes?: string | null;
}
export interface ContactIn {
  name: string;
  roles: string[];
  phone?: string | null;
  email?: string | null;
  notes?: string | null;
}
export interface DocumentIn {
  title: string;
  category: string;
  location?: string | null;
  status: string;
  review_date?: string | null;
  related_to?: string | null;
  notes?: string | null;
}

// Profile is a singleton — PUT, never POST/DELETE.
export const putProfile = (b: ProfileIn) => apiSend<{ ok: boolean }>("/estate/profile", "PUT", b);

export const createContact = (b: ContactIn) => apiSend<{ ok: boolean; id: number }>("/estate/contacts", "POST", b);
export const updateContact = (id: number, b: ContactIn) =>
  apiSend<{ ok: boolean; id: number }>(`/estate/contacts/${id}`, "PATCH", b);
export const deleteContact = (id: number) => apiSend<{ ok: boolean }>(`/estate/contacts/${id}`, "DELETE");

export const createDocument = (b: DocumentIn) => apiSend<{ ok: boolean; id: number }>("/estate/documents", "POST", b);
export const updateDocument = (id: number, b: DocumentIn) =>
  apiSend<{ ok: boolean; id: number }>(`/estate/documents/${id}`, "PATCH", b);
export const deleteDocument = (id: number) => apiSend<{ ok: boolean }>(`/estate/documents/${id}`, "DELETE");
