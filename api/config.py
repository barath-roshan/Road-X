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
