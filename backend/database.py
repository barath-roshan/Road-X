"""SQLAlchemy 2.x Database Engine, Session Factory, and Dependency Providers."""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import db_settings
from ml.common.logging_config import get_logger

logger = get_logger("backend.database")


class Base(DeclarativeBase):
    """Base declarative class for all RoadX SQLAlchemy models."""

    pass


def create_db_engine(custom_url: str | None = None):
    """Create SQLAlchemy engine with environment-appropriate parameters."""
    url = custom_url or db_settings.database_url
    kwargs = {"echo": db_settings.db_echo}

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = db_settings.db_pool_size
        kwargs["max_overflow"] = db_settings.db_max_overflow

    logger.info("Initializing SQLAlchemy engine with URL scheme: %s", url.split("://")[0])
    return create_engine(url, **kwargs)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency Provider producing an isolated database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
