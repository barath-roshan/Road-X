"""Configuration management for RoadX ML subsystem."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Automatically load environment variables from .env if present
load_dotenv()


def _resolve_project_root() -> Path:
    """Dynamically determine the root directory of the RoadX repository."""
    env_root = os.getenv("ROADX_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # ml/common/config.py -> parents[2] is the project root
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    """RoadX system paths and environment configuration."""

    project_root: Path = field(default_factory=_resolve_project_root)
    env: str = field(default_factory=lambda: os.getenv("ROADX_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("ROADX_LOG_LEVEL", "INFO"))

    data_dir: Path = field(init=False)
    raw_data_dir: Path = field(init=False)
    processed_data_dir: Path = field(init=False)
    external_data_dir: Path = field(init=False)
    models_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        """Resolve and assign all core directory paths relative to project root or environment."""
        env_data = os.getenv("ROADX_DATA_DIR")
        self.data_dir = Path(env_data).resolve() if env_data else self.project_root / "data"

        self.raw_data_dir = self.data_dir / "raw"
        self.processed_data_dir = self.data_dir / "processed"
        self.external_data_dir = self.data_dir / "external"

        env_models = os.getenv("ROADX_MODELS_DIR")
        self.models_dir = Path(env_models).resolve() if env_models else self.project_root / "models"

        env_logs = os.getenv("ROADX_LOGS_DIR")
        self.logs_dir = Path(env_logs).resolve() if env_logs else self.project_root / "logs"

    def ensure_directories(self) -> None:
        """Create required runtime directories if they do not already exist."""
        for directory in [
            self.data_dir,
            self.raw_data_dir,
            self.processed_data_dir,
            self.external_data_dir,
            self.models_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Global singleton instance for application use
settings = Settings()
