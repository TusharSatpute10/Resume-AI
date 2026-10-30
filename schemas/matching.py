from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    resume_id: int

    semantic_score: float | None = None
    skill_score: float | None = None
    experience_score: float | None = None
    education_score: float | None = None
    project_score: float | None = None

    final_score: float | None = None
    rank: int | None = None

    matched_skills: list = Field(default_factory=list)
    missing_skills: list = Field(default_factory=list)

    explanation: str | None = None
    model_version: str | None = None
    created_at: datetime


class RankedCandidateResponse(MatchResultResponse):
    student_name: str
    resume_file_name: str