import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.control.schemas import SessionCreate, SessionListItem, SessionRead
from app.modules.control.service import ControlService

router = APIRouter(prefix="/control", tags=["control"])
DB = Annotated[AsyncSession, Depends(get_db)]

MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/sessions", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: CurrentUser,
    db: DB,
) -> SessionRead:
    service = ControlService(db)
    session = await service.create_session(current_user, data.project_id)
    return SessionRead.model_validate(session)


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[SessionListItem]:
    service = ControlService(db)
    sessions = await service.list_sessions(current_user, limit=limit, offset=offset)
    return [SessionListItem.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> SessionRead:
    service = ControlService(db)
    session = await service.get_session(session_id, current_user)
    return SessionRead.model_validate(session)


@router.post("/sessions/{session_id}/photos", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    session_id: UUID,
    current_user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(400, "File too large (max 20 MB)")

    service = ControlService(db)
    photo = await service.upload_photo(session_id, current_user, file.filename or "photo.jpg", data)
    return {"photo_id": str(photo.id), "is_blurry": photo.is_blurry}


@router.post("/sessions/{session_id}/analyze", response_model=dict)
async def start_analysis(
    session_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    service = ControlService(db)
    session = await service.start_analysis(session_id, current_user)
    # Fire-and-forget processing (in real deployment this goes to Redis queue via worker)
    asyncio.create_task(_run_analysis(session_id))
    return {"status": session.status.value, "session_id": str(session_id)}


@router.get("/sessions/{session_id}/events")
async def session_events(
    session_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> StreamingResponse:
    """SSE endpoint for real-time session progress."""

    async def event_generator():  # type: ignore[return]
        service = ControlService(db)
        import asyncio

        max_polls = 60
        for _ in range(max_polls):
            try:
                session = await service.get_session(session_id, current_user)
            except Exception:
                yield f"data: {json.dumps({'error': 'session not found'})}\n\n"
                return

            payload = {"status": session.status.value, "session_id": str(session_id)}
            if session.status.value in ("completed", "failed"):
                if session.verdict:
                    payload["verdict"] = session.verdict
                if session.error_message:
                    payload["error"] = session.error_message
                yield f"data: {json.dumps(payload)}\n\n"
                return

            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(2)

        yield f"data: {json.dumps({'error': 'timeout'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _run_analysis(session_id: UUID) -> None:
    """Background task wrapper — in production replaced by arq worker."""
    from app.db.session import AsyncSessionFactory
    from app.modules.control.service import ControlService

    async with AsyncSessionFactory() as db:
        service = ControlService(db)
        await service.process_session(session_id)
