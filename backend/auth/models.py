"""
Auth-related database model and Pydantic schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel


# ── DB Table ──────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    id:              Optional[int] = Field(default=None, primary_key=True)
    email:           str           = Field(unique=True, index=True)
    name:            str
    hashed_password: str
    plan:            str           = Field(default="starter")   # starter | growth | enterprise
    is_active:       bool          = Field(default=True)
    created_at:      datetime      = Field(default_factory=datetime.utcnow)


# ── Request / Response schemas ────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Register a new user."""
    email:    str
    name:     str
    password: str
    plan:     str = "starter"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("plan")
    @classmethod
    def plan_valid(cls, v: str) -> str:
        if v not in ("starter", "growth", "enterprise"):
            return "starter"
        return v


class LoginRequest(BaseModel):
    """Login with email + password."""
    email:    str
    password: str


class UserRead(BaseModel):
    """Public user profile returned in API responses."""
    id:         int
    email:      str
    name:       str
    plan:       str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type:   str = "bearer"
    user:         UserRead
