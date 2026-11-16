from tests.conftest import auth
from tests.helpers import invite_and_accept


async def _user_id(client, token):
    r = await client.get("/api/users/me", headers=auth(token))
    return r.json()["user"]["id"]


async def test_admin_reset_link_works_once_and_supersedes_old(client, admin_token):
    emp_token = await invite_and_accept(
        client, admin_token, email="rl@x.com", role="employee", full_name="Reset Me"
    )
    uid = await _user_id(client, emp_token)

    r1 = await client.post(f"/api/users/{uid}/reset-link", headers=auth(admin_token))
    assert r1.status_code == 200, r1.text
    old_token = r1.json()["reset_link"].split("token=")[1]
    r2 = await client.post(f"/api/users/{uid}/reset-link", headers=auth(admin_token))
    new_token = r2.json()["reset_link"].split("token=")[1]

    # Older link is invalidated by issuing a newer one.
    r = await client.post(
        "/api/auth/reset-password", json={"token": old_token, "new_password": "Fresh1234!"}
    )
    assert r.status_code == 400

    r = await client.post(
        "/api/auth/reset-password", json={"token": new_token, "new_password": "Fresh1234!"}
    )
    assert r.status_code == 204
    r = await client.post(
        "/api/auth/login", json={"email": "rl@x.com", "password": "Fresh1234!"}
    )
    assert r.status_code == 200

    # Single use.
    r = await client.post(
        "/api/auth/reset-password", json={"token": new_token, "new_password": "Again1234!"}
    )
    assert r.status_code == 400


async def test_reset_link_rbac(client, admin_token):
    hr_token = await invite_and_accept(
        client, admin_token, email="hr-rl@x.com", role="hr", full_name="HR Person"
    )
    emp_token = await invite_and_accept(
        client, admin_token, email="emp-rl@x.com", role="employee", full_name="Emp Person"
    )
    admin_id = await _user_id(client, admin_token)
    emp_id = await _user_id(client, emp_token)

    # Employees can't issue links.
    r = await client.post(f"/api/users/{admin_id}/reset-link", headers=auth(emp_token))
    assert r.status_code == 403
    # HR can for employees, but not for admins/executives.
    r = await client.post(f"/api/users/{emp_id}/reset-link", headers=auth(hr_token))
    assert r.status_code == 200
    r = await client.post(f"/api/users/{admin_id}/reset-link", headers=auth(hr_token))
    assert r.status_code == 403


async def test_reset_link_rejects_pending_user(client, admin_token):
    r = await client.post(
        "/api/users/invite",
        headers=auth(admin_token),
        json={"email": "pend@x.com", "role": "employee",
              "initial_employee": {"full_name": "Pending"}},
    )
    uid = r.json()["user_id"]
    r = await client.post(f"/api/users/{uid}/reset-link", headers=auth(admin_token))
    assert r.status_code == 400
