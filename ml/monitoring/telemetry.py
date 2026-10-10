"""Inference Operational Telemetry and Monitoring Instrumentation (Phase 21).

Collects operational metrics for inference requests (latency, success/failure counts,
model versions, validation errors, prediction distributions) without leaking
sensitive user data or high-cardinality identifiers.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

import numpy as np

from ml.common.logging_config import get_logger

logger = get_logger("monitoring.telemetry")


class InferenceTelemetry:
    """Thread-safe operational telemetry collector for model inference services."""

    _instance: Optional["InferenceTelemetry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "InferenceTelemetry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self) -> None:
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.validation_failures = 0
        self.model_inferences: Dict[str, int] = {}
        self.prediction_distribution: Dict[str, int] = {}
        self.latencies_ms: Deque[float] = deque(maxlen=2000)
        self.last_inference_time: Optional[str] = None

    def record_inference(
        self,
        latency_ms: float,
        success: bool = True,
        model_id: str = "spatiotemporal_xgb",
        model_version: str = "v1.0",
        prediction_label: Optional[str] = None,
        is_validation_failure: bool = False,
    ) -> None:
        """Safely record an inference invocation metrics event.

        Strictly avoids high-cardinality labels (citizen IDs, request IDs, images).
        Never throws exceptions that could disrupt caller execution.
        """
        try:
            with self.lock:
                self.total_requests += 1
                self.last_inference_time = datetime.now(timezone.utc).isoformat()

                if is_validation_failure:
                    self.validation_failures += 1

                if success:
                    self.successful_requests += 1
                else:
                    self.failed_requests += 1

                # Record latency
                if latency_ms >= 0:
                    self.latencies_ms.append(float(latency_ms))

                # Track model version invocation count
                model_key = f"{model_id}:{model_version}"
                self.model_inferences[model_key] = self.model_inferences.get(model_key, 0) + 1

                # Track prediction distribution if categorical/binned
                if prediction_label is not None:
                    label_str = str(prediction_label)
                    self.prediction_distribution[label_str] = (
                        self.prediction_distribution.get(label_str, 0) + 1
                    )
        except Exception as e:
            # Observability telemetry must NEVER disrupt caller inference
            logger.warning("Telemetry recording failed non-fatally: %s", e)

    def get_metrics(self) -> Dict[str, Any]:
        """Aggregate and return current operational metrics summary."""
        with self.lock:
            latencies = list(self.latencies_ms)
            uptime_seconds = round(time.time() - self.start_time, 2)

            if latencies:
                avg_latency = float(np.mean(latencies))
                p50_latency = float(np.percentile(latencies, 50))
                p95_latency = float(np.percentile(latencies, 95))
                p99_latency = float(np.percentile(latencies, 99))
                min_latency = float(np.min(latencies))
                max_latency = float(np.max(latencies))
            else:
                avg_latency = 0.0
                p50_latency = 0.0
                p95_latency = 0.0
                p99_latency = 0.0
                min_latency = 0.0
                max_latency = 0.0

            success_rate = (
                round((self.successful_requests / self.total_requests) * 100, 2)
                if self.total_requests > 0
                else 100.0
            )

            return {
                "started_at": self.started_at,
                "uptime_seconds": uptime_seconds,
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "validation_failures": self.validation_failures,
                "success_rate_pct": success_rate,
                "latency_metrics": {
                    "sample_size": len(latencies),
                    "avg_ms": round(avg_latency, 2),
                    "p50_ms": round(p50_latency, 2),
                    "p95_ms": round(p95_latency, 2),
                    "p99_ms": round(p99_latency, 2),
                    "min_ms": round(min_latency, 2),
                    "max_ms": round(max_latency, 2),
                },
                "model_inferences": dict(self.model_inferences),
                "prediction_distribution": dict(self.prediction_distribution),
                "last_inference_time": self.last_inference_time,
            }

    def reset(self) -> None:
        """Reset internal metrics counters (primarily used for unit testing)."""
        with self.lock:
            self._init_state()


# Global telemetry singleton
telemetry = InferenceTelemetry()
