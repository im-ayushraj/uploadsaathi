"""Document upload API tests — the whole Phase 5 flow through HTTP."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings

from .synthetic import corrupt, make_image, make_oversized_jpeg, make_pdf

ADULT_SLOTS = ("identity_proof", "address_proof", "dob_proof")


def _stored_file_count() -> int:
    root = Path(settings.STORAGE_DIR)
    return len(list(root.iterdir())) if root.exists() else 0


def new_enrolment(client: TestClient, headers: dict[str, str], applicant_type: str = "adult") -> int:
    r = client.post("/api/v1/enrolments", json={"applicant_type": applicant_type}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def upload(client, headers, enrolment_id, slot, data, filename="bill.jpg", mode=None):
    form = {"document_type": slot}
    if mode:
        form["mode"] = mode
    return client.post(
        f"/api/v1/enrolments/{enrolment_id}/documents",
        data=form,
        files={"file": (filename, data, "application/octet-stream")},
        headers=headers,
    )


def fill_details(client, headers, enrolment_id):
    r = client.patch(
        f"/api/v1/enrolments/{enrolment_id}",
        json={
            "personal_details": {
                "full_name": "Demo Applicant",
                "date_of_birth": "1995-04-12",
                "gender": "female",
            },
            "address": {
                "address_line1": "12 Demo Lane",
                "village_town_city": "Patna",
                "district": "Patna",
                "state": "Bihar",
                "pincode": "800001",
            },
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text


def test_upload_optimises_and_stores_pending_document(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    data = make_oversized_jpeg()

    r = upload(client, auth_headers, enrolment_id, "address_proof", data, "electricity bill.JPG")
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["ready"] is True
    assert body["outcome"]["original_size"] == len(data)
    assert body["outcome"]["optimized_size"] <= 512_000
    assert body["outcome"]["format"] == "JPEG"
    assert body["outcome"]["readable"] is True
    assert "%" in body["message"]
    assert body["document"]["status"] == "pending"
    assert body["document"]["accepted"] is False
    # `ready` is the engine's verdict, `accepted` is the citizen's — they are not the same thing.
    assert body["document"]["ready"] is True


def test_accept_marks_document_done_and_completes_the_step(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    fill_details(client, auth_headers, enrolment_id)

    for slot in ADULT_SLOTS:
        r = upload(client, auth_headers, enrolment_id, slot, make_image(1400, 1000, fmt="JPEG"))
        assert r.status_code == 201, r.text
        document_id = r.json()["document"]["id"]
        accepted = client.post(
            f"/api/v1/enrolments/{enrolment_id}/documents/{document_id}/accept",
            headers=auth_headers,
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["accepted"] is True

    detail = client.get(f"/api/v1/enrolments/{enrolment_id}", headers=auth_headers).json()
    assert sorted(detail["progress"]["documents_required"]) == sorted(ADULT_SLOTS)
    assert detail["progress"]["documents"] is True
    assert detail["progress"]["can_prepare"] is True


def test_prepare_now_requires_all_documents(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    fill_details(client, auth_headers, enrolment_id)

    blocked = client.post(f"/api/v1/enrolments/{enrolment_id}/prepare", headers=auth_headers)
    assert blocked.status_code == 400
    assert "documents" in blocked.json()["detail"]

    for slot in ADULT_SLOTS:
        r = upload(client, auth_headers, enrolment_id, slot, make_image(1400, 1000, fmt="JPEG"))
        client.post(
            f"/api/v1/enrolments/{enrolment_id}/documents/{r.json()['document']['id']}/accept",
            headers=auth_headers,
        )

    prepared = client.post(f"/api/v1/enrolments/{enrolment_id}/prepare", headers=auth_headers)
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["reference_code"].startswith("PREP-")


def test_reupload_replaces_the_slot(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    upload(client, auth_headers, enrolment_id, "dob_proof", make_image(900, 700, fmt="JPEG"))
    files_after_first = _stored_file_count()

    second = upload(
        client, auth_headers, enrolment_id, "dob_proof", make_image(1000, 800, fmt="PNG"), "dob.png"
    )
    assert second.status_code == 201, second.text

    listed = client.get(
        f"/api/v1/enrolments/{enrolment_id}/documents", headers=auth_headers
    ).json()
    assert len(listed) == 1
    assert listed[0]["id"] == second.json()["document"]["id"]
    assert listed[0]["original_filename"] == "dob.png"
    # The replaced file's bytes go with it, so a re-upload never leaves an orphan behind.
    assert _stored_file_count() == files_after_first


def test_optimised_file_can_be_downloaded(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    r = upload(client, auth_headers, enrolment_id, "identity_proof", make_oversized_jpeg())
    document = r.json()["document"]

    served = client.get(
        f"/api/v1/enrolments/{enrolment_id}/documents/{document['id']}/file", headers=auth_headers
    )
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    assert 'filename="identity_proof.jpg"' in served.headers["content-disposition"]
    assert len(served.content) == document["optimized_size"]
    assert served.content[:3] == b"\xff\xd8\xff"


def test_unusable_upload_is_reported_without_storing_anything(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    r = upload(client, auth_headers, enrolment_id, "address_proof", corrupt(make_image(800, 600)))
    assert r.status_code == 201
    body = r.json()
    assert body["ready"] is False
    assert body["document"] is None
    assert "could not be opened" in body["message"]
    assert client.get(
        f"/api/v1/enrolments/{enrolment_id}/documents", headers=auth_headers
    ).json() == []


def test_multipage_pdf_for_photograph_slot_is_explained(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    data = make_pdf(pages=3, image_bytes=make_image(600, 800))
    r = upload(client, auth_headers, enrolment_id, "photograph", data, "photos.pdf")
    body = r.json()
    assert body["ready"] is False
    assert "lose pages" in body["message"]


def test_document_that_is_not_ready_cannot_be_accepted(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    # A tiny photo cannot reach the photograph slot's 350x450 minimum.
    r = upload(client, auth_headers, enrolment_id, "photograph", make_image(200, 260), "me.jpg")
    body = r.json()
    assert body["ready"] is False
    assert body["document"] is not None  # readable, so the citizen can still see it
    assert body["document"]["ready"] is False

    blocked = client.post(
        f"/api/v1/enrolments/{enrolment_id}/documents/{body['document']['id']}/accept",
        headers=auth_headers,
    )
    assert blocked.status_code == 409


def test_delete_removes_document_and_reopens_the_step(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    r = upload(client, auth_headers, enrolment_id, "address_proof", make_image(1400, 1000))
    document_id = r.json()["document"]["id"]
    client.post(
        f"/api/v1/enrolments/{enrolment_id}/documents/{document_id}/accept", headers=auth_headers
    )

    removed = client.delete(
        f"/api/v1/enrolments/{enrolment_id}/documents/{document_id}", headers=auth_headers
    )
    assert removed.status_code == 204
    detail = client.get(f"/api/v1/enrolments/{enrolment_id}", headers=auth_headers).json()
    assert detail["progress"]["documents"] is False
    assert detail["progress"]["documents_accepted"] == []


def test_unknown_slot_and_empty_file_are_rejected(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    unknown = upload(client, auth_headers, enrolment_id, "caste_certificate", make_image(400, 300))
    assert unknown.status_code == 400
    empty = upload(client, auth_headers, enrolment_id, "address_proof", b"")
    assert empty.status_code == 400


def test_documents_are_private_to_their_owner(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    r = upload(client, auth_headers, enrolment_id, "address_proof", make_image(1400, 1000))
    document_id = r.json()["document"]["id"]

    other = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Nosy User",
            "email": "nosy.user@example.com",
            "mobile": "9876500022",
            "password": "DemoPass123",
        },
    )
    assert other.status_code == 201, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert client.get(
        f"/api/v1/enrolments/{enrolment_id}/documents", headers=other_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/enrolments/{enrolment_id}/documents/{document_id}/file", headers=other_headers
    ).status_code == 404
    assert client.get(f"/api/v1/enrolments/{enrolment_id}/documents").status_code == 401


def test_prepared_application_locks_documents(client, auth_headers):
    enrolment_id = new_enrolment(client, auth_headers)
    fill_details(client, auth_headers, enrolment_id)
    for slot in ADULT_SLOTS:
        r = upload(client, auth_headers, enrolment_id, slot, make_image(1400, 1000, fmt="JPEG"))
        client.post(
            f"/api/v1/enrolments/{enrolment_id}/documents/{r.json()['document']['id']}/accept",
            headers=auth_headers,
        )
    client.post(f"/api/v1/enrolments/{enrolment_id}/prepare", headers=auth_headers)

    locked = upload(client, auth_headers, enrolment_id, "address_proof", make_image(900, 700))
    assert locked.status_code == 409
