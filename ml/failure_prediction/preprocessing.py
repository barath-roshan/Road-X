"""Data preprocessing utilities for road failure prediction."""

from __future__ import annotations

from typing import Any, Dict, List
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger
from ml.failure_prediction.schemas import RoadGrievanceInput

logger = get_logger("failure_prediction.preprocessing")


class FailureDataPreprocessor:
    """Preprocesses raw grievance records and sensor/context signals for failure prediction."""

    def __init__(self) -> None:
        self._is_initialized = True

    def validate_record(self, record: RoadGrievanceInput) -> None:
        """Validate geographic bounds and realistic numerical ranges.

        Raises:
            RoadXDataError: If coordinates or measurements are physically invalid.
        """
        if not (-90.0 <= record.latitude <= 90.0):
            raise RoadXDataError(f"Invalid latitude: {record.latitude}")
        if not (-180.0 <= record.longitude <= 180.0):
            raise RoadXDataError(f"Invalid longitude: {record.longitude}")
        if record.estimated_depth_cm is not None and record.estimated_depth_cm < 0:
            raise RoadXDataError(f"Negative depth provided: {record.estimated_depth_cm}")
        if record.estimated_area_sqm is not None and record.estimated_area_sqm < 0:
            raise RoadXDataError(f"Negative area provided: {record.estimated_area_sqm}")

    def clean_record(self, record: RoadGrievanceInput) -> Dict[str, Any]:
        """Convert validated grievance schema to a standardized dictionary."""
        self.validate_record(record)
        return record.model_dump()
