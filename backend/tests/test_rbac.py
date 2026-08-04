from tests.conftest import auth
from tests.helpers import invite_and_accept


async def _user(client, admin, email, role):
    return await invite_and_accept(
        client, admin, email=email, role=role, full_name=f"{role.title()} User"
    )


async def test_hr_manages_people_and_cycles_but_not_roles(client, admin_token):
    hr = await _user(client, admin_token, "hr@z.com", "hr")

    # can invite employees, run cycles, manage KPIs
    r = await client.post(
        "/api/users/invite",
        headers=auth(hr),
        json={"email": "e@z.com", "role": "employee", "initial_employee": {"full_name": "Emp"}},
    )
    assert r.status_code == 201
    emp_user_id = r.json()["user_id"]
    r = await client.post(
        "/api/cycles",
        headers=auth(hr),
        json={"year": 2035, "type": "mid_year",
              "opens_at": "2035-06-01T00:00:00Z", "closes_at": "2035-07-31T00:00:00Z"},
    )
    assert r.status_code == 201
    r = await client.post(
        "/api/kpis", headers=auth(hr),
        json={"name": "Punctuality", "category": "Ownership & Initiative"},
    )
    assert r.status_code == 201

    # cannot hand out elevated roles, or change anyone's role
    r = await client.post(
        "/api/users/invite", headers=auth(hr),
        json={"email": "x@z.com", "role": "executive", "initial_employee": {"full_name": "Ex"}},
    )
    assert r.status_code == 403
    r = await client.patch(
        f"/api/users/{emp_user_id}", headers=auth(hr), json={"role": "manager"}
    )
    assert r.status_code == 403


async def test_manager_has_no_admin_powers(client, admin_token):
    mgr = await _user(client, admin_token, "m@z.com", "manager")
    for path in [
        "/api/cycles", "/api/users", "/api/analytics/summary",
        "/api/audit", "/api/dashboard/overview",
    ]:
        r = await client.get(path, headers=auth(mgr))
        assert r.status_code == 403, path
    r = await client.post(
        "/api/kpis", headers=auth(mgr),
        json={"name": "Y", "category": "Ownership & Initiative"},
    )
    assert r.status_code == 403


async def test_employee_sees_only_self(client, admin_token):
    emp = await _user(client, admin_token, "emp@z.com", "employee")
    r = await client.get("/api/employees", headers=auth(emp))
    assert [e["full_name"] for e in r.json()] == ["Employee User"]
    assert (await client.get("/api/cycles", headers=auth(emp))).status_code == 403
    assert (await client.get("/api/analytics/summary", headers=auth(emp))).status_code == 403


async def test_executive_has_full_access(client, admin_token):
    exe = await _user(client, admin_token, "exec@z.com", "executive")
    assert (await client.get("/api/users", headers=auth(exe))).status_code == 200
    assert (await client.get("/api/analytics/summary", headers=auth(exe))).status_code == 200
    assert (await client.get("/api/dashboard/overview", headers=auth(exe))).status_code == 200

    # executives can change roles
    r = await client.post(
        "/api/users/invite", headers=auth(exe),
        json={"email": "p@z.com", "role": "employee", "initial_employee": {"full_name": "Prom"}},
    )
    uid = r.json()["user_id"]
    r = await client.patch(f"/api/users/{uid}", headers=auth(exe), json={"role": "manager"})
    assert r.status_code == 200
    assert r.json()["role"] == "manager"
