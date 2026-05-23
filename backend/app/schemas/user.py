"""User Pydantic schemas."""

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$")
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class UserInfo(BaseModel):
    """Schema for current user info."""

    id: int
    username: str
