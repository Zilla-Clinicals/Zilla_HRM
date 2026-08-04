from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, auth


async def test_login_and_me(client, admin_token):
    r = await client.get("/api/users/me", headers=auth(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["user"]["role"] == "admin"
    assert body["employee"]["full_name"] == "HR Admin"


async def test_login_bad_password(client):
    r = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}
    )
    assert r.status_code == 401


async def test_refresh_rotates_and_logout(client, admin_token):
    # login already set the refresh cookie on the client jar
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in r.json()

    r = await client.post("/api/auth/logout")
    assert r.status_code == 204

    # after logout the (now revoked) cookie can't refresh
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_invite_accept_flow(client, admin_token):
    r = await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={
            "email": "newbie@zillaclinicals.com",
            "role": "employee",
            "initial_employee": {"full_name": "New Bie", "team": "Ops"},
        },
    )
    assert r.status_code == 201, r.text
    link = r.json()["invite_link"]
    assert link and "token=" in link
    token = link.split("token=")[1]

    r = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "full_name": "New Bie", "password": "NewbiePass1!"},
    )
    assert r.status_code == 200, r.text
    new_token = r.json()["access_token"]

    r = await client.get("/api/users/me", headers=auth(new_token))
    assert r.json()["user"]["email"] == "newbie@zillaclinicals.com"

    # token is one-time use
    r = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "full_name": "x", "password": "AnotherPass1!"},
    )
    assert r.status_code == 400


async def test_duplicate_invite_conflicts(client, admin_token):
    payload = {
        "email": "dupe@zillaclinicals.com",
        "role": "employee",
        "initial_employee": {"full_name": "Dupe"},
    }
    r1 = await client.post("/api/users/invite", headers=auth(admin_token), json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/users/invite", headers=auth(admin_token), json=payload)
    assert r2.status_code == 409


async def test_forgot_password_always_202(client):
    r = await client.post(
        "/api/auth/forgot-password", json={"email": "nobody@nowhere.com"}
    )
    assert r.status_code == 202
    r = await client.post("/api/auth/forgot-password", json={"email": ADMIN_EMAIL})
    assert r.status_code == 202


async def test_change_own_password(client, admin_token):
    r = await client.post(
        "/api/users/me/password",
        headers=auth(admin_token),
        json={"current_password": ADMIN_PASSWORD, "new_password": "BrandNew123!"},
    )
    assert r.status_code == 204

    # old password no longer works, new one does
    r = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 401
    r = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "BrandNew123!"}
    )
    assert r.status_code == 200


async def test_protected_route_requires_token(client):
    r = await client.get("/api/users/me")
    assert r.status_code in (401, 403)
