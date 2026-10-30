from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from constants.roles import UserRole
from core.dependencies import require_role
from db.database import get_db
from db.models.hr_user import HRUser
from db.models.user import User
from schemas.hr import HRProfileResponse


router = APIRouter(
    prefix="/hr",
    tags=["HR"],
)


@router.get(
    "/me",
    response_model=HRProfileResponse,
)
def get_my_hr_profile(
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    hr_profile = (
        db.query(HRUser)
        .filter(HRUser.user_id == current_user.id)
        .first()
    )

    if not hr_profile:
        raise HTTPException(
            status_code=404,
            detail="HR profile not found",
        )

    return hr_profile