"""ComplaintAnalyzer orchestrator service for RoadX Complaint Intelligence (Phase 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, Dict, Any
import numpy as np

from ml.common.exceptions import ModelNotFittedError, ModelArtifactNotFoundError
from ml.complaint_intelligence.config import config
from ml.complaint_intelligence.preprocessing import ComplaintPreprocessor
from ml.complaint_intelligence.features import ComplaintFeatureExtractor
from ml.complaint_intelligence.location_extractor import LocationExtractor
from ml.complaint_intelligence.classifiers import IssueClassifier, UrgencyClassifier, SafetyRiskClassifier
from ml.complaint_intelligence.embedder import ComplaintEmbedder
from ml.complaint_intelligence.schemas import (
    ComplaintAnalysisRequest,
    ComplaintAnalysisResponse,
    IssueCategory,
    UrgencyLevel,
    SafetyRiskLevel,
    LocationMention,
)


class ComplaintAnalyzer:
    """Orchestrates natural language complaint processing, location extraction, multi-dimensional

    classification, and semantic embedding generation.
    """

    def __init__(
        self,
        preprocessor: Optional[ComplaintPreprocessor] = None,
        feature_extractor: Optional[ComplaintFeatureExtractor] = None,
        issue_classifier: Optional[IssueClassifier] = None,
        urgency_classifier: Optional[UrgencyClassifier] = None,
        safety_classifier: Optional[SafetyRiskClassifier] = None,
        location_extractor: Optional[LocationExtractor] = None,
        embedder: Optional[ComplaintEmbedder] = None,
        version: str = "v1",
    ) -> None:
        self.preprocessor = preprocessor or ComplaintPreprocessor()
        self.feature_extractor = feature_extractor or ComplaintFeatureExtractor()
        self.issue_classifier = issue_classifier or IssueClassifier(version=version)
        self.urgency_classifier = urgency_classifier or UrgencyClassifier(version=version)
        self.safety_classifier = safety_classifier or SafetyRiskClassifier(version=version)
        self.location_extractor = location_extractor or LocationExtractor()
        self.embedder = embedder or ComplaintEmbedder(
            feature_extractor=self.feature_extractor,
            embedding_dim=config.embedding_dim,
        )
        self.version = version

    @property
    def is_fitted(self) -> bool:
        """Returns True if feature extractor and all classifiers are fitted."""
        return (
            self.feature_extractor.is_fitted
            and self.issue_classifier.is_fitted
            and self.urgency_classifier.is_fitted
            and self.safety_classifier.is_fitted
        )

    def analyze(self, text: str) -> ComplaintAnalysisResponse:
        """Analyze citizen complaint text and return structured analysis response.

        Args:
            text: Raw or clean citizen complaint text.

        Returns:
            ComplaintAnalysisResponse validated Pydantic model.
        """
        # Validate request payload
        req = ComplaintAnalysisRequest(text=text)

        if not self.is_fitted:
            raise ModelNotFittedError(
                "ComplaintAnalyzer models are not trained or loaded. Call load() or train models first."
            )

        # 1. Text Preprocessing
        clean_text = self.preprocessor.clean_text(req.text)

        # 2. Location Mention Extraction
        location_mentions = self.location_extractor.extract_locations(clean_text)

        # 3. Feature Vectorization
        features = self.feature_extractor.transform([clean_text])

        # 4. Issue Category Prediction
        issue_label, issue_conf = self.issue_classifier.predict_with_confidence(features)[0]

        # 5. Urgency Level Prediction
        urgency_label, urgency_conf = self.urgency_classifier.predict_with_confidence(features)[0]

        # 6. Safety Risk Prediction
        safety_label, safety_conf = self.safety_classifier.predict_with_confidence(features)[0]

        # 7. Semantic Embedding Available Flag
        embedding_vec = self.embed(req.text)
        embedding_available = embedding_vec is not None and len(embedding_vec) > 0

        return ComplaintAnalysisResponse(
            issue_category=IssueCategory(issue_label),
            issue_confidence=issue_conf,
            urgency=UrgencyLevel(urgency_label),
            urgency_confidence=urgency_conf,
            safety_risk=SafetyRiskLevel(safety_label),
            safety_confidence=safety_conf,
            location_mentions=location_mentions,
            embedding_available=embedding_available,
            model_version=self.version,
        )

    def embed(self, text: str) -> np.ndarray:
        """Generate semantic embedding vector for downstream consumption (Phase 6)."""
        return self.embedder.embed(text)

    def save(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        """Save all component models and artifacts to model directory."""
        if not self.is_fitted:
            raise ModelNotFittedError("Cannot save un-fitted ComplaintAnalyzer pipeline.")

        target_dir = Path(model_dir or config.model_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        self.feature_extractor.save(target_dir / "vectorizer.joblib")
        self.issue_classifier.save(target_dir / "issue_classifier" / "model.joblib")
        self.urgency_classifier.save(target_dir / "urgency_classifier" / "model.joblib")
        self.safety_classifier.save(target_dir / "safety_classifier" / "model.joblib")

    @classmethod
    def load(cls, model_dir: Optional[Union[str, Path]] = None) -> ComplaintAnalyzer:
        """Load fitted pipeline artifacts from model directory."""
        target_dir = Path(model_dir or config.model_dir)
        vec_path = target_dir / "vectorizer.joblib"
        issue_path = target_dir / "issue_classifier" / "model.joblib"
        urgency_path = target_dir / "urgency_classifier" / "model.joblib"
        safety_path = target_dir / "safety_classifier" / "model.joblib"

        if not vec_path.exists():
            raise ModelArtifactNotFoundError(f"Feature vectorizer artifact missing at {vec_path}")

        feature_extractor = ComplaintFeatureExtractor.load(vec_path)
        issue_classifier = IssueClassifier.load(issue_path)
        urgency_classifier = UrgencyClassifier.load(urgency_path)
        safety_classifier = SafetyRiskClassifier.load(safety_path)
        location_extractor = LocationExtractor()
        embedder = ComplaintEmbedder(feature_extractor=feature_extractor, embedding_dim=config.embedding_dim)

        return cls(
            feature_extractor=feature_extractor,
            issue_classifier=issue_classifier,
            urgency_classifier=urgency_classifier,
            safety_classifier=safety_classifier,
            location_extractor=location_extractor,
            embedder=embedder,
            version=issue_classifier.version,
        )
