"""Admin endpoints: user management, system stats."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import UserRead, UserUpdate
from app.core.exceptions import ForbiddenError

router = APIRouter(prefix="/admin", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role not in (UserRole.superadmin, UserRole.org_admin):
        raise ForbiddenError("Admin access required")
    return current_user


@router.get("/users", response_model=list[UserRead])
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    db: DB,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    stmt = (
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return [UserRead.model_validate(u) for u in result.scalars().all()]


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: DB,
) -> UserRead:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    await db.flush()
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: DB,
) -> None:
    from datetime import UTC, datetime
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted_at = datetime.now(UTC)


@router.get("/stats")
async def get_stats(
    current_user: Annotated[User, Depends(require_admin)],
    db: DB,
) -> dict:
    from sqlalchemy import text
    from app.core.cost_tracker import get_monthly_cost

    users_count = (await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )).scalar() or 0

    sessions_count = (await db.execute(
        text("SELECT COUNT(*) FROM control.sessions WHERE deleted_at IS NULL")
    )).scalar() or 0

    pto_queries_count = (await db.execute(
        text("SELECT COUNT(*) FROM pto.queries")
    )).scalar() or 0

    registry_count = (await db.execute(
        text("SELECT COUNT(*) FROM pto.registry WHERE deleted_at IS NULL")
    )).scalar() or 0

    monthly_cost = await get_monthly_cost(db)

    return {
        "users_total": users_count,
        "control_sessions_total": sessions_count,
        "pto_queries_total": pto_queries_count,
        "registry_items": registry_count,
        "monthly_llm_cost_rub": round(monthly_cost, 2),
    }


@router.get("/costs")
async def get_costs(
    current_user: Annotated[User, Depends(require_admin)],
    db: DB,
) -> dict:
    from app.core.cost_tracker import check_budget_alert
    return await check_budget_alert(db)
