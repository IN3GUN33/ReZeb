from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        action: str,
        user_id: UUID | None = None,
        user_email: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        payload: dict | None = None,
    ) -> None:
        event = AuditEvent(
            action=action,
            user_id=user_id,
            user_email=user_email,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload or {},
        )
        self.db.add(event)
        # No commit — caller's transaction handles it

    async def get_events(
        self,
        user_id: UUID | None = None,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
        if user_id:
            stmt = stmt.where(AuditEvent.user_id == user_id)
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
