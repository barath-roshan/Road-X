"""API integration tests for Government Officer workflow routes (/api/v1/government/...)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from api.main import app
from backend.database import Base, get_db
from backend.models.user import User, UserRole
from backend.models.road import RoadSegment
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.work_order import WorkOrder, WorkOrderStatus


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
def test_setup(db_session: Session):
    """Seed test database with users, road segment, and initial grievance."""
    gov_user = User(
        name="Officer Jenny",
        email="officer@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    citizen_user = User(
        name="John Citizen",
        email="john@example.com",
        role=UserRole.CITIZEN,
    )
    contractor_user = User(
        name="BuildCorp Contractor",
        email="contractor@buildcorp.com",
        role=UserRole.CONTRACTOR,
    )
    db_session.add_all([gov_user, citizen_user, contractor_user])
    db_session.flush()

    road = RoadSegment(
        segment_id="ROAD-MG-04",
        road_name="MG Road Section 4",
        area="Indiranagar",
        latitude=12.9716,
        longitude=77.5946,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    grievance = Grievance(
        citizen_id=citizen_user.id,
        road_id=road.id,
        description="Pothole near city center junction",
        issue_category="POTHOLE",
        latitude=12.9720,
        longitude=77.5950,
        status=GrievanceStatus.SUBMITTED,
    )
    db_session.add(grievance)
    db_session.commit()

    return {
        "gov_user": gov_user,
        "citizen_user": citizen_user,
        "contractor_user": contractor_user,
        "road": road,
        "grievance": grievance,
    }


def test_list_grievances_unauthorized(api_client: TestClient, test_setup):
    """Verify that a non-government officer is rejected with HTTP 403."""
    citizen = test_setup["citizen_user"]
    headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    response = api_client.get("/api/v1/government/grievances", headers=headers)
    assert response.status_code == 403


def test_list_grievances_authorized(api_client: TestClient, test_setup):
    """Verify government officer can list grievances."""
    gov = test_setup["gov_user"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}
    response = api_client.get("/api/v1/government/grievances", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == test_setup["grievance"].id


def test_get_grievance_details(api_client: TestClient, test_setup):
    """Verify government officer can fetch grievance details."""
    gov = test_setup["gov_user"]
    grievance_id = test_setup["grievance"].id
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    response = api_client.get(f"/api/v1/government/grievances/{grievance_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == grievance_id


def test_review_grievance_reject(api_client: TestClient, test_setup):
    """Verify rejecting a grievance sets status to REJECTED."""
    gov = test_setup["gov_user"]
    grievance_id = test_setup["grievance"].id
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    payload = {
        "decision": "REJECT",
        "reason": "Out of municipal jurisdiction",
        "notes": "Forwarded to NHAI",
    }
    response = api_client.post(
        f"/api/v1/government/grievances/{grievance_id}/review",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["decision"] == "REJECT"
    assert res_json["grievance_id"] == grievance_id

    # Check updated grievance detail
    detail_res = api_client.get(f"/api/v1/government/grievances/{grievance_id}", headers=headers)
    assert detail_res.json()["status"] == "REJECTED"


def test_full_government_workflow_lifecycle(api_client: TestClient, test_setup, db_session: Session):
    """Full integration test: Review Accept -> Create Work Order -> Contractor work -> Verify Approve -> RESOLVED."""
    gov = test_setup["gov_user"]
    contractor = test_setup["contractor_user"]
    grievance_id = test_setup["grievance"].id
    gov_headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    # 1. Government accepts grievance
    review_res = api_client.post(
        f"/api/v1/government/grievances/{grievance_id}/review",
        headers=gov_headers,
        json={"decision": "ACCEPT", "notes": "Approved for maintenance"},
    )
    assert review_res.status_code == 201
    assert review_res.json()["decision"] == "ACCEPT"

    # 2. Government creates & assigns work order
    wo_res = api_client.post(
        f"/api/v1/government/grievances/{grievance_id}/work-orders",
        headers=gov_headers,
        json={
            "title": "Repair pothole on MG Road",
            "description": "Cold mix asphalt patch",
            "priority": "HIGH",
            "assigned_contractor_id": contractor.id,
        },
    )
    assert wo_res.status_code == 201
    wo_data = wo_res.json()
    work_order_id = wo_data["id"]
    assert wo_data["status"] == "ASSIGNED"
    assert wo_data["assigned_contractor_id"] == contractor.id

    # Check grievance status is now IN_PROGRESS
    gr_res = api_client.get(f"/api/v1/government/grievances/{grievance_id}", headers=gov_headers)
    assert gr_res.json()["status"] == "IN_PROGRESS"

    # 3. Simulate Contractor updating status to PENDING_VERIFICATION directly in DB (Phase 13 simulation)
    wo_db = db_session.query(WorkOrder).filter_by(id=work_order_id).first()
    wo_db.status = WorkOrderStatus.PENDING_VERIFICATION
    gr_db = db_session.query(Grievance).filter_by(id=grievance_id).first()
    gr_db.status = GrievanceStatus.PENDING_VERIFICATION
    db_session.commit()

    # Crucial Rule Check: Grievance MUST NOT be RESOLVED yet
    assert gr_db.status == GrievanceStatus.PENDING_VERIFICATION

    # 4. Contractor attempts verification -> Forbidden 403
    contractor_headers = {"X-Actor-User-ID": contractor.id, "X-Actor-Role": "CONTRACTOR"}
    fail_verify = api_client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=contractor_headers,
        json={"decision": "APPROVE", "notes": "I did it!"},
    )
    assert fail_verify.status_code == 403

    # 5. Government officer verifies completion (APPROVE)
    verify_res = api_client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=gov_headers,
        json={"decision": "APPROVE", "notes": "Quality audit passed on site."},
    )
    assert verify_res.status_code == 201
    assert verify_res.json()["decision"] == "APPROVE"

    # 6. Verify grievance is now RESOLVED and work order is COMPLETED
    gr_final = api_client.get(f"/api/v1/government/grievances/{grievance_id}", headers=gov_headers)
    assert gr_final.json()["status"] == "RESOLVED"

    wo_final = api_client.get(f"/api/v1/government/work-orders/{work_order_id}", headers=gov_headers)
    assert wo_final.json()["status"] == "COMPLETED"

    # 7. Check audit history route
    history_res = api_client.get(f"/api/v1/government/grievances/{grievance_id}/history", headers=gov_headers)
    assert history_res.status_code == 200
    events = history_res.json()
    assert len(events) >= 3
    event_types = [ev["event_type"] for ev in events]
    assert "GRIEVANCE_ACCEPTED" in event_types
    assert "WORK_ORDER_CREATED" in event_types
    assert "WORK_VERIFICATION_APPROVED" in event_types
