from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


class EnrolmentDocument(Base):
    """One document slot of an application, after UploadSaathi has made it portal-ready.

    Only the optimised file is kept (`storage_key`); the original upload is never persisted.
    `result` holds the UploadResult contract so the UI can re-show what was done without
    re-processing. Nothing here is a claim about the document's authenticity.
    """

    __tablename__ = "enrolment_documents"
    __table_args__ = (
        UniqueConstraint("enrolment_id", "document_type", name="uq_document_per_slot"),
        Index("ix_enrolment_documents_status", "enrolment_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrolment_id: Mapped[int] = mapped_column(
        ForeignKey("enrolments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # pending -> accepted (a pending slot is a preview the citizen has not confirmed yet)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_size: Mapped[int] = mapped_column(Integer, nullable=False)
    optimized_size: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted: Mapped[bool] = mapped_column(default=False, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    enrolment = relationship("Enrolment", back_populates="documents")

    @property
    def ready(self) -> bool:
        """The engine's verdict on the stored file — distinct from `accepted`, the citizen's."""
        return bool(self.result.get("accepted")) if self.result else False
