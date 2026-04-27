"""Additional registry management endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.pto.models import RegistryItem
from app.modules.pto.schemas import RegistryItemRead

router = APIRouter(prefix="/pto/registry", tags=["pto-registry"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[RegistryItemRead])
async def list_registry(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
) -> list[RegistryItemRead]:
    stmt = (
        select(RegistryItem)
        .where(RegistryItem.deleted_at.is_(None))
        .order_by(RegistryItem.category, RegistryItem.name)
        .limit(limit)
        .offset(offset)
    )
    if category:
        stmt = stmt.where(RegistryItem.category == category)
    result = await db.execute(stmt)
    return [RegistryItemRead.model_validate(i) for i in result.scalars().all()]


@router.get("/categories")
async def list_categories(current_user: CurrentUser, db: DB) -> list[str]:
    from sqlalchemy import distinct, func
    stmt = select(distinct(RegistryItem.category)).where(
        RegistryItem.deleted_at.is_(None),
        RegistryItem.category.isnot(None),
    ).order_by(RegistryItem.category)
    result = await db.execute(stmt)
    return [r[0] for r in result.fetchall()]


@router.get("/{item_id}", response_model=RegistryItemRead)
async def get_registry_item(
    item_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> RegistryItemRead:
    from app.core.exceptions import NotFoundError
    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    return RegistryItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_registry_item(
    item_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> None:
    from app.core.exceptions import NotFoundError, ForbiddenError
    from app.modules.auth.models import UserRole
    from datetime import UTC, datetime

    if current_user.role not in (UserRole.superadmin, UserRole.org_admin, UserRole.pto_specialist):
        raise ForbiddenError("Insufficient permissions")

    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    item.deleted_at = datetime.now(UTC)
