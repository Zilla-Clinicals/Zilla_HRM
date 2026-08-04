import pytest

from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept


async def _login_worker(client, admin_token):
    """Log in Wale Worker, created by the cycle_setup fixture."""
    r = await client.post(
        "/api/auth/login", json={"email": "worker@z.com", "password": "MemberPass1!"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
async def cycle_setup(client, admin_token):
    """Manager + report, a draft cycle, assigned. Returns ids and tokens."""
    mgr_token = await invite_and_accept(
        client, admin_token, email="boss@z.com", role="manager", full_name="Bola Boss",
        team="Clinical Ops",
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Bola Boss")
    await invite_and_accept(
        client, admin_token, email="worker@z.com", role="employee", full_name="Wale Worker",
        team="Clinical Ops", manager_id=mgr_id,
    )

    r = await client.post(
        "/api/cycles",
        headers=auth(admin_token),
        json={
            "year": 2026, "type": "mid_year",
            "opens_at": "2026-06-01T00:00:00Z", "closes_at": "2026-07-31T23:59:59Z",
        },
    )
    assert r.status_code == 201, r.text
    cycle_id = r.json()["id"]

    r = await client.post(
        f"/api/cycles/{cycle_id}/assign",
        headers=auth(admin_token),
        json={"skip_without_manager": True},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1  # only the worker has a manager
    return {"cycle_id": cycle_id, "mgr_token": mgr_token, "admin_token": admin_token}


async def test_cannot_open_without_assignments(client, admin_token):
    r = await client.post(
        "/api/cycles",
        headers=auth(admin_token),
        json={
            "year": 2027, "type": "end_year",
            "opens_at": "2027-12-01T00:00:00Z", "closes_at": "2028-01-31T00:00:00Z",
        },
    )
    cycle_id = r.json()["id"]
    r = await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))
    assert r.status_code == 409


async def test_subject_cannot_see_draft_reviewer_scores(client, cycle_setup):
    """Regression (F2): the subject must not read the reviewer's scores/summary
    until the review is submitted."""
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    mgr_token = cycle_setup["mgr_token"]

    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))
    assignment_id = (await client.get("/api/reviews/mine", headers=auth(mgr_token))).json()[0]["id"]
    kpis = (await client.get("/api/kpis", headers=auth(mgr_token))).json()

    # manager drafts a reviewer score (assignment now in_progress, NOT submitted)
    await client.put(
        f"/api/reviews/{assignment_id}/scores/{kpis[0]['id']}",
        headers=auth(mgr_token),
        json={"status": "partial", "comment": "confidential draft note"},
    )

    worker = await _login_worker(client, admin_token)
    # subject fetches the same assignment — reviewer scores must be hidden
    r = await client.get(f"/api/reviews/{assignment_id}", headers=auth(worker))
    assert r.status_code == 200
    assert r.json()["scores"] == []
    assert r.json()["summary_comment"] is None

    # the reviewer themselves still sees their own draft
    r = await client.get(f"/api/reviews/{assignment_id}", headers=auth(mgr_token))
    assert any(s["comment"] == "confidential draft note" for s in r.json()["scores"])

    # complete the flow, then the subject may see the finalized review
    self_aid = (await client.get("/api/self-assessments", headers=auth(worker))).json()[0]["id"]
    for k in kpis:
        await client.put(
            f"/api/self-assessments/{self_aid}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "met", "comment": "self view"},
        )
    await client.post(f"/api/self-assessments/{self_aid}/submit", headers=auth(worker), json={})
    for k in kpis:
        await client.put(
            f"/api/reviews/{assignment_id}/scores/{k['id']}",
            headers=auth(mgr_token),
            json={"status": "met", "comment": "final"},
        )
    await client.post(
        f"/api/reviews/{assignment_id}/submit",
        headers=auth(mgr_token),
        json={"summary_comment": "Well done."},
    )

    r = await client.get(f"/api/reviews/{assignment_id}", headers=auth(worker))
    assert len(r.json()["scores"]) == len(kpis)
    assert r.json()["summary_comment"] == "Well done."


async def test_full_review_flow(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    mgr_token = cycle_setup["mgr_token"]

    # reviewer can't see assignments until cycle is open
    r = await client.get("/api/reviews/mine", headers=auth(mgr_token))
    assert r.json() == []

    # open the cycle
    r = await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))
    assert r.status_code == 200
    assert r.json()["status"] == "open"

    r = await client.get("/api/reviews/mine", headers=auth(mgr_token))
    mine = r.json()
    assert len(mine) == 1
    assignment_id = mine[0]["id"]
    assert mine[0]["subject_name"] == "Wale Worker"

    # cannot submit before every KPI has a status + comment
    kpis = (await client.get("/api/kpis", headers=auth(mgr_token))).json()
    r = await client.post(
        f"/api/reviews/{assignment_id}/submit", headers=auth(mgr_token), json={}
    )
    assert r.status_code == 400

    # score every KPI Met with a comment
    for k in kpis:
        r = await client.put(
            f"/api/reviews/{assignment_id}/scores/{k['id']}",
            headers=auth(mgr_token),
            json={"status": "met", "comment": "exceeded target"},
        )
        assert r.status_code == 200, r.text

    # upsert (same kpi again) should update, not duplicate
    r = await client.put(
        f"/api/reviews/{assignment_id}/scores/{kpis[0]['id']}",
        headers=auth(mgr_token),
        json={"status": "partial", "comment": "partly met"},
    )
    assert r.status_code == 200

    # self-first gate: manager can't submit until the employee submits their self-assessment
    r = await client.post(
        f"/api/reviews/{assignment_id}/submit",
        headers=auth(mgr_token),
        json={"summary_comment": "Solid."},
    )
    assert r.status_code == 409

    worker = await _login_worker(client, admin_token)
    self_aid = (
        await client.get("/api/self-assessments", headers=auth(worker))
    ).json()[0]["id"]
    for k in kpis:
        await client.put(
            f"/api/self-assessments/{self_aid}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "met", "comment": "self view"},
        )
    await client.post(f"/api/self-assessments/{self_aid}/submit", headers=auth(worker), json={})

    # now the manager can submit
    r = await client.post(
        f"/api/reviews/{assignment_id}/submit",
        headers=auth(mgr_token),
        json={"summary_comment": "Solid."},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"

    # editing after submit is blocked
    r = await client.put(
        f"/api/reviews/{assignment_id}/scores/{kpis[0]['id']}",
        headers=auth(mgr_token),
        json={"status": "met", "comment": "x"},
    )
    assert r.status_code == 409

    # dashboard reflects completion (points out of 100)
    r = await client.get(f"/api/dashboard/cycle/{cycle_id}", headers=auth(admin_token))
    d = r.json()
    assert d["completion_rate"] == 1.0
    assert d["submitted_assignments"] == 1
    assert d["average_score"] is not None
    # 19 Met + 1 Partial of a 100-point scale
    assert 90 < d["average_score"] < 100
    assert len(d["category_rollup"]) == 5

    # close cycle → read-only
    r = await client.post(f"/api/cycles/{cycle_id}/close", headers=auth(admin_token))
    assert r.json()["status"] == "closed"


async def test_reviewer_cannot_touch_others_assignment(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))

    # a random employee with no assignment
    outsider = await invite_and_accept(
        client, admin_token, email="out@z.com", role="employee", full_name="Out Sider"
    )
    mine = (await client.get("/api/reviews/mine", headers=auth(cycle_setup["mgr_token"]))).json()
    assignment_id = mine[0]["id"]

    kpis = (await client.get("/api/kpis", headers=auth(admin_token))).json()
    r = await client.put(
        f"/api/reviews/{assignment_id}/scores/{kpis[0]['id']}",
        headers=auth(outsider),
        json={"status": "met", "comment": "x"},
    )
    assert r.status_code == 403


async def test_list_and_reassign_reviewer(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]

    # HR can list assignments with names
    r = await client.get(
        f"/api/cycles/{cycle_id}/assignments", headers=auth(admin_token)
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    a = rows[0]
    assert a["subject_name"] == "Wale Worker"
    assert a["reviewer_name"] == "Bola Boss"
    assignment_id = a["id"]

    # reassign to the HR admin's own employee record
    hr_emp_id = await employee_id_by_name(client, admin_token, "HR Admin")
    r = await client.patch(
        f"/api/cycles/{cycle_id}/assignments/{assignment_id}",
        headers=auth(admin_token),
        json={"reviewer_employee_id": hr_emp_id},
    )
    assert r.status_code == 200
    assert r.json()["reviewer_name"] == "HR Admin"

    # cannot make someone review themselves
    subject_id = a["subject_employee_id"]
    r = await client.patch(
        f"/api/cycles/{cycle_id}/assignments/{assignment_id}",
        headers=auth(admin_token),
        json={"reviewer_employee_id": subject_id},
    )
    assert r.status_code == 400


async def test_cannot_reassign_after_open(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    rows = (
        await client.get(f"/api/cycles/{cycle_id}/assignments", headers=auth(admin_token))
    ).json()
    assignment_id = rows[0]["id"]
    hr_emp_id = await employee_id_by_name(client, admin_token, "HR Admin")

    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))
    r = await client.patch(
        f"/api/cycles/{cycle_id}/assignments/{assignment_id}",
        headers=auth(admin_token),
        json={"reviewer_employee_id": hr_emp_id},
    )
    assert r.status_code == 409


async def test_self_assessment_flow(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]

    # log the subject (Wale Worker) in
    worker = await _login_worker(client, admin_token)

    # nothing to self-assess until the cycle opens
    r = await client.get("/api/self-assessments", headers=auth(worker))
    assert r.json() == []

    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))

    r = await client.get("/api/self-assessments", headers=auth(worker))
    mine = r.json()
    assert len(mine) == 1
    assert mine[0]["self_status"] == "not_started"
    assignment_id = mine[0]["id"]

    kpis = (await client.get("/api/kpis", headers=auth(worker))).json()

    # can't submit a partial self-assessment
    for k in kpis[:3]:
        await client.put(
            f"/api/self-assessments/{assignment_id}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "partial", "comment": "self view"},
        )
    r = await client.post(
        f"/api/self-assessments/{assignment_id}/submit", headers=auth(worker), json={}
    )
    assert r.status_code == 400

    # score every KPI, then submit
    for k in kpis:
        r = await client.put(
            f"/api/self-assessments/{assignment_id}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "partial", "comment": "self view"},
        )
        assert r.status_code == 200, r.text

    r = await client.post(
        f"/api/self-assessments/{assignment_id}/submit",
        headers=auth(worker),
        json={"summary_comment": "I did okay."},
    )
    assert r.status_code == 200
    assert r.json()["self_status"] == "submitted"

    # cannot edit self scores after submitting
    r = await client.put(
        f"/api/self-assessments/{assignment_id}/scores/{kpis[0]['id']}",
        headers=auth(worker),
        json={"status": "met", "comment": "x"},
    )
    assert r.status_code == 409


async def test_reviewer_sees_self_assessment(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    mgr_token = cycle_setup["mgr_token"]
    worker = await _login_worker(client, admin_token)

    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))

    assignment_id = (
        await client.get("/api/self-assessments", headers=auth(worker))
    ).json()[0]["id"]
    kpis = (await client.get("/api/kpis", headers=auth(worker))).json()
    for k in kpis:
        await client.put(
            f"/api/self-assessments/{assignment_id}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "partial", "comment": "honest self view"},
        )
    await client.post(
        f"/api/self-assessments/{assignment_id}/submit",
        headers=auth(worker),
        json={"summary_comment": "self summary"},
    )

    # reviewer sees the self scores alongside their own view
    r = await client.get(f"/api/reviews/{assignment_id}", headers=auth(mgr_token))
    assert r.status_code == 200
    body = r.json()
    assert body["self_comment"] == "self summary"
    assert len(body["self_scores"]) == len(kpis)
    assert body["scores"] == []  # reviewer hasn't scored yet


async def test_self_scores_excluded_from_weighted_total(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    mgr_token = cycle_setup["mgr_token"]
    worker = await _login_worker(client, admin_token)
    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))

    assignment_id = (
        await client.get("/api/reviews/mine", headers=auth(mgr_token))
    ).json()[0]["id"]
    kpis = (await client.get("/api/kpis", headers=auth(mgr_token))).json()

    # self marks everything Not Met, reviewer marks everything Met
    self_aid = (await client.get("/api/self-assessments", headers=auth(worker))).json()[0]["id"]
    for k in kpis:
        await client.put(
            f"/api/self-assessments/{self_aid}/scores/{k['id']}",
            headers=auth(worker),
            json={"status": "not_met", "comment": "self"},
        )
        await client.put(
            f"/api/reviews/{assignment_id}/scores/{k['id']}",
            headers=auth(mgr_token),
            json={"status": "met", "comment": "reviewer"},
        )
    # employee submits self-assessment (required before the manager can submit)
    await client.post(f"/api/self-assessments/{self_aid}/submit", headers=auth(worker), json={})
    await client.post(
        f"/api/reviews/{assignment_id}/submit", headers=auth(mgr_token), json={}
    )

    # all Met from the reviewer -> full 100 points; self Not Met is excluded
    d = (
        await client.get(f"/api/dashboard/cycle/{cycle_id}", headers=auth(admin_token))
    ).json()
    assert d["average_score"] == 100.0


async def test_admin_overrides_self_first_gate(client, cycle_setup):
    cycle_id = cycle_setup["cycle_id"]
    admin_token = cycle_setup["admin_token"]
    mgr_token = cycle_setup["mgr_token"]
    await client.post(f"/api/cycles/{cycle_id}/open", headers=auth(admin_token))
    aid = (await client.get("/api/reviews/mine", headers=auth(mgr_token))).json()[0]["id"]
    kpis = (await client.get("/api/kpis", headers=auth(admin_token))).json()
    for k in kpis:
        await client.put(
            f"/api/reviews/{aid}/scores/{k['id']}",
            headers=auth(admin_token),
            json={"status": "met", "comment": "x"},
        )
    # employee never self-assessed, but admin/HR can override the self-first gate
    r = await client.post(f"/api/reviews/{aid}/submit", headers=auth(admin_token), json={})
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"


async def test_duplicate_cycle_conflicts(client, admin_token):
    body = {
        "year": 2030, "type": "mid_year",
        "opens_at": "2030-06-01T00:00:00Z", "closes_at": "2030-07-31T00:00:00Z",
    }
    r1 = await client.post("/api/cycles", headers=auth(admin_token), json=body)
    assert r1.status_code == 201
    r2 = await client.post("/api/cycles", headers=auth(admin_token), json=body)
    assert r2.status_code == 409
