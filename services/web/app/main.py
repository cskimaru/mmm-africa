import hashlib
import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mmm_common.app import create_app
from mmm_common.security import ACCESS_COOKIE

from .config import get_settings
from .content import ContentClient

HERE = Path(__file__).parent
settings = get_settings()


async def shutdown(app: FastAPI) -> None:
    await app.state.content.close()


app = create_app(settings, title="MMM Africa web", on_shutdown=shutdown)
app.state.content = ContentClient(settings)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")

AFRICA_MAP = json.loads((HERE / "africa_map.json").read_text())
# (key, name shown to reviewers). Each has a painted background in static/art/<key>.webp.
PALETTES = [
    ("sunrise", "Savanna sunrise"),
    ("coast", "Coast"),
    ("highlands", "Highlands"),
    ("evening", "Evening"),
]
TOPICS = {
    "general": "General question",
    "start_chapter": "Starting a chapter in my country",
    "partner": "Partnering with the African Chapter",
    "volunteer": "Volunteering",
}


DASH = "\u2013"  # en dash, as used in date ranges


def date_range(start: str, end: str) -> str:
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError):
        return ""
    if a == b:
        return f"{a.day} {a:%B %Y}"
    if a.year == b.year and a.month == b.month:
        return f"{a.day}{DASH}{b.day} {a:%B %Y}"
    if a.year == b.year:
        return f"{a.day} {a:%B} {DASH} {b.day} {b:%B %Y}"
    return f"{a.day} {a:%B %Y} {DASH} {b.day} {b:%B %Y}"


def initials(name: str) -> str:
    return "".join(p[0] for p in name.split()[:2]).upper()


def static_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for f in sorted(root.rglob("*")):
        if f.is_file():
            digest.update(f.relative_to(root).as_posix().encode())
            digest.update(f.read_bytes())
    return digest.hexdigest()[:12]


templates.env.filters["date_range"] = date_range
templates.env.filters["initials"] = initials
templates.env.globals.update(
    asset_version=settings.asset_version or static_fingerprint(HERE / "static"),
    site_origin=settings.site_origin,
    site_preview=settings.site_preview,
    palettes=PALETTES,
    palette=settings.site_palette if settings.site_palette in dict(PALETTES) else "sunrise",
    contact_email=settings.contact_email,
    contact_phone=settings.contact_phone,
    map_source=AFRICA_MAP["source"],
    year=date.today().year,
)

NO_STORE = {"Cache-Control": "no-store"}
PUBLIC = {"Cache-Control": "public, max-age=30"}


def auth_headers(request: Request) -> dict | None:
    token = request.cookies.get(ACCESS_COOKIE)
    return {"cookie": f"{ACCESS_COOKIE}={token}"} if token else None


async def fetch(request: Request, path: str):
    return await request.app.state.content.get(path, auth_headers(request))


def render(request: Request, name: str, ctx: dict, status: int = 200) -> HTMLResponse:
    headers = NO_STORE if auth_headers(request) else PUBLIC
    return templates.TemplateResponse(request, name, ctx, status_code=status, headers=headers)


def not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "404.html", {"nav": ""}, status_code=404, headers=NO_STORE)


def unavailable(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "503.html", {"nav": ""}, status_code=503, headers=NO_STORE)


def empty_structure() -> dict:
    return {"international": [], "continental": [], "national": []}


def map_countries(national: list[dict]) -> list[dict]:
    by_code = {u["country_code"]: u for u in national if u.get("country_code")}
    out = []
    for c in AFRICA_MAP["countries"]:
        unit = by_code.get(c["code"])
        out.append({**c, "unit": unit, "status": unit["status"] if unit else ""})
    return out


def split_events(events: list[dict]) -> tuple[list[dict], list[dict]]:
    upcoming = sorted((e for e in events if e["state"] != "ended"), key=lambda e: e["starts_on"])
    past = [e for e in events if e["state"] == "ended"]
    return upcoming, past


# ---- Public pages ----


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    st = await fetch(request, "/api/directory/structure")
    ev = await fetch(request, "/api/directory/events")
    structure = st.data if st.ok else empty_structure()
    upcoming, past = split_events(ev.data if ev.ok else [])
    return render(
        request,
        "index.html",
        {
            "nav": "home",
            "structure": structure,
            "countries": map_countries(structure["national"]),
            "map_viewbox": AFRICA_MAP["viewBox"],
            "featured": (upcoming or past or [None])[0],
            "degraded": st.degraded or ev.degraded or not st.ok,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> HTMLResponse:
    st = await fetch(request, "/api/directory/structure")
    structure = st.data if st.ok else empty_structure()
    return render(request, "about.html", {"nav": "about", "structure": structure, "degraded": st.degraded or not st.ok})


@app.get("/chapters", response_class=HTMLResponse)
async def chapters(request: Request) -> HTMLResponse:
    st = await fetch(request, "/api/directory/structure")
    structure = st.data if st.ok else empty_structure()
    return render(
        request,
        "chapters.html",
        {
            "nav": "chapters",
            "chapters": structure["national"],
            "countries": map_countries(structure["national"]),
            "map_viewbox": AFRICA_MAP["viewBox"],
            "degraded": st.degraded or not st.ok,
        },
    )


@app.get("/chapters/{slug}", response_class=HTMLResponse)
async def chapter(request: Request, slug: str) -> HTMLResponse:
    res = await fetch(request, f"/api/directory/units/{slug}")
    if res.status == 404 or (res.ok and res.data["level"] != "national"):
        return not_found(request)
    if not res.ok:
        return unavailable(request)
    ev = await fetch(request, "/api/directory/events")
    hosted = [e for e in (ev.data if ev.ok else []) if e.get("host_unit_id") == res.data["id"]]
    return render(request, "chapter.html", {"nav": "chapters", "unit": res.data, "events": hosted})


@app.get("/leadership", response_class=HTMLResponse)
async def leadership(request: Request) -> HTMLResponse:
    res = await fetch(request, "/api/directory/units/africa")
    if not res.ok:
        return unavailable(request)
    return render(request, "leadership.html", {"nav": "leadership", "unit": res.data})


@app.get("/events", response_class=HTMLResponse)
async def events(request: Request) -> HTMLResponse:
    ev = await fetch(request, "/api/directory/events")
    upcoming, past = split_events(ev.data if ev.ok else [])
    return render(
        request,
        "events.html",
        {"nav": "events", "upcoming": upcoming, "past": past, "degraded": ev.degraded or not ev.ok},
    )


@app.get("/events/{slug}", response_class=HTMLResponse)
async def event(request: Request, slug: str) -> HTMLResponse:
    res = await fetch(request, f"/api/directory/events/{slug}")
    if res.status == 404:
        return not_found(request)
    if not res.ok:
        return unavailable(request)
    return render(request, "event.html", {"nav": "events", "event": res.data})


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request) -> HTMLResponse:
    topic = request.query_params.get("topic", "general")
    return render(
        request, "contact.html", {"nav": "contact", "topics": TOPICS, "topic": topic if topic in TOPICS else "general"}
    )


# ---- Officers ----


@app.get("/officers", response_class=HTMLResponse)
async def officers(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "officers.html", {"nav": ""}, headers=NO_STORE)


@app.get("/invite", response_class=HTMLResponse)
async def invite(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "invite.html", {"nav": ""}, headers=NO_STORE)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return "User-agent: *\nDisallow: /officers\nDisallow: /invite\nDisallow: /api/\n"
