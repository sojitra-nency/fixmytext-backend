"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password (8-128 chars)"
    )
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="Display name"
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(
        False, description="Persist session across browser restarts"
    )


class TokenResponse(BaseModel):
    """Response containing a JWT access token."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105


class UserResponse(BaseModel):
    """Response containing the authenticated user's profile."""

    id: str
    email: str
    display_name: str
    subscription_tier: str = "free"
