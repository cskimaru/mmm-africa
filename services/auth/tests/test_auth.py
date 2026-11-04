import uuid

from httpx import ASGITransport, AsyncClient


async def login(client, email, password):
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def test_login_sets_session_and_me_works(client, owner):
    r = await login(client, owner["email"], owner["password"])
    assert r.status_code == 200, r.text
    assert "owner" in r.json()["roles"]
    assert "mmma_access" in client.cookies
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == owner["email"]


async def test_wrong_password_then_lockout(client, owner):
    for _ in range(5):
        r = await login(client, owner["email"], "wrong password!!")
        assert r.status_code == 401
    r = await login(client, owner["email"], owner["password"])
    assert r.status_code == 423
    # unlock for other tests
    from sqlalchemy import update

    from app.main import db
    from app.models import User

    async with db.sessionmaker() as s:
        await s.execute(update(User).values(locked_until=None, failed_logins=0))
        await s.commit()


async def test_unknown_email_gives_same_error(client):
    r = await login(client, "nobody@example.com", "whatever password")
    assert r.status_code == 401
    assert r.json()["detail"] == "That email and password don't match an account."


async def test_invitation_flow(client, owner):
    await login(client, owner["email"], owner["password"])
    email = f"cousin-{uuid.uuid4().hex[:6]}@example.com"
    r = await client.post("/api/auth/invitations", json={"email": email, "roles": ["editor"]})
    assert r.status_code == 201, r.text
    url = r.json()["invite_url"]
    token = url.split("#", 1)[1]

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"origin": "http://testserver"}
    ) as guest:
        info = await guest.get("/api/auth/invitations/lookup", params={"token": token})
        assert info.status_code == 200
        assert info.json()["email"] == email
        weak = await guest.post(
            "/api/auth/invitations/accept", json={"token": token, "display_name": "Cousin", "password": "short"}
        )
        assert weak.status_code == 422
        ok = await guest.post(
            "/api/auth/invitations/accept",
            json={"token": token, "display_name": "Cousin", "password": "a long family phrase"},
        )
        assert ok.status_code == 201, ok.text
        assert ok.json()["roles"] == ["editor"]
        # Editors cannot invite others.
        r = await guest.post("/api/auth/invitations", json={"email": "x@example.com"})
        assert r.status_code == 403
        # The link works only once.
        again = await guest.get("/api/auth/invitations/lookup", params={"token": token})
        assert again.status_code == 404


async def test_refresh_rotation_and_reuse_detection(client, owner):
    await login(client, owner["email"], owner["password"])
    first = client.cookies.get("mmma_refresh")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200
    second = client.cookies.get("mmma_refresh")
    assert first != second
    # Replaying the old token ends the whole session chain.
    client.cookies.set("mmma_refresh", first, path="/api/auth")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401
    client.cookies.set("mmma_refresh", second, path="/api/auth")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_cross_site_write_is_blocked(client, owner):
    await login(client, owner["email"], owner["password"])
    r = await client.post(
        "/api/auth/invitations", json={"email": "evil@example.com"}, headers={"origin": "https://evil.example"}
    )
    assert r.status_code == 403


async def test_last_owner_cannot_be_removed(client, owner):
    r = await login(client, owner["email"], owner["password"])
    uid = r.json()["id"]
    r = await client.patch(f"/api/auth/users/{uid}", json={"roles": ["editor"]})
    assert r.status_code == 409


async def test_logout_clears_session(client, owner):
    await login(client, owner["email"], owner["password"])
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_owner_manages_people_and_invitations(client, owner):
    await login(client, owner["email"], owner["password"])
    r = await client.post("/api/auth/invitations", json={"email": "aunt@example.com", "roles": ["editor"]})
    inv = r.json()
    assert r.status_code == 201
    dup = await client.post("/api/auth/invitations", json={"email": "owner@example.com"})
    assert dup.status_code == 409
    listed = (await client.get("/api/auth/invitations")).json()
    assert any(i["id"] == inv["id"] for i in listed)
    assert (await client.delete(f"/api/auth/invitations/{inv['id']}")).status_code == 204
    token = inv["invite_url"].split("#")[1]
    assert (await client.get("/api/auth/invitations/lookup", params={"token": token})).status_code == 404
    assert (await client.delete("/api/auth/invitations/missing")).status_code == 404
    bad_role = await client.post("/api/auth/invitations", json={"email": "x@example.com", "roles": ["admin"]})
    assert bad_role.status_code == 422


async def test_deactivated_user_loses_access(client, owner):
    await login(client, owner["email"], owner["password"])
    email = f"temp-{uuid.uuid4().hex[:6]}@example.com"
    token = (await client.post("/api/auth/invitations", json={"email": email})).json()["invite_url"].split("#")[1]
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"origin": "http://testserver"}
    ) as other:
        uid = (
            await other.post(
                "/api/auth/invitations/accept",
                json={"token": token, "display_name": "Temp", "password": "a sturdy passphrase"},
            )
        ).json()["id"]
        users = (await client.get("/api/auth/users")).json()
        assert any(u["id"] == uid for u in users)
        r = await client.patch(f"/api/auth/users/{uid}", json={"is_active": False})
        assert r.status_code == 200 and r.json()["is_active"] is False
        assert (await other.post("/api/auth/refresh")).status_code == 401
        assert (await login(other, email, "a sturdy passphrase")).status_code == 401
    assert (await client.patch("/api/auth/users/missing", json={"is_active": False})).status_code == 404


async def test_change_password(client):
    from app.cli import create_owner

    await create_owner("pw@example.com", "Pw", "first long password")
    await login(client, "pw@example.com", "first long password")
    bad = await client.post("/api/auth/password", json={"current_password": "wrong", "new_password": "x" * 12})
    assert bad.status_code == 400
    weak = await client.post(
        "/api/auth/password", json={"current_password": "first long password", "new_password": "aaaaaaaaaaaa"}
    )
    assert weak.status_code == 422
    ok = await client.post(
        "/api/auth/password", json={"current_password": "first long password", "new_password": "second long password"}
    )
    assert ok.status_code == 204
    assert (await client.post("/api/auth/refresh")).status_code == 401
    assert (await login(client, "pw@example.com", "second long password")).status_code == 200


async def test_cli_rejects_short_password_and_promotes_existing():
    from app.cli import create_owner

    assert await create_owner("short@example.com", "S", "short") == 2
    assert await create_owner("owner@example.com", "Anita", "correct horse battery") == 0


async def test_health_and_metrics(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    ready = await client.get("/readyz")
    assert ready.status_code == 200 and ready.json()["checks"]["database"] is True
    assert "http_requests_total" in (await client.get("/metrics")).text


async def test_extra_origins_are_accepted(owner):
    """While shared through a tunnel the site is also opened at http://localhost:8080; edits from there work."""
    from app.main import app
    from mmm_common.middleware import OriginCheckMiddleware

    mw = next(m for m in app.user_middleware if m.cls is OriginCheckMiddleware)
    original = mw.kwargs["allowed_origins"]
    mw.kwargs["allowed_origins"] = frozenset({"http://testserver", "http://localhost:8080"})
    app.middleware_stack = None  # rebuild with the new setting
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver", headers={"origin": "http://localhost:8080"}
        ) as c:
            await c.post("/api/auth/login", json={"email": owner["email"], "password": owner["password"]})
            ok = await c.post("/api/auth/invitations", json={"email": f"x-{uuid.uuid4().hex[:6]}@example.com"})
            assert ok.status_code == 201
            bad = await c.post(
                "/api/auth/invitations", json={"email": "y@example.com"}, headers={"origin": "https://evil.example"}
            )
            assert bad.status_code == 403
    finally:
        mw.kwargs["allowed_origins"] = original
        app.middleware_stack = None


def test_allowed_origins_setting():
    from mmm_common.config import CommonSettings

    s = CommonSettings(site_origin="https://abc.trycloudflare.com/", extra_origins="http://localhost:8080, ")
    assert s.allowed_origins == {"https://abc.trycloudflare.com", "http://localhost:8080"}


async def test_cli_reset_password_lets_the_owner_sign_in_again(client):
    from app import cli

    assert await cli.create_owner("chair@example.org", "Chair", "first-password-1") == 0
    # A typo at creation: the intended password does not work.
    r = await client.post("/api/auth/login", json={"email": "chair@example.org", "password": "intended-pass-2"})
    assert r.status_code == 401
    # Running create-owner again does not change the password...
    assert await cli.create_owner("chair@example.org", "Chair", "intended-pass-2") == 0
    r = await client.post("/api/auth/login", json={"email": "chair@example.org", "password": "intended-pass-2"})
    assert r.status_code == 401
    # ...reset-password does, and also clears a lock.
    assert await cli.reset_password("CHAIR@example.org", "intended-pass-2") == 0
    r = await client.post("/api/auth/login", json={"email": "chair@example.org", "password": "intended-pass-2"})
    assert r.status_code == 200
    assert await cli.reset_password("nobody@example.org", "intended-pass-2") == 1
    assert await cli.reset_password("chair@example.org", "short") == 2


REQ = {
    "display_name": "Grace Achieng",
    "email": "grace@example.org",
    "phone": "+254 712 345 678",
    "position": "Secretary, MMM Kenya Chapter",
    "country": "Kenya",
    "password": "healing hands 2026",
}


async def _owner_headers(client):
    from app import cli

    await cli.create_owner("owner-req@example.org", "Owner", "owner password 1")
    r = await client.post("/api/auth/login", json={"email": "owner-req@example.org", "password": "owner password 1"})
    assert r.status_code == 200
    return {"origin": "http://testserver"}


async def test_access_request_flow(client):
    # Phone must carry a country code.
    bad = await client.post("/api/auth/requests", json={**REQ, "phone": "0712345678"})
    assert bad.status_code == 422
    r = await client.post("/api/auth/requests", json=REQ)
    assert r.status_code == 202
    # Asking twice is refused politely.
    assert (await client.post("/api/auth/requests", json=REQ)).status_code == 409
    # Before approval, signing in says the request is waiting (only with the right password).
    r = await client.post("/api/auth/login", json={"email": REQ["email"], "password": REQ["password"]})
    assert r.status_code == 403 and "waiting" in r.json()["detail"]
    r = await client.post("/api/auth/login", json={"email": REQ["email"], "password": "wrong password 9"})
    assert r.status_code == 401
    # Only owners see and decide requests.
    assert (await client.get("/api/auth/requests")).status_code == 401
    headers = await _owner_headers(client)
    rows = (await client.get("/api/auth/requests", headers=headers)).json()
    assert [x["email"] for x in rows] == [REQ["email"]]
    assert rows[0]["phone"] == "+254712345678"
    r = await client.post(f"/api/auth/requests/{rows[0]['id']}/approve", json={"roles": ["editor"]}, headers=headers)
    assert r.status_code == 200
    assert r.json()["position"] == "Secretary, MMM Kenya Chapter"
    assert (await client.get("/api/auth/requests", headers=headers)).json() == []
    # The leader now signs in with the password they chose.
    await client.post("/api/auth/logout", headers=headers)
    r = await client.post("/api/auth/login", json={"email": REQ["email"], "password": REQ["password"]})
    assert r.status_code == 200 and r.json()["roles"] == ["editor"]


async def test_declined_request_cannot_sign_in(client):
    req = {**REQ, "email": "someone@example.org"}
    assert (await client.post("/api/auth/requests", json=req)).status_code == 202
    headers = await _owner_headers(client)
    rid = (await client.get("/api/auth/requests", headers=headers)).json()[0]["id"]
    assert (await client.post(f"/api/auth/requests/{rid}/decline", headers=headers)).status_code == 200
    await client.post("/api/auth/logout", headers=headers)
    r = await client.post("/api/auth/login", json={"email": req["email"], "password": req["password"]})
    assert r.status_code == 401
