"""Auth endpoint tests. Database and TestClient come from conftest."""

import pytest
from fastapi.testclient import TestClient

ACCOUNT = {
    "full_name": "Demo Applicant",
    "email": "demo.applicant@example.com",
    "mobile": "9876543210",
    "password": "DemoPass123",
}


@pytest.fixture(scope="module")
def token(client: TestClient) -> str:
    r = client.post("/api/v1/auth/signup", json=ACCOUNT)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == ACCOUNT["email"]
    assert "password" not in body["user"]
    return body["access_token"]


def test_signup_rejects_duplicate(client: TestClient, token: str):
    r = client.post("/api/v1/auth/signup", json=ACCOUNT)
    assert r.status_code == 409


def test_signup_rejects_bad_mobile(client: TestClient):
    bad = {**ACCOUNT, "email": "x@example.com", "mobile": "12345"}
    assert client.post("/api/v1/auth/signup", json=bad).status_code == 422


def test_signup_rejects_short_password(client: TestClient):
    bad = {**ACCOUNT, "email": "y@example.com", "mobile": "9000000001", "password": "short"}
    assert client.post("/api/v1/auth/signup", json=bad).status_code == 422


@pytest.mark.parametrize("identifier", [ACCOUNT["email"], ACCOUNT["mobile"], "+91 98765 43210"])
def test_login_with_email_or_mobile(client: TestClient, token: str, identifier: str):
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": ACCOUNT["password"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, token: str):
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": ACCOUNT["email"], "password": "WrongPass123"},
    )
    assert r.status_code == 401
    assert "email/mobile or password" in r.json()["detail"]


def test_me_requires_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_me_with_token(client: TestClient, token: str):
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["mobile"] == ACCOUNT["mobile"]


def test_logout(client: TestClient, token: str):
    r = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
