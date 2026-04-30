from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import CurrentUser

router = APIRouter(prefix="/audit", tags=["audit"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/events")
async def get_events(
    current_user: CurrentUser,
    db: DB,
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    service = AuditService(db)
    events = await service.get_events(
        user_id=current_user.id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": str(e.id),
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "created_at": str(e.created_at),
            "payload": e.payload,
        }
        for e in events
    ]
