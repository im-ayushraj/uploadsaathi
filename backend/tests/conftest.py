"""Shared test setup: an isolated SQLite database created before the app is imported."""

import os
import tempfile

_db_dir = tempfile.mkdtemp(prefix="uploadsaathi_test_").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_dir}/test.db"
os.environ["JWT_SECRET"] = "test-secret-" + "0" * 32

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.models import Enrolment, User  # noqa: E402,F401  (register tables)
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """A fresh synthetic account per test, so tests never share state."""
    import uuid

    suffix = uuid.uuid4().hex[:8]
    mobile = "9" + str(int(uuid.uuid4().int % 10**9)).zfill(9)
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Demo User",
            "email": f"demo.{suffix}@example.com",
            "mobile": mobile,
            "password": "DemoPass123",
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
