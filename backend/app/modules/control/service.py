"""Control module service: photo upload, quality check, async processing pipeline."""

from __future__ import annotations

import io
import json
from uuid import UUID

import cv2
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.aitunnel import TokenUsage, vision_completion
from app.core.config import get_settings
from app.core.exceptions import LimitExceededError, NotFoundError
from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.control.models import (
    ConstructionSession,
    Defect,
    DefectSeverity,
    Photo,
    SessionStatus,
)
from app.modules.control.prompts import (
    ESCALATION_PROMPT,
    PHOTO_ANALYSIS_PROMPT,
    SYSTEM_PHOTO_ANALYSIS,
)
from app.modules.media.service import MediaService

logger = get_logger(__name__)
settings = get_settings()


class ControlService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.media = MediaService()

    async def create_session(
        self, user: User, project_id: UUID | None = None
    ) -> ConstructionSession:
        await self._check_daily_limit(user)
        session = ConstructionSession(user_id=user.id, project_id=project_id)
        self.db.add(session)
        await self.db.flush()
        return session

    async def upload_photo(
        self,
        session_id: UUID,
        user: User,
        filename: str,
        data: bytes,
    ) -> Photo:
        session = await self._get_session(session_id, user.id)
        if session.status not in (SessionStatus.pending, SessionStatus.queued):
            raise ValueError("Cannot add photos to a session in progress or completed")

        # Quality check
        sharpness, is_blurry, has_aruco, scale_mm_per_px = self._quality_check(data)
        width, height = self._get_dimensions(data)

        # Upload to S3
        s3_key = await self.media.upload_photo(data, str(session_id), filename)

        photo = Photo(
            session_id=session_id,
            s3_key=s3_key,
            original_filename=filename,
            file_size_bytes=len(data),
            width=width,
            height=height,
            is_blurry=is_blurry,
            sharpness_score=sharpness,
            has_aruco_marker=has_aruco,
            aruco_scale_mm_per_px=scale_mm_per_px,
        )
        self.db.add(photo)
        await self.db.flush()
        return photo

    async def start_analysis(self, session_id: UUID, user: User) -> ConstructionSession:
        """Enqueue session for background processing."""
        session = await self._get_session(session_id, user.id)
        session.status = SessionStatus.queued
        await self.db.flush()
        return session

    async def process_session(self, session_id: UUID) -> None:
        """Full pipeline: CV → RAG → LLM → save results. Called by background worker."""
        session = await self._get_session_with_photos(session_id)
        session.status = SessionStatus.processing
        await self.db.commit()

        try:
            photos = session.photos
            if not photos:
                raise ValueError("No photos in session")

            # Get first non-blurry photo for LLM analysis
            best_photo = next((p for p in photos if not p.is_blurry), photos[0])
            image_bytes = await self.media.download(best_photo.s3_key)

            # Build YOLO context (mock for MVP if ML service unavailable)
            yolo_context = self._format_yolo_results(best_photo.yolo_detections)

            # RAG: fetch NTD context (simplified for MVP — full RAG in ntd.service)
            ntd_context = "Нормативные требования будут добавлены после индексации НТД."

            # Primary LLM analysis
            prompt = PHOTO_ANALYSIS_PROMPT.format(
                construction_type="не определён (определи автоматически)",
                yolo_results=yolo_context,
                ntd_context=ntd_context,
            )
            raw, usage = await vision_completion(
                model=settings.model_vision,
                text_prompt=prompt,
                image_bytes=image_bytes,
                system=SYSTEM_PHOTO_ANALYSIS,
            )

            verdict = self._parse_verdict(raw)
            escalated = False
            total_usage = usage

            # Escalation: low confidence or critical defects
            should_escalate = verdict.get(
                "construction_type_confidence", 1.0
            ) < settings.escalation_confidence_threshold or any(
                d.get("severity") == "critical" for d in verdict.get("defects", [])
            )

            if should_escalate:
                escalation_prompt = ESCALATION_PROMPT.format(
                    initial_verdict=json.dumps(verdict, ensure_ascii=False, indent=2),
                    ntd_context=ntd_context,
                )
                raw2, usage2 = await vision_completion(
                    model=settings.model_complex,
                    text_prompt=escalation_prompt,
                    image_bytes=image_bytes,
                    system=SYSTEM_PHOTO_ANALYSIS,
                )
                verdict = self._parse_verdict(raw2)
                escalated = True
                total_usage = self._merge_usage(usage, usage2)

            # Save defects
            for d in verdict.get("defects", []):
                defect = Defect(
                    session_id=session.id,
                    photo_id=best_photo.id,
                    defect_type=d.get("defect_type", "unknown"),
                    severity=DefectSeverity(d.get("severity", "acceptable")),
                    description=d.get("description", ""),
                    measurement_mm=d.get("measurement_mm"),
                    confidence=d.get("confidence", 0.5),
                    ntd_references=d.get("ntd_references", []),
                )
                self.db.add(defect)

            session.verdict = verdict
            session.verdict_model = settings.model_complex if escalated else settings.model_vision
            session.escalated = escalated
            session.construction_type = verdict.get("construction_type")
            session.construction_type_confidence = verdict.get("construction_type_confidence")
            session.status = SessionStatus.completed
            session.input_tokens = total_usage.input_tokens
            session.output_tokens = total_usage.output_tokens
            session.cached_tokens = total_usage.cached_tokens
            session.cost_rub = total_usage.cost_rub

            await self.db.commit()
            logger.info(
                "session_completed", session_id=str(session_id), cost_rub=total_usage.cost_rub
            )

        except Exception as exc:
            session.status = SessionStatus.failed
            session.error_message = str(exc)
            await self.db.commit()
            logger.error("session_failed", session_id=str(session_id), error=str(exc))
            raise

    async def get_session(self, session_id: UUID, user: User) -> ConstructionSession:
        return await self._get_session_with_photos(session_id, user_id=user.id)

    async def list_sessions(
        self, user: User, limit: int = 20, offset: int = 0
    ) -> list[ConstructionSession]:
        stmt = (
            select(ConstructionSession)
            .where(ConstructionSession.user_id == user.id, ConstructionSession.deleted_at.is_(None))
            .order_by(ConstructionSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _get_session(
        self, session_id: UUID, user_id: UUID | None = None
    ) -> ConstructionSession:
        session = await self.db.get(ConstructionSession, session_id)
        if not session or session.deleted_at is not None:
            raise NotFoundError("Session not found")
        if user_id and session.user_id != user_id:
            raise NotFoundError("Session not found")
        return session

    async def _get_session_with_photos(
        self, session_id: UUID, user_id: UUID | None = None
    ) -> ConstructionSession:
        stmt = (
            select(ConstructionSession)
            .options(
                selectinload(ConstructionSession.photos), selectinload(ConstructionSession.defects)
            )
            .where(ConstructionSession.id == session_id)
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Session not found")
        if user_id and session.user_id != user_id:
            raise NotFoundError("Session not found")
        return session

    async def _check_daily_limit(self, user: User) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if user.daily_reset_at is None or user.daily_reset_at.date() < now.date():
            user.daily_control_used = 0
            user.daily_reset_at = now

        if user.daily_control_used >= settings.daily_control_limit_per_user:
            raise LimitExceededError(
                f"Daily control limit ({settings.daily_control_limit_per_user}) reached"
            )
        user.daily_control_used += 1

    @staticmethod
    def _quality_check(data: bytes) -> tuple[float, bool, bool, float | None]:
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0, True, False, None

        # Laplacian sharpness
        sharpness = float(cv2.Laplacian(img, cv2.CV_64F).var())
        is_blurry = sharpness < 100.0

        # ArUco marker detection
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        corners, ids, _ = detector.detectMarkers(img)
        has_aruco = ids is not None and len(ids) > 0
        scale: float | None = None
        if has_aruco and corners:
            # Assume 100mm marker side — calculate px/mm ratio
            side_px = float(np.linalg.norm(corners[0][0][0] - corners[0][0][1]))
            if side_px > 0:
                scale = 100.0 / side_px

        return sharpness, is_blurry, has_aruco, scale

    @staticmethod
    def _get_dimensions(data: bytes) -> tuple[int, int]:
        try:
            img = Image.open(io.BytesIO(data))
            return img.size  # (width, height)
        except Exception:
            return 0, 0

    @staticmethod
    def _format_yolo_results(detections: dict | None) -> str:
        if not detections:
            return "CV-детекция не выполнена (требуется ML-сервис)"
        return json.dumps(detections, ensure_ascii=False, indent=2)

    @staticmethod
    def _parse_verdict(raw: str) -> dict:
        # Strip markdown code blocks if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": text, "defects": [], "error": "parse_failed"}

    @staticmethod
    def _merge_usage(u1: TokenUsage, u2: TokenUsage) -> TokenUsage:
        return TokenUsage(
            u1.input_tokens + u2.input_tokens,
            u1.output_tokens + u2.output_tokens,
            u1.cached_tokens + u2.cached_tokens,
            u1.cost_rub + u2.cost_rub,
        )
