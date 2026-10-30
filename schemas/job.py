from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=20)
    location: str | None = Field(default=None, max_length=150)
    remote_policy: str | None = Field(default=None, max_length=50)
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    required_experience_years: float | None = Field(default=None, ge=0)
    experience_level: str | None = Field(default=None, max_length=50)
    required_education: str | None = Field(default=None, max_length=150)
    openings: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_salary_range(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError(
                "salary_min cannot exceed salary_max"
            )
        return self


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=20)
    location: str | None = Field(default=None, max_length=150)
    remote_policy: str | None = Field(default=None, max_length=50)
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    required_experience_years: float | None = Field(default=None, ge=0)
    experience_level: str | None = Field(default=None, max_length=50)
    required_education: str | None = Field(default=None, max_length=150)
    openings: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_salary_range(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError(
                "salary_min cannot exceed salary_max"
            )
        return self


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    created_by: int
    title: str
    description: str
    # Populated by the jobs API from job.company.name.
    company_name: str | None = None
    location: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    required_experience_years: float | None = None
    experience_level: str | None = None
    required_education: str | None = None
    status: str
    openings: int
    created_at: datetime
    updated_at: datetime
