from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from constants.roles import UserRole
from core.dependencies import require_role
from db.database import get_db
from db.models.company import Company
from db.models.hr_user import HRUser
from db.models.user import User
from schemas.company import CompanyResponse, CompanyUpdate


router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


def get_current_hr_company(
    current_user: User,
    db: Session,
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

    company = (
        db.query(Company)
        .filter(Company.id == hr_profile.company_id)
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company


@router.get(
    "/me",
    response_model=CompanyResponse,
)
def get_my_company(
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    return get_current_hr_company(current_user, db)


@router.patch(
    "/me",
    response_model=CompanyResponse,
)
def update_my_company(
    company_data: CompanyUpdate,
    current_user: User = Depends(
        require_role(UserRole.HR.value)
    ),
    db: Session = Depends(get_db),
):
    company = get_current_hr_company(current_user, db)

    try:
        update_data = company_data.model_dump(
            exclude_unset=True,
        )

        # Convert Pydantic's HttpUrl value to a normal string.
        if "website" in update_data:
            website = update_data["website"]

            update_data["website"] = (
                str(website) if website is not None else None
            )

        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to update company",
        )

    return company