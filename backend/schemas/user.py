"""Pydantic schemas for User actor entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.models.user import UserRole


class UserBase(BaseModel):
    """Base fields for User payload."""

    name: str = Field(min_length=1, max_length=100, description="Full name of user")
    email: EmailStr = Field(description="Unique email address")
    phone: Optional[str] = Field(default=None, max_length=30, description="Contact phone number")
    role: UserRole = Field(default=UserRole.CITIZEN, description="Assigned administrative role")


class UserCreate(UserBase):
    """Request schema for creating a user."""

    pass


class UserUpdate(BaseModel):
    """Request schema for updating a user."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class UserRead(UserBase):
    """Response schema for User entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique UUID string identifier")
    is_active: bool = Field(description="Active account status flag")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
