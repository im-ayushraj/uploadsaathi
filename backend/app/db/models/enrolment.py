from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


class Enrolment(Base):
    """A draft document-preparation application. Holds synthetic demo data only.

    personal_details / address are JSON so the same table can serve other portals later.
    No Aadhaar number is ever stored — this prototype never handles real Aadhaar data.
    """

    __tablename__ = "enrolments"
    __table_args__ = (Index("ix_enrolments_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    portal_id: Mapped[str] = mapped_column(String(40), default="aadhaar", nullable=False)
    applicant_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # draft -> prepared
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    personal_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reference_code: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
