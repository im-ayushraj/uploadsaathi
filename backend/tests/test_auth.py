"""Auth tests run against a throwaway SQLite file with a fresh schema."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = (
    "sqlite+pysqlite:///" + tempfile.mkdtemp(prefix="us_test_").replace("\\", "/") + "/test.db"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.db.models import User  # noqa: E402,F401  (registers the table)
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ACCOUNT = {
    "full_name": "Demo Applicant",
    "email": "demo.applicant@example.com",
    "mobile": "9876543210",
    "password": "DemoPass123",
}


@pytest.fixture(scope="module")
def token() -> str:
    r = client.post("/api/v1/auth/signup", json=ACCOUNT)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == ACCOUNT["email"]
    assert "password" not in body["user"]
    return body["access_token"]


def test_signup_rejects_duplicate(token: str):
    r = client.post("/api/v1/auth/signup", json=ACCOUNT)
    assert r.status_code == 409


def test_signup_rejects_bad_mobile():
    bad = {**ACCOUNT, "email": "x@example.com", "mobile": "12345"}
    assert client.post("/api/v1/auth/signup", json=bad).status_code == 422


def test_signup_rejects_short_password():
    bad = {**ACCOUNT, "email": "y@example.com", "mobile": "9000000001", "password": "short"}
    assert client.post("/api/v1/auth/signup", json=bad).status_code == 422


@pytest.mark.parametrize("identifier", [ACCOUNT["email"], ACCOUNT["mobile"], "+91 98765 43210"])
def test_login_with_email_or_mobile(token: str, identifier: str):
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": ACCOUNT["password"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password(token: str):
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": ACCOUNT["email"], "password": "WrongPass123"},
    )
    assert r.status_code == 401
    assert "email/mobile or password" in r.json()["detail"]


def test_me_requires_token():
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_me_with_token(token: str):
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["mobile"] == ACCOUNT["mobile"]


def test_logout(token: str):
    r = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
