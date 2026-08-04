from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept


async def _login(client, email, pw="MemberPass1!"):
    r = await client.post("/api/auth/login", json={"email": email, "password": pw})
    return r.json()["access_token"]


async def _build_survey(client, admin_token, *, anonymous=False):
    sid = (
        await client.post(
            "/api/surveys",
            headers=auth(admin_token),
            json={"title": "Engagement", "description": "How are we doing?", "anonymous": anonymous},
        )
    ).json()["id"]
    # a choice + a rating + a text question
    q_choice = (
        await client.post(
            f"/api/surveys/{sid}/questions",
            headers=auth(admin_token),
            json={"type": "single_choice", "prompt": "Pick one", "required": True,
                  "choices": ["A", "B", "C"]},
        )
    ).json()["id"]
    q_rate = (
        await client.post(
            f"/api/surveys/{sid}/questions",
            headers=auth(admin_token),
            json={"type": "rating", "prompt": "Rate us", "required": True, "scale_max": 5},
        )
    ).json()["id"]
    q_text = (
        await client.post(
            f"/api/surveys/{sid}/questions",
            headers=auth(admin_token),
            json={"type": "long_text", "prompt": "Comments"},
        )
    ).json()["id"]
    return sid, q_choice, q_rate, q_text


async def test_full_survey_flow_attributed(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="resp@z.com", role="employee", full_name="Resp Ondent"
    )
    eid = await employee_id_by_name(client, admin_token, "Resp Ondent")
    sid, q_choice, q_rate, q_text = await _build_survey(client, admin_token)

    # can't open without recipients... assign, then open
    r = await client.post(f"/api/surveys/{sid}/open", headers=auth(admin_token))
    assert r.status_code == 409
    r = await client.post(
        f"/api/surveys/{sid}/assign",
        headers=auth(admin_token),
        json={"scope": "employees", "employee_ids": [eid]},
    )
    assert r.status_code == 200 and r.json()["assigned_count"] == 1
    r = await client.post(f"/api/surveys/{sid}/open", headers=auth(admin_token))
    assert r.status_code == 200 and r.json()["status"] == "open"

    # respondent sees it assigned
    r = await client.get("/api/surveys/assigned", headers=auth(emp))
    assert len(r.json()) == 1 and r.json()[0]["completed"] is False

    # required validation
    r = await client.post(
        f"/api/surveys/{sid}/respond",
        headers=auth(emp),
        json={"answers": [{"question_id": q_text, "value": "only text"}]},
    )
    assert r.status_code == 400  # missing required choice + rating

    # submit properly
    r = await client.post(
        f"/api/surveys/{sid}/respond",
        headers=auth(emp),
        json={"answers": [
            {"question_id": q_choice, "value": "B"},
            {"question_id": q_rate, "value": 4},
            {"question_id": q_text, "value": "Great place"},
        ]},
    )
    assert r.status_code == 204

    # can't respond twice
    r = await client.post(
        f"/api/surveys/{sid}/respond",
        headers=auth(emp),
        json={"answers": [{"question_id": q_choice, "value": "A"}, {"question_id": q_rate, "value": 1}]},
    )
    assert r.status_code == 409

    # results
    r = await client.get(f"/api/surveys/{sid}/results", headers=auth(admin_token))
    d = r.json()
    assert d["assigned_count"] == 1 and d["response_count"] == 1
    choice_q = next(q for q in d["questions"] if q["question_id"] == q_choice)
    assert {c["label"]: c["count"] for c in choice_q["counts"]} == {"A": 0, "B": 1, "C": 0}
    rate_q = next(q for q in d["questions"] if q["question_id"] == q_rate)
    assert rate_q["average"] == 4.0
    text_q = next(q for q in d["questions"] if q["question_id"] == q_text)
    assert text_q["texts"] == ["Great place"]

    # assignment tracking shows completion + who
    r = await client.get(f"/api/surveys/{sid}/assignments", headers=auth(admin_token))
    assert r.json()[0]["completed"] is True and r.json()[0]["name"] == "Resp Ondent"


async def test_anonymous_survey_unlinks_responses(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="anon@z.com", role="employee", full_name="Anon User"
    )
    eid = await employee_id_by_name(client, admin_token, "Anon User")
    sid, q_choice, q_rate, _ = await _build_survey(client, admin_token, anonymous=True)
    await client.post(
        f"/api/surveys/{sid}/assign", headers=auth(admin_token),
        json={"scope": "employees", "employee_ids": [eid]},
    )
    await client.post(f"/api/surveys/{sid}/open", headers=auth(admin_token))
    await client.post(
        f"/api/surveys/{sid}/respond", headers=auth(emp),
        json={"answers": [{"question_id": q_choice, "value": "A"}, {"question_id": q_rate, "value": 3}]},
    )
    # response recorded, but not linked to the person
    from sqlalchemy import select

    from app.db import async_session_factory
    from app.models.surveys import SurveyResponse

    async with async_session_factory() as db:
        resp = (await db.scalars(select(SurveyResponse).where(SurveyResponse.survey_id == sid))).all()
    assert len(resp) == 1
    assert resp[0].respondent_employee_id is None  # anonymised

    # aggregate results still work; completion still tracked
    d = (await client.get(f"/api/surveys/{sid}/results", headers=auth(admin_token))).json()
    assert d["response_count"] == 1 and d["anonymous"] is True


async def test_manager_survey_scoped_to_team(client, admin_token):
    mgr = await invite_and_accept(
        client, admin_token, email="lead@z.com", role="manager", full_name="Team Lead"
    )
    mgr_id = await employee_id_by_name(client, admin_token, "Team Lead")
    await invite_and_accept(
        client, admin_token, email="rep@z.com", role="employee", full_name="My Report",
        manager_id=mgr_id,
    )
    rep_eid = await employee_id_by_name(client, admin_token, "My Report")
    # an outsider not on the team
    await invite_and_accept(
        client, admin_token, email="out@z.com", role="employee", full_name="Outsider"
    )
    out_eid = await employee_id_by_name(client, admin_token, "Outsider")

    sid = (
        await client.post("/api/surveys", headers=auth(mgr), json={"title": "Team pulse"})
    ).json()["id"]
    await client.post(
        f"/api/surveys/{sid}/questions", headers=auth(mgr),
        json={"type": "yes_no", "prompt": "Happy?", "required": True},
    )
    # manager assigns to their team + tries to sneak in an outsider — outsider is dropped
    r = await client.post(
        f"/api/surveys/{sid}/assign", headers=auth(mgr),
        json={"scope": "employees", "employee_ids": [rep_eid, out_eid]},
    )
    assert r.status_code == 200 and r.json()["assigned_count"] == 1  # only the report

    assignees = {a["employee_id"] for a in (await client.get(f"/api/surveys/{sid}/assignments", headers=auth(mgr))).json()}
    assert assignees == {rep_eid}


async def test_survey_permissions(client, admin_token):
    emp = await invite_and_accept(
        client, admin_token, email="e@z.com", role="employee", full_name="Plain Emp"
    )
    # employees cannot create surveys
    r = await client.post("/api/surveys", headers=auth(emp), json={"title": "x"})
    assert r.status_code == 403
    # employees cannot list the admin surveys endpoint
    assert (await client.get("/api/surveys", headers=auth(emp))).status_code == 403
