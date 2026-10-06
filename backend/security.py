"""Actor Context and Role-Based Authorization enforcement layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from backend.models.user import UserRole
from ml.common.exceptions import RoadXDataError


class UnauthorizedError(RoadXDataError):
    """Raised when an actor lacks administrative authorization for a business operation."""

    def __init__(self, message: str = "Actor is not authorized to perform this operation.") -> None:
        super().__init__(message)


class InvalidStateTransitionError(RoadXDataError):
    """Raised when a lifecycle status transition violates workflow rules."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass
class UserContext:
    """Actor context container holding user identifier and assigned role."""

    user_id: Optional[str]
    role: UserRole

    def require_role(self, expected_role: UserRole) -> None:
        """Enforce exact actor role or raise UnauthorizedError."""
        if self.role != expected_role:
            raise UnauthorizedError(
                f"Role '{self.role.value}' is not authorized. Operation requires '{expected_role.value}'."
            )

    def is_government_officer(self) -> bool:
        """Check if active actor is a government officer."""
        return self.role == UserRole.GOVERNMENT_OFFICER

    def is_contractor(self) -> bool:
        """Check if active actor is a contractor."""
        return self.role == UserRole.CONTRACTOR

    def is_citizen(self) -> bool:
        """Check if active actor is a citizen."""
        return self.role == UserRole.CITIZEN
