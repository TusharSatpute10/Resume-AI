from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.roles import UserRole
from core.dependencies import get_current_user, require_role
from db.database import get_db
from db.models.student import Student
from db.models.user import User
from schemas.student import (
    StudentProfileResponse,
    StudentProfileUpdate,
)


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


# =============================================================
# GET CURRENT STUDENT PROFILE
# =============================================================

@router.get(
    "/me",
    response_model=StudentProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    return student


# =============================================================
# UPDATE CURRENT STUDENT PROFILE
# =============================================================

@router.put(
    "/me",
    response_model=StudentProfileResponse,
)
def update_my_profile(
    request: StudentProfileUpdate,
    current_user: User = Depends(
        require_role(UserRole.STUDENT.value)
    ),
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    # ---------------------------------------------------------
    # Update allowed profile fields
    # ---------------------------------------------------------

    student.full_name = request.full_name
    student.phone = request.phone
    student.location = request.location
    student.linkedin_url = request.linkedin_url
    student.github_url = request.github_url
    student.portfolio_url = request.portfolio_url
    student.headline = request.headline
    student.bio = request.bio

    db.commit()
    db.refresh(student)

    return student