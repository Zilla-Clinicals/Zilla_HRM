from tests.conftest import auth
from tests.helpers import employee_id_by_name, invite_and_accept

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 128


async def test_photo_upload_serve_and_delete(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="pic@z.com", role="employee", full_name="Pic Person"
    )
    eid = await employee_id_by_name(client, admin_token, "Pic Person")

    # no photo yet
    r = await client.get(f"/api/employees/{eid}/photo", headers=auth(admin_token))
    assert r.status_code == 404

    # upload
    r = await client.post(
        f"/api/employees/{eid}/photo",
        headers=auth(admin_token),
        files={"file": ("me.png", PNG, "image/png")},
    )
    assert r.status_code == 201, r.text

    # served with the right content type
    r = await client.get(f"/api/employees/{eid}/photo", headers=auth(admin_token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == PNG

    # employee list reflects has_photo
    r = await client.get("/api/employees", headers=auth(admin_token))
    pic = next(e for e in r.json() if e["id"] == eid)
    assert pic["has_photo"] is True

    # delete
    r = await client.delete(f"/api/employees/{eid}/photo", headers=auth(admin_token))
    assert r.status_code == 204
    r = await client.get(f"/api/employees/{eid}/photo", headers=auth(admin_token))
    assert r.status_code == 404


async def test_photo_rejects_bad_type(client, admin_token):
    await invite_and_accept(
        client, admin_token, email="p2@z.com", role="employee", full_name="P Two"
    )
    eid = await employee_id_by_name(client, admin_token, "P Two")
    r = await client.post(
        f"/api/employees/{eid}/photo",
        headers=auth(admin_token),
        files={"file": ("bad.pdf", PDF, "application/pdf")},
    )
    assert r.status_code == 415


async def test_document_vault_lifecycle(client, admin_token):
    emp_token = await invite_and_accept(
        client, admin_token, email="doc@z.com", role="employee", full_name="Doc Owner"
    )
    eid = await employee_id_by_name(client, admin_token, "Doc Owner")

    # HR uploads an offer letter
    r = await client.post(
        f"/api/employees/{eid}/documents",
        headers=auth(admin_token),
        data={"kind": "offer_letter", "title": "Offer Letter 2024"},
        files={"file": ("offer.pdf", PDF, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]

    # listed for HR and for the employee themselves
    r = await client.get(f"/api/employees/{eid}/documents", headers=auth(admin_token))
    assert len(r.json()) == 1 and r.json()[0]["kind"] == "offer_letter"
    r = await client.get(f"/api/employees/{eid}/documents", headers=auth(emp_token))
    assert len(r.json()) == 1

    # download returns the bytes as an attachment
    r = await client.get(
        f"/api/employees/{eid}/documents/{doc_id}", headers=auth(admin_token)
    )
    assert r.status_code == 200
    assert r.content == PDF
    assert "attachment" in r.headers.get("content-disposition", "")

    # delete
    r = await client.delete(
        f"/api/employees/{eid}/documents/{doc_id}", headers=auth(admin_token)
    )
    assert r.status_code == 204
    r = await client.get(f"/api/employees/{eid}/documents", headers=auth(admin_token))
    assert r.json() == []


async def test_document_permissions(client, admin_token):
    # owner + an unrelated employee
    await invite_and_accept(
        client, admin_token, email="owner@z.com", role="employee", full_name="The Owner"
    )
    other = await invite_and_accept(
        client, admin_token, email="other@z.com", role="employee", full_name="The Other"
    )
    eid = await employee_id_by_name(client, admin_token, "The Owner")
    await client.post(
        f"/api/employees/{eid}/documents",
        headers=auth(admin_token),
        data={"kind": "degree", "title": "BSc"},
        files={"file": ("d.pdf", PDF, "application/pdf")},
    )

    # a different employee cannot list or download the owner's documents
    r = await client.get(f"/api/employees/{eid}/documents", headers=auth(other))
    assert r.status_code == 403

    # a plain employee cannot upload documents
    r = await client.post(
        f"/api/employees/{eid}/documents",
        headers=auth(other),
        data={"kind": "other", "title": "x"},
        files={"file": ("x.pdf", PDF, "application/pdf")},
    )
    assert r.status_code == 403
