# SPDX-License-Identifier: AGPL-3.0-or-later
"""The constrained served markup model, and the reason it is stripped before guarding.

page-help §9-bis-11(b). Two obligations are tested here, and only the second is obvious:

1. Everything the catalogue serves stays inside the sanctioned subset (no freeform HTML).
2. **Formatting cannot hide a claim from the accuracy guards.** This is the load-bearing one.
   Every guard in `test_help_content_accuracy.py` matches phrases against shipped product
   strings; an inline marker inside a phrase breaks the match. Bold text is therefore, without
   stripping, a way to smuggle advice or a retired term past a green suite — the silent-success
   mode this codebase keeps re-learning. The specimens below prove the hiding is real and that
   stripping closes it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.help import HELP, all_help, search_help
from app.services.help_markup import (
    HEADING_PREFIX,
    LIST_PREFIX,
    MARKUP_DIALECT,
    strip_deep,
    strip_markup,
    validate_markup,
)
from tests.unit.test_help_content_accuracy import _prose, _prose_fields

REPO = Path(__file__).resolve().parents[2]

# --- The subset holds ------------------------------------------------------------------------- #


@pytest.mark.parametrize("entry", HELP, ids=lambda e: e["id"])
def test_every_served_string_stays_inside_the_sanctioned_subset(entry: dict):
    """No freeform HTML, no link/image syntax, no unbalanced markers — anywhere in the catalogue.

    `validate_markup` reports rather than raises precisely so this failure names every offending
    field at once instead of stopping at the first.
    """
    bad: list[str] = []
    for field in _prose_fields(entry):
        value = entry.get(field)
        for text in ([value] if isinstance(value, str) else
                     [v for v in value if isinstance(v, str)] if isinstance(value, list) else []):
            for problem in validate_markup(text):
                bad.append(f"{field}: {problem} — in {text[:70]!r}")
    assert not bad, f'{entry["id"]} serves markup outside the sanctioned subset:\n  ' + \
                    "\n  ".join(bad)


def test_stripping_removes_markers_without_rewording():
    """A stripper that normalised or dropped text would make every guard check something the
    user never sees — the guards would be honest about a string that was never served."""
    assert strip_markup("**Net worth** is *derived*.") == "Net worth is derived."
    assert strip_markup("## Reading it\n\n- One item\n- Two") == "Reading it\n\nOne item\nTwo"
    # Wording, spacing between words, and punctuation survive untouched.
    assert strip_markup("a  double  space") == "a  double  space"
    assert strip_markup("") == ""
    # Identifiers with underscores are not emphasis and must survive.
    assert strip_markup("home_layout") == "home_layout"


def test_stripping_reaches_list_valued_fields():
    """`inputs`/`options`/`outputs` are lists. A strip that only handled scalars would leave the
    highest-risk prose in the catalogue — the named affordances — unstripped."""
    assert strip_deep(["**Retry** — re-reads", "*Sort*"]) == ["Retry — re-reads", "Sort"]
    assert strip_deep({"a": "**b**"}) == {"a": "b"}
    assert strip_deep(None) is None


# --- THE SPECIMENS: formatting must not hide a claim ------------------------------------------ #
#
# Each specimen states the defect in the form it would really ship in, proves the RAW string
# defeats the guard's own matcher, and proves the STRIPPED string does not. Testing the matcher
# directly (rather than mutating HELP) is deliberate: it pins the mechanism the guards rely on,
# so this stays red if someone removes the strip from `_prose()` even if the catalogue is clean.


def test_SPECIMEN_bold_hides_advice_from_the_no_advice_guard():
    """The platform's central guarantee — it never advises — defeated by two asterisks.

    `test_no_help_copy_advises_or_leaks_an_implementation_note` matches the literal substring
    "you should". Emphasising one word of it breaks the substring while the USER STILL READS
    THE ADVICE, in bold, more prominently than before.
    """
    smuggled = "For a balanced portfolio you **should** rebalance quarterly."

    assert "you should" not in smuggled.lower(), (
        "specimen is not exercising the defect — the raw string must defeat the substring match, "
        "otherwise this test proves nothing"
    )
    assert "you should" in strip_markup(smuggled).lower(), (
        "stripping must restore the phrase, or the no-advice guard stays blind to bold advice"
    )


def test_SPECIMEN_bold_hides_a_retired_term_from_the_deprecated_guard():
    """`\\btotal value\\b` is broken by a marker sitting INSIDE the phrase.

    The distinction matters and this specimen was wrong on the first attempt: `**total value**`
    still matches, because `*` is a non-word character and the word boundaries survive. Only
    `total **value**` — emphasis on part of the phrase, which is exactly how an author would
    really write it — separates the words and defeats the regex. The specimen's own
    "is it exercising the defect" assertion is what caught the mistake.
    """
    pattern = r"\btotal value\b"
    smuggled = "Your total **value** across accounts."

    assert not re.search(pattern, smuggled.lower()), "specimen is not exercising the defect"
    assert re.search(pattern, strip_markup(smuggled).lower()), \
        "stripping must restore the retired term to the deprecated guard's view"


def test_SPECIMEN_bold_hides_an_invented_control_from_the_dead_affordance_guard():
    """The dead-affordance guard asks whether a named control exists in the shipped product.

    Markup breaks that lookup in BOTH directions, and both are defects: a REAL control wrapped in
    emphasis stops being found (a false alarm that teaches the next reader to relax the guard),
    and the label the guard reports back is a marker-laden string no one can grep for.
    """
    real_control_emphasised = "**Retry** — re-reads a card whose source could not be reached"
    label = re.split(r"\s+[—:]\s+", real_control_emphasised, maxsplit=1)[0].strip()

    assert label == "**Retry**", "specimen is not exercising the defect"
    stripped_label = re.split(r"\s+[—:]\s+", strip_markup(real_control_emphasised), maxsplit=1)[0].strip()
    assert stripped_label == "Retry", \
        "the affordance guard must read a strippable label, not the marker-laden one"


@pytest.mark.parametrize("entry", HELP, ids=lambda e: e["id"])
def test_the_guards_actually_read_stripped_text(entry: dict):
    """The wiring itself, not the stripper. `_prose()` is the single funnel every phrase-matching
    guard flows through; if it ever stops stripping, the three specimens above become live
    defects and NOTHING else would say so."""
    blob = _prose(entry)
    assert "**" not in blob, (
        f'{entry["id"]}: `_prose()` returned raw markup, so every phrase-matching guard is now '
        f"blind to any claim an author emphasises. Restore the strip in `_prose()`."
    )
    assert not re.search(r"^\s*##\s", blob, re.M), \
        f'{entry["id"]}: `_prose()` returned an unstripped heading marker'


# --- The AI is served plain text -------------------------------------------------------------- #


def test_search_results_are_served_STRIPPED_because_the_AI_quotes_them():
    """`search_help()` feeds `app/ai/tools.py` `help_facts()`, which passes `body` to the model as
    a grounding fact. Serving markers there would put `**` into answers the user reads — the same
    class of defect as §9-bis-9(b), where a sample marker had to live in the served string
    because the AI reads strings and not styling.
    """
    for hit in search_help("what is net worth", limit=6):
        assert "**" not in hit["body"], \
            f'search hit {hit["id"]} serves raw markup to the AI grounding pack'
        assert not hit["body"].lstrip().startswith("## "), \
            f'search hit {hit["id"]} serves a raw heading marker to the AI'


# --- The two implementations of one dialect ---------------------------------------------------- #
# The subset is defined in Python and rendered in TypeScript. Two definitions of one dialect WILL
# drift, and the drift would be invisible: prose that renders correctly on one side and wrong on
# the other, with both test suites green. The pin lives here, on the side that can read both files
# — the accuracy corpus already sweeps `frontend/src/**/*.tsx`, so this is the established
# direction, and it avoids widening the frontend tsconfig to expose `node:fs` to all of `src/`.

_RENDERER = REPO / "frontend" / "src" / "routes" / "helpMarkup.tsx"
_HELP_PAGE = REPO / "frontend" / "src" / "routes" / "Help.tsx"
_JS_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def test_the_renderer_agrees_with_the_backend_on_the_block_prefixes():
    src = _RENDERER.read_text(encoding="utf-8")
    assert f"const HEADING = '{HEADING_PREFIX}'" in src, \
        "the renderer's heading prefix has drifted from `help_markup.HEADING_PREFIX`"
    assert f"const LIST = '{LIST_PREFIX}'" in src, \
        "the renderer's list prefix has drifted from `help_markup.LIST_PREFIX`"


def test_the_renderer_never_injects_html():
    """The safety argument is STRUCTURAL — the renderer builds React elements, so there is no path
    from a served string to markup. This guard keeps it structural, against the day someone
    reaches for `dangerouslySetInnerHTML` to "just render the markdown".

    COMMENTS ARE STRIPPED FIRST, and that is not housekeeping: the first run of this guard went RED
    on `helpMarkup.tsx`, whose header comment says "NO dangerouslySetInnerHTML, ANYWHERE". Same
    lesson as §9-bis-9(d) — comments are not shipped code, and a guard that reads them is checking
    the prose around the code instead of the code.
    """
    for path in (_RENDERER, _HELP_PAGE):
        code = _JS_COMMENT.sub(" ", path.read_text(encoding="utf-8"))
        assert "dangerouslySetInnerHTML" not in code, \
            f"{path.name} injects HTML — the served-markup model's safety property is structural " \
            f"and this breaks it"


def test_the_catalogue_declares_its_markup_dialect():
    """A consumer cannot know `body` is markup-bearing unless the response says so. Versioned, so
    a future change to the subset is a visible contract change rather than a silent
    reinterpretation of the same strings."""
    assert all_help()["markup"] == MARKUP_DIALECT
    assert MARKUP_DIALECT == "lf-help-markup-1"


# --- The WIRING, not the renderer -------------------------------------------------------------- #
# Found by the 3a pre-pass, not by review, and not by any unit test: the served strings carried
# emphasis on 54 affordance labels while `inputs`/`options`/`outputs` still rendered as raw text,
# so the page showed a literal `**Quote source**` to the user. Every markup test was green — they
# tested the RENDERER, and the renderer was fine. What was wrong was which fields it was wired to.
#
# A correct component wired to half its fields is a whole class of defect that component tests
# cannot see, which is why this reads the page instead.


def test_every_served_prose_field_is_rendered_THROUGH_the_markup_renderer():
    src = _HELP_PAGE.read_text(encoding="utf-8")

    # The three list-valued fields render inline markup.
    for field in ("entry.inputs", "entry.options", "entry.outputs"):
        line = next((ln for ln in src.splitlines() if f"{field}.map" in ln), None)
        assert line, f"{field} is not rendered on the Help page at all"
        assert "HelpInline" in line, (
            f"{field} renders RAW — its served `**` markers will show to the user as literal "
            f"asterisks. Wrap the item in <HelpInline>."
        )

    # The prose fields go through the block renderer.
    for field in ("entry.body", "entry.interpret", "entry.example"):
        assert f"<HelpProse text={{{field}}}" in src, \
            f"{field} does not go through HelpProse — it will render raw markup"

    # The glossary triad, which renders inside <dd>.
    for field in ("entry.what", "entry.why", "entry.improves"):
        assert f"<HelpProse text={{{field}" in src, \
            f"{field} does not go through HelpProse — it will render raw markup"
