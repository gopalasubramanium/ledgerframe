# SPDX-License-Identifier: AGPL-3.0-or-later
"""The CONSTRAINED SERVED MARKUP MODEL for help prose (page-help §9-bis-11(b)).

Help entry bodies carry typographic structure — headings, bold, italic, lists, spacing — so a
long entry reads as a document instead of a wall. The owner's ruling names the shape of that
capability precisely, and the constraint is the substance:

* a **minimal sanctioned subset**, defined here and nowhere else;
* **no freeform HTML injection**, in either direction;
* **accuracy guards run on MARKUP-STRIPPED text**, so formatting can never hide a claim.

WHY A SUBSET AND NOT MARKDOWN. Markdown is an open-ended language with an HTML escape hatch at
its centre; adopting it would mean adopting a parser, an ADR, and a sanitiser, and would put
arbitrary HTML one authoring mistake away from the page. What this catalogue actually needs is
five constructs. Five constructs are enumerable, and an enumerable subset can be *validated* —
`validate_markup()` rejects everything it does not recognise, which is the opposite posture from
a sanitiser trying to enumerate badness.

WHY STRIPPING IS A SAFETY PROPERTY, NOT A CONVENIENCE. Every accuracy guard in
`tests/unit/test_help_content_accuracy.py` matches phrases against the shipped product. An inline
marker inside a phrase BREAKS those matches: `Net **worth**` does not match `\\bnet worth\\b`, so a
deprecated term, an advice phrase, or a retired label could sit in shipped copy with its guard
GREEN — the silent-success mode this module exists to prevent. Guards therefore read
`strip_markup()` output, never the raw string. That is proven by a fail-first specimen
(`test_help_markup.py`), not asserted here.

THE SUBSET
----------
Block level, decided per line:

* ``## Heading``  — a section heading inside an entry body.
* ``- item``      — a list item; consecutive items form one list.
* blank line      — a block separator.
* anything else   — a paragraph line (consecutive lines join into one paragraph).

Inline, within any block:

* ``**bold**``    — strong emphasis.
* ``*italic*``    — emphasis.

Everything else is NOT markup and is rejected by `validate_markup()`. In particular there is no
link syntax (pointers have their own `links` field — a POINTER, never a figure), no image syntax,
no code fences, no raw HTML, and no underscore emphasis (it would corrupt identifiers like
`home_layout`).
"""

from __future__ import annotations

import re

# The dialect id served in the contract (`HelpResponse.markup`). Versioned so that a future change
# to the subset is VISIBLE to consumers rather than a silent reinterpretation of the same strings.
MARKUP_DIALECT = "lf-help-markup-1"

HEADING_PREFIX = "## "
LIST_PREFIX = "- "

_BOLD = re.compile(r"\*\*(?P<text>.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(?P<text>[^*]+?)(?<!\*)\*(?!\*)")

# Constructs that are NOT in the subset and must never appear. Each carries the reason it is
# barred, because a rejection a reader cannot understand gets worked around rather than fixed.
_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"<[^>]*>"),
     "raw HTML is not in the subset — the renderer builds elements, it never injects markup"),
    (re.compile(r"!\[[^\]]*\]"), "image syntax is not in the subset"),
    (re.compile(r"\[[^\]]*\]\([^)]*\)"),
     "link syntax is not in the subset — pointers belong in the entry's `links` field"),
    (re.compile(r"```"), "code fences are not in the subset"),
    (re.compile(r"(?<![A-Za-z0-9])_[^_\n]+_(?![A-Za-z0-9])"),
     "underscore emphasis is not in the subset — it would corrupt identifiers like `home_layout`"),
    (re.compile(r"^\s*#{1}(?!#)\s", re.M),
     "a level-1 heading is not in the subset — the entry TITLE is the entry's only h-level above "
     "its blocks"),
    (re.compile(r"^\s*#{3,}\s", re.M), "only `## ` headings are in the subset"),
)


def strip_markup(text: str) -> str:
    """Return the plain reading text: every sanctioned marker removed, wording untouched.

    This is what the accuracy guards read, and what the AI is served. It must never *reword*
    anything — a stripper that normalised whitespace inside a phrase, or dropped a list bullet's
    text, would make the guards check something the user never sees.
    """
    if not text:
        return text
    out = _BOLD.sub(lambda m: m.group("text"), text)
    out = _ITALIC.sub(lambda m: m.group("text"), out)
    lines = []
    for line in out.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith(HEADING_PREFIX):
            lines.append(stripped[len(HEADING_PREFIX):])
        elif stripped.startswith(LIST_PREFIX):
            lines.append(stripped[len(LIST_PREFIX):])
        else:
            lines.append(line)
    return "\n".join(lines)


def strip_deep(value):
    """`strip_markup` over a string, a list of strings, or a dict of either — unchanged otherwise.

    Entry fields are a mix of scalars and lists (`inputs`/`options`/`outputs`), and every guard
    that flattens an entry needs the same treatment applied uniformly. Doing it in one place is
    what keeps a newly-added list field from being silently unstripped.
    """
    if isinstance(value, str):
        return strip_markup(value)
    if isinstance(value, list):
        return [strip_deep(v) for v in value]
    if isinstance(value, dict):
        return {k: strip_deep(v) for k, v in value.items()}
    return value


def validate_markup(text: str) -> list[str]:
    """Return a list of violations — empty means the string is inside the sanctioned subset.

    Returns rather than raises: the guard reports EVERY offending field across the whole
    catalogue in one run, instead of failing on the first and hiding the rest.
    """
    if not text:
        return []
    problems = [reason for pattern, reason in _FORBIDDEN if pattern.search(text)]
    # Unbalanced inline markers. An odd `**` means an author opened emphasis and never closed it:
    # the raw marker then RENDERS TO THE USER, and — worse — the phrase it sits inside is broken
    # for every guard that matches on it.
    if text.count("**") % 2:
        problems.append("unbalanced `**` — an unclosed bold marker renders raw and breaks "
                        "phrase-matching guards")
    if len(_ITALIC.sub("", text.replace("**", "")).split("*")) > 1:
        problems.append("unbalanced `*` — an unclosed italic marker renders raw and breaks "
                        "phrase-matching guards")
    return problems
