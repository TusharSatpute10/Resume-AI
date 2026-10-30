from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    file_name: str
    file_path: str
    raw_text: str | None = None
    summary: str | None = None
    total_experience_years: float | None = None
    experience_level: str | None = None
    parse_confidence: float | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    total_experience_years: float | None = None
    experience_level: str | None = None
    parse_confidence: float | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime