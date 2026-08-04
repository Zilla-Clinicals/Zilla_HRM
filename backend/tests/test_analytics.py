import pytest

from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept


@pytest.fixture
async def scored_cycle(client, admin_token):
    """An open cycle where the reviewer has scored every KPI Met."""
    mgr = await invite_and_accept(
        client, admin_token, email="boss@z.com", role="manager", full_name="Bola Boss",
        team="Clinical Ops",
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Bola Boss")
    await invite_and_accept(
        client, admin_token, email="worker@z.com", role="employee", full_name="Wale Worker",
        team="Clinical Ops", manager_id=mgr_id,
    )
    worker = (
        await client.post(
            "/api/auth/login", json={"email": "worker@z.com", "password": "MemberPass1!"}
        )
    ).json()["access_token"]

    cid = (
        await client.post(
            "/api/cycles",
            headers=auth(admin_token),
            json={
                "year": 2026, "type": "mid_year",
                "opens_at": "2026-06-01T00:00:00Z", "closes_at": "2026-07-31T00:00:00Z",
            },
        )
    ).json()["id"]
    await client.post(f"/api/cycles/{cid}/assign", headers=auth(admin_token), json={})
    await client.post(f"/api/cycles/{cid}/open", headers=auth(admin_token))

    aid = (await client.get("/api/reviews/mine", headers=auth(mgr))).json()[0]["id"]
    kpis = (await client.get("/api/kpis", headers=auth(mgr))).json()
    for k in kpis:
        await client.put(
            f"/api/reviews/{aid}/scores/{k['id']}",
            headers=auth(mgr),
            json={"status": "met", "comment": "great"},
        )
    # a partial self-assessment for calibration
    self_aid = (
        await client.get("/api/self-assessments", headers=auth(worker))
    ).json()[0]["id"]
    for k in kpis:
        await client.put(
            f"/api/self-assessments/{self_aid}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "partial", "comment": "ok"},
        )
    return {"cid": cid, "admin_token": admin_token}


async def test_summary(client, scored_cycle):
    admin = scored_cycle["admin_token"]
    r = await client.get("/api/analytics/summary", headers=auth(admin))
    assert r.status_code == 200
    d = r.json()
    assert len(d["cycles"]) == 1
    assert d["cycles"][0]["avg_score"] == 100.0
    assert d["latest_cycle_id"] == scored_cycle["cid"]
    assert len(d["category_series"]) == 5
    assert any(s["name"] == "Clinical Ops" for s in d["team_series"])


async def test_cycle_analytics_and_calibration(client, scored_cycle):
    admin = scored_cycle["admin_token"]
    cid = scored_cycle["cid"]
    r = await client.get(f"/api/analytics/cycle/{cid}", headers=auth(admin))
    assert r.status_code == 200
    d = r.json()
    assert len(d["kpis"]) == 20
    assert all(k["pct"] == 1.0 for k in d["kpis"])  # all Met
    assert len(d["calibration"]) == 5
    assert d["calibration_pairs"] == 1
    # reviewer (Met=100%) rated higher than the self (Partial=50%)
    assert d["calibration_overall_reviewer"] > d["calibration_overall_self"]


async def test_employee_trajectories(client, scored_cycle):
    admin = scored_cycle["admin_token"]
    r = await client.get("/api/analytics/employees", headers=auth(admin))
    assert r.status_code == 200
    d = r.json()
    assert len(d["cycles"]) == 1
    worker = next(e for e in d["employees"] if e["name"] == "Wale Worker")
    assert worker["latest"] == 100.0


async def test_analytics_is_hr_only(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="e@z.com", role="employee", full_name="Emp"
    )
    r = await client.get("/api/analytics/summary", headers=auth(emp))
    assert r.status_code == 403
