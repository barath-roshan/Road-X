"""Unit tests for database connection, session creation, and transaction rollbacks."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.user import User, UserRole
from backend.repositories.user_repository import UserRepository


def test_database_connection_and_session(db_session: Session):
    """Test basic database connection and session creation."""
    assert db_session is not None
    assert db_session.is_active is True


def test_transaction_rollback_on_error(db_session: Session):
    """Test that failed database transactions roll back cleanly."""
    repo = UserRepository(db_session)
    user1 = User(name="User 1", email="duplicate@example.com", role=UserRole.CITIZEN)
    repo.add(user1)

    # Attempt adding duplicate email
    user2 = User(name="User 2", email="duplicate@example.com", role=UserRole.CITIZEN)
    with pytest.raises(Exception):
        repo.add(user2)

    # Verify database session remains valid and original user exists
    found = repo.get_by_email("duplicate@example.com")
    assert found is not None
    assert found.name == "User 1"
