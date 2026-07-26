from app.models.role import RoleEnum


async def _publish_offer(client, company_headers, pm_headers, **fields):
    response = await client.post("/offers", json=fields, headers=company_headers)
    offer_id = response.json()["id"]
    await client.patch(f"/offers/{offer_id}/submit", headers=company_headers)
    await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "publish"}, headers=pm_headers
    )
    return offer_id


async def test_student_application_lifecycle(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    offer_id = await _publish_offer(client, company, pm, title="t", mission="m", skills="s")

    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    assert response.status_code == 201
    application_id = response.json()["id"]
    assert response.json()["status"] == "pending"

    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    assert response.status_code == 400

    response = await client.patch(
        f"/applications/{application_id}/decision",
        json={"decision": "accepted"},
        headers=pm,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    response = await client.delete(f"/applications/{application_id}", headers=student)
    assert response.status_code == 400


async def test_company_isolation_on_offer_applications(client, register_and_login):
    """Required by the subject: a company must never see another
    company's applications."""
    _, company_a = await register_and_login("companyA", RoleEnum.company)
    _, company_b = await register_and_login("companyB", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    offer_id = await _publish_offer(client, company_a, pm, title="t", mission="m", skills="s")
    await client.post(f"/offers/{offer_id}/applications", headers=student)

    response = await client.get(f"/offers/{offer_id}/applications", headers=company_b)
    assert response.status_code == 404

    response = await client.get(f"/offers/{offer_id}/applications", headers=company_a)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(f"/offers/{offer_id}/applications", headers=student)
    assert response.status_code == 403


async def test_withdraw_then_reapply_is_allowed(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    offer_id = await _publish_offer(client, company, pm, title="t", mission="m", skills="s")
    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    application_id = response.json()["id"]

    response = await client.delete(f"/applications/{application_id}", headers=student)
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"

    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    assert response.status_code == 201


async def test_cannot_withdraw_someone_elses_application(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, student_a = await register_and_login("studentA", RoleEnum.student)
    _, student_b = await register_and_login("studentB", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    offer_id = await _publish_offer(client, company, pm, title="t", mission="m", skills="s")
    response = await client.post(f"/offers/{offer_id}/applications", headers=student_a)
    application_id = response.json()["id"]

    response = await client.delete(f"/applications/{application_id}", headers=student_b)
    assert response.status_code == 404


async def test_apply_to_unpublished_or_nonexistent_offer_returns_404(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)

    response = await client.post("/offers", json={}, headers=company)
    draft_offer_id = response.json()["id"]

    response = await client.post(f"/offers/{draft_offer_id}/applications", headers=student)
    assert response.status_code == 404

    response = await client.post("/offers/999999/applications", headers=student)
    assert response.status_code == 404


async def test_list_applications_for_nonexistent_offer_returns_404(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    response = await client.get("/offers/999999/applications", headers=company)
    assert response.status_code == 404


async def test_decide_nonexistent_application_returns_404(client, register_and_login):
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)
    response = await client.patch(
        "/applications/999999/decision", json={"decision": "accepted"}, headers=pm
    )
    assert response.status_code == 404


async def test_cannot_redecide_an_already_decided_application(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    offer_id = await _publish_offer(client, company, pm, title="t", mission="m", skills="s")
    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    application_id = response.json()["id"]

    response = await client.patch(
        f"/applications/{application_id}/decision", json={"decision": "rejected"}, headers=pm
    )
    assert response.status_code == 200

    response = await client.patch(
        f"/applications/{application_id}/decision", json={"decision": "accepted"}, headers=pm
    )
    assert response.status_code == 400
