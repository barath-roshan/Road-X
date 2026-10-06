"""Business logic service for User management."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.schemas.user import UserCreate, UserUpdate
from ml.common.exceptions import RoadXDataError


class UserService:
    """UserService managing user validation and persistence business rules."""

    def __init__(self, db: Session) -> None:
        self.user_repo = UserRepository(db)

    def create_user(self, payload: UserCreate) -> User:
        """Create a new user ensuring unique email address."""
        existing = self.user_repo.get_by_email(payload.email)
        if existing:
            raise RoadXDataError(f"User with email '{payload.email}' already exists.")

        user = User(
            name=payload.name.strip(),
            email=payload.email.strip().lower(),
            phone=payload.phone.strip() if payload.phone else None,
            role=payload.role,
        )
        return self.user_repo.add(user)

    def get_user(self, user_id: str) -> User:
        """Retrieve user by UUID or raise error if not found."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise RoadXDataError(f"User with ID '{user_id}' not found.")
        return user

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List active platform users."""
        return self.user_repo.list_all(skip=skip, limit=limit)
