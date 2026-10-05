"""Centralized logging configuration for RoadX ML subsystem."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from ml.common.config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Configure and return root logger for RoadX ML.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to write file logs.

    Returns:
        Configured root logger for RoadX.
    """
    level_name = (log_level or settings.log_level).upper()
    numeric_level = getattr(logging, level_name, logging.INFO)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger("roadx")
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Obtain a child logger under the 'roadx' namespace.

    Args:
        name: Name of module or component requesting logger.

    Returns:
        logging.Logger instance.
    """
    if name.startswith("roadx."):
        return logging.getLogger(name)
    return logging.getLogger(f"roadx.{name}")
