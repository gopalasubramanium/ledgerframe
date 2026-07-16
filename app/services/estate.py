# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estate & document readiness (W4) — family governance, never legal advice.

Records what exists and where (will status, people & roles, a key-document register) and
surfaces neutral reminders. It never drafts anything, never gives legal/estate advice, and
states status (e.g. "Will: not recorded") rather than telling the user what to do.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EstateContact, EstateDocument, EstateProfile

DOC_CATEGORIES = ["will", "insurance", "property", "loan", "identity", "bank", "tax", "medical", "other"]
CONTACT_ROLES = ["nominee", "beneficiary", "executor", "emergency", "guardian"]
WILL_STATUSES = ["none", "draft", "executed", "needs_update"]
DOC_STATUSES = ["present", "missing", "outdated"]
_REVIEW_SOON_DAYS = 30


# --- profile (singleton) --------------------------------------------------- #
async def get_or_create_profile(session: AsyncSession) -> EstateProfile:
    p = (await session.execute(select(EstateProfile).limit(1))).scalars().first()
    if p is None:
        p = EstateProfile()
        session.add(p)
        await session.flush()
    return p


def _profile_dict(p: EstateProfile) -> dict:
    return {"will_status": p.will_status, "will_location": p.will_location, "executor": p.executor,
            "last_reviewed": p.last_reviewed, "next_review_date": p.next_review_date, "notes": p.notes}


async def update_profile(session: AsyncSession, data: dict) -> dict:
    p = await get_or_create_profile(session)
    for k in ("will_status", "will_location", "executor", "last_reviewed", "next_review_date", "notes"):
        if k in data:
            v = data[k]
            v = v.strip() if isinstance(v, str) else v
            setattr(p, k, v or None)
    if p.will_status not in WILL_STATUSES:
        p.will_status = "none"
    await session.flush()
    return _profile_dict(p)


# --- contacts -------------------------------------------------------------- #
def _contact_dict(c: EstateContact) -> dict:
    try:
        roles = json.loads(c.roles) if c.roles else []
    except (ValueError, TypeError):
        roles = []
    return {"id": c.id, "name": c.name, "roles": roles,
            "phone": c.phone, "email": c.email, "notes": c.notes}


def _apply_contact(c: EstateContact, data: dict) -> None:
    if "name" in data and (data["name"] or "").strip():
        c.name = data["name"].strip()[:120]
    for k in ("phone", "email", "notes"):
        if k in data:
            v = (data[k] or "").strip() if isinstance(data[k], str) else data[k]
            setattr(c, k, v or None)
    if "roles" in data and isinstance(data["roles"], list):
        c.roles = json.dumps([r for r in data["roles"] if r in CONTACT_ROLES])


async def create_contact(session: AsyncSession, data: dict) -> dict:
    c = EstateContact(name=(data.get("name") or "Contact").strip()[:120], roles="[]")
    _apply_contact(c, data)
    session.add(c)
    await session.flush()
    return _contact_dict(c)


async def update_contact(session: AsyncSession, cid: int, data: dict) -> dict:
    c = await session.get(EstateContact, cid)
    if c is None:
        raise ValueError("contact not found")
    _apply_contact(c, data)
    await session.flush()
    return _contact_dict(c)


async def delete_contact(session: AsyncSession, cid: int) -> None:
    c = await session.get(EstateContact, cid)
    if c is not None:
        await session.delete(c)


# --- documents ------------------------------------------------------------- #
def _doc_dict(d: EstateDocument) -> dict:
    return {"id": d.id, "title": d.title, "category": d.category, "location": d.location,
            "status": d.status, "review_date": d.review_date, "related_to": d.related_to, "notes": d.notes}


def _apply_doc(d: EstateDocument, data: dict) -> None:
    if "title" in data and (data["title"] or "").strip():
        d.title = data["title"].strip()[:120]
    for k in ("location", "review_date", "related_to", "notes"):
        if k in data:
            v = (data[k] or "").strip() if isinstance(data[k], str) else data[k]
            setattr(d, k, v or None)
    if "category" in data:
        d.category = data["category"] if data["category"] in DOC_CATEGORIES else "other"
    if "status" in data:
        d.status = data["status"] if data["status"] in DOC_STATUSES else "present"


async def create_document(session: AsyncSession, data: dict) -> dict:
    d = EstateDocument(title=(data.get("title") or "Document").strip()[:120])
    _apply_doc(d, data)
    session.add(d)
    await session.flush()
    return _doc_dict(d)


async def update_document(session: AsyncSession, did: int, data: dict) -> dict:
    d = await session.get(EstateDocument, did)
    if d is None:
        raise ValueError("document not found")
    _apply_doc(d, data)
    await session.flush()
    return _doc_dict(d)


async def delete_document(session: AsyncSession, did: int) -> None:
    d = await session.get(EstateDocument, did)
    if d is not None:
        await session.delete(d)


# --- report + review signals ---------------------------------------------- #
async def estate_report(session: AsyncSession) -> dict:
    profile = _profile_dict(await get_or_create_profile(session))
    contacts = [_contact_dict(c) for c in (await session.execute(
        select(EstateContact).order_by(EstateContact.name))).scalars().all()]
    docs = [_doc_dict(d) for d in (await session.execute(
        select(EstateDocument).order_by(EstateDocument.category, EstateDocument.title))).scalars().all()]

    def _has_role(role: str) -> int:
        return sum(1 for c in contacts if role in c["roles"])

    readiness = {
        "docs_total": len(docs),
        "docs_present": sum(1 for d in docs if d["status"] == "present"),
        "docs_attention": sum(1 for d in docs if d["status"] in ("missing", "outdated")),
        "will_status": profile["will_status"],
        "nominees": _has_role("nominee") + _has_role("beneficiary"),
        "executors": _has_role("executor"),
        "emergency": _has_role("emergency"),
    }
    return {"profile": profile, "contacts": contacts, "documents": docs, "readiness": readiness,
            "disclaimer": "Family governance — a record of what exists and where, and reminders "
                          "to keep it current. Not legal or estate-planning advice."}


async def estate_signals(session: AsyncSession) -> list[str]:
    """Neutral status statements for the review feed (never advice)."""
    out: list[str] = []
    profile = await get_or_create_profile(session)
    if profile.will_status == "none":
        out.append("No will recorded")
    elif profile.will_status == "needs_update":
        out.append("Will is marked as needing an update")

    docs = (await session.execute(select(EstateDocument))).scalars().all()
    attention = sum(1 for d in docs if d.status in ("missing", "outdated"))
    if attention:
        out.append(f"{attention} key document{'s' if attention != 1 else ''} marked missing or outdated")

    if profile.next_review_date:
        try:
            days = (date.fromisoformat(profile.next_review_date) - datetime.now(UTC).date()).days
            if days < 0:
                out.append(f"Estate review is overdue (was {profile.next_review_date})")
            elif days <= _REVIEW_SOON_DAYS:
                out.append(f"Estate review due in {days} days")
        except ValueError:
            pass
    return out
