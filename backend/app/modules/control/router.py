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
    from app.core.queue import enqueue_control_session

    service = ControlService(db)
    session = await service.start_analysis(session_id, current_user)
    try:
        await enqueue_control_session(str(session_id))
    except Exception:
        # Fallback: run in-process if Redis unavailable (dev mode)
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


@router.get("/sessions/{session_id}/photos/{photo_id}/url")
async def get_photo_url(
    session_id: UUID,
    photo_id: UUID,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Get presigned S3 URL for a photo."""
    from app.modules.control.models import Photo
    from app.modules.media.service import MediaService

    photo = await db.get(Photo, photo_id)
    if not photo or photo.session_id != session_id:
        raise HTTPException(404, "Photo not found")
    url = await MediaService().get_presigned_url(photo.s3_key)
    return {"url": url, "expires_in": 3600}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: UUID,
    current_user: CurrentUser,
    db: DB,
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
) -> dict:
    """Export session results as JSON or CSV-ready dict."""
    service = ControlService(db)
    session = await service.get_session(session_id, current_user)

    data = {
        "session_id": str(session.id),
        "status": session.status.value,
        "construction_type": session.construction_type,
        "construction_type_confidence": session.construction_type_confidence,
        "escalated": session.escalated,
        "verdict_model": session.verdict_model,
        "overall_assessment": session.verdict.get("overall_assessment") if session.verdict else None,
        "requires_immediate_action": session.verdict.get("requires_immediate_action") if session.verdict else False,
        "defects": [
            {
                "defect_type": d.defect_type,
                "severity": d.severity.value,
                "description": d.description,
                "measurement_mm": d.measurement_mm,
                "confidence": d.confidence,
                "ntd_references": d.ntd_references,
            }
            for d in session.defects
        ],
        "cost_rub": session.cost_rub,
        "disclaimer": "Заключение носит предварительный характер. Требует проверки специалистом.",
    }
    return data


async def _run_analysis(session_id: UUID) -> None:
    """Background task wrapper — in production replaced by arq worker."""
    from app.db.session import AsyncSessionFactory
    from app.modules.control.service import ControlService

    async with AsyncSessionFactory() as db:
        service = ControlService(db)
        await service.process_session(session_id)
