import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.pto.schemas import PTOQueryCreate, PTOQueryRead, RegistryImportResult, RegistryItemRead
from app.modules.pto.service import PTOService

router = APIRouter(prefix="/pto", tags=["pto"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/queries", response_model=PTOQueryRead, status_code=status.HTTP_201_CREATED)
async def create_query(
    data: PTOQueryCreate,
    current_user: CurrentUser,
    db: DB,
) -> PTOQueryRead:
    from app.core.queue import enqueue_pto_query

    service = PTOService(db)
    query = await service.create_query(current_user, data.raw_text, data.project_id)
    try:
        await enqueue_pto_query(str(query.id))
    except Exception:
        asyncio.create_task(_run_query(query.id))
    return PTOQueryRead.model_validate(query)


@router.get("/queries/{query_id}", response_model=PTOQueryRead)
async def get_query(
    query_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> PTOQueryRead:
    service = PTOService(db)
    query = await service.get_query(query_id, current_user)
    return PTOQueryRead.model_validate(query)


@router.get("/registry/search", response_model=list[RegistryItemRead])
async def search_registry(
    current_user: CurrentUser,
    db: DB,
    q: str = Query(min_length=2),
    limit: int = Query(default=20, le=100),
) -> list[RegistryItemRead]:
    service = PTOService(db)
    items = await service.search_registry(q, limit=limit)
    return [RegistryItemRead.model_validate(i) for i in items]


@router.post("/registry/import", response_model=RegistryImportResult)
async def import_registry(
    current_user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
) -> RegistryImportResult:
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only Excel files (.xlsx, .xls) are supported")

    data = await file.read()
    service = PTOService(db)
    result = await service.import_registry_from_excel(data, file.filename)
    return RegistryImportResult(**result)


async def _run_query(query_id: UUID) -> None:
    from app.db.session import AsyncSessionFactory

    async with AsyncSessionFactory() as db:
        service = PTOService(db)
        await service.process_query(query_id)
