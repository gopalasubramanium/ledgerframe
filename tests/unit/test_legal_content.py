# SPDX-License-Identifier: AGPL-3.0-or-later
"""LEGAL CONTENT GUARDS (page-legal §9, ruled 2026-07-19).

The Legal page's copy is SERVED (§9-3) for exactly one reason: **server-side corpora are bound by
guards**. This module is the redemption of that rationale. If Legal's strings were a frontend
constant, none of what follows could exist, and the page whose entire job is to be true would be
the only page in the product nothing checks.

WHAT IS GUARDED HERE
--------------------
* **AC-L3** — the seven Product Guarantees are VERBATIM. Asserted by string equality against
  ``docs/specs/PRODUCT-SPEC.md`` §3, parsed at test time. Not by eye, and not by a copy of the
  spec text living in the test (which would only prove the test agrees with itself).
* **AC-L5** — the §9-8 NEVER list, as four independent bites with named RED specimens.
* the served shape matches what the IA says Legal owns, so a section cannot quietly go missing.

The AC-L6 scoped-caveat registry lives in ``test_scoped_caveats.py``: it guards the TEN OTHER
surfaces, not this one, and a guard belongs with what it protects.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.help_markup import strip_markup
from app.services.legal import GUARANTEES, PACK_FOOTER, all_legal

REPO = Path(__file__).resolve().parents[2]
PRODUCT_SPEC = REPO / "docs" / "specs" / "PRODUCT-SPEC.md"


# ---------------------------------------------------------------------------------------------
# AC-L3 — VERBATIM, ENFORCED
# ---------------------------------------------------------------------------------------------
def _spec_guarantees() -> list[str]:
    """Parse the seven guarantees out of PRODUCT-SPEC.md §3.

    Whitespace-normalised on BOTH sides: the spec hard-wraps inside a blockquote at 76 columns,
    which is a rendering of the sentence rather than the sentence. "Verbatim" means the same words
    in the same order — never the same line breaks. Every other difference is a failure.
    """
    text = PRODUCT_SPEC.read_text(encoding="utf-8")
    section = text.split("## 3. Product Guarantees")[1].split("\n---")[0]
    # BLOCKQUOTE LINES ONLY. Seen RED writing this: §3 ends with an unquoted parenthetical —
    # "(The validation contract itself is normative in SECURITY-BASELINE.md.)" — which a
    # strip-the-markers parser silently appends to Guarantee 7. The guarantees are exactly what
    # the blockquote contains; the prose around it is the spec talking ABOUT them.
    body = "\n".join(line[2:] if line.startswith("> ") else ""
                     for line in section.splitlines() if line.startswith(">"))
    items = re.split(r"^\d+\.\s+", body, flags=re.M)[1:]
    return [" ".join(i.split()) for i in items]


def test_the_spec_parser_can_still_see_the_guarantees():
    """The parser's OWN health check — the part that is allowed to fail.

    A parser that drifts (the heading is renamed, the blockquote is dropped, the list is
    restyled) returns ZERO guarantees, and a zero-length comparison passes vacuously against a
    zero-length slice. That silent-success mode is the whole risk of parsing a spec, so the count
    is asserted here and nowhere else. Seven is not incidental: PRODUCT-SPEC.md:60 names this
    block as destined for the Legal page, and the page's own copy calls them "these seven".
    """
    parsed = _spec_guarantees()
    assert len(parsed) == 7, (
        f"parsed {len(parsed)} guarantees from PRODUCT-SPEC.md §3, expected 7 — the spec's heading, "
        f"blockquote or list format has drifted and this file's verbatim check has gone blind."
    )


@pytest.mark.parametrize("n", range(7))
def test_each_guarantee_is_served_VERBATIM_from_the_spec(n: int):
    """AC-L3. String equality, per guarantee, so a failure names WHICH one drifted.

    Editing either side alone goes RED — which is the point. The wording is not the Legal page's
    to improve: it is ratified in DECISIONS.md, mirrored into PRODUCT-SPEC.md, and *"destined
    verbatim for … the Legal page"* (PRODUCT-SPEC.md:60). Amend the spec and this guard carries
    the change across.
    """
    spec = _spec_guarantees()
    assert GUARANTEES[n] == spec[n], (
        f"Guarantee {n + 1} is NOT verbatim.\n"
        f"  spec  : {spec[n]!r}\n"
        f"  served: {GUARANTEES[n]!r}\n"
        f"Fix the SPEC (docs/specs/PRODUCT-SPEC.md §3) — never app/services/legal.py alone."
    )


def test_the_page_serves_all_seven_and_in_the_spec_order():
    served = all_legal()["guarantees"]["items"]
    assert served == list(_spec_guarantees())


# ---------------------------------------------------------------------------------------------
# AC-L5 — THE NEVER LIST (page-legal §9-8, owner)
#
# Four bites, one per lettered constraint, because "the page claims nothing false" is not a thing
# a test can assert — but each of the four specific ways this page would go wrong IS.
#
# Every bite reads MARKUP-STRIPPED text, for the reason help_markup.py records: an inline marker
# inside a phrase breaks phrase-matching, so `**secure**` would sail past a guard looking for
# `\bsecure\b` and the guard would be green on the exact copy it exists to catch.
# ---------------------------------------------------------------------------------------------
def _all_prose() -> list[tuple[str, str]]:
    """(where, text) for every user-visible string the Legal page serves, markup stripped."""
    d = all_legal()
    out = [(f"section:{s['id']}", strip_markup(s["body"])) for s in d["sections"]]
    out += [(f"section-title:{s['id']}", s["title"]) for s in d["sections"]]
    out.append(("guarantees:intro", strip_markup(d["guarantees"]["intro"])))
    out += [(f"guarantee:{i}", strip_markup(g)) for i, g in enumerate(d["guarantees"]["items"], 1)]
    out += [(f"pointer:{p['file']}", strip_markup(p["what"])) for p in d["pointers"]]
    out.append(("pack_footer", strip_markup(d["pack_footer"])))
    return out


# (a) No jurisdiction-compliance claim. The product has NO jurisdiction logic at all (D-077,
#     Guarantee 4), so naming a regulator, statute or tax code as something it complies with is
#     not an overstatement — it is a FABRICATION, against Guarantee 3.
_JURISDICTION_CLAIMS = re.compile(
    r"\b(complies?\s+with|compliant\s+with|in\s+compliance\s+with|conforms?\s+to|"
    r"approved\s+by|registered\s+with|regulated\s+by|licen[cs]ed\s+by)\b",
    re.I,
)

# (b) Warranty / indemnity / liability terms of the product's OWN. The AGPL's sections 15 and 16
#     ARE the warranty position; restating them in other words risks contradicting the licence the
#     product ships under. Naming them is allowed — that is what the page does — so the guard
#     fires on the product ASSERTING such a term, not on the words appearing.
_OWN_WARRANTY_TERMS = re.compile(
    r"\b(we\s+(warrant|indemnif\w+|guarantee)|"
    r"(is|are)\s+(warranted|indemnified)|"
    r"(no|limited)\s+liability\s+(is|shall)|"
    r"hold\s+harmless|"
    r"to\s+the\s+(maximum|fullest)\s+extent\s+permitted)\b",
    re.I,
)

# (c) Abstract self-praise. SECURITY-BASELINE.md is normative and SPECIFIC; adjectives are not.
#     A product that calls itself secure has said nothing checkable and implied something it has
#     not earned.
_ABSTRACT_ADJECTIVES = re.compile(
    r"\b(is|are|fully|completely|entirely)\s+(secure|compliant|audited|bank[- ]grade|"
    r"military[- ]grade|hack[- ]proof|unbreakable)\b",
    re.I,
)

# (d) Implied counsel review. §9-8 makes this the owner's statement to make, never the build's.
_COUNSEL_REVIEW = re.compile(
    r"\b(reviewed\s+by\s+(counsel|(a\s+)?lawyer|(an\s+)?attorney|legal\s+counsel)|"
    r"attorney[- ]reviewed|lawyer[- ]reviewed|"
    r"legal(ly)?\s+(reviewed|vetted|approved)|"
    r"(this|the)\s+(page|document)\s+constitutes\s+legal\s+advice)\b",
    re.I,
)

_NEVER = (
    ("(a) a jurisdiction-compliance claim", _JURISDICTION_CLAIMS),
    ("(b) a warranty/indemnity term beyond the AGPL", _OWN_WARRANTY_TERMS),
    ('(c) abstract "secure/compliant/audited"', _ABSTRACT_ADJECTIVES),
    ("(d) implied review by counsel", _COUNSEL_REVIEW),
)


@pytest.mark.parametrize("label,pattern", _NEVER, ids=[n for n, _ in _NEVER])
def test_the_legal_page_never_says_it(label: str, pattern: re.Pattern[str]):
    """AC-L5 — the §9-8 NEVER list, on the shipped copy."""
    hits = [(where, pattern.search(text).group(0))  # type: ignore[union-attr]
            for where, text in _all_prose() if pattern.search(text)]
    assert not hits, (
        f"THE LEGAL PAGE MUST NEVER MAKE {label} (page-legal §9-8, owner 2026-07-19).\n"
        + "\n".join(f"  {where}: {found!r}" for where, found in hits)
    )


# The RED specimens. §9-8's constraints are only real if the guard above actually bites; a
# never-tested regex is a comment with syntax. Each specimen is copy this page could PLAUSIBLY
# have shipped — the reassuring sentence a legal page naturally drifts toward — not a strawman.
_RED_SPECIMENS = (
    ("(a)", "LedgerFrame complies with SEC and FCA reporting requirements, and its tax outputs "
            "conform to IRS Publication 550."),
    ("(b)", "We warrant that the figures are accurate and will indemnify you for any loss arising "
            "from their use, to the fullest extent permitted by law."),
    ("(c)", "LedgerFrame is secure and fully audited; your data is protected with bank-grade "
            "encryption."),
    ("(d)", "This page has been reviewed by counsel and legally approved for your jurisdiction."),
)


@pytest.mark.parametrize("letter,specimen", _RED_SPECIMENS, ids=[l for l, _ in _RED_SPECIMENS])
def test_the_never_guard_BITES_its_red_specimen(letter: str, specimen: str):
    """Fail-first, kept: proof each bite catches the copy it exists to catch.

    Seen RED before the guard's regexes were written — this test is the RED evidence, retained in
    the suite rather than reported once in a commit message. A guard whose failing case lives only
    in a close report cannot be re-verified by the next reader.
    """
    matched = [label for label, pattern in _NEVER if pattern.search(specimen)]
    assert matched, (
        f"NEVER-list bite {letter} does NOT catch its own specimen — the guard is decorative:\n"
        f"  {specimen!r}"
    )


# ---------------------------------------------------------------------------------------------
# SHAPE — the four IA contents, present
# ---------------------------------------------------------------------------------------------
def test_the_page_carries_the_four_contents_the_IA_says_it_owns():
    """INFORMATION-ARCHITECTURE.md:86 fixes Legal's scope: *"License, disclaimer, Product
    Guarantees, no-jurisdiction-tax stance."* Four owned contents, ratified by the IA — this
    milestone may not drop one, and may not add a fifth without an IA amendment.
    """
    d = all_legal()
    ids = {s["id"] for s in d["sections"]}
    assert {"position", "licence", "jurisdiction"} <= ids, ids
    assert d["guarantees"]["items"], "the Guarantees block is empty"


def test_pointers_name_files_and_never_urls():
    """§9-5: a pointer NAMES THE FILE THAT SHIPS WITH THE SOURCE, never a URL.

    `LegalPointer` has no url field, so this cannot be violated by adding one — but a URL pasted
    into `file` or `what` would slip through the schema. A local-first product's legal page is the
    last surface that should stop working offline.
    """
    d = all_legal()
    for p in d["pointers"]:
        blob = f"{p['file']} {p['what']}"
        assert not re.search(r"https?://|www\.", blob, re.I), (
            f"pointer {p['file']!r} carries a URL. A local-first product cannot link to a hosted "
            f"licence page (page-legal §9-5) — name the file that ships with the source."
        )


def test_the_pack_footer_is_one_line_and_states_the_product_level_position():
    """§9-4: ONE line, not the Guarantees block. The Pack is a print artifact; seven paragraphs
    of guarantee on every page of every export is why this was ruled a single line."""
    assert "\n" not in PACK_FOOTER, "the Pack footer is ONE line (page-legal §9-4)"
    plain = strip_markup(PACK_FOOTER).lower()
    assert "reporting only" in plain
    assert "advice" in plain
