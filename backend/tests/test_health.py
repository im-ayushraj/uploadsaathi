from fastapi.testclient import TestClient


def test_health_ok(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert "UIDAI" in body["prototype_notice"]
