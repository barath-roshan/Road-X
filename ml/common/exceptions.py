"""Custom exception hierarchy for RoadX ML subsystem."""


class RoadXError(Exception):
    """Base exception for all RoadX ML errors."""


class RoadXConfigError(RoadXError):
    """Raised when configuration validation or path resolution fails."""


class RoadXDataError(RoadXError):
    """Raised when data loading, schema validation, or preprocessing fails."""


class RoadXModelError(RoadXError):
    """Base exception for model training, inference, and serialization errors."""


class ModelNotFittedError(RoadXModelError):
    """Raised when inference is attempted on an un-fitted or un-initialized model."""


class ModelArtifactNotFoundError(RoadXModelError):
    """Raised when required model checkpoint/weights artifacts cannot be located."""
