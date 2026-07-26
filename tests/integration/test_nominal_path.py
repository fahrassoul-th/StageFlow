from app.models.role import RoleEnum


async def test_full_nominal_path_offer_to_accepted_application(client, register_and_login):
    """End-to-end happy path required by the subject: an offer goes from
    creation to publication, a student applies, and the application is
    accepted - checking every response along the way."""
    _, company = await register_and_login("company", RoleEnum.company)
    _, student = await register_and_login("student", RoleEnum.student)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    response = await client.post(
        "/offers",
        json={"title": "Data intern", "mission": "ETL pipeline", "skills": "SQL, Python"},
        headers=company,
    )
    assert response.status_code == 201
    offer_id = response.json()["id"]

    response = await client.patch(f"/offers/{offer_id}/submit", headers=company)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"

    response = await client.patch(
        f"/offers/{offer_id}/review", json={"decision": "publish"}, headers=pm
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    response = await client.get("/offers", headers=student)
    assert offer_id in [offer["id"] for offer in response.json()]

    response = await client.post(f"/offers/{offer_id}/applications", headers=student)
    assert response.status_code == 201
    application_id = response.json()["id"]

    response = await client.get("/applications/me", headers=student)
    assert application_id in [app["id"] for app in response.json()]

    response = await client.patch(
        f"/applications/{application_id}/decision",
        json={"decision": "accepted"},
        headers=pm,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    response = await client.get("/stats", headers=pm)
    assert response.status_code == 200
    assert response.json()["offers_by_status"] == {"published": 1}
    assert response.json()["applications_by_status"] == {"accepted": 1}
