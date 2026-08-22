"""Document upload endpoints — the API face of UploadSaathi.

The flow is deliberately two-step: optimising a file produces a *pending* document the citizen can
look at, and only an explicit accept marks it as ready. Nothing here decides whether a document is
good enough; that judgement comes from the engine's UploadResult.

No document is ever sent anywhere. Only the optimised file is stored.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_enrolment
from app.core.config import settings
from app.db.models.document import EnrolmentDocument
from app.db.models.enrolment import Enrolment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import DocumentDetail, DocumentOut, UploadResponse
from app.services.storage import storage
from app.uploadsaathi.formats import extension_for
from app.uploadsaathi.requirements.resolver import (
    DocumentTypeNotFoundError,
    PortalNotFoundError,
    get_resolver,
)
from app.uploadsaathi.service import UploadResult, UploadService
from app.uploadsaathi.strategy import OptimizationMode

router = APIRouter(prefix="/enrolments/{enrolment_id}/documents", tags=["documents"])

upload_service = UploadService()

# Shown to the citizen. Plain language, no blame, and never a claim about the document's contents.
ISSUE_MESSAGES: dict[str, str] = {
    "file_too_large": "Still larger than the portal allows.",
    "file_too_small": "The file is smaller than the portal's minimum size.",
    "format_not_accepted": "This file type is not accepted for this document.",
    "below_min_width": "The image is not wide enough for this document.",
    "below_min_height": "The image is not tall enough for this document.",
    "above_max_width": "The image is wider than the portal allows.",
    "above_max_height": "The image is taller than the portal allows.",
    "too_many_pages": "This document has more pages than the portal accepts.",
    "colour_document_required": "A colour document is required for this slot.",
    "greyscale_document_required": "A greyscale document is required for this slot.",
    "unsupported_format": "We cannot read this file type. Please upload a JPG, PNG or PDF.",
    "corrupted_or_unreadable": "This file could not be opened. It may be incomplete.",
    "password_protected": "This PDF is password protected. Please remove the password first.",
    "image_too_large_to_process": "This image is too large for us to process safely.",
    "multipage_pdf_cannot_convert_to_image": (
        "This slot needs a single image, and splitting a multi-page PDF would lose pages."
    ),
    "format_not_accepted_and_no_conversion_available": (
        "This file type is not accepted and cannot be converted safely."
    ),
    "readability_below_acceptable_level": (
        "Meeting the size limit would have made this unreadable, so we stopped."
    ),
    "processing_failed": "Something went wrong while preparing this file. Please try again.",
}


def _resolve_slot(enrolment: Enrolment, document_type: str) -> None:
    """Reject a document type the portal configuration does not define."""
    try:
        get_resolver().resolve(enrolment.portal_id, document_type)
    except PortalNotFoundError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown portal")
    except DocumentTypeNotFoundError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown document type")


def _require_draft(enrolment: Enrolment) -> None:
    if enrolment.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This application is already prepared and cannot be changed"
        )


def _get_document(document_id: int, enrolment: Enrolment, db: Session) -> EnrolmentDocument:
    document = db.get(EnrolmentDocument, document_id)
    if document is None or document.enrolment_id != enrolment.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def _summary(result: UploadResult) -> str:
    if result.accepted:
        if result.quality_status == "unchanged":
            return "This file already met the portal's requirements — nothing was changed."
        saved = result.original_size - result.optimized_size
        if saved > 0:
            return (
                f"Ready for upload. Reduced by {result.reduction_percent}% "
                f"({saved:,} bytes saved) while keeping it readable."
            )
        return "Ready for upload."
    for issue in result.issues:
        if issue in ISSUE_MESSAGES:
            return ISSUE_MESSAGES[issue]
    return "This file cannot be made to meet the portal's requirements."


def _replace_existing(enrolment: Enrolment, document_type: str, db: Session) -> None:
    """One document per slot: the previous file (and its bytes) go away."""
    previous = db.scalars(
        select(EnrolmentDocument).where(
            EnrolmentDocument.enrolment_id == enrolment.id,
            EnrolmentDocument.document_type == document_type,
        )
    ).all()
    for row in previous:
        storage.delete(row.storage_key)
        db.delete(row)
    if previous:
        db.flush()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    enrolment_id: int,
    document_type: str = Form(...),
    mode: str = Form(OptimizationMode.BALANCED.value),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Run UploadSaathi over one uploaded file and keep the optimised result as pending."""
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    _require_draft(enrolment)
    _resolve_slot(enrolment, document_type)

    try:
        optimization_mode = OptimizationMode(mode)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown optimisation mode")

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Please upload a file smaller than {limit_mb} MB",
        )

    result = upload_service.process(
        data, file.filename or "upload", enrolment.portal_id, document_type, optimization_mode
    )
    del data  # the original is not persisted, and it is not needed beyond this point

    _replace_existing(enrolment, document_type, db)

    document: EnrolmentDocument | None = None
    if result.readable:
        key = storage.new_key(result.format)
        storage.save(key, result.data)
        document = EnrolmentDocument(
            enrolment_id=enrolment.id,
            document_type=document_type,
            status="pending",
            original_filename=(file.filename or None),
            original_size=result.original_size,
            optimized_size=result.optimized_size,
            format=result.format,
            mime_type=result.mime_type,
            storage_key=key,
            quality_status=result.quality_status,
            accepted=False,
            result=result.to_dict(),
        )
        db.add(document)
    db.commit()
    if document is not None:
        db.refresh(document)

    return UploadResponse(
        ready=result.accepted,
        outcome=result.to_dict(),
        document=DocumentOut.model_validate(document) if document else None,
        message=_summary(result),
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    enrolment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[DocumentOut]:
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    rows = db.scalars(
        select(EnrolmentDocument)
        .where(EnrolmentDocument.enrolment_id == enrolment.id)
        .order_by(EnrolmentDocument.document_type)
    ).all()
    return [DocumentOut.model_validate(r) for r in rows]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    enrolment_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentDetail:
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    return DocumentDetail.model_validate(_get_document(document_id, enrolment, db))


@router.get("/{document_id}/file")
def download_document(
    enrolment_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Serve the optimised file back for preview or download."""
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    document = _get_document(document_id, enrolment, db)
    data = storage.read(document.storage_key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The stored file is no longer available")
    filename = f"{document.document_type}.{extension_for(document.format)}"
    return Response(
        content=data,
        media_type=document.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{document_id}/accept", response_model=DocumentDetail)
def accept_document(
    enrolment_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentDetail:
    """The citizen confirms the optimised file. Only accepted documents count as done."""
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    _require_draft(enrolment)
    document = _get_document(document_id, enrolment, db)

    if not document.result.get("accepted"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This file does not meet the portal's requirements yet, so it cannot be accepted",
        )

    document.status = "accepted"
    document.accepted = True
    db.commit()
    db.refresh(document)
    return DocumentDetail.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    enrolment_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    enrolment = get_owned_enrolment(enrolment_id, user, db)
    _require_draft(enrolment)
    document = _get_document(document_id, enrolment, db)
    storage.delete(document.storage_key)
    db.delete(document)
    db.commit()
