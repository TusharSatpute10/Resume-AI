from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class JobSkillCreate(BaseModel):
    skill_id: int = Field(gt=0)
    requirement_type: Literal["REQUIRED", "PREFERRED"] = "REQUIRED"
    minimum_years: float | None = Field(default=None, ge=0, le=50)
    importance_weight: float | None = Field(default=1.0, ge=0, le=1)


class JobSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    skill_id: int
    requirement_type: str
    minimum_years: float | None
    importance_weight: float | None


class JobSkillDetailResponse(JobSkillResponse):
    skill_name: str
    skill_category: str | None = None