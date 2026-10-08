"""Road Operation Service managing government lifecycle execution, citizen public visibility, detours, and audit tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance
from backend.models.road import RoadSegment
from backend.models.road_operation import (
    RoadOperation,
    RoadOperationEvent,
    RoadOperationStatus,
    RoadOperationType,
)
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder
from backend.repositories.grievance_repository import GrievanceRepository
from backend.repositories.road_operation_repository import RoadOperationRepository
from backend.repositories.road_repository import RoadRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.work_order_repository import WorkOrderRepository
from backend.schemas.road_operation import (
    CitizenRoadOperationRead,
    GovernmentRoadOperationRead,
    RoadOperationCreate,
    RoadOperationEventRead,
    RoadOperationUpdate,
)
from backend.security import UserContext, UnauthorizedError, InvalidStateTransitionError
from backend.services.state_machine import RoadOperationStateMachine
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.road_operation")


class RoadOperationService:
    """Service coordinating municipal road operations, closures, detours, and citizen visibility."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.operation_repo = RoadOperationRepository(db)
        self.road_repo = RoadRepository(db)
        self.grievance_repo = GrievanceRepository(db)
        self.work_order_repo = WorkOrderRepository(db)
        self.user_repo = UserRepository(db)

    def _verify_government_officer(self, actor: UserContext) -> str:
        """Enforce GOVERNMENT_OFFICER role and return user_id."""
        actor.require_role(UserRole.GOVERNMENT_OFFICER)
        if not actor.user_id:
            raise UnauthorizedError("Actor user_id is missing.")
        return actor.user_id

    def _log_operation_event(
        self,
        operation_id: str,
        actor: UserContext,
        event_type: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> RoadOperationEvent:
        """Create an immutable audit log entry for road operation events."""
        event = RoadOperationEvent(
            operation_id=operation_id,
            actor_id=actor.user_id,
            actor_role=actor.role.value if actor.role else None,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )
        self.db.add(event)
        return event

    def _validate_foreign_keys(
        self,
        road_id: Optional[str] = None,
        grievance_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        alternative_road_id: Optional[str] = None,
    ) -> None:
        """Ensure linked entities exist if IDs are supplied."""
        if road_id:
            if not self.road_repo.get_by_id(road_id):
                raise RoadXDataError(f"Road segment with ID '{road_id}' not found.")
        if grievance_id:
            if not self.grievance_repo.get_by_id(grievance_id):
                raise RoadXDataError(f"Grievance with ID '{grievance_id}' not found.")
        if work_order_id:
            if not self.work_order_repo.get_by_id(work_order_id):
                raise RoadXDataError(f"Work order with ID '{work_order_id}' not found.")
        if alternative_road_id:
            if not self.road_repo.get_by_id(alternative_road_id):
                raise RoadXDataError(f"Alternative road segment with ID '{alternative_road_id}' not found.")

    def create_operation(
        self,
        actor: UserContext,
        payload: RoadOperationCreate,
    ) -> GovernmentRoadOperationRead:
        """Government officer creates a new road operation (closure, restriction, detour)."""
        officer_id = self._verify_government_officer(actor)

        if payload.expected_end_time <= payload.start_time:
            raise RoadXDataError("expected_end_time must be strictly after start_time.")

        self._validate_foreign_keys(
            road_id=payload.road_id,
            grievance_id=payload.grievance_id,
            work_order_id=payload.work_order_id,
            alternative_road_id=payload.alternative_road_id,
        )

        initial_status = payload.status or RoadOperationStatus.PLANNED

        op = RoadOperation(
            road_id=payload.road_id,
            grievance_id=payload.grievance_id,
            work_order_id=payload.work_order_id,
            created_by=officer_id,
            title=payload.title,
            description=payload.description,
            reason=payload.reason,
            operation_type=payload.operation_type,
            status=initial_status,
            start_time=payload.start_time,
            expected_end_time=payload.expected_end_time,
            alternative_route_name=payload.alternative_route_name,
            alternative_route_instructions=payload.alternative_route_instructions,
            alternative_road_id=payload.alternative_road_id,
            alternative_distance_km=payload.alternative_distance_km,
        )
        self.db.add(op)
        self.db.flush()

        self._log_operation_event(
            operation_id=op.id,
            actor=actor,
            event_type="ROAD_OPERATION_CREATED",
            old_status=None,
            new_status=initial_status.value,
            notes=f"Road operation created: '{op.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(op)
            logger.info("Government Officer '%s' created RoadOperation '%s'", officer_id, op.id)
            return self.get_operation_government(actor, op.id)
        except Exception as e:
            self.db.rollback()
            raise e

    def update_operation(
        self,
        actor: UserContext,
        operation_id: str,
        payload: RoadOperationUpdate,
        notes: Optional[str] = None,
    ) -> GovernmentRoadOperationRead:
        """Government officer updates road operation details."""
        self._verify_government_officer(actor)

        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        if op.status in (RoadOperationStatus.COMPLETED, RoadOperationStatus.CANCELLED):
            raise InvalidStateTransitionError(
                f"Cannot update road operation in terminal state '{op.status.value}'."
            )

        start = payload.start_time or op.start_time
        exp_end = payload.expected_end_time or op.expected_end_time
        if exp_end <= start:
            raise RoadXDataError("expected_end_time must be strictly after start_time.")

        self._validate_foreign_keys(
            road_id=payload.road_id,
            grievance_id=payload.grievance_id,
            work_order_id=payload.work_order_id,
            alternative_road_id=payload.alternative_road_id,
        )

        old_status = op.status.value

        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(op, field, value)

        self._log_operation_event(
            operation_id=op.id,
            actor=actor,
            event_type="ROAD_OPERATION_UPDATED",
            old_status=old_status,
            new_status=op.status.value,
            notes=notes or f"Updated operation '{op.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(op)
            logger.info("Updated RoadOperation '%s'", op.id)
            return self.get_operation_government(actor, op.id)
        except Exception as e:
            self.db.rollback()
            raise e

    def activate_operation(
        self,
        actor: UserContext,
        operation_id: str,
        notes: Optional[str] = None,
    ) -> GovernmentRoadOperationRead:
        """Transition road operation to ACTIVE status."""
        self._verify_government_officer(actor)

        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        old_status = op.status
        RoadOperationStateMachine.validate_transition(old_status, RoadOperationStatus.ACTIVE)
        op.status = RoadOperationStatus.ACTIVE

        self._log_operation_event(
            operation_id=op.id,
            actor=actor,
            event_type="ROAD_OPERATION_ACTIVATED",
            old_status=old_status.value,
            new_status=op.status.value,
            notes=notes or f"Activated road operation '{op.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(op)
            logger.info("Activated RoadOperation '%s'", op.id)
            return self.get_operation_government(actor, op.id)
        except Exception as e:
            self.db.rollback()
            raise e

    def complete_operation(
        self,
        actor: UserContext,
        operation_id: str,
        notes: Optional[str] = None,
        actual_end_time: Optional[datetime] = None,
    ) -> GovernmentRoadOperationRead:
        """Transition road operation to COMPLETED status."""
        self._verify_government_officer(actor)

        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        old_status = op.status
        RoadOperationStateMachine.validate_transition(old_status, RoadOperationStatus.COMPLETED)
        op.status = RoadOperationStatus.COMPLETED
        op.actual_end_time = actual_end_time or datetime.now(timezone.utc)

        self._log_operation_event(
            operation_id=op.id,
            actor=actor,
            event_type="ROAD_OPERATION_COMPLETED",
            old_status=old_status.value,
            new_status=op.status.value,
            notes=notes or f"Completed road operation '{op.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(op)
            logger.info("Completed RoadOperation '%s'", op.id)
            return self.get_operation_government(actor, op.id)
        except Exception as e:
            self.db.rollback()
            raise e

    def cancel_operation(
        self,
        actor: UserContext,
        operation_id: str,
        notes: Optional[str] = None,
    ) -> GovernmentRoadOperationRead:
        """Transition road operation to CANCELLED status."""
        self._verify_government_officer(actor)

        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        old_status = op.status
        RoadOperationStateMachine.validate_transition(old_status, RoadOperationStatus.CANCELLED)
        op.status = RoadOperationStatus.CANCELLED

        self._log_operation_event(
            operation_id=op.id,
            actor=actor,
            event_type="ROAD_OPERATION_CANCELLED",
            old_status=old_status.value,
            new_status=op.status.value,
            notes=notes or f"Cancelled road operation '{op.title}'.",
        )

        try:
            self.db.commit()
            self.db.refresh(op)
            logger.info("Cancelled RoadOperation '%s'", op.id)
            return self.get_operation_government(actor, op.id)
        except Exception as e:
            self.db.rollback()
            raise e

    def get_operation_government(
        self,
        actor: UserContext,
        operation_id: str,
    ) -> GovernmentRoadOperationRead:
        """Fetch complete government view of a road operation."""
        self._verify_government_officer(actor)

        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        road = self.road_repo.get_by_id(op.road_id) if op.road_id else None
        alt_road = self.road_repo.get_by_id(op.alternative_road_id) if op.alternative_road_id else None
        officer = self.user_repo.get_by_id(op.created_by) if op.created_by else None

        events = self.operation_repo.get_events_for_operation(op.id)
        event_reads = [RoadOperationEventRead.model_validate(e) for e in events]

        return GovernmentRoadOperationRead(
            id=op.id,
            road_id=op.road_id,
            road_name=road.road_name if road else None,
            grievance_id=op.grievance_id,
            work_order_id=op.work_order_id,
            created_by=op.created_by,
            creator_name=officer.name if officer else None,
            title=op.title,
            description=op.description,
            reason=op.reason,
            operation_type=op.operation_type,
            status=op.status,
            start_time=op.start_time,
            expected_end_time=op.expected_end_time,
            actual_end_time=op.actual_end_time,
            alternative_route_name=op.alternative_route_name,
            alternative_route_instructions=op.alternative_route_instructions,
            alternative_road_id=op.alternative_road_id,
            alternative_road_name=alt_road.road_name if alt_road else None,
            alternative_distance_km=op.alternative_distance_km,
            created_at=op.created_at,
            updated_at=op.updated_at,
            history=event_reads,
        )

    def list_operations_government(
        self,
        actor: UserContext,
        status_filter: Optional[RoadOperationStatus] = None,
        operation_type: Optional[RoadOperationType] = None,
        road_id: Optional[str] = None,
        grievance_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GovernmentRoadOperationRead]:
        """List road operations for government officer review."""
        self._verify_government_officer(actor)

        ops = self.operation_repo.filter_operations(
            status=status_filter,
            operation_type=operation_type,
            road_id=road_id,
            grievance_id=grievance_id,
            work_order_id=work_order_id,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

        results: List[GovernmentRoadOperationRead] = []
        for op in ops:
            road = self.road_repo.get_by_id(op.road_id) if op.road_id else None
            alt_road = self.road_repo.get_by_id(op.alternative_road_id) if op.alternative_road_id else None
            officer = self.user_repo.get_by_id(op.created_by) if op.created_by else None

            results.append(
                GovernmentRoadOperationRead(
                    id=op.id,
                    road_id=op.road_id,
                    road_name=road.road_name if road else None,
                    grievance_id=op.grievance_id,
                    work_order_id=op.work_order_id,
                    created_by=op.created_by,
                    creator_name=officer.name if officer else None,
                    title=op.title,
                    description=op.description,
                    reason=op.reason,
                    operation_type=op.operation_type,
                    status=op.status,
                    start_time=op.start_time,
                    expected_end_time=op.expected_end_time,
                    actual_end_time=op.actual_end_time,
                    alternative_route_name=op.alternative_route_name,
                    alternative_route_instructions=op.alternative_route_instructions,
                    alternative_road_id=op.alternative_road_id,
                    alternative_road_name=alt_road.road_name if alt_road else None,
                    alternative_distance_km=op.alternative_distance_km,
                    created_at=op.created_at,
                    updated_at=op.updated_at,
                    history=[],
                )
            )

        return results

    def get_operation_citizen(
        self,
        operation_id: str,
    ) -> CitizenRoadOperationRead:
        """Citizen public read view of a road operation."""
        op = self.operation_repo.get_by_id(operation_id)
        if not op:
            raise RoadXDataError(f"Road operation with ID '{operation_id}' not found.")

        road = self.road_repo.get_by_id(op.road_id) if op.road_id else None
        alt_road = self.road_repo.get_by_id(op.alternative_road_id) if op.alternative_road_id else None

        return CitizenRoadOperationRead(
            id=op.id,
            road_id=op.road_id,
            road_name=road.road_name if road else None,
            title=op.title,
            description=op.description,
            reason=op.reason,
            operation_type=op.operation_type,
            status=op.status,
            start_time=op.start_time,
            expected_end_time=op.expected_end_time,
            actual_end_time=op.actual_end_time,
            alternative_route_name=op.alternative_route_name,
            alternative_route_instructions=op.alternative_route_instructions,
            alternative_road_name=alt_road.road_name if alt_road else None,
            alternative_distance_km=op.alternative_distance_km,
            created_at=op.created_at,
            updated_at=op.updated_at,
        )

    def list_operations_citizen(
        self,
        status_filter: Optional[RoadOperationStatus] = None,
        road_id: Optional[str] = None,
        operation_type: Optional[RoadOperationType] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CitizenRoadOperationRead]:
        """List active/planned road operations for citizens."""
        ops = self.operation_repo.filter_operations(
            status=status_filter,
            operation_type=operation_type,
            road_id=road_id,
            active_only=active_only if status_filter is None else False,
            skip=skip,
            limit=limit,
        )

        results: List[CitizenRoadOperationRead] = []
        for op in ops:
            road = self.road_repo.get_by_id(op.road_id) if op.road_id else None
            alt_road = self.road_repo.get_by_id(op.alternative_road_id) if op.alternative_road_id else None

            results.append(
                CitizenRoadOperationRead(
                    id=op.id,
                    road_id=op.road_id,
                    road_name=road.road_name if road else None,
                    title=op.title,
                    description=op.description,
                    reason=op.reason,
                    operation_type=op.operation_type,
                    status=op.status,
                    start_time=op.start_time,
                    expected_end_time=op.expected_end_time,
                    actual_end_time=op.actual_end_time,
                    alternative_route_name=op.alternative_route_name,
                    alternative_route_instructions=op.alternative_route_instructions,
                    alternative_road_name=alt_road.road_name if alt_road else None,
                    alternative_distance_km=op.alternative_distance_km,
                    created_at=op.created_at,
                    updated_at=op.updated_at,
                )
            )

        return results
