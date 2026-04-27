"""API keys for programmatic access (org-level)."""
import hashlib
import secrets
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "auth"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @staticmethod
    def generate() -> tuple[str, str, str]:
        """Returns (full_key, prefix, hash)."""
        raw = "rzb_" + secrets.token_urlsafe(32)
        prefix = raw[:10]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, key_hash
