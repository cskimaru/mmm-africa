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


PAGE = {
    "id": "p1",
    "slug": "news",
    "title": "News",
    "summary": "Latest from the chapters",
    "body": (
        "## Outreach\n\nWe served <b>200</b> people.\n\n"
        "- Nairobi\n- [Kisumu](https://example.org)\n- [bad](javascript:alert(1))"
    ),
    "in_menu": True,
    "position": 1,
    "hidden": False,
    "updated_at": "2026-11-03T00:00:00Z",
}


def mock_all(content=None, pages=None):
    respx.get(f"{D}/content").mock(return_value=httpx.Response(200, json={"values": content or {}}))
    respx.get(f"{D}/pages").mock(return_value=httpx.Response(200, json=[PAGE] if pages is None else pages))
    respx.get(f"{D}/pages/news").mock(return_value=httpx.Response(200, json=PAGE))
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
    respx.get(f"{D}/content").mock(side_effect=httpx.ConnectError("down"))
    respx.get(f"{D}/pages").mock(side_effect=httpx.ConnectError("down"))
    respx.get(f"{D}/structure").mock(side_effect=httpx.ConnectError("down"))
    respx.get(f"{D}/events").mock(side_effect=httpx.ConnectError("down"))
    r = await client.get("/")
    assert r.status_code == 200
    assert "could not be loaded" in r.text


@respx.mock
async def test_officer_pages_are_not_cached_or_indexed(client):
    mock_all()
    r = await client.get("/officers")
    assert r.headers["cache-control"] == "no-store"
    assert "noindex" in r.text
    assert "Disallow: /officers" in (await client.get("/robots.txt")).text


@respx.mock
async def test_no_church_comparison_on_public_pages(client):
    mock_all()
    for path in ("/", "/about", "/chapters", "/chapters/kenya"):
        html = (await client.get(path)).text
        for phrase in ("Seventh-day", "General Conference", "Division", "Union", "finances"):
            assert phrase not in html, (path, phrase)


@respx.mock
async def test_officers_text_and_colour_scheme_replace_the_defaults(client):
    mock_all(
        content={
            "home.hero_title": "Healing <Africa>",
            "site.palette": "coast",
            "about.story_body": "See [MMMK](/chapters/kenya).",
        }
    )
    home = (await client.get("/")).text
    assert "Healing &lt;Africa&gt;" in home
    assert 'data-palette="coast"' in home
    assert "One continent. One calling." not in home
    about = (await client.get("/about")).text
    assert '<a href="/chapters/kenya">MMMK</a>' in about


@respx.mock
async def test_officer_written_page_and_menu(client):
    mock_all()
    home = (await client.get("/")).text
    assert '<a href="/pages/news">News</a>' in home
    html = (await client.get("/pages/news")).text
    assert "<h2>Outreach</h2>" in html
    assert "&lt;b&gt;200&lt;/b&gt;" in html
    assert '<a href="https://example.org" rel="noopener" target="_blank">Kisumu</a>' in html
    assert "javascript:" not in html.split("<main")[1].split("</main>")[0].replace("[bad](javascript:alert(1))", "")


@respx.mock
async def test_officers_area_lists_every_text_field(client):
    mock_all()
    html = (await client.get("/officers")).text
    from app.site_text import DEFAULTS

    for key in DEFAULTS:
        assert f'data-key="{key}"' in html


async def test_background_pictures_get_a_fingerprint_so_changes_show(client):
    r = await client.get("/static/site.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "url(/static/art/sunrise.webp?v=" in r.text
    assert "url(/static/art/sunrise.webp)" not in r.text
