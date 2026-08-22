"""Enrolment journey API tests (portal config + draft lifecycle + ownership)."""

from fastapi.testclient import TestClient

from .synthetic import make_image

ADULT_PERSONAL = {
    "full_name": "Anita Sharma",
    "date_of_birth": "1994-06-12",
    "gender": "female",
    "email": "anita.demo@example.com",
    "mobile": "9876500011",
}

ADDRESS = {
    "address_line1": "12 Gandhi Marg",
    "village_town_city": "Patna",
    "district": "Patna",
    "state": "Bihar",
    "pincode": "800001",
}


def _create(client: TestClient, headers: dict[str, str], applicant_type: str = "adult") -> dict:
    r = client.post("/api/v1/enrolments", json={"applicant_type": applicant_type}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _accept_all_documents(client: TestClient, headers: dict[str, str], eid: int) -> None:
    """Upload and accept every document the portal configuration asks for."""
    detail = client.get(f"/api/v1/enrolments/{eid}", headers=headers).json()
    for slot in detail["progress"]["documents_required"]:
        r = client.post(
            f"/api/v1/enrolments/{eid}/documents",
            data={"document_type": slot},
            files={"file": ("proof.jpg", make_image(1400, 1000), "image/jpeg")},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["ready"] is True, r.json()["message"]
        document_id = r.json()["document"]["id"]
        accepted = client.post(
            f"/api/v1/enrolments/{eid}/documents/{document_id}/accept", headers=headers
        )
        assert accepted.status_code == 200, accepted.text


def test_portal_config_endpoint(client: TestClient):
    r = client.get("/api/v1/portals/aadhaar")
    assert r.status_code == 200
    body = r.json()
    assert body["portal_id"] == "aadhaar"
    assert any(a["id"] == "adult" for a in body["applicant_types"])
    assert client.get("/api/v1/portals/unknown_portal").status_code == 404


def test_documents_endpoint_is_config_driven(client: TestClient):
    r = client.get("/api/v1/portals/aadhaar/documents", params={"applicant_type": "adult"})
    assert r.status_code == 200
    docs = r.json()
    assert [d["id"] for d in docs] == ["identity_proof", "address_proof", "dob_proof"]
    assert docs[0]["requirement"]["max_bytes"] == 2097152
    bad = client.get("/api/v1/portals/aadhaar/documents", params={"applicant_type": "nope"})
    assert bad.status_code == 404


def test_enrolments_require_auth(client: TestClient):
    assert client.get("/api/v1/enrolments").status_code == 401
    assert client.post("/api/v1/enrolments", json={"applicant_type": "adult"}).status_code == 401


def test_create_rejects_unknown_applicant_type(client: TestClient, auth_headers):
    r = client.post("/api/v1/enrolments", json={"applicant_type": "alien"}, headers=auth_headers)
    assert r.status_code == 400


def test_full_draft_to_prepared_flow(client: TestClient, auth_headers):
    created = _create(client, auth_headers)
    eid = created["id"]
    assert created["status"] == "draft"
    assert created["progress"]["can_prepare"] is False

    # Cannot prepare before the required steps are filled in.
    early = client.post(f"/api/v1/enrolments/{eid}/prepare", headers=auth_headers)
    assert early.status_code == 400
    assert "personal details" in early.json()["detail"]

    r = client.patch(
        f"/api/v1/enrolments/{eid}", json={"personal_details": ADULT_PERSONAL}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["progress"]["personal_details"] is True

    r = client.patch(f"/api/v1/enrolments/{eid}", json={"address": ADDRESS}, headers=auth_headers)
    assert r.json()["progress"]["address"] is True
    # Documents are the last gate: details alone are not enough to prepare.
    assert r.json()["progress"]["can_prepare"] is False

    _accept_all_documents(client, auth_headers, eid)
    assert (
        client.get(f"/api/v1/enrolments/{eid}", headers=auth_headers).json()["progress"][
            "can_prepare"
        ]
        is True
    )

    r = client.post(f"/api/v1/enrolments/{eid}/prepare", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "prepared"
    assert body["reference_code"].startswith("PREP-")
    assert body["prepared_at"]

    # Prepared applications are immutable.
    locked = client.patch(
        f"/api/v1/enrolments/{eid}", json={"address": ADDRESS}, headers=auth_headers
    )
    assert locked.status_code == 409

    # Preparing again is idempotent, not an error.
    again = client.post(f"/api/v1/enrolments/{eid}/prepare", headers=auth_headers)
    assert again.status_code == 200
    assert again.json()["reference_code"] == body["reference_code"]


def test_validation_rejects_bad_pincode_and_future_dob(client: TestClient, auth_headers):
    eid = _create(client, auth_headers)["id"]
    bad_pin = client.patch(
        f"/api/v1/enrolments/{eid}",
        json={"address": {**ADDRESS, "pincode": "0123"}},
        headers=auth_headers,
    )
    assert bad_pin.status_code == 422
    bad_dob = client.patch(
        f"/api/v1/enrolments/{eid}",
        json={"personal_details": {**ADULT_PERSONAL, "date_of_birth": "2099-01-01"}},
        headers=auth_headers,
    )
    assert bad_dob.status_code == 422


def test_another_user_cannot_see_or_change_it(client: TestClient, auth_headers):
    eid = _create(client, auth_headers)["id"]

    other = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Other Person",
            "email": "other.person@example.com",
            "mobile": "9999000011",
            "password": "DemoPass123",
        },
    )
    assert other.status_code == 201
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert client.get(f"/api/v1/enrolments/{eid}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/enrolments/{eid}", json={"address": ADDRESS}, headers=other_headers
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/enrolments/{eid}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/enrolments/{eid}", headers=auth_headers).status_code == 200


def test_list_and_delete(client: TestClient, auth_headers):
    eid = _create(client, auth_headers, "minor_5_17")["id"]
    listed = client.get("/api/v1/enrolments", headers=auth_headers).json()
    assert any(e["id"] == eid for e in listed)
    assert client.delete(f"/api/v1/enrolments/{eid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/enrolments/{eid}", headers=auth_headers).status_code == 404
