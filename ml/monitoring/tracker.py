"""MLflow Experiment Tracker with safe offline fallback for RoadX ML Subsystems (Phase 21)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from ml.common.config import settings
from ml.common.logging_config import get_logger
from ml.monitoring.config import monitoring_config

logger = get_logger("monitoring.tracker")

# Check for MLflow library availability
try:
    import mlflow
    HAS_MLFLOW = True
except ImportError:
    mlflow = None
    HAS_MLFLOW = False


class MLflowTracker:
    """Modular tracking layer for ML experiments, parameters, metrics, and artifact metadata."""

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.tracking_uri = tracking_uri or monitoring_config.mlflow_tracking_uri
        self.experiment_name = experiment_name or monitoring_config.mlflow_experiment_name
        self.enabled = enabled if enabled is not None else monitoring_config.mlflow_enabled
        self.history_file = settings.models_dir / "monitoring" / "experiment_history.json"
        self._is_active = False

        if self.enabled and HAS_MLFLOW:
            self._setup_mlflow()

    def _setup_mlflow(self) -> None:
        """Configure MLflow tracking URI and active experiment name."""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            self._is_active = True
            logger.info("Initialized MLflow tracking at %s (Experiment: %s)", self.tracking_uri, self.experiment_name)
        except Exception as e:
            logger.warning("Failed to initialize MLflow tracking server: %s. Using local fallback.", e)
            self._is_active = False

    def log_experiment(
        self,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        artifacts: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        run_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record parameters, metrics, and metadata for an ML training/evaluation run.

        Returns:
            Dictionary containing run summary and run_id.
        """
        timestamp_str = datetime.now(timezone.utc).isoformat()
        run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Sanitize parameters (convert complex objects to string representations, exclude secrets)
        safe_params = {}
        for k, v in params.items():
            if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
                continue
            safe_params[k] = str(v) if not isinstance(v, (int, float, bool, str)) else v

        # Sanitize metrics
        safe_metrics = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float, np.number))}

        mlflow_run_id = None

        if self._is_active and HAS_MLFLOW:
            try:
                with mlflow.start_run(run_name=run_name or run_id) as active_run:
                    mlflow_run_id = active_run.info.run_id
                    
                    # Log parameters
                    mlflow.log_params(safe_params)

                    # Log metrics
                    mlflow.log_metrics(safe_metrics)

                    # Log tags
                    if tags:
                        mlflow.set_tags(tags)

                    # Log artifacts if dict provided
                    if artifacts:
                        tmp_art_path = settings.models_dir / "monitoring" / f"artifacts_{mlflow_run_id}.json"
                        tmp_art_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(tmp_art_path, "w", encoding="utf-8") as f:
                            json.dump(artifacts, f, indent=2)
                        mlflow.log_artifact(str(tmp_art_path))
                        if tmp_art_path.exists():
                            tmp_art_path.unlink()

                    logger.info("Successfully logged run to MLflow (run_id=%s)", mlflow_run_id)
            except Exception as e:
                logger.error("MLflow logging failed: %s. Saving to local history fallback.", e)

        # Fallback local file persistence
        run_summary = {
            "run_id": mlflow_run_id or run_id,
            "timestamp": timestamp_str,
            "run_name": run_name or run_id,
            "params": safe_params,
            "metrics": safe_metrics,
            "tags": tags or {},
            "mlflow_tracked": self._is_active and mlflow_run_id is not None,
        }

        self._save_local_history(run_summary)
        return run_summary

    def _save_local_history(self, summary: Dict[str, Any]) -> None:
        """Persist run summary to local experiment_history.json."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            history: List[Dict[str, Any]] = []
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

            history.append(summary)

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error("Failed to write local experiment history: %s", e)

    def get_experiment_history(self) -> List[Dict[str, Any]]:
        """Retrieve local recorded experiment history."""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
