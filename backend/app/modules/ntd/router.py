from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.ntd.service import NTDService

router = APIRouter(prefix="/ntd", tags=["ntd"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/documents")
async def list_documents(current_user: CurrentUser, db: DB) -> list[dict]:
    service = NTDService(db)
    docs = await service.list_documents()
    return [
        {
            "id": str(d.id),
            "code": d.code,
            "title": d.title,
            "doc_type": d.doc_type,
            "version": d.version,
        }
        for d in docs
    ]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: DB,
    file: Annotated[UploadFile, File(...)],
    code: Annotated[str, Form(...)],
    title: Annotated[str, Form(...)],
    doc_type: Annotated[str, Form()] = "SP",
    version: Annotated[str | None, Form()] = None,
    effective_date: Annotated[str | None, Form()] = None,
) -> dict:
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    data = await file.read()
    service = NTDService(db)
    doc = await service.add_document(
        code=code,
        title=title,
        doc_type=doc_type,
        file_data=data,
        filename=file.filename or "document.pdf",
        version=version,
        effective_date=effective_date,
    )
    return {"id": str(doc.id), "code": doc.code, "title": doc.title}


@router.get("/search")
async def search_clauses(
    current_user: CurrentUser,
    db: DB,
    q: Annotated[str, Query(min_length=3)],
    top_k: Annotated[int, Query(le=20)] = 5,
) -> list[dict]:
    service = NTDService(db)
    return await service.search_clauses(q, top_k=top_k)
