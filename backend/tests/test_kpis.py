from tests.conftest import auth
from tests.helpers import invite_and_accept


async def test_seed_kpis_present(client, admin_token):
    r = await client.get("/api/kpis", headers=auth(admin_token))
    assert r.status_code == 200
    kpis = r.json()
    assert len(kpis) == 20  # the workbook's 20-KPI catalog
    # each KPI carries its derived category weight + points
    assert all(k["category_weight"] is not None and k["points"] > 0 for k in kpis)


async def test_categories_weighted_and_sum_to_100(client, admin_token):
    r = await client.get("/api/kpis/categories", headers=auth(admin_token))
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 5
    assert round(sum(float(c["weight"]) for c in cats), 2) == 100.0
    # Performance & Delivery is 35 across 4 KPIs -> 8.75 each
    pd = next(c for c in cats if c["name"] == "Performance & Delivery")
    assert pd["kpi_count"] == 4
    assert pd["points_per_kpi"] == 8.75


async def test_create_and_soft_delete_kpi(client, admin_token):
    r = await client.post(
        "/api/kpis",
        headers=auth(admin_token),
        json={"name": "Punctuality", "category": "Ownership & Initiative"},
    )
    assert r.status_code == 201, r.text
    kpi_id = r.json()["id"]

    r = await client.delete(f"/api/kpis/{kpi_id}", headers=auth(admin_token))
    assert r.status_code == 204

    # soft-deleted → not in default list, present when including inactive
    r = await client.get("/api/kpis", headers=auth(admin_token))
    assert kpi_id not in [k["id"] for k in r.json()]
    r = await client.get("/api/kpis?include_inactive=true", headers=auth(admin_token))
    assert kpi_id in [k["id"] for k in r.json()]


async def test_create_kpi_rejects_unknown_category(client, admin_token):
    r = await client.post(
        "/api/kpis",
        headers=auth(admin_token),
        json={"name": "Bad", "category": "Nonexistent Category"},
    )
    assert r.status_code == 400


async def test_non_hr_cannot_create_kpi(client, admin_token):
    emp_token = await invite_and_accept(
        client, admin_token, email="e@z.com", role="employee", full_name="Emp"
    )
    r = await client.post(
        "/api/kpis",
        headers=auth(emp_token),
        json={"name": "X", "category": "Y"},
    )
    assert r.status_code == 403
