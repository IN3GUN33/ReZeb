from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.projects.models import Project

router = APIRouter(prefix="/projects", tags=["projects"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    location: str | None = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    location: str | None
    status: str
    model_config = {"from_attributes": True}


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, current_user: CurrentUser, db: DB) -> ProjectRead:
    project = Project(owner_id=current_user.id, **data.model_dump())
    db.add(project)
    await db.flush()
    return ProjectRead.model_validate(project)


@router.get("", response_model=list[ProjectRead])
async def list_projects(current_user: CurrentUser, db: DB) -> list[ProjectRead]:
    stmt = (
        select(Project)
        .where(Project.owner_id == current_user.id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    return [ProjectRead.model_validate(p) for p in result.scalars().all()]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, current_user: CurrentUser, db: DB) -> ProjectRead:
    from app.core.exceptions import NotFoundError
    project = await db.get(Project, project_id)
    if not project or project.owner_id != current_user.id or project.deleted_at:
        raise NotFoundError("Project not found")
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, current_user: CurrentUser, db: DB) -> None:
    from app.core.exceptions import NotFoundError
    from datetime import UTC, datetime
    project = await db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise NotFoundError("Project not found")
    project.deleted_at = datetime.now(UTC)
