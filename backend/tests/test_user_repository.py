"""Unit tests for UserRepository and UserService."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.user import UserRole
from backend.schemas.user import UserCreate
from backend.services.user_service import UserService
from ml.common.exceptions import RoadXDataError


def test_create_and_get_user(db_session: Session):
    """Test creating user and retrieving by ID or email."""
    service = UserService(db_session)
    payload = UserCreate(
        name="Aarav Sharma",
        email="aarav@example.com",
        phone="+919876543210",
        role=UserRole.CITIZEN,
    )
    user = service.create_user(payload)

    assert user.id is not None
    assert user.name == "Aarav Sharma"
    assert user.email == "aarav@example.com"
    assert user.role == UserRole.CITIZEN

    retrieved = service.get_user(user.id)
    assert retrieved.id == user.id


def test_duplicate_user_email_raises_error(db_session: Session):
    """Test creating user with duplicate email raises RoadXDataError."""
    service = UserService(db_session)
    payload = UserCreate(name="Officer Ramesh", email="ramesh@roadx.gov.in", role=UserRole.GOVERNMENT_OFFICER)
    service.create_user(payload)

    with pytest.raises(RoadXDataError, match="already exists"):
        service.create_user(payload)
