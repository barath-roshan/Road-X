"""Database and Backend Configuration Settings for RoadX."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ml.common.config import settings as ml_settings


def _default_db_url() -> str:
    """Resolve default database URL from environment or sqlite fallback."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    
    # Fallback to local SQLite file database for development if PostgreSQL is unconfigured
    sqlite_path = ml_settings.project_root / "data" / "roadx.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path.as_posix()}"


@dataclass
class DatabaseSettings:
    """Configuration container for database parameters."""

    database_url: str = field(default_factory=_default_db_url)
    db_echo: bool = field(
        default_factory=lambda: os.getenv("ROADX_DB_ECHO", "false").lower() in ("true", "1")
    )
    db_pool_size: int = field(
        default_factory=lambda: int(os.getenv("ROADX_DB_POOL_SIZE", "5"))
    )
    db_max_overflow: int = field(
        default_factory=lambda: int(os.getenv("ROADX_DB_MAX_OVERFLOW", "10"))
    )

    @property
    def is_sqlite(self) -> bool:
        """Check whether active connection is SQLite."""
        return self.database_url.startswith("sqlite")


db_settings = DatabaseSettings()


@dataclass
class NotificationSettings:
    """Configuration container for Notification & Twilio SMS parameters."""

    notifications_enabled: bool = field(
        default_factory=lambda: os.getenv("NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1")
    )
    twilio_enabled: bool = field(
        default_factory=lambda: os.getenv("TWILIO_ENABLED", "false").lower() in ("true", "1")
    )
    twilio_account_sid: str | None = field(
        default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID")
    )
    twilio_auth_token: str | None = field(
        default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN")
    )
    twilio_phone_number: str | None = field(
        default_factory=lambda: os.getenv("TWILIO_PHONE_NUMBER")
    )


notification_settings = NotificationSettings()

