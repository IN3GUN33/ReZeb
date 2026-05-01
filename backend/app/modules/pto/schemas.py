from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.pto.models import MatchStatus


class PTOQueryCreate(BaseModel):
    raw_text: str = Field(min_length=2, max_length=2000)
    project_id: UUID | None = None


class RegistryItemRead(BaseModel):
    id: UUID
    code: str | None
    name: str
    unit: str | None
    category: str | None
    manufacturer: str | None

    model_config = {"from_attributes": True}


class PTOQueryRead(BaseModel):
    id: UUID
    raw_text: str
    normalized_text: str | None
    status: str
    match_status: MatchStatus | None
    confidence: float | None
    results: list[dict[str, Any]]
    best_match: RegistryItemRead | None = None

    model_config = {"from_attributes": True}


class RegistryImportResult(BaseModel):
    imported: int
    skipped: int
    errors: int
