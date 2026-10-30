from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


InterviewType = Literal["ONLINE", "OFFLINE"]
InterviewStatus = Literal["SCHEDULED", "CANCELLED", "COMPLETED"]
MeetingLinkStatus = Literal["PENDING", "AVAILABLE"]


class InterviewCreate(BaseModel):
    application_id: int = Field(gt=0)

    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)

    round_name: str = Field(
        default="Technical Round",
        min_length=2,
        max_length=100,
    )

    interview_type: InterviewType

    meeting_link: str | None = Field(default=None, max_length=500)
    venue: str | None = Field(default=None, max_length=500)
    instructions: str | None = None

    @model_validator(mode="after")
    def validate_interview_details(self):
        if self.scheduled_at <= datetime.now(
            self.scheduled_at.tzinfo
        ):
            raise ValueError("Interview must be scheduled in the future.")

        if self.interview_type == "ONLINE" and self.venue:
            raise ValueError("Online interviews should not have a venue.")

        if self.interview_type == "OFFLINE" and self.meeting_link:
            raise ValueError("Offline interviews should not have a meeting link.")

        return self


class BulkInterviewCreate(BaseModel):
    interviews: list[InterviewCreate] = Field(
        min_length=1,
        max_length=100,
    )


class InterviewUpdate(BaseModel):
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    round_name: str | None = Field(default=None, min_length=2, max_length=100)
    interview_type: InterviewType | None = None
    meeting_link: str | None = Field(default=None, max_length=500)
    venue: str | None = Field(default=None, max_length=500)
    instructions: str | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.scheduled_at is not None:
            if self.scheduled_at <= datetime.now(
                self.scheduled_at.tzinfo
            ):
                raise ValueError("Interview must be scheduled in the future.")

        if self.interview_type == "ONLINE" and self.venue:
            raise ValueError("Online interviews should not have a venue.")

        if self.interview_type == "OFFLINE" and self.meeting_link:
            raise ValueError("Offline interviews should not have a meeting link.")

        return self


class MeetingLinkUpdate(BaseModel):
    meeting_link: str = Field(min_length=5, max_length=500)


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    scheduled_by: int

    scheduled_at: datetime
    duration_minutes: int
    round_name: str

    interview_type: str
    meeting_link: str | None
    meeting_link_status: str

    venue: str | None
    instructions: str | None

    status: str
    feedback: str | None
    cancelled_at: datetime | None

    created_at: datetime
    updated_at: datetime

    student_name: str | None = None
    student_email: str | None = None

    job_title: str | None = None
    company_name: str | None = None


class InterviewActionResponse(BaseModel):
    message: str
    interview: InterviewResponse