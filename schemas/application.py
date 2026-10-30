from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


ApplicationStatus = Literal[
    "APPLIED",
    "UNDER_REVIEW",
    "SHORTLISTED",
    "INTERVIEW_SCHEDULED",
    "REJECTED",
    "HIRED",
]


class ApplicationCreate(BaseModel):
    resume_id: int


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    job_id: int
    resume_id: int
    status: str
    applied_at: datetime
    updated_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicantResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_email: str
    resume_id: int
    status: str
    applied_at: datetime
    updated_at: datetime