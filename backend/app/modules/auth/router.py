from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DB) -> UserRead:
    service = AuthService(db)
    user = await service.register(data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(data: LoginRequest, db: DB) -> TokenPair:
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, db: DB) -> TokenPair:
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: DB) -> None:
    service = AuthService(db)
    await service.logout(data.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(data: ForgotPasswordRequest, db: DB) -> dict:
    service = AuthService(db)
    token = await service.forgot_password(data.email)
    response: dict = {"message": "Если аккаунт существует, инструкции отправлены на email"}
    if token:
        response["debug_token"] = token  # only present in APP_DEBUG=true
    return response


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordRequest, db: DB) -> None:
    service = AuthService(db)
    await service.reset_password(data.token, data.new_password)
