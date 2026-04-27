"""User profile update endpoint."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import UserRead
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationError

router = APIRouter(prefix="/auth/profile", tags=["profile"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


@router.patch("", response_model=UserRead)
async def update_profile(data: ProfileUpdate, current_user: CurrentUser, db: DB) -> UserRead:
    if data.full_name is not None:
        current_user.full_name = data.full_name
    await db.flush()
    return UserRead.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: PasswordChange, current_user: CurrentUser, db: DB) -> None:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise ValidationError("Current password is incorrect")
    current_user.hashed_password = hash_password(data.new_password)
    await db.flush()
