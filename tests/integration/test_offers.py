from app.models.role import RoleEnum


async def test_offer_visibility_hides_drafts_as_404(client, register_and_login):
    _, company_a = await register_and_login("companyA", RoleEnum.company)
    _, company_b = await register_and_login("companyB", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)

    response = await client.post("/offers", json={}, headers=company_a)
    assert response.status_code == 201
    offer_id = response.json()["id"]
    assert response.json()["status"] == "draft"

    assert (await client.get(f"/offers/{offer_id}", headers=student)).status_code == 404
    assert (await client.get(f"/offers/{offer_id}", headers=company_b)).status_code == 404
    assert (await client.get(f"/offers/{offer_id}", headers=company_a)).status_code == 200


async def test_student_cannot_create_offer(client, register_and_login):
    _, student = await register_and_login("student", RoleEnum.student)
    response = await client.post("/offers", json={}, headers=student)
    assert response.status_code == 403


async def test_submit_transition_rules(client, register_and_login):
    _, company_a = await register_and_login("companyA", RoleEnum.company)
    _, company_b = await register_and_login("companyB", RoleEnum.company)

    response = await client.post("/offers", json={}, headers=company_a)
    offer_id = response.json()["id"]

    assert (
        await client.patch(f"/offers/{offer_id}/submit", headers=company_b)
    ).status_code == 404

    response = await client.patch(f"/offers/{offer_id}/submit", headers=company_a)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"

    assert (
        await client.patch(f"/offers/{offer_id}/submit", headers=company_a)
    ).status_code == 400


async def test_publish_requires_complete_offer(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    response = await client.post("/offers", json={}, headers=company)
    offer_id = response.json()["id"]
    await client.patch(f"/offers/{offer_id}/submit", headers=company)

    response = await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "publish"}, headers=pm
    )
    assert response.status_code == 400

    response = await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "reject"}, headers=pm
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


async def test_publish_succeeds_when_offer_is_complete(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)
    _, student = await register_and_login("student", RoleEnum.student)

    response = await client.post(
        "/offers",
        json={"title": "Data intern", "mission": "ETL", "skills": "SQL"},
        headers=company,
    )
    offer_id = response.json()["id"]
    await client.patch(f"/offers/{offer_id}/submit", headers=company)
    response = await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "publish"}, headers=pm
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    response = await client.get("/offers", headers=student)
    assert offer_id in [offer["id"] for offer in response.json()]


async def test_offer_catalog_is_role_aware(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, other_company = await register_and_login("other", RoleEnum.company)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    await client.post("/offers", json={}, headers=company)
    await client.post("/offers", json={}, headers=company)

    response = await client.get("/offers", headers=company)
    assert len(response.json()) == 2

    response = await client.get("/offers", headers=other_company)
    assert len(response.json()) == 0

    response = await client.get("/offers", headers=pm)
    assert len(response.json()) == 2


async def test_get_nonexistent_offer_returns_404(client, register_and_login):
    _, student = await register_and_login("student", RoleEnum.student)
    response = await client.get("/offers/999999", headers=student)
    assert response.status_code == 404


async def test_review_requires_submitted_status(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    response = await client.post("/offers", json={}, headers=company)
    offer_id = response.json()["id"]

    response = await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "publish"}, headers=pm
    )
    assert response.status_code == 400


async def test_review_nonexistent_offer_returns_404(client, register_and_login):
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)
    response = await client.patch(
        "/offers/999999/review", json={"decision": "publish"}, headers=pm
    )
    assert response.status_code == 404
