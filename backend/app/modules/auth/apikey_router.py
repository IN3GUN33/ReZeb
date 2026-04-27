"""API key management endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.apikey_models import APIKey
from app.modules.auth.dependencies import CurrentUser

router = APIRouter(prefix="/auth/api-keys", tags=["api-keys"])
DB = Annotated[AsyncSession, Depends(get_db)]


class APIKeyCreate(BaseModel):
    name: str


class APIKeyRead(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    created_at: str
    last_used_at: str | None
    revoked_at: str | None
    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyRead):
    key: str  # Only shown once at creation


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(data: APIKeyCreate, current_user: CurrentUser, db: DB) -> APIKeyCreated:
    raw, prefix, key_hash = APIKey.generate()
    api_key = APIKey(user_id=current_user.id, name=data.name, key_prefix=prefix, key_hash=key_hash)
    db.add(api_key)
    await db.flush()
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=raw,
        created_at=str(api_key.created_at),
        last_used_at=None,
        revoked_at=None,
    )


@router.get("", response_model=list[APIKeyRead])
async def list_api_keys(current_user: CurrentUser, db: DB) -> list[APIKeyRead]:
    stmt = select(APIKey).where(
        APIKey.user_id == current_user.id,
        APIKey.revoked_at.is_(None),
    ).order_by(APIKey.created_at.desc())
    result = await db.execute(stmt)
    return [
        APIKeyRead(
            id=k.id, name=k.name, key_prefix=k.key_prefix,
            created_at=str(k.created_at),
            last_used_at=str(k.last_used_at) if k.last_used_at else None,
            revoked_at=None,
        )
        for k in result.scalars().all()
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: UUID, current_user: CurrentUser, db: DB) -> None:
    from app.core.exceptions import NotFoundError
    from datetime import UTC, datetime
    key = await db.get(APIKey, key_id)
    if not key or key.user_id != current_user.id:
        raise NotFoundError("API key not found")
    key.revoked_at = datetime.now(UTC)
