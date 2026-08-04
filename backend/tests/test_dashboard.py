from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept


async def test_org_overview(client, admin_token):
    # seed a manager + two reports with employment details
    await invite_and_accept(
        client, admin_token, email="mgr@z.com", role="manager", full_name="Manny Mgr",
        team="Ops",
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Manny Mgr")
    for i in range(2):
        await invite_and_accept(
            client, admin_token, email=f"e{i}@z.com", role="employee",
            full_name=f"Emp {i}", team="Ops", manager_id=mgr_id,
        )
        eid = await employee_id_by_name(client, admin_token, f"Emp {i}")
        await client.patch(
            f"/api/employees/{eid}",
            headers=auth(admin_token),
            json={"employment_type": "full_time", "gender": "male"},
        )

    # one still-pending invite (never accepted)
    await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={
            "email": "pending@z.com",
            "role": "employee",
            "initial_employee": {"full_name": "Pat Pending", "team": "Ops"},
        },
    )

    r = await client.get("/api/dashboard/overview", headers=auth(admin_token))
    assert r.status_code == 200
    d = r.json()
    # HR admin + manager + 2 employees + 1 pending = 5 employee records
    assert d["total_employees"] == 5
    assert d["active_employees"] == 4  # admin, manager, 2 employees
    assert d["pending_employees"] == 1
    assert d["managers"] == 1  # one person has reports
    assert d["employment_type_breakdown"][0]["label"] == "Full-time"
    assert d["employment_type_breakdown"][0]["count"] == 2
    assert any(t["label"] == "Ops" for t in d["headcount_by_team"])


async def test_overview_is_hr_only(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="e@z.com", role="employee", full_name="Emp"
    )
    r = await client.get("/api/dashboard/overview", headers=auth(emp))
    assert r.status_code == 403
