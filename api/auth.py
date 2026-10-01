from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.dependencies import get_current_user, require_role

from constants.roles import UserRole
from core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from db.database import get_db
from db.models.company import Company
from db.models.hr_user import HRUser
from db.models.student import Student
from db.models.user import User
from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)



# =============================================================
# REGISTER
# =============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Check whether email already exists
    # ---------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    # ---------------------------------------------------------
    # 2. Validate HR-specific requirement
    # ---------------------------------------------------------

    if request.role == UserRole.HR and not request.company_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_name is required for HR registration",
        )

    # ---------------------------------------------------------
    # 3. Create User
    # ---------------------------------------------------------

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        role=request.role.value,
        is_active=True,
    )

    db.add(user)
    db.flush()

    # ---------------------------------------------------------
    # 4. Create role-specific profile
    # ---------------------------------------------------------

    if request.role == UserRole.STUDENT:

        student = Student(
            user_id=user.id,
            full_name=request.full_name,
        )

        db.add(student)

    elif request.role == UserRole.HR:

        company = Company(
            name=request.company_name,
        )

        db.add(company)
        db.flush()

        hr_user = HRUser(
            user_id=user.id,
            company_id=company.id,
            full_name=request.full_name,
        )

        db.add(hr_user)

    # ---------------------------------------------------------
    # 5. Commit transaction
    # ---------------------------------------------------------

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

    # ---------------------------------------------------------
    # 6. Return safe user information
    # ---------------------------------------------------------

    return user


# =============================================================
# LOGIN
# =============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Find user by email
    # ---------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    # ---------------------------------------------------------
    # 2. Check email
    # ---------------------------------------------------------

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # ---------------------------------------------------------
    # 3. Verify password
    # ---------------------------------------------------------

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # ---------------------------------------------------------
    # 4. Check whether account is active
    # ---------------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # ---------------------------------------------------------
    # 5. Create JWT access token
    # ---------------------------------------------------------

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
        },
        expires_delta=timedelta(minutes=60),
    )

    # ---------------------------------------------------------
    # 6. Return token
    # ---------------------------------------------------------

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )
    
    # =============================================================
    # CURRENT USER
    # =============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

# =============================================================
# RBAC TEST — STUDENT ONLY
# =============================================================

@router.get("/student-test")
def student_test(
    current_user: User = Depends(
        require_role("STUDENT")
    ),
):
    return {
        "message": "Student access granted",
        "user_id": current_user.id,
        "role": current_user.role,
    }


# =============================================================
# RBAC TEST — HR ONLY
# =============================================================

@router.get("/hr-test")
def hr_test(
    current_user: User = Depends(
        require_role("HR")
    ),
):
    return {
        "message": "HR access granted",
        "user_id": current_user.id,
        "role": current_user.role,
    }