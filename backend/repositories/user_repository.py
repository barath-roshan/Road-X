"""Repository for User entity persistence operations."""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """UserRepository managing User database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by unique email address."""
        return self.db.query(User).filter(User.email == email.strip().lower()).first()
