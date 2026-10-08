"""API Integration tests for Notification Endpoints (/api/v1/notifications/...)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from api.main import app
from backend.database import Base, get_db
from backend.models.notification import DeliveryStatus, Notification, NotificationChannel, NotificationType
from backend.models.user import User, UserRole


@pytest.fixture(scope="function")
def db_engine():
    """Create isolated in-memory SQLite engine using StaticPool for test isolation."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide clean database session for test execution."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def api_client(db_session: Session):
    """TestClient overriding get_db to use test database session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def api_notif_setup(db_session: Session):
    """Seed test users and persistent notifications."""
    citizen = User(name="Notif Citizen", email="notif_cit@test.com", role=UserRole.CITIZEN, phone="+15559999")
    citizen2 = User(name="Other Citizen", email="other_cit@test.com", role=UserRole.CITIZEN)

    db_session.add_all([citizen, citizen2])
    db_session.flush()

    n1 = Notification(
        recipient_id=citizen.id,
        notification_type=NotificationType.GRIEVANCE_ACCEPTED,
        title="Grievance Accepted",
        message="Your grievance #123 has been accepted.",
        channel=NotificationChannel.IN_APP,
        delivery_status=DeliveryStatus.SENT,
        is_read=False,
    )
    n2 = Notification(
        recipient_id=citizen.id,
        notification_type=NotificationType.WORK_STARTED,
        title="Work Started",
        message="Work has started on Main St.",
        channel=NotificationChannel.IN_APP,
        delivery_status=DeliveryStatus.SENT,
        is_read=False,
    )
    n3 = Notification(
        recipient_id=citizen2.id,
        notification_type=NotificationType.GRIEVANCE_REJECTED,
        title="Grievance Rejected",
        message="Your grievance #456 was rejected.",
        channel=NotificationChannel.IN_APP,
        delivery_status=DeliveryStatus.SENT,
        is_read=False,
    )

    db_session.add_all([n1, n2, n3])
    db_session.commit()

    return {"citizen": citizen, "citizen2": citizen2, "n1": n1, "n2": n2, "n3": n3}


def test_list_and_read_notifications_api(api_client: TestClient, api_notif_setup: dict):
    """Verify notification listing, detail retrieval, marking read, and ownership security."""
    citizen = api_notif_setup["citizen"]
    citizen2 = api_notif_setup["citizen2"]
    n1 = api_notif_setup["n1"]

    headers_c1 = {
        "X-Actor-User-ID": citizen.id,
        "X-Actor-Role": UserRole.CITIZEN.value,
    }
    headers_c2 = {
        "X-Actor-User-ID": citizen2.id,
        "X-Actor-Role": UserRole.CITIZEN.value,
    }

    # 1. List notifications for Citizen 1
    resp = api_client.get("/api/v1/notifications", headers=headers_c1)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["items"]) == 2

    # 2. View specific notification for Citizen 1
    resp = api_client.get(f"/api/v1/notifications/{n1.id}", headers=headers_c1)
    assert resp.status_code == 200
    assert resp.json()["id"] == n1.id

    # 3. Citizen 2 tries to view Citizen 1's notification -> 403 Forbidden
    resp = api_client.get(f"/api/v1/notifications/{n1.id}", headers=headers_c2)
    assert resp.status_code == 403

    # 4. Mark n1 as read
    resp = api_client.post(f"/api/v1/notifications/{n1.id}/read", headers=headers_c1)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    # Check list again -> unread count is 1
    resp = api_client.get("/api/v1/notifications", headers=headers_c1)
    assert resp.json()["unread_count"] == 1

    # 5. Mark all as read for Citizen 1
    resp = api_client.post("/api/v1/notifications/read-all", headers=headers_c1)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = api_client.get("/api/v1/notifications", headers=headers_c1)
    assert resp.json()["unread_count"] == 0
