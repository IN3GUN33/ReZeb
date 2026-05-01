import enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class SessionStatus(enum.StrEnum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DefectSeverity(enum.StrEnum):
    acceptable = "acceptable"
    significant = "significant"
    critical = "critical"


class ConstructionSession(Base, TimestampMixin, SoftDeleteMixin):
    """One inspection session = one or more photos for one construction element."""

    __tablename__ = "sessions"
    __table_args__ = {"schema": "control"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, schema="control"),
        nullable=False,
        default=SessionStatus.pending,
    )
    construction_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    construction_type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # LLM verdict
    verdict: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    verdict_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token usage tracking
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_rub: Mapped[float] = mapped_column(Float, default=0.0)

    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="session", cascade="all, delete-orphan"
    )
    defects: Mapped[list["Defect"]] = relationship(
        "Defect", back_populates="session", cascade="all, delete-orphan"
    )


class Photo(Base, TimestampMixin):
    __tablename__ = "photos"
    __table_args__ = {"schema": "control"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("control.sessions.id", ondelete="CASCADE"), nullable=False
    )
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality check results
    is_blurry: Mapped[bool] = mapped_column(Boolean, default=False)
    sharpness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_aruco_marker: Mapped[bool] = mapped_column(Boolean, default=False)
    aruco_scale_mm_per_px: Mapped[float | None] = mapped_column(Float, nullable=True)

    # YOLO raw detections
    yolo_detections: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    session: Mapped[ConstructionSession] = relationship(
        "ConstructionSession", back_populates="photos"
    )


class Defect(Base, TimestampMixin):
    __tablename__ = "defects"
    __table_args__ = {"schema": "control"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("control.sessions.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("control.photos.id"), nullable=True
    )

    defect_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[DefectSeverity] = mapped_column(
        Enum(DefectSeverity, schema="control"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # NTD references
    ntd_references: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Bounding box [x1, y1, x2, y2] normalized 0..1
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)

    session: Mapped[ConstructionSession] = relationship(
        "ConstructionSession", back_populates="defects"
    )
