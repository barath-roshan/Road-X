"""Notification Service dispatching event-driven, role-aware, multi-channel notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.config import notification_settings
from backend.models.grievance import Grievance
from backend.models.notification import DeliveryStatus, Notification, NotificationChannel, NotificationType
from backend.models.road import RoadSegment
from backend.models.road_operation import RoadOperation, RoadOperationEvent
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder
from backend.models.workflow_event import WorkflowEvent, WorkflowEventType
from backend.notifications.providers import SMSProvider, TwilioSMSProvider
from backend.notifications.templates import render_notification_template
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.user_repository import UserRepository
from backend.security import UserContext, UnauthorizedError
from ml.common.exceptions import RoadXDataError
from ml.common.logging_config import get_logger

logger = get_logger("backend.services.notification")


class NotificationService:
    """Service handling notification persistence, idempotency, recipient targeting, and multi-channel dispatch."""

    def __init__(
        self,
        db: Session,
        sms_provider: Optional[SMSProvider] = None,
    ) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.user_repo = UserRepository(db)

        if sms_provider:
            self.sms_provider = sms_provider
        else:
            self.sms_provider = TwilioSMSProvider(
                account_sid=notification_settings.twilio_account_sid,
                auth_token=notification_settings.twilio_auth_token,
                from_phone=notification_settings.twilio_phone_number,
                enabled=notification_settings.twilio_enabled,
            )

    def create_and_dispatch(
        self,
        recipient_id: str,
        notification_type: NotificationType,
        context: Dict[str, str],
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> List[Notification]:
        """
        Create and dispatch notifications for a recipient user.
        Always persists IN_APP notification; attempts SMS if recipient phone & SMS settings are enabled.
        Enforces idempotency using event_id + recipient_id + channel to prevent duplicate sends.
        Guarantees failure isolation: SMS failures do not abort the overall database transaction.
        """
        if not notification_settings.notifications_enabled:
            logger.info("Notification system globally disabled in settings. Skipping dispatch.")
            return []

        recipient = self.user_repo.get_by_id(recipient_id)
        if not recipient:
            logger.warning(f"Cannot dispatch notification: Recipient '{recipient_id}' not found.")
            return []

        title, message = render_notification_template(notification_type, context)
        created_notifications: List[Notification] = []

        # 1. IN_APP Notification (Always created and saved)
        in_app_idempotency = f"{event_id}:{recipient_id}:IN_APP" if event_id else None
        if not in_app_idempotency or not self.repo.get_by_idempotency_key(in_app_idempotency):
            in_app_notif = Notification(
                recipient_id=recipient_id,
                notification_type=notification_type,
                title=title,
                message=message,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                channel=NotificationChannel.IN_APP,
                delivery_status=DeliveryStatus.SENT,
                is_read=False,
                idempotency_key=in_app_idempotency,
                delivered_at=datetime.now(timezone.utc),
            )
            self.db.add(in_app_notif)
            created_notifications.append(in_app_notif)

        # 2. SMS Notification (If recipient has phone & SMS channel enabled)
        if recipient.phone and notification_settings.twilio_enabled:
            sms_idempotency = f"{event_id}:{recipient_id}:SMS" if event_id else None
            if not sms_idempotency or not self.repo.get_by_idempotency_key(sms_idempotency):
                sms_notif = Notification(
                    recipient_id=recipient_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id,
                    channel=NotificationChannel.SMS,
                    delivery_status=DeliveryStatus.PENDING,
                    is_read=False,
                    idempotency_key=sms_idempotency,
                )
                self.db.add(sms_notif)

                # Attempt SMS delivery with failure isolation
                try:
                    success = self.sms_provider.send_sms(recipient.phone, message)
                    if success:
                        sms_notif.delivery_status = DeliveryStatus.SENT
                        sms_notif.delivered_at = datetime.now(timezone.utc)
                    else:
                        sms_notif.delivery_status = DeliveryStatus.SKIPPED
                except Exception as exc:
                    logger.error(f"SMS delivery failed for recipient '{recipient_id}': {exc}")
                    sms_notif.delivery_status = DeliveryStatus.FAILED
                    sms_notif.error_message = str(exc)

                created_notifications.append(sms_notif)

        self.db.flush()
        return created_notifications

    def process_workflow_event(
        self,
        event: WorkflowEvent,
        grievance: Grievance,
        work_order: Optional[WorkOrder] = None,
    ) -> List[Notification]:
        """Map WorkflowEvent to target recipients and dispatch appropriate notifications."""
        dispatched: List[Notification] = []
        road_name = grievance.road_segment.road_name if grievance.road_segment else "your area road"

        context = {
            "grievance_id": grievance.id[:8] if grievance.id else "N/A",
            "work_order_id": work_order.id[:8] if work_order and work_order.id else "N/A",
            "road_name": road_name,
            "reason": event.notes or "",
        }

        # 1. Citizen Notifications
        if event.event_type == WorkflowEventType.GRIEVANCE_ACCEPTED:
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=grievance.citizen_id,
                    notification_type=NotificationType.GRIEVANCE_ACCEPTED,
                    context=context,
                    related_entity_type="Grievance",
                    related_entity_id=grievance.id,
                    event_id=event.id,
                )
            )

        elif event.event_type == WorkflowEventType.GRIEVANCE_REJECTED:
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=grievance.citizen_id,
                    notification_type=NotificationType.GRIEVANCE_REJECTED,
                    context=context,
                    related_entity_type="Grievance",
                    related_entity_id=grievance.id,
                    event_id=event.id,
                )
            )

        elif event.event_type == WorkflowEventType.WORK_STARTED:
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=grievance.citizen_id,
                    notification_type=NotificationType.WORK_STARTED,
                    context=context,
                    related_entity_type="Grievance",
                    related_entity_id=grievance.id,
                    event_id=event.id,
                )
            )

        elif event.event_type == WorkflowEventType.WORK_PROGRESS_UPDATED:
            if work_order:
                context["progress_percentage"] = str(getattr(work_order, "progress_percentage", 0))
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=grievance.citizen_id,
                    notification_type=NotificationType.WORK_PROGRESS_UPDATED,
                    context=context,
                    related_entity_type="Grievance",
                    related_entity_id=grievance.id,
                    event_id=event.id,
                )
            )

        elif event.event_type == WorkflowEventType.WORK_VERIFICATION_APPROVED:
            # Notify citizen
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=grievance.citizen_id,
                    notification_type=NotificationType.WORK_VERIFICATION_APPROVED,
                    context=context,
                    related_entity_type="Grievance",
                    related_entity_id=grievance.id,
                    event_id=event.id,
                )
            )
            # Notify assigned contractor
            if work_order and work_order.assigned_contractor_id:
                dispatched.extend(
                    self.create_and_dispatch(
                        recipient_id=work_order.assigned_contractor_id,
                        notification_type=NotificationType.WORK_VERIFICATION_APPROVED,
                        context=context,
                        related_entity_type="WorkOrder",
                        related_entity_id=work_order.id,
                        event_id=event.id,
                    )
                )

        # 2. Contractor Notifications
        elif event.event_type in (WorkflowEventType.WORK_ORDER_CREATED, WorkflowEventType.WORK_ORDER_ASSIGNED):
            if work_order and work_order.assigned_contractor_id:
                dispatched.extend(
                    self.create_and_dispatch(
                        recipient_id=work_order.assigned_contractor_id,
                        notification_type=NotificationType.WORK_ORDER_ASSIGNED,
                        context=context,
                        related_entity_type="WorkOrder",
                        related_entity_id=work_order.id,
                        event_id=event.id,
                    )
                )

        elif event.event_type == WorkflowEventType.WORK_VERIFICATION_REJECTED:
            if work_order and work_order.assigned_contractor_id:
                dispatched.extend(
                    self.create_and_dispatch(
                        recipient_id=work_order.assigned_contractor_id,
                        notification_type=NotificationType.WORK_VERIFICATION_REJECTED,
                        context=context,
                        related_entity_type="WorkOrder",
                        related_entity_id=work_order.id,
                        event_id=event.id,
                    )
                )

        # 3. Government Officer Notifications (Verification Submitted)
        elif event.event_type in (WorkflowEventType.WORK_VERIFICATION_SUBMITTED, WorkflowEventType.WORK_COMPLETION_SUBMITTED):
            # Notify government officers
            officers = self.db.query(User).filter(User.role == UserRole.GOVERNMENT_OFFICER, User.is_active.is_(True)).all()
            for officer in officers:
                dispatched.extend(
                    self.create_and_dispatch(
                        recipient_id=officer.id,
                        notification_type=NotificationType.WORK_VERIFICATION_SUBMITTED,
                        context=context,
                        related_entity_type="WorkOrder",
                        related_entity_id=work_order.id if work_order else None,
                        event_id=f"{event.id}:{officer.id}",
                    )
                )

        return dispatched

    def process_road_operation_event(
        self,
        event: RoadOperationEvent,
        operation: RoadOperation,
    ) -> List[Notification]:
        """Map RoadOperationEvent to target recipients (linked grievance citizen & assigned contractor)."""
        dispatched: List[Notification] = []
        road_name = operation.road_segment.road_name if operation.road_segment else "municipal road"

        context = {
            "operation_title": operation.title,
            "road_name": road_name,
            "reason": operation.reason or "",
        }

        notif_type = None
        if event.event_type == "ROAD_OPERATION_ACTIVATED":
            notif_type = NotificationType.ROAD_OPERATION_ACTIVATED
        elif event.event_type == "ROAD_OPERATION_COMPLETED":
            notif_type = NotificationType.ROAD_OPERATION_COMPLETED
        elif event.event_type == "ROAD_OPERATION_CANCELLED":
            notif_type = NotificationType.ROAD_OPERATION_CANCELLED

        if not notif_type:
            return []

        # If linked to a grievance, notify citizen
        if operation.grievance and operation.grievance.citizen_id:
            context["grievance_id"] = operation.grievance.id[:8]
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=operation.grievance.citizen_id,
                    notification_type=notif_type,
                    context=context,
                    related_entity_type="RoadOperation",
                    related_entity_id=operation.id,
                    event_id=event.id,
                )
            )

        # If linked to a work order with contractor, notify contractor
        if operation.work_order and operation.work_order.assigned_contractor_id:
            context["work_order_id"] = operation.work_order.id[:8]
            dispatched.extend(
                self.create_and_dispatch(
                    recipient_id=operation.work_order.assigned_contractor_id,
                    notification_type=notif_type,
                    context=context,
                    related_entity_type="RoadOperation",
                    related_entity_id=operation.id,
                    event_id=f"{event.id}:contractor",
                )
            )

        return dispatched

    def list_user_notifications(
        self,
        actor: UserContext,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Notification], int, int]:
        """Retrieve paginated notifications for the authenticated user along with unread count."""
        if not actor.user_id:
            raise UnauthorizedError("Authentication required to list notifications.")

        items, total = self.repo.list_user_notifications(
            user_id=actor.user_id,
            unread_only=unread_only,
            page=page,
            page_size=page_size,
        )
        unread_count = self.repo.count_unread(actor.user_id)
        return items, total, unread_count

    def get_user_notification(self, actor: UserContext, notification_id: str) -> Notification:
        """Retrieve a specific notification after enforcing recipient ownership."""
        if not actor.user_id:
            raise UnauthorizedError("Authentication required.")

        notification = self.repo.get_by_id(notification_id)
        if not notification:
            raise RoadXDataError(f"Notification '{notification_id}' not found.")

        if notification.recipient_id != actor.user_id:
            raise UnauthorizedError("You do not have permission to access another user's notification.")

        return notification

    def mark_notification_read(self, actor: UserContext, notification_id: str) -> Notification:
        """Mark a specific user notification as read."""
        notification = self.get_user_notification(actor, notification_id)
        return self.repo.mark_as_read(notification)

    def mark_all_user_notifications_read(self, actor: UserContext) -> int:
        """Mark all notifications for the authenticated user as read."""
        if not actor.user_id:
            raise UnauthorizedError("Authentication required.")

        return self.repo.mark_all_as_read(actor.user_id)
