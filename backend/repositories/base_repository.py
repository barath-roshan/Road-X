"""Base repository class providing session & transaction capabilities."""

from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session

from backend.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing core CRUD operations and transaction safety."""

    def __init__(self, model: Type[ModelType], db: Session) -> None:
        self.model = model
        self.db = db

    def get_by_id(self, id_val: str) -> Optional[ModelType]:
        """Fetch model entity by primary key string."""
        return self.db.query(self.model).filter(self.model.id == id_val).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """List model entities with offset pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def add(self, instance: ModelType) -> ModelType:
        """Add new entity instance to session and commit."""
        try:
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, instance: ModelType) -> ModelType:
        """Commit updates to an existing instance."""
        try:
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, instance: ModelType) -> None:
        """Delete instance from session and commit."""
        try:
            self.db.delete(instance)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
