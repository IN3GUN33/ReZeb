from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.control.models import DefectSeverity, SessionStatus


class SessionCreate(BaseModel):
    project_id: UUID | None = None


class DefectRead(BaseModel):
    id: UUID
    defect_type: str
    severity: DefectSeverity
    description: str
    measurement_mm: float | None
    confidence: float
    ntd_references: list[dict]
    bbox: list[float] | None

    model_config = {"from_attributes": True}


class PhotoRead(BaseModel):
    id: UUID
    original_filename: str
    file_size_bytes: int
    is_blurry: bool
    sharpness_score: float | None
    has_aruco_marker: bool

    model_config = {"from_attributes": True}


class SessionRead(BaseModel):
    id: UUID
    status: SessionStatus
    construction_type: str | None
    construction_type_confidence: float | None
    verdict: dict | None
    escalated: bool
    error_message: str | None
    photos: list[PhotoRead]
    defects: list[DefectRead]

    model_config = {"from_attributes": True}


class SessionListItem(BaseModel):
    id: UUID
    status: SessionStatus
    construction_type: str | None
    created_at: str

    model_config = {"from_attributes": True}
