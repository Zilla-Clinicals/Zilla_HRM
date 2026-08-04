import re

from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept

_NUMBER_RE = re.compile(r"^[A-Z]{2}-\d{5,}$")


async def test_employee_number_auto_assigned_and_unique(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="a1@z.com", role="employee", full_name="Ada Aro"
    )
    await invite_and_accept(
        client, admin_token, email="a2@z.com", role="employee", full_name="Ada Aro"
    )
    r = await client.get("/api/employees", headers=auth(admin_token))
    aros = [e for e in r.json() if e["full_name"] == "Ada Aro"]
    assert len(aros) == 2
    for e in aros:
        assert e["employee_number"] and _NUMBER_RE.match(e["employee_number"]), e
        assert e["employee_number"].startswith("AA-")  # initials of "Ada Aro"
    # even with identical names, the numbers differ
    assert aros[0]["employee_number"] != aros[1]["employee_number"]


async def test_duplicate_employee_number_rejected(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="x1@z.com", role="employee", full_name="One Person"
    )
    await invite_and_accept(
        client, admin_token, email="x2@z.com", role="employee", full_name="Two Person"
    )
    e1 = await _employee(client, admin_token, "One Person")
    e2 = await _employee(client, admin_token, "Two Person")
    r = await client.patch(
        f"/api/employees/{e2['id']}",
        headers=auth(admin_token),
        json={"employee_number": e1["employee_number"]},
    )
    assert r.status_code == 409


async def _employee(client, admin_token, name):
    r = await client.get("/api/employees", headers=auth(admin_token))
    return next(e for e in r.json() if e["full_name"] == name)


async def test_status_lifecycle_and_resend_and_deactivate(client, admin_token):
    # invite (not yet accepted) -> pending
    r = await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={
            "email": "pending@z.com",
            "role": "employee",
            "initial_employee": {"full_name": "Pat Pending"},
        },
    )
    assert r.status_code == 201
    user_id = r.json()["user_id"]

    e = await _employee(client, admin_token, "Pat Pending")
    assert e["status"] == "pending" and e["is_active"] is False

    # resend invite returns a fresh, copyable link
    r = await client.post(f"/api/users/{user_id}/resend-invite", headers=auth(admin_token))
    assert r.status_code == 200
    link = r.json()["invite_link"]
    assert link and "token=" in link

    # accept via the resent link -> active
    token = link.split("token=")[1]
    r = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "full_name": "Pat Pending", "password": "PatPass123!"},
    )
    assert r.status_code == 200
    e = await _employee(client, admin_token, "Pat Pending")
    assert e["status"] == "active" and e["is_active"] is True

    # deactivate -> inactive, and login is blocked
    r = await client.patch(
        f"/api/users/{user_id}", headers=auth(admin_token), json={"is_active": False}
    )
    assert r.status_code == 200
    e = await _employee(client, admin_token, "Pat Pending")
    assert e["status"] == "inactive"
    r = await client.post(
        "/api/auth/login", json={"email": "pending@z.com", "password": "PatPass123!"}
    )
    assert r.status_code == 401

    # reactivate -> active again
    r = await client.patch(
        f"/api/users/{user_id}", headers=auth(admin_token), json={"is_active": True}
    )
    assert r.status_code == 200
    e = await _employee(client, admin_token, "Pat Pending")
    assert e["status"] == "active"


async def test_cannot_resend_after_accept(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="done@z.com", role="employee", full_name="Al Ready"
    )
    e = await _employee(client, admin_token, "Al Ready")
    r = await client.post(
        f"/api/users/{e['user_id']}/resend-invite", headers=auth(admin_token)
    )
    assert r.status_code == 400


async def test_update_full_employee_record(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="rich@z.com", role="employee", full_name="Rich Record"
    )
    eid = await employee_id_by_name(client, admin_token, "Rich Record")

    payload = {
        "date_of_birth": "1990-05-14",
        "gender": "female",
        "marital_status": "married",
        "nationality": "Nigerian",
        "personal_email": "rich.personal@example.com",
        "phone": "+2348012345678",
        "address": "12 Clinic Road",
        "city": "Lagos",
        "country": "Nigeria",
        "employee_number": "ZC-0042",
        "job_title": "Staff Nurse",
        "team": "Clinical Ops",
        "employment_type": "full_time",
        "work_location": "Lagos HQ",
        "hire_date": "2024-01-08",
        "emergency_contact_name": "Ada Record",
        "emergency_contact_phone": "+2348098765432",
        "emergency_contact_relationship": "Sister",
    }
    r = await client.patch(f"/api/employees/{eid}", headers=auth(admin_token), json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    for k, v in payload.items():
        assert body[k] == v, f"{k}: {body[k]} != {v}"

    # persisted on read-back
    r = await client.get(f"/api/employees/{eid}", headers=auth(admin_token))
    assert r.json()["employee_number"] == "ZC-0042"
    assert r.json()["gender"] == "female"


async def test_invalid_enum_field_rejected(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="bad@z.com", role="employee", full_name="Bad Enum"
    )
    eid = await employee_id_by_name(client, admin_token, "Bad Enum")
    r = await client.patch(
        f"/api/employees/{eid}", headers=auth(admin_token), json={"gender": "unknown"}
    )
    assert r.status_code == 422


async def test_admin_cannot_deactivate_self(client, admin_token):
    me = (await client.get("/api/users/me", headers=auth(admin_token))).json()
    r = await client.patch(
        f"/api/users/{me['user']['id']}", headers=auth(admin_token), json={"is_active": False}
    )
    assert r.status_code == 400


async def test_hr_sees_all_employee_visibility(client, admin_token):
    mgr_token = await invite_and_accept(
        client, admin_token, email="mgr@z.com", role="manager", full_name="Manny Mgr",
        team="Ops",
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Manny Mgr")
    emp_token = await invite_and_accept(
        client, admin_token, email="emp@z.com", role="employee", full_name="Ella Emp",
        team="Ops", manager_id=mgr_id,
    )

    # HR sees everyone (admin + manager + employee = 3)
    r = await client.get("/api/employees", headers=auth(admin_token))
    assert len(r.json()) == 3

    # employee sees only self
    r = await client.get("/api/employees", headers=auth(emp_token))
    names = [e["full_name"] for e in r.json()]
    assert names == ["Ella Emp"]

    # manager sees self + report
    r = await client.get("/api/employees", headers=auth(mgr_token))
    names = sorted(e["full_name"] for e in r.json())
    assert names == ["Ella Emp", "Manny Mgr"]


async def test_employee_cannot_view_others(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="a@z.com", role="employee", full_name="Alpha"
    )
    emp_token = await invite_and_accept(
        client, admin_token, email="b@z.com", role="employee", full_name="Beta"
    )
    alpha_id = await employee_id_by_name(client, admin_token, "Alpha")
    r = await client.get(f"/api/employees/{alpha_id}", headers=auth(emp_token))
    assert r.status_code == 403


async def test_only_hr_can_edit_employee(client, admin_token):
    emp_token = await invite_and_accept(
        client, admin_token, email="c@z.com", role="employee", full_name="Gamma"
    )
    gamma_id = await employee_id_by_name(client, admin_token, "Gamma")

    r = await client.patch(
        f"/api/employees/{gamma_id}", headers=auth(emp_token), json={"team": "Hacked"}
    )
    assert r.status_code == 403

    r = await client.patch(
        f"/api/employees/{gamma_id}", headers=auth(admin_token), json={"team": "Clinical"}
    )
    assert r.status_code == 200
    assert r.json()["team"] == "Clinical"
