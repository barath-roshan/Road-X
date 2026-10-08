"""Unit tests for Notification Service, Twilio provider, idempotency, failure isolation, and workflow event triggers."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from backend.config import notification_settings
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.notification import DeliveryStatus, Notification, NotificationChannel, NotificationType
from backend.models.road import RoadSegment
from backend.models.road_operation import RoadOperation, RoadOperationEvent, RoadOperationStatus, RoadOperationType
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.workflow_event import WorkflowEvent, WorkflowEventType
from backend.notifications.providers import SMSProvider, TwilioSMSProvider, NotificationProviderError
from backend.notifications.templates import render_notification_template
from backend.security import UserContext, UnauthorizedError
from backend.services.government_workflow_service import GovernmentWorkflowService
from backend.services.notification_service import NotificationService
from ml.common.exceptions import RoadXDataError


@pytest.fixture
def notif_setup(db_session: Session):
    """Seed test users, road, grievance, and work order."""
    gov = User(name="Officer Bob", email="bob@gov.in", role=UserRole.GOVERNMENT_OFFICER, phone="+15550001")
    citizen = User(name="Citizen Alice", email="alice@citizen.com", role=UserRole.CITIZEN, phone="+15550002")
    contractor = User(name="Contractor Charlie", email="charlie@contractor.com", role=UserRole.CONTRACTOR, phone="+15550003")
    citizen2 = User(name="Citizen Bob", email="bob@citizen.com", role=UserRole.CITIZEN, phone="+15550004")

    db_session.add_all([gov, citizen, contractor, citizen2])
    db_session.flush()

    road = RoadSegment(segment_id="SEG-NOTIF-1", road_name="Notification Way", area="North Zone", latitude=12.91, longitude=77.61)
    db_session.add(road)
    db_session.flush()

    grievance = Grievance(
        issue_category="POTHOLE",
        description="Hazardous hole on street",
        citizen_id=citizen.id,
        road_id=road.segment_id,
        status=GrievanceStatus.SUBMITTED,
    )
    db_session.add(grievance)
    db_session.flush()

    work_order = WorkOrder(
        grievance_id=grievance.id,
        created_by=gov.id,
        assigned_contractor_id=contractor.id,
        title="Repair Pothole",
        description="Fix surface pothole",
        status=WorkOrderStatus.ASSIGNED,
    )
    db_session.add(work_order)
    db_session.flush()

    return {
        "gov": gov,
        "citizen": citizen,
        "contractor": contractor,
        "citizen2": citizen2,
        "road": road,
        "grievance": grievance,
        "work_order": work_order,
    }


def test_notification_creation_and_templates(db_session: Session, notif_setup: dict):
    """Verify template rendering and basic in-app notification persistence."""
    service = NotificationService(db_session)
    citizen = notif_setup["citizen"]

    title, msg = render_notification_template(
        NotificationType.GRIEVANCE_ACCEPTED,
        {"grievance_id": "12345678", "road_name": "Main Street"},
    )
    assert title == "Grievance Accepted"
    assert "12345678" in msg
    assert "Main Street" in msg

    notifs = service.create_and_dispatch(
        recipient_id=citizen.id,
        notification_type=NotificationType.GRIEVANCE_ACCEPTED,
        context={"grievance_id": "GRV-101", "road_name": "Main Street"},
        related_entity_type="Grievance",
        related_entity_id="GRV-101",
    )

    assert len(notifs) >= 1
    in_app = [n for n in notifs if n.channel == NotificationChannel.IN_APP][0]
    assert in_app.recipient_id == citizen.id
    assert in_app.is_read is False
    assert in_app.delivery_status == DeliveryStatus.SENT


def test_notification_idempotency(db_session: Session, notif_setup: dict):
    """Verify duplicate notifications with exact same idempotency_key are skipped."""
    service = NotificationService(db_session)
    citizen = notif_setup["citizen"]

    event_id = "EVT-UNIQUE-999"

    # First dispatch
    n1 = service.create_and_dispatch(
        recipient_id=citizen.id,
        notification_type=NotificationType.GRIEVANCE_ACCEPTED,
        context={"grievance_id": "GRV-101"},
        event_id=event_id,
    )
    assert len(n1) >= 1

    # Second dispatch with exact same event_id
    n2 = service.create_and_dispatch(
        recipient_id=citizen.id,
        notification_type=NotificationType.GRIEVANCE_ACCEPTED,
        context={"grievance_id": "GRV-101"},
        event_id=event_id,
    )
    # Duplicate creation skipped
    assert len(n2) == 0


def test_twilio_mock_success_and_failure(db_session: Session, notif_setup: dict):
    """Test Twilio provider dispatch success and failure isolation."""
    mock_provider = MagicMock(spec=SMSProvider)
    mock_provider.send_sms.return_value = True

    with patch.object(notification_settings, "twilio_enabled", True):
        service = NotificationService(db_session, sms_provider=mock_provider)
        citizen = notif_setup["citizen"]

        notifs = service.create_and_dispatch(
            recipient_id=citizen.id,
            notification_type=NotificationType.GRIEVANCE_ACCEPTED,
            context={"grievance_id": "GRV-101"},
            event_id="EVT-SMS-1",
        )

        mock_provider.send_sms.assert_called_once()
        sms_notif = [n for n in notifs if n.channel == NotificationChannel.SMS][0]
        assert sms_notif.delivery_status == DeliveryStatus.SENT

    # Test provider failure handling without aborting transaction
    failing_provider = MagicMock(spec=SMSProvider)
    failing_provider.send_sms.side_effect = NotificationProviderError("Twilio API 500 Network Error")

    with patch.object(notification_settings, "twilio_enabled", True):
        fail_service = NotificationService(db_session, sms_provider=failing_provider)
        notifs_fail = fail_service.create_and_dispatch(
            recipient_id=citizen.id,
            notification_type=NotificationType.GRIEVANCE_REJECTED,
            context={"grievance_id": "GRV-102"},
            event_id="EVT-SMS-FAIL",
        )
        sms_fail = [n for n in notifs_fail if n.channel == NotificationChannel.SMS][0]
        assert sms_fail.delivery_status == DeliveryStatus.FAILED
        assert "Twilio API 500 Network Error" in sms_fail.error_message


def test_notification_ownership_and_reading(db_session: Session, notif_setup: dict):
    """Verify notification ownership enforcement and mark-as-read methods."""
    service = NotificationService(db_session)
    citizen1 = notif_setup["citizen"]
    citizen2 = notif_setup["citizen2"]

    c1_actor = UserContext(user_id=citizen1.id, role=UserRole.CITIZEN)
    c2_actor = UserContext(user_id=citizen2.id, role=UserRole.CITIZEN)

    notifs = service.create_and_dispatch(
        recipient_id=citizen1.id,
        notification_type=NotificationType.WORK_STARTED,
        context={"grievance_id": "GRV-200"},
        event_id="EVT-READ-1",
    )
    in_app = [n for n in notifs if n.channel == NotificationChannel.IN_APP][0]

    # Citizen 2 cannot view Citizen 1's notification -> UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.get_user_notification(c2_actor, in_app.id)

    # Citizen 2 cannot mark Citizen 1's notification as read -> UnauthorizedError
    with pytest.raises(UnauthorizedError):
        service.mark_notification_read(c2_actor, in_app.id)

    # Citizen 1 views & marks read -> Success
    read_notif = service.mark_notification_read(c1_actor, in_app.id)
    assert read_notif.is_read is True
    assert read_notif.read_at is not None

    # Mark all read for Citizen 1
    items, total, unread = service.list_user_notifications(c1_actor)
    assert unread == 0


def test_government_workflow_event_notifications(db_session: Session, notif_setup: dict):
    """Verify workflow events in GovernmentWorkflowService automatically generate recipient notifications."""
    gov_service = GovernmentWorkflowService(db_session)
    notif_service = NotificationService(db_session)

    gov_actor = UserContext(user_id=notif_setup["gov"].id, role=UserRole.GOVERNMENT_OFFICER)
    citizen_actor = UserContext(user_id=notif_setup["citizen"].id, role=UserRole.CITIZEN)

    # Government accepts grievance -> Citizen receives notification
    gov_service.review_grievance(
        actor=gov_actor,
        grievance_id=notif_setup["grievance"].id,
        decision=from_import_review_decision(),
        notes="Grievance accepted for repair",
    )

    items, total, unread = notif_service.list_user_notifications(citizen_actor)
    assert total >= 1
    assert any(n.notification_type == NotificationType.GRIEVANCE_ACCEPTED for n in items)


def from_import_review_decision():
    from backend.models.government_review import ReviewDecision
    return ReviewDecision.ACCEPT
