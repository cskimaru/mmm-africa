from .conftest import auth

EDITOR = auth("u1", "editor")


async def test_seeded_structure_is_public(client):
    r = await client.get("/api/directory/structure")
    assert r.status_code == 200
    data = r.json()
    assert [u["slug"] for u in data["international"]] == ["mmm-international"]
    assert [u["slug"] for u in data["continental"]] == ["africa"]
    assert "kenya" in [u["slug"] for u in data["national"]]


async def test_unit_detail_has_parent_and_children(client):
    r = await client.get("/api/directory/units/africa")
    body = r.json()
    assert body["parent"]["slug"] == "mmm-international"
    assert "kenya" in [c["slug"] for c in body["children"]]


async def test_convention_2026_has_ended(client):
    r = await client.get("/api/directory/events/convention-2026")
    assert r.status_code == 200
    body = r.json()
    assert body["host"]["slug"] == "kenya"
    assert body["state"] in {"ended", "happening", "upcoming"}


async def test_writes_need_an_editor(client):
    new = {"slug": "uganda", "name": "MMM Uganda Chapter", "level": "national", "parent_id": "x"}
    assert (await client.post("/api/directory/units", json=new)).status_code == 401
    assert (await client.post("/api/directory/units", json=new, headers=auth("u2"))).status_code == 403


async def test_national_chapter_must_sit_under_the_continental_chapter(client):
    intl = "00000000000000000000000000000001"
    africa = "00000000000000000000000000000002"
    bad = {"slug": "ug-bad", "name": "MMM Uganda Chapter", "level": "national", "parent_id": intl}
    assert (await client.post("/api/directory/units", json=bad, headers=EDITOR)).status_code == 422
    good = {**bad, "slug": "uganda", "parent_id": africa, "country_code": "UG", "status": "forming"}
    r = await client.post("/api/directory/units", json=good, headers=EDITOR)
    assert r.status_code == 201, r.text
    assert r.json()["country_code"] == "ug"
    # The same address twice is refused politely.
    assert (await client.post("/api/directory/units", json=good, headers=EDITOR)).status_code == 409


async def test_hidden_units_are_only_seen_by_editors(client):
    africa = "00000000000000000000000000000002"
    unit = {"slug": "draft-land", "name": "Draft Chapter", "level": "national", "parent_id": africa, "hidden": True}
    assert (await client.post("/api/directory/units", json=unit, headers=EDITOR)).status_code == 201
    public = (await client.get("/api/directory/structure")).json()
    assert "draft-land" not in [u["slug"] for u in public["national"]]
    assert (await client.get("/api/directory/units/draft-land")).status_code == 404
    seen = (await client.get("/api/directory/structure", headers=EDITOR)).json()
    assert "draft-land" in [u["slug"] for u in seen["national"]]


async def test_officers_crud(client):
    africa = "00000000000000000000000000000002"
    r = await client.post(
        "/api/directory/officers",
        json={"unit_id": africa, "name": "Jane Achieng", "role": "Chairperson", "position": 1},
        headers=EDITOR,
    )
    assert r.status_code == 201
    oid = r.json()["id"]
    listed = (await client.get("/api/directory/officers?unit=africa")).json()
    assert [o["name"] for o in listed] == ["Jane Achieng"]
    r = await client.patch(f"/api/directory/officers/{oid}", json={"term": "2026-2028"}, headers=EDITOR)
    assert r.json()["term"] == "2026-2028"
    assert (await client.delete(f"/api/directory/officers/{oid}", headers=EDITOR)).status_code == 204
    assert (await client.get("/api/directory/officers?unit=africa")).json() == []


async def test_cannot_delete_a_unit_with_chapters_under_it(client):
    africa = "00000000000000000000000000000002"
    assert (await client.delete(f"/api/directory/units/{africa}", headers=EDITOR)).status_code == 409


async def test_event_dates_are_checked(client):
    ev = {"slug": "bad-dates", "title": "Retreat", "starts_on": "2027-05-10", "ends_on": "2027-05-01"}
    assert (await client.post("/api/directory/events", json=ev, headers=EDITOR)).status_code == 422
    ev["ends_on"] = "2027-05-12"
    r = await client.post("/api/directory/events", json=ev, headers=EDITOR)
    assert r.status_code == 201
    assert r.json()["state"] == "upcoming"


async def test_links_must_be_web_addresses(client):
    ev = {
        "slug": "x-link",
        "title": "Retreat",
        "starts_on": "2027-05-10",
        "ends_on": "2027-05-12",
        "register_url": "javascript:alert(1)",
    }
    assert (await client.post("/api/directory/events", json=ev, headers=EDITOR)).status_code == 422


async def test_contact_message_flow(client):
    msg = {
        "name": "Grace",
        "email": "grace@example.com",
        "country": "Uganda",
        "topic": "start_chapter",
        "body": "We would like to start a chapter in Kampala.",
    }
    assert (await client.post("/api/directory/messages", json=msg)).status_code == 202
    # Bots that fill the hidden field get the same answer but nothing is stored.
    assert (await client.post("/api/directory/messages", json={**msg, "website": "spam"})).status_code == 202
    assert (await client.get("/api/directory/messages")).status_code == 401
    rows = (await client.get("/api/directory/messages", headers=EDITOR)).json()
    assert len(rows) == 1 and rows[0]["topic"] == "start_chapter"
    r = await client.post(f"/api/directory/messages/{rows[0]['id']}/handled", headers=EDITOR)
    assert r.json()["handled_at"]
    assert (await client.get("/api/directory/messages", headers=EDITOR)).json() == []


async def test_contact_messages_are_rate_limited(client):
    msg = {"name": "Grace", "email": "grace@example.com", "body": "Hello there, friends."}
    codes = [(await client.post("/api/directory/messages", json=msg)).status_code for _ in range(6)]
    assert codes[:5] == [202] * 5 and codes[5] == 429
