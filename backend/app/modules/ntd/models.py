from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base, SoftDeleteMixin, TimestampMixin

settings = get_settings()
EMBEDDING_DIM = settings.embedding_dimensions


class NTDDocument(Base, TimestampMixin, SoftDeleteMixin):
    """Normative document (SP, GOST, STO, etc.)."""

    __tablename__ = "documents"
    __table_args__ = {"schema": "ntd"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SP / GOST / STO / etc.
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ntd.documents.id"), nullable=True
    )

    clauses: Mapped[list["NTDClause"]] = relationship(
        "NTDClause", back_populates="document", cascade="all, delete-orphan"
    )


class NTDClause(Base, TimestampMixin):
    """Individual clause within a normative document, with vector embedding for RAG."""

    __tablename__ = "clauses"
    __table_args__ = (
        Index(
            "ix_clauses_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 50},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_clauses_fts", "fts_vector", postgresql_using="gin"),
        {"schema": "ntd"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ntd.documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    fts_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    document: Mapped[NTDDocument] = relationship("NTDDocument", back_populates="clauses")
