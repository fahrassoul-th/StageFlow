async def test_root_and_health_endpoints(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
