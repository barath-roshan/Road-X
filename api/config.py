"""Configuration settings for RoadX FastAPI Service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from ml.common.config import settings as ml_settings


@dataclass
class APISettings:
    """FastAPI Service configuration parameters."""

    app_name: str = "RoadX ML Service"
    app_description: str = (
        "Production-grade FastAPI inference service for RoadX Unified ML Pipeline."
    )
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    env: str = field(default_factory=lambda: os.getenv("ROADX_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("ROADX_LOG_LEVEL", "INFO"))

    # CORS Settings
    cors_allowed_origins: List[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
            ).split(",")
            if origin.strip()
        ]
    )

    # Image Upload Validation Constraints
    max_image_size_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))
    )
    allowed_image_content_types: List[str] = field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    )


api_settings = APISettings()


def _is_placeholder(value: str | None) -> bool:
    """Check if a credential contains missing, whitespace, or template placeholder text."""
    if not value or not value.strip():
        return True
    val_lower = value.strip().lower()
    return "placeholder" in val_lower or val_lower.startswith("your_") or val_lower in ("changeme", "secret", "none")


def validate_startup_configuration() -> List[str]:
    """Audit startup configuration for production readiness and security guidelines.

    Returns:
        List of warning/advisory messages. Never raises fatal errors or leaks secrets.
    """
    warnings: List[str] = []

    # 1. CORS audit
    if "*" in api_settings.cors_allowed_origins:
        warnings.append("CORS_ALLOWED_ORIGINS contains wildcard (*). Restrict to specific domains in production.")

    # 2. Database audit
    try:
        from backend.config import db_settings
        if api_settings.env == "production" and db_settings.is_sqlite:
            warnings.append(
                "ROADX_ENV is set to production but DATABASE_URL is SQLite. "
                "PostgreSQL is strongly recommended for production deployments."
            )
    except Exception:
        pass

    # 3. Notification & Twilio audit
    try:
        from backend.config import notification_settings
        if notification_settings.twilio_enabled:
            if _is_placeholder(notification_settings.twilio_account_sid) or _is_placeholder(notification_settings.twilio_auth_token):
                warnings.append(
                    "TWILIO_ENABLED is true but TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing or contains an unconfigured placeholder. "
                    "SMS delivery will fail."
                )
    except Exception:
        pass

    # 4. LLM provider audit
    try:
        from backend.config import chatbot_settings
        if chatbot_settings.llm_provider != "mock" and _is_placeholder(chatbot_settings.llm_api_key):
            warnings.append(
                f"ROADX_LLM_PROVIDER is set to '{chatbot_settings.llm_provider}' but ROADX_LLM_API_KEY is unset or contains an unconfigured placeholder. "
                "Chatbot will fall back to offline responses."
            )
    except Exception:
        pass

    return warnings
