"""Enrolment (document-preparation application) endpoints.

This prototype prepares the document portion of an Aadhaar enrolment. It never submits
anything to a government system and never performs Aadhaar authentication.
"""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.enrolment import Enrolment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.enrolment import (
    Address,
    EnrolmentCreate,
    EnrolmentDetail,
    EnrolmentOut,
    EnrolmentProgress,
    EnrolmentUpdate,
    PersonalDetails,
)
from app.uploadsaathi.requirements.resolver import (
    ApplicantTypeNotFoundError,
    PortalNotFoundError,
    get_resolver,
)

router = APIRouter(prefix="/enrolments", tags=["enrolments"])


def _validate_applicant_type(portal_id: str, applicant_type: str) -> None:
    try:
        get_resolver().applicant_type(portal_id, applicant_type)
    except PortalNotFoundError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown portal")
    except ApplicantTypeNotFoundError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown applicant type")


def _progress(enrolment: Enrolment) -> EnrolmentProgress:
    has_personal = bool(enrolment.personal_details)
    has_address = bool(enrolment.address)
    # Document upload arrives in Phase 5; until then the documents step is informational.
    documents_done = False
    return EnrolmentProgress(
        applicant_type=bool(enrolment.applicant_type),
        personal_details=has_personal,
        address=has_address,
        documents=documents_done,
        can_prepare=has_personal and has_address,
    )


def _detail(enrolment: Enrolment) -> EnrolmentDetail:
    return EnrolmentDetail(
        **EnrolmentOut.model_validate(enrolment).model_dump(),
        progress=_progress(enrolment),
    )


def _get_owned(enrolment_id: int, user: User, db: Session) -> Enrolment:
    enrolment = db.get(Enrolment, enrolment_id)
    # Do not leak the existence of another user's record.
    if enrolment is None or enrolment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return enrolment


def _require_draft(enrolment: Enrolment) -> None:
    if enrolment.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This application is already prepared and cannot be changed"
        )


@router.post("", response_model=EnrolmentDetail, status_code=status.HTTP_201_CREATED)
def create_enrolment(
    payload: EnrolmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnrolmentDetail:
    _validate_applicant_type(payload.portal_id, payload.applicant_type)
    enrolment = Enrolment(
        user_id=user.id, portal_id=payload.portal_id, applicant_type=payload.applicant_type
    )
    db.add(enrolment)
    db.commit()
    db.refresh(enrolment)
    return _detail(enrolment)


@router.get("", response_model=list[EnrolmentOut])
def list_enrolments(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EnrolmentOut]:
    rows = db.scalars(
        select(Enrolment).where(Enrolment.user_id == user.id).order_by(Enrolment.id.desc())
    ).all()
    return [EnrolmentOut.model_validate(r) for r in rows]


@router.get("/{enrolment_id}", response_model=EnrolmentDetail)
def get_enrolment(
    enrolment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> EnrolmentDetail:
    return _detail(_get_owned(enrolment_id, user, db))


@router.patch("/{enrolment_id}", response_model=EnrolmentDetail)
def update_enrolment(
    enrolment_id: int,
    payload: EnrolmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnrolmentDetail:
    enrolment = _get_owned(enrolment_id, user, db)
    _require_draft(enrolment)

    if payload.applicant_type is not None:
        _validate_applicant_type(enrolment.portal_id, payload.applicant_type)
        enrolment.applicant_type = payload.applicant_type
    if payload.personal_details is not None:
        enrolment.personal_details = payload.personal_details.model_dump(mode="json")
    if payload.address is not None:
        enrolment.address = payload.address.model_dump(mode="json")

    db.commit()
    db.refresh(enrolment)
    return _detail(enrolment)


@router.post("/{enrolment_id}/prepare", response_model=EnrolmentDetail)
def prepare_enrolment(
    enrolment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> EnrolmentDetail:
    """Marks the document pack as prepared. Nothing is submitted to any government system."""
    enrolment = _get_owned(enrolment_id, user, db)
    if enrolment.status == "prepared":
        return _detail(enrolment)

    progress = _progress(enrolment)
    if not progress.can_prepare:
        missing = [
            name
            for name, done in (
                ("personal details", progress.personal_details),
                ("address", progress.address),
            )
            if not done
        ]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Please complete: {', '.join(missing)}"
        )

    enrolment.status = "prepared"
    enrolment.prepared_at = datetime.now(timezone.utc)
    # Synthetic prototype reference. Deliberately not shaped like a real UIDAI EID/URN.
    enrolment.reference_code = f"PREP-{secrets.token_hex(4).upper()}"
    db.commit()
    db.refresh(enrolment)
    return _detail(enrolment)


@router.delete("/{enrolment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrolment(
    enrolment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    enrolment = _get_owned(enrolment_id, user, db)
    db.delete(enrolment)
    db.commit()


# Re-exported for schema clarity in generated OpenAPI docs.
__all__ = ["router", "Address", "PersonalDetails"]
