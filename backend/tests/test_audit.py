from tests.conftest import auth
from tests.helpers import invite_and_accept


async def test_audit_records_admin_actions(client, admin_token):
    # an invite should produce a user.invite audit entry
    await invite_and_accept(
        client, admin_token, email="audit@z.com", role="employee", full_name="Aud It"
    )
    # create a cycle → cycle.create
    r = await client.post(
        "/api/cycles",
        headers=auth(admin_token),
        json={
            "year": 2029, "type": "mid_year",
            "opens_at": "2029-06-01T00:00:00Z", "closes_at": "2029-07-31T00:00:00Z",
        },
    )
    assert r.status_code == 201

    r = await client.get("/api/audit", headers=auth(admin_token))
    assert r.status_code == 200
    entries = r.json()
    actions = {e["action"] for e in entries}
    assert "user.invite" in actions
    assert "cycle.create" in actions

    invite_entry = next(e for e in entries if e["action"] == "user.invite")
    assert invite_entry["actor_email"] == "admin@zillaclinicals.com"
    assert invite_entry["target_type"] == "user"
    assert invite_entry["detail"]["email"] == "audit@z.com"


async def test_audit_is_hr_only(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="e@z.com", role="employee", full_name="Emp"
    )
    r = await client.get("/api/audit", headers=auth(emp))
    assert r.status_code == 403


async def test_deactivate_is_audited(client, admin_token):
    r = await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={
            "email": "victim@z.com",
            "role": "employee",
            "initial_employee": {"full_name": "Vic Tim"},
        },
    )
    user_id = r.json()["user_id"]
    await client.patch(
        f"/api/users/{user_id}", headers=auth(admin_token), json={"is_active": False}
    )
    r = await client.get("/api/audit", headers=auth(admin_token))
    actions = [(e["action"], e["target_id"]) for e in r.json()]
    assert ("user.update", user_id) in actions
