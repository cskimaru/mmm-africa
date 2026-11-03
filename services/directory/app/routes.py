from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mmm_common.db import utcnow
from mmm_common.ratelimit import client_ip, hash_value, rate_limit
from mmm_common.security import ROLE_EDITOR, Principal, optional_principal, require_roles

from .models import AuditLog, Event, Message, Officer, Page, Setting, Unit
from .schemas import (
    ContentIn,
    ContentOut,
    EventIn,
    EventOut,
    EventPatch,
    MessageIn,
    MessageOut,
    OfficerIn,
    OfficerOut,
    OfficerPatch,
    PageIn,
    PageOut,
    PagePatch,
    StructureOut,
    UnitDetailOut,
    UnitIn,
    UnitOut,
    UnitPatch,
)

router = APIRouter(prefix="/api/directory")
editor = require_roles(ROLE_EDITOR)

# A unit may only sit directly under the level above it, as in the church structure.
PARENT_LEVEL = {"international": None, "continental": "international", "national": "continental"}


async def session_dep(request: Request):
    async for s in request.app.state.db.session():
        yield s


def is_editor(p: Principal | None) -> bool:
    return bool(p and p.has(ROLE_EDITOR))


def audit(s: AsyncSession, actor: str | None, action: str, target: str = "") -> None:
    s.add(AuditLog(actor_id=actor, action=action, target=target))


async def commit_or_conflict(s: AsyncSession, what: str) -> None:
    try:
        await s.commit()
    except IntegrityError as e:
        await s.rollback()
        raise HTTPException(409, f"That web address is already used by another {what}. Choose a different one.") from e


# ---- Structure and units ----


async def check_parent(s: AsyncSession, level: str, parent_id: str | None) -> None:
    wanted = PARENT_LEVEL[level]
    if wanted is None:
        if parent_id:
            raise HTTPException(422, "The international level sits at the top and has no parent.")
        return
    parent = await s.get(Unit, parent_id) if parent_id else None
    if parent is None or parent.level != wanted:
        raise HTTPException(422, f"A {level} unit must sit under a {wanted} unit.")


@router.get("/structure", response_model=StructureOut)
async def structure(
    p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> StructureOut:
    q = select(Unit).order_by(Unit.position, Unit.name)
    if not is_editor(p):
        q = q.where(Unit.hidden.is_(False))
    units = [UnitOut.model_validate(u) for u in (await s.execute(q)).scalars()]
    return StructureOut(
        international=[u for u in units if u.level == "international"],
        continental=[u for u in units if u.level == "continental"],
        national=[u for u in units if u.level == "national"],
    )


@router.get("/units/{slug}", response_model=UnitDetailOut)
async def unit_detail(
    slug: str, p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> UnitDetailOut:
    u = (await s.execute(select(Unit).where(Unit.slug == slug))).scalar_one_or_none()
    if u is None or (u.hidden and not is_editor(p)):
        raise HTTPException(404, "Not found.")
    officers = (
        await s.execute(select(Officer).where(Officer.unit_id == u.id).order_by(Officer.position, Officer.name))
    ).scalars()
    children_q = select(Unit).where(Unit.parent_id == u.id).order_by(Unit.position, Unit.name)
    if not is_editor(p):
        children_q = children_q.where(Unit.hidden.is_(False))
    parent = await s.get(Unit, u.parent_id) if u.parent_id else None
    return UnitDetailOut(
        **UnitOut.model_validate(u).model_dump(),
        officers=[OfficerOut.model_validate(o) for o in officers],
        parent=UnitOut.model_validate(parent) if parent else None,
        children=[UnitOut.model_validate(c) for c in (await s.execute(children_q)).scalars()],
    )


@router.post("/units", response_model=UnitOut, status_code=201)
async def create_unit(body: UnitIn, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)) -> UnitOut:
    await check_parent(s, body.level, body.parent_id)
    u = Unit(**body.model_dump())
    s.add(u)
    audit(s, p.user_id, "unit.create", body.slug)
    await commit_or_conflict(s, "chapter")
    return UnitOut.model_validate(u)


@router.patch("/units/{unit_id}", response_model=UnitOut)
async def update_unit(
    unit_id: str, body: UnitPatch, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> UnitOut:
    u = await s.get(Unit, unit_id)
    if u is None:
        raise HTTPException(404, "Not found.")
    changes = body.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        await check_parent(s, u.level, changes["parent_id"])
    if "country_code" in changes and changes["country_code"] is not None:
        changes["country_code"] = changes["country_code"].strip().lower()[:2]
    for k, v in changes.items():
        if v is not None or k == "parent_id":
            setattr(u, k, v)
    audit(s, p.user_id, "unit.update", u.id)
    await commit_or_conflict(s, "chapter")
    return UnitOut.model_validate(u)


@router.delete("/units/{unit_id}", status_code=204)
async def delete_unit(unit_id: str, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)) -> Response:
    u = await s.get(Unit, unit_id)
    if u is None:
        raise HTTPException(404, "Not found.")
    children = await s.scalar(select(func.count()).select_from(Unit).where(Unit.parent_id == u.id))
    if children:
        raise HTTPException(409, "Move or remove the chapters under this one first.")
    for o in (await s.execute(select(Officer).where(Officer.unit_id == u.id))).scalars():
        await s.delete(o)
    await s.delete(u)
    audit(s, p.user_id, "unit.delete", unit_id)
    await s.commit()
    return Response(status_code=204)


# ---- Officers ----


@router.get("/officers", response_model=list[OfficerOut])
async def list_officers(unit: str, s: AsyncSession = Depends(session_dep)) -> list[OfficerOut]:
    """Leaders of one unit, by its slug."""
    u = (await s.execute(select(Unit).where(Unit.slug == unit))).scalar_one_or_none()
    if u is None:
        return []
    rows = await s.execute(select(Officer).where(Officer.unit_id == u.id).order_by(Officer.position, Officer.name))
    return [OfficerOut.model_validate(o) for o in rows.scalars()]


@router.post("/officers", response_model=OfficerOut, status_code=201)
async def create_officer(
    body: OfficerIn, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> OfficerOut:
    if await s.get(Unit, body.unit_id) is None:
        raise HTTPException(422, "Choose which chapter this leader serves.")
    o = Officer(**body.model_dump())
    s.add(o)
    audit(s, p.user_id, "officer.create", body.unit_id)
    await s.commit()
    return OfficerOut.model_validate(o)


@router.patch("/officers/{officer_id}", response_model=OfficerOut)
async def update_officer(
    officer_id: str, body: OfficerPatch, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> OfficerOut:
    o = await s.get(Officer, officer_id)
    if o is None:
        raise HTTPException(404, "Not found.")
    for k, v in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(o, k, v)
    audit(s, p.user_id, "officer.update", o.id)
    await s.commit()
    return OfficerOut.model_validate(o)


@router.delete("/officers/{officer_id}", status_code=204)
async def delete_officer(
    officer_id: str, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> Response:
    o = await s.get(Officer, officer_id)
    if o is not None:
        await s.delete(o)
        audit(s, p.user_id, "officer.delete", officer_id)
        await s.commit()
    return Response(status_code=204)


# ---- Events ----


def event_state(e: Event, today: date) -> str:
    if today < e.starts_on:
        return "upcoming"
    if today <= e.ends_on:
        return "happening"
    return "ended"


async def event_out(s: AsyncSession, e: Event, today: date) -> EventOut:
    host = await s.get(Unit, e.host_unit_id) if e.host_unit_id else None
    out = EventOut.model_validate(e)
    out.host = UnitOut.model_validate(host) if host else None
    out.state = event_state(e, today)
    return out


@router.get("/events", response_model=list[EventOut])
async def list_events(
    p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> list[EventOut]:
    q = select(Event).order_by(Event.starts_on.desc())
    if not is_editor(p):
        q = q.where(Event.hidden.is_(False))
    today = utcnow().date()
    return [await event_out(s, e, today) for e in (await s.execute(q)).scalars()]


@router.get("/events/{slug}", response_model=EventOut)
async def get_event(
    slug: str, p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> EventOut:
    e = (await s.execute(select(Event).where(Event.slug == slug))).scalar_one_or_none()
    if e is None or (e.hidden and not is_editor(p)):
        raise HTTPException(404, "Not found.")
    return await event_out(s, e, utcnow().date())


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(
    body: EventIn, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> EventOut:
    if body.host_unit_id and await s.get(Unit, body.host_unit_id) is None:
        raise HTTPException(422, "The host chapter was not found.")
    e = Event(**body.model_dump())
    s.add(e)
    audit(s, p.user_id, "event.create", body.slug)
    await commit_or_conflict(s, "event")
    return await event_out(s, e, utcnow().date())


@router.patch("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: str, body: EventPatch, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> EventOut:
    e = await s.get(Event, event_id)
    if e is None:
        raise HTTPException(404, "Not found.")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None or k == "host_unit_id":
            setattr(e, k, v)
    if e.ends_on < e.starts_on:
        raise HTTPException(422, "The end date must be on or after the start date.")
    audit(s, p.user_id, "event.update", e.id)
    await commit_or_conflict(s, "event")
    return await event_out(s, e, utcnow().date())


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: str, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> Response:
    e = await s.get(Event, event_id)
    if e is not None:
        await s.delete(e)
        audit(s, p.user_id, "event.delete", event_id)
        await s.commit()
    return Response(status_code=204)


# ---- Contact messages ----


@router.post("/messages", status_code=202, dependencies=[Depends(rate_limit("message", 5, 3600))])
async def send_message(body: MessageIn, request: Request, s: AsyncSession = Depends(session_dep)) -> dict:
    # A filled-in hidden field means a bot: say thanks, keep nothing.
    if not body.website:
        s.add(
            Message(
                name=body.name.strip(),
                email=str(body.email),
                country=body.country.strip(),
                topic=body.topic,
                body=body.body.strip(),
                ip_hash=hash_value(client_ip(request), request.app.state.settings.ip_hash_salt),
            )
        )
        await s.commit()
    return {"detail": "Thank you. The Africa Chapter secretariat will get back to you."}


@router.get("/messages", response_model=list[MessageOut])
async def list_messages(
    status: str = "open", p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> list[MessageOut]:
    q = select(Message).order_by(Message.created_at.desc()).limit(200)
    if status == "open":
        q = q.where(Message.handled_at.is_(None))
    elif status == "handled":
        q = q.where(Message.handled_at.is_not(None))
    return [MessageOut.model_validate(m) for m in (await s.execute(q)).scalars()]


@router.post("/messages/{message_id}/handled", response_model=MessageOut)
async def mark_handled(
    message_id: str, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> MessageOut:
    m = await s.get(Message, message_id)
    if m is None:
        raise HTTPException(404, "Not found.")
    m.handled_at = utcnow()
    m.handled_by = p.user_id
    audit(s, p.user_id, "message.handled", m.id)
    await s.commit()
    return MessageOut.model_validate(m)


# ---- Website text and options ----


@router.get("/content", response_model=ContentOut)
async def get_content(s: AsyncSession = Depends(session_dep)) -> ContentOut:
    """Text the officers have changed. Anything not listed uses the website's built-in default."""
    rows = (await s.execute(select(Setting))).scalars()
    return ContentOut(values={r.key: r.value for r in rows})


@router.put("/content", response_model=ContentOut)
async def save_content(
    body: ContentIn, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> ContentOut:
    for key, value in body.values.items():
        row = await s.get(Setting, key)
        if value.strip() == "":
            if row is not None:
                await s.delete(row)
        elif row is None:
            s.add(Setting(key=key, value=value, updated_by=p.user_id))
        else:
            row.value = value
            row.updated_by = p.user_id
    if body.values:
        audit(s, p.user_id, "content.save", ",".join(sorted(body.values))[:64])
    await s.commit()
    return await get_content(s)


# ---- Officer-written pages ----


@router.get("/pages", response_model=list[PageOut])
async def list_pages(
    p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> list[PageOut]:
    q = select(Page).order_by(Page.position, Page.title)
    if not is_editor(p):
        q = q.where(Page.hidden.is_(False))
    return [PageOut.model_validate(x) for x in (await s.execute(q)).scalars()]


@router.get("/pages/{slug}", response_model=PageOut)
async def get_page(
    slug: str, p: Principal | None = Depends(optional_principal), s: AsyncSession = Depends(session_dep)
) -> PageOut:
    page = (await s.execute(select(Page).where(Page.slug == slug))).scalar_one_or_none()
    if page is None or (page.hidden and not is_editor(p)):
        raise HTTPException(404, "Not found.")
    return PageOut.model_validate(page)


@router.post("/pages", response_model=PageOut, status_code=201)
async def create_page(body: PageIn, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)) -> PageOut:
    page = Page(**body.model_dump())
    s.add(page)
    audit(s, p.user_id, "page.create", body.slug)
    await commit_or_conflict(s, "page")
    return PageOut.model_validate(page)


@router.patch("/pages/{page_id}", response_model=PageOut)
async def update_page(
    page_id: str, body: PagePatch, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)
) -> PageOut:
    page = await s.get(Page, page_id)
    if page is None:
        raise HTTPException(404, "Not found.")
    for k, v in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(page, k, v)
    audit(s, p.user_id, "page.update", page.id)
    await commit_or_conflict(s, "page")
    return PageOut.model_validate(page)


@router.delete("/pages/{page_id}", status_code=204)
async def delete_page(page_id: str, p: Principal = Depends(editor), s: AsyncSession = Depends(session_dep)) -> Response:
    page = await s.get(Page, page_id)
    if page is not None:
        await s.delete(page)
        audit(s, p.user_id, "page.delete", page_id)
        await s.commit()
    return Response(status_code=204)
