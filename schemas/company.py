from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    location: str | None = None
    created_at: datetime


class CompanyUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    website: HttpUrl | None = None
    industry: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=150)