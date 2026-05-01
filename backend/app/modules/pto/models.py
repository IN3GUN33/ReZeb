import enum
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base, SoftDeleteMixin, TimestampMixin

settings = get_settings()
EMBEDDING_DIM = settings.embedding_dimensions


class MatchStatus(enum.StrEnum):
    exact = "exact"
    analog = "analog"
    not_found = "not_found"


class RegistryItem(Base, TimestampMixin, SoftDeleteMixin):
    """PTO materials registry (~6700 rows imported from Excel)."""

    __tablename__ = "registry"
    __table_args__ = (
        Index(
            "ix_registry_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_registry_fts", "fts_vector", postgresql_using="gin"),
        {"schema": "pto"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Vector embedding (text-embedding-3-large, 3072 dims)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    # Full-text search vector (ru + en)
    fts_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    synonyms: Mapped[list["RegistrySynonym"]] = relationship(
        "RegistrySynonym", back_populates="registry_item"
    )


class RegistrySynonym(Base, TimestampMixin):
    __tablename__ = "synonyms"
    __table_args__ = (
        UniqueConstraint("registry_item_id", "synonym", name="uq_synonym"),
        {"schema": "pto"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    registry_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pto.registry.id", ondelete="CASCADE"), nullable=False
    )
    synonym: Mapped[str] = mapped_column(Text, nullable=False)

    registry_item: Mapped[RegistryItem] = relationship("RegistryItem", back_populates="synonyms")


class PTOQuery(Base, TimestampMixin):
    """One PTO matching query (one material from procurement docs)."""

    __tablename__ = "queries"
    __table_args__ = {"schema": "pto"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Raw input from procurement document
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # After Haiku normalization
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Results
    status: Mapped[str] = mapped_column(String(50), default="pending")
    results: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    best_match_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pto.registry.id"), nullable=True
    )
    match_status: Mapped[MatchStatus | None] = mapped_column(
        Enum(MatchStatus, schema="pto"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Token tracking
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
