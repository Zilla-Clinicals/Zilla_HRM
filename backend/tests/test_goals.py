from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept


async def _login(client, email, pw="MemberPass1!"):
    r = await client.post("/api/auth/login", json={"email": email, "password": pw})
    return r.json()["access_token"]


async def test_goal_lifecycle_and_checkins(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="goalie@z.com", role="employee", full_name="Goal Getter"
    )

    # create a goal
    r = await client.post(
        "/api/goals",
        headers=auth(emp),
        json={"year": 2026, "title": "Ship the portal", "category": "performance"},
    )
    assert r.status_code == 201, r.text
    goal = r.json()
    assert goal["progress"] == 0 and goal["status"] == "not_started"
    gid = goal["id"]

    # appears in my goals
    r = await client.get("/api/goals/mine?year=2026", headers=auth(emp))
    assert len(r.json()) == 1

    # owner check-in moves progress + flips status
    r = await client.post(
        f"/api/goals/{gid}/checkins",
        headers=auth(emp),
        json={"progress": 60, "note": "Halfway there"},
    )
    assert r.status_code == 201
    r = await client.get(f"/api/goals/{gid}", headers=auth(emp))
    body = r.json()
    assert body["progress"] == 60 and body["status"] == "in_progress"
    assert len(body["checkins"]) == 1

    # complete it
    r = await client.patch(
        f"/api/goals/{gid}", headers=auth(emp), json={"status": "completed", "progress": 100}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


async def test_manager_can_view_and_comment_but_not_edit(client, admin_token):
    mgr = await invite_and_accept(
        client, admin_token, email="lead@z.com", role="manager", full_name="Team Lead"
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Team Lead")
    await invite_and_accept(
        client, admin_token, email="rep@z.com", role="employee", full_name="Report Person",
        manager_id=mgr_id,
    )
    rep = await _login(client, "rep@z.com")
    rep_eid = await employee_id_by_name(client, admin_token, "Report Person")

    gid = (
        await client.post(
            "/api/goals", headers=auth(rep),
            json={"year": 2026, "title": "Learn SQL"},
        )
    ).json()["id"]

    # manager sees the report's goals
    r = await client.get(f"/api/employees/{rep_eid}/goals", headers=auth(mgr))
    assert r.status_code == 200 and len(r.json()) == 1

    # manager can comment (no progress change)
    r = await client.post(
        f"/api/goals/{gid}/checkins", headers=auth(mgr), json={"progress": 90, "note": "Nice work"}
    )
    assert r.status_code == 201
    detail = (await client.get(f"/api/goals/{gid}", headers=auth(mgr))).json()
    assert detail["progress"] == 0  # manager's progress ignored
    assert detail["checkins"][0]["note"] == "Nice work"

    # manager cannot edit the goal
    r = await client.patch(
        f"/api/goals/{gid}", headers=auth(mgr), json={"title": "Hacked"}
    )
    assert r.status_code == 403


async def test_others_cannot_see_goals(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="a@z.com", role="employee", full_name="Alpha"
    )
    other = await invite_and_accept(
        client, admin_token, email="b@z.com", role="employee", full_name="Beta"
    )
    alpha = await _login(client, "a@z.com")
    alpha_eid = await employee_id_by_name(client, admin_token, "Alpha")
    gid = (
        await client.post(
            "/api/goals", headers=auth(alpha), json={"year": 2026, "title": "Private"}
        )
    ).json()["id"]

    # unrelated employee is blocked
    r = await client.get(f"/api/employees/{alpha_eid}/goals", headers=auth(other))
    assert r.status_code == 403
    assert (await client.get(f"/api/goals/{gid}", headers=auth(other))).status_code == 403

    # HR/admin sees everything
    r = await client.get(f"/api/employees/{alpha_eid}/goals", headers=auth(admin_token))
    assert r.status_code == 200 and len(r.json()) == 1
