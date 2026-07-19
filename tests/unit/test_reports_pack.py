# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reports Pack (`GET /reports/pack`) — the print/export artifact (D-038/D-061, reports-pack §3b).

Content pins for Phase 0 (reports-pack §11). The artifact is asserted directly (the §14 lesson:
assert the RENDERED artifact, not a DOM theory). Fail-first: with the route removed the path 404s
(demonstrated at build time by disabling the registration); the empty/zero cases were seen to
render the served reason before the honest-note branches were wired.
"""

from __future__ import annotations

from app.models import Entity
from app.services.reports_pack import render_reports_pack

# ------------------------------------------------------------------------ the route + seeded content


async def test_reports_pack_route_serves_html_with_the_header_block(app_client):
    """The route exists, serves HTML, and carries the Pack-5 header block (title · generated ·
    base currency · not-advice)."""
    resp = await app_client.get("/reports/pack")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    html = resp.text
    assert "<h1>Reports Pack</h1>" in html
    assert "Generated" in html
    assert "Base currency" in html
    assert "reporting only, not tax or financial advice" in html  # Pack-5 not-advice line


async def test_reports_pack_renders_all_four_consolidated_sections(app_client):
    """Pack-1 order: consolidated = net-worth trend · review · cash flow · scenarios."""
    html = (await app_client.get("/reports/pack")).text
    assert '<div class="pack-group-label">Consolidated</div>' in html
    for heading in ("Net worth trend", "Review", "Cash flow", "Scenarios"):
        assert f"<h2>{heading}</h2>" in html, f"missing consolidated section: {heading}"


async def test_reports_pack_renders_a_per_entity_section_per_seeded_entity(app_client):
    """Pack-6: one per-entity section per entity, alphabetical, composed with entity_id (§9-2)."""
    entities = (await app_client.get("/api/v1/entities")).json()["entities"]
    assert entities, "the demo seed should define at least one entity"
    html = (await app_client.get("/reports/pack")).text
    assert '<div class="pack-group-label">Per-entity</div>' in html
    for ent in entities:
        assert f"Per-entity &mdash; {ent['name']}" in html or f"Per-entity — {ent['name']}" in html, (
            f"missing per-entity section for {ent['name']!r}"
        )
    assert html.count('pack-section--entity') == len(entities)


async def test_reports_pack_preserves_a_served_disclaimer_verbatim(app_client):
    """Pack-5/D-061: a reader's served disclaimer renders verbatim inside the artifact."""
    html = (await app_client.get("/reports/pack")).text
    # The review reader's served disclaimer (review.py:259).
    assert "reporting only, not advice or a required action." in html


async def test_attribution_rows_render_served_labels_not_reader_keys(app_client):
    """§12pk-1 / §12es-3 (label truth on the server-side composer): the attribution 'by asset class'
    rows render the SERVED /refdata display label — the same truth every JSON route serves through —
    never the raw reader key. The seed's Household holds a fixed deposit, so attribution surfaces a
    by-asset-class row for it; `fixed_deposit` is the load-bearing case (an underscore key that
    titleizes to 'Fixed deposit')."""
    html = (await app_client.get("/reports/pack")).text
    assert "Fixed deposit" in html, "the served asset-class display label must render in the artifact"
    # The raw reader key must not leak into the rendered artifact (copy-hygiene / label-truth).
    assert "fixed_deposit" not in html, "the raw reader key must not render — it is not a display label"


async def test_review_rows_render_the_served_item_text_not_just_labels(app_client):
    """§14pk-2: each Review row renders the reader's served signal TEXT (review.py `_item` serves it as
    `title`, not `body`) — a category label without its item is a blank wearing a costume. The seed's
    estate register has one MISSING + one OUTDATED document → a stable, date-independent review signal
    ('… documents marked missing or outdated')."""
    html = (await app_client.get("/reports/pack")).text
    assert "documents marked missing or outdated" in html, (
        "the served review item text must render inside the artifact, not just its area/severity tags"
    )


async def test_realised_sections_share_one_consistent_period_label(app_client):
    """§14pk-3: every per-entity Realised P/L section is scoped to ONE household-wide period, stated in
    the heading, and the empty-entity note cites the SAME period — not a per-entity year default that
    leaked the current year for empty entities. The seed's only realised event is 2024 (AAPL), so the
    household period is 2024; the empty entities must say '… for 2024', never the current year."""
    html = (await app_client.get("/reports/pack")).text
    assert "Realised P/L — 2024" in html, "the Realised section heading states the true period (2024)"
    assert "No realised events recorded for 2024." in html, "the empty-entity note cites the SAME period"
    # The leaked per-entity current-year default is gone (empties no longer say the wall-clock year).
    from datetime import date
    assert f"No realised events recorded for {date.today().year}." not in html or date.today().year == 2024, (
        "empty entities must not leak the current year as the realised period"
    )


async def test_single_card_consolidated_sections_render_one_heading_not_h2_plus_h3(app_client):
    """§12pk-3: a single-card consolidated subsection prints ONE heading — the section <h2> — never a
    duplicated card <h3> of the same text (the DataTable-caption lesson). Per-entity sections keep
    their card <h3>s (their <h2> is the entity name, so the card titles are NOT duplicates)."""
    html = (await app_client.get("/reports/pack")).text
    for title in ("Net worth trend", "Review", "Cash flow", "Scenarios"):
        assert f"<h2>{title}</h2>" in html, f"the consolidated section heading for {title!r} is present"
        assert f"<h3>{title}</h3>" not in html, f"duplicate card heading for {title!r} (§12pk-3)"


# ------------------------------------------------------------------- Pack-3 empty / Pack-4 degenerate


async def test_empty_entity_renders_served_reasons_not_blanks_or_zeros(session):
    """Pack-3 / Guarantee 3: an entity with no accounts renders each reader's honest served reason,
    never a blank or a fabricated 0 — and the section stays present (structural stability)."""
    session.add(Entity(name="Empty Estate", kind="trust"))
    await session.commit()

    html = await render_reports_pack(session)
    assert "Per-entity &mdash; Empty Estate" in html or "Per-entity — Empty Estate" in html
    # Each entity-aware reader's honest empty reason (Pack-3), not a 0:
    assert "No holdings recorded for this entity." in html          # value_portfolio empty
    assert "No policy targets set for this entity" in html          # drift has_targets=False
    assert "No realised events recorded for" in html                # realised currency_groups=[]
    assert "Risk metrics unavailable" in html                       # risk available=False
    assert "insufficient cost basis" in html                        # attribution served reason


async def test_zero_entities_renders_consolidated_plus_the_omission_note(session):
    """Pack-4 degenerate case: zero entities → consolidated view + an honest omission note, and NO
    per-entity entity section (no empty shell)."""
    html = await render_reports_pack(session)
    assert '<div class="pack-group-label">Consolidated</div>' in html
    assert "No ownership entities are defined" in html
    # The omission-note card is the only thing under Per-entity — no real entity section.
    assert "Per-entity &mdash;" not in html and "Per-entity —" not in html


async def test_single_entity_still_renders_its_per_entity_section(session):
    """Pack-4 recording note: with ONE entity, its per-entity section still renders (the partial
    overlap with consolidated is accepted, not collapsed)."""
    session.add(Entity(name="Solo Household", kind="self"))
    await session.commit()

    html = await render_reports_pack(session)
    assert "Per-entity &mdash; Solo Household" in html or "Per-entity — Solo Household" in html
    assert html.count("pack-section--entity") == 1


# --------------------------------------------------- AC-L8: the product-level footer (page-legal §9-4)
#
# ONE source, TWO renderers. The Legal page and this artifact must render the same bytes, and the
# only way that stays true is a test that compares them rather than a convention that asks nicely.


async def test_the_pack_carries_the_product_level_footer_line(app_client):
    """§9-4: the Pack gains ONE product-level reporting-only / no-advice line."""
    html = (await app_client.get("/reports/pack")).text
    assert '<footer class="pack-footer">' in html


async def test_the_footer_matches_LEGALS_SERVED_STRING_byte_for_byte(app_client):
    """AC-L8 — the anti-drift guard, and the whole point of §9-4's "one source, two renderers".

    Fail-first: seen RED with a single character changed in the Pack's copy of the line. The two
    surfaces would otherwise drift the ordinary way — someone improves the wording on the page,
    the print artifact keeps the old sentence, and for a while the product states its position two
    different ways depending on where you read it.

    Compared against what the ENDPOINT serves, not against the module constant, so the assertion
    covers the whole path the page actually receives.

    Note the path: `/api/v1/legal`, not `/legal`. The Pack is registered at the app root, but the
    Legal reader is on the versioned API router — and unprefixed `/legal` is swallowed by the SPA
    catch-all, which answers 200 with `index.html`. Seen RED writing this: the wrong path returned
    HTML and the test died on a JSON decode rather than on a drift, which would have read as a
    content bug.
    """
    import html as _html

    resp = await app_client.get("/api/v1/legal")
    assert resp.status_code == 200, resp.text
    served = resp.json()["pack_footer"]
    pack = (await app_client.get("/reports/pack")).text

    marker = '<footer class="pack-footer">'
    rendered = pack[pack.index(marker) + len(marker):pack.index("</footer>")]
    assert _html.unescape(rendered) == served, (
        "The Reports Pack footer has DRIFTED from the string Legal serves.\n"
        f"  legal serves: {served!r}\n"
        f"  pack renders: {_html.unescape(rendered)!r}\n"
        "One source, two renderers (page-legal §9-4) — change app/services/legal.py, never the "
        "Pack's copy."
    )


async def test_the_footer_did_not_replace_the_per_reader_disclaimers(app_client):
    """The addition is an ADDITION (D-106). §9-4 keeps the Pack's per-reader disclaimers unchanged;
    the footer states the product's position, it does not absorb theirs."""
    html = (await app_client.get("/reports/pack")).text
    assert 'class="pack-disclaimer"' in html, (
        "the per-reader disclaimers vanished from the Pack — the §9-4 footer is an addition, never "
        "a replacement (page-legal §9-2 / D-106: removing a scoped caveat is an honesty regression)"
    )


async def test_the_reporting_only_fallback_caption_is_unchanged(app_client):
    """§9-4 explicitly leaves `reports_pack.py`'s fallback caption for readers that serve no
    disclaimer of their own alone. Pinned so a later tidy-up cannot fold it into the new footer."""
    from app.services.reports_pack import _REPORTING_CAPTION

    assert _REPORTING_CAPTION == "Reporting only, not advice."
    assert _REPORTING_CAPTION in (await app_client.get("/reports/pack")).text


async def test_the_seven_guarantees_stay_OFF_the_print_artifact(app_client):
    """§9-4 ruled the Guarantees do NOT go into the Pack — a page, not a report footer, and they
    would bloat every print artifact. Guarded so a future "make the Pack more complete" change has
    to argue with the ruling instead of quietly reversing it."""
    from app.services.legal import GUARANTEES

    html = (await app_client.get("/reports/pack")).text
    for g in GUARANTEES:
        assert g not in html, f"a Product Guarantee reached the print artifact: {g[:48]!r}…"
