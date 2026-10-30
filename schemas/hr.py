from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HRProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_id: int
    full_name: str
    designation: str | None = None
    created_at: datetime