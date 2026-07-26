from app.models.role import RoleEnum


async def test_stats_reserved_to_program_manager(client, register_and_login):
    _, company = await register_and_login("company", RoleEnum.company)
    _, pm = await register_and_login("pmgr", RoleEnum.program_manager)

    response = await client.get("/stats", headers=company)
    assert response.status_code == 403

    response = await client.get("/stats", headers=pm)
    assert response.status_code == 200
    assert "offers_by_status" in response.json()
    assert "applications_by_status" in response.json()
