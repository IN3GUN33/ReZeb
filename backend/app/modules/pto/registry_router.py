"""Additional registry management endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.auth.models import UserRole
from app.modules.pto.models import RegistryItem, RegistrySynonym
from app.modules.pto.schemas import RegistryItemRead

router = APIRouter(prefix="/pto/registry", tags=["pto-registry"])
AdminOnly = Annotated[None, Depends(require_roles(UserRole.superadmin, UserRole.org_admin, UserRole.pto_specialist))]


class RegistryItemUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    unit: str | None = None
    category: str | None = None
    manufacturer: str | None = None


class SynonymCreate(BaseModel):
    synonym: str


class SynonymRead(BaseModel):
    id: UUID
    synonym: str
    model_config = {"from_attributes": True}
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


@router.patch("/{item_id}", response_model=RegistryItemRead)
async def update_registry_item(
    item_id: UUID,
    data: RegistryItemUpdate,
    current_user: CurrentUser,
    db: DB,
    _admin: AdminOnly = None,
) -> RegistryItemRead:
    from app.core.exceptions import NotFoundError
    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.flush()
    return RegistryItemRead.model_validate(item)


@router.get("/{item_id}/synonyms", response_model=list[SynonymRead])
async def list_synonyms(item_id: UUID, current_user: CurrentUser, db: DB) -> list[SynonymRead]:
    from app.core.exceptions import NotFoundError
    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    stmt = select(RegistrySynonym).where(RegistrySynonym.registry_item_id == item_id)
    result = await db.execute(stmt)
    return [SynonymRead.model_validate(s) for s in result.scalars().all()]


@router.post("/{item_id}/synonyms", response_model=SynonymRead, status_code=status.HTTP_201_CREATED)
async def add_synonym(
    item_id: UUID,
    data: SynonymCreate,
    current_user: CurrentUser,
    db: DB,
    _admin: AdminOnly = None,
) -> SynonymRead:
    from app.core.exceptions import NotFoundError
    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    syn = RegistrySynonym(registry_item_id=item_id, synonym=data.synonym.strip())
    db.add(syn)
    await db.flush()
    return SynonymRead.model_validate(syn)


@router.delete("/{item_id}/synonyms/{synonym_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_synonym(
    item_id: UUID,
    synonym_id: UUID,
    current_user: CurrentUser,
    db: DB,
    _admin: AdminOnly = None,
) -> None:
    from app.core.exceptions import NotFoundError
    syn = await db.get(RegistrySynonym, synonym_id)
    if not syn or syn.registry_item_id != item_id:
        raise NotFoundError("Synonym not found")
    await db.delete(syn)


@router.delete("/{item_id}", status_code=204)
async def delete_registry_item(
    item_id: UUID,
    current_user: CurrentUser,
    db: DB,
    _admin: AdminOnly = None,
) -> None:
    from app.core.exceptions import NotFoundError
    from datetime import UTC, datetime
    item = await db.get(RegistryItem, item_id)
    if not item or item.deleted_at:
        raise NotFoundError("Registry item not found")
    item.deleted_at = datetime.now(UTC)
