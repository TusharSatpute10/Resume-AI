from pydantic import BaseModel, EmailStr, Field

from constants.roles import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    full_name: str = Field(min_length=2, max_length=150)

    # Required when role is HR
    company_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool