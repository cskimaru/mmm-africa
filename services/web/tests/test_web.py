import httpx
import respx

D = "http://directory.internal/api/directory"


def unit(slug, level, **kw):
    base = {
        "id": slug,
        "slug": slug,
        "name": kw.pop("name", slug.title()),
        "short_name": "",
        "level": level,
        "parent_id": None,
        "country_code": "",
        "city": "",
        "status": "established",
        "website_url": "",
        "email": "",
        "phone": "",
        "summary": "",
        "position": 1,
        "hidden": False,
    }
    return {**base, **kw}


INTL = unit(
    "mmm-international",
    "international",
    name="Medical Missionary Movement International",
    website_url="https://medicalmissionarymovement.org/",
)
AFRICA = unit("africa", "continental", name="MMM African Chapter")
KENYA = unit(
    "kenya",
    "national",
    name="MMM Kenya Chapter",
    short_name="MMMK",
    country_code="ke",
    website_url="https://mmmkenya.org",
    summary="<script>alert(1)</script>",
)
STRUCTURE = {"international": [INTL], "continental": [AFRICA], "national": [KENYA]}
EVENT = {
    "id": "e1",
    "slug": "convention-2026",
    "title": "MMM African Chapter Annual Convention 2026",
    "theme": "We Have Seen His Star",
    "scripture": "Matthew 2:2",
    "starts_on": "2026-09-27",
    "ends_on": "2026-10-04",
    "venue": "Watamu Adventist Beach Resort",
    "location": "Watamu, Kenya",
    "host_unit_id": "kenya",
    "host": KENYA,
    "summary": "A week of worship.",
    "recap": "Thank you to every delegate.",
    "register_url": "",
    "hidden": False,
    "state": "ended",
}


def mock_all():
    respx.get(f"{D}/structure").mock(return_value=httpx.Response(200, json=STRUCTURE))
    respx.get(f"{D}/events").mock(return_value=httpx.Response(200, json=[EVENT]))
    respx.get(f"{D}/events/convention-2026").mock(return_value=httpx.Response(200, json=EVENT))
    respx.get(f"{D}/units/kenya").mock(
        return_value=httpx.Response(200, json={**KENYA, "officers": [], "parent": AFRICA, "children": []})
    )
    respx.get(f"{D}/units/africa").mock(
        return_value=httpx.Response(
            200,
            json={
                **AFRICA,
                "parent": INTL,
                "children": [KENYA],
                "officers": [
                    {
                        "id": "o1",
                        "unit_id": "africa",
                        "name": "Jane Achieng",
                        "role": "Chairperson",
                        "term": "",
                        "email": "",
                        "position": 1,
                    }
                ],
            },
        )
    )


@respx.mock
async def test_home_shows_structure_map_and_thank_you(client):
    mock_all()
    r = await client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "How the MMM family fits together" in html
    assert "MMM Kenya Chapter" in html
    assert 'class="country is-established"' in html  # Kenya coloured on the map
    assert "Thank you to every delegate." in html
    # Content from the directory is escaped.
    assert "<script>alert(1)</script>" not in html


@respx.mock
async def test_all_public_pages_render(client):
    mock_all()
    for path in (
        "/about",
        "/chapters",
        "/chapters/kenya",
        "/leadership",
        "/events",
        "/events/convention-2026",
        "/contact",
    ):
        r = await client.get(path)
        assert r.status_code == 200, path
    assert "Jane Achieng" in (await client.get("/leadership")).text
    event = (await client.get("/events/convention-2026")).text
    assert "Event complete" in event and "Register" not in event.split("<main")[1]


@respx.mock
async def test_missing_pages_are_404(client):
    mock_all()
    respx.get(f"{D}/units/nowhere").mock(return_value=httpx.Response(404, json={"detail": "Not found."}))
    assert (await client.get("/chapters/nowhere")).status_code == 404
    # The continental unit is not a national chapter page.
    assert (await client.get("/chapters/africa")).status_code == 404


@respx.mock
async def test_last_good_copy_is_served_when_directory_is_down(client):
    mock_all()
    assert (await client.get("/chapters")).status_code == 200
    respx.get(f"{D}/structure").mock(side_effect=httpx.ConnectError("down"))
    r = await client.get("/chapters")
    assert r.status_code == 200
    assert "MMM Kenya Chapter" in r.text
    assert "older copy" in r.text


@respx.mock
async def test_home_still_renders_with_nothing_cached(client):
    respx.get(f"{D}/structure").mock(side_effect=httpx.ConnectError("down"))
    respx.get(f"{D}/events").mock(side_effect=httpx.ConnectError("down"))
    r = await client.get("/")
    assert r.status_code == 200
    assert "could not be loaded" in r.text


async def test_officer_pages_are_not_cached_or_indexed(client):
    r = await client.get("/officers")
    assert r.headers["cache-control"] == "no-store"
    assert "noindex" in r.text
    assert "Disallow: /officers" in (await client.get("/robots.txt")).text
