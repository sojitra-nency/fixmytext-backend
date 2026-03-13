"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="User email")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 chars)")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Persist session across browser restarts")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
