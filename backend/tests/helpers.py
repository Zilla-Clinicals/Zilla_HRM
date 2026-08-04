from httpx import AsyncClient

from tests.conftest import auth


async def invite_and_accept(
    client: AsyncClient,
    admin_token: str,
    *,
    email: str,
    role: str,
    full_name: str,
    team: str | None = None,
    manager_id: int | None = None,
    password: str = "MemberPass1!",
) -> str:
    """Invite a user, accept the invite, return their access token."""
    r = await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={
            "email": email,
            "role": role,
            "initial_employee": {
                "full_name": full_name,
                "team": team,
                "manager_id": manager_id,
            },
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["invite_link"].split("token=")[1]

    r = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "full_name": full_name, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def employee_id_by_name(client: AsyncClient, admin_token: str, name: str) -> int:
    r = await client.get("/api/employees", headers=auth(admin_token))
    assert r.status_code == 200
    for e in r.json():
        if e["full_name"] == name:
            return e["id"]
    raise AssertionError(f"employee {name!r} not found")
