"""Schemas for the document step.

`UploadOutcome` mirrors the UploadService contract one-to-one — the API adds no interpretation of
its own, so the engine stays the single source of truth about what happened to a document.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadOutcome(BaseModel):
    """What UploadSaathi did. Mirrors UploadResult.to_dict()."""

    filename: str
    original_size: int
    optimized_size: int
    format: str
    mime_type: str | None = None
    reduction_percent: float
    size_valid: bool
    format_valid: bool
    quality_status: str
    accepted: bool
    readable: bool
    steps: list[str] = []
    issues: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    width: int | None = None
    height: int | None = None
    pages: int | None = None
    quality_used: int | None = None
    scale_applied: float = 1.0
    mode: str = "balanced"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: str
    status: str
    original_filename: str | None = None
    original_size: int
    optimized_size: int
    format: str
    mime_type: str | None = None
    quality_status: str
    accepted: bool
    ready: bool
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentOut):
    """A stored document plus the full optimisation report it was created from."""

    result: UploadOutcome


class UploadResponse(BaseModel):
    """The result of one optimisation attempt.

    `document` is present whenever the output was storable — i.e. UploadSaathi produced something
    the citizen can look at. `ready` says whether it satisfies the portal.
    """

    ready: bool
    outcome: UploadOutcome
    document: DocumentOut | None = None
    message: str
