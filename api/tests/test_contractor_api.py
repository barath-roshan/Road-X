"""API integration tests for Contractor Workflow routes (/api/v1/contractor/...)."""

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
    """Seed test database with users, road segment, grievance, and assigned work order."""
    gov_user = User(
        name="Officer Bob",
        email="officer.bob@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor_a = User(
        name="Contractor Alice (BuildCorp)",
        email="alice@buildcorp.com",
        role=UserRole.CONTRACTOR,
    )
    contractor_b = User(
        name="Contractor Charlie (RoadFix)",
        email="charlie@roadfix.com",
        role=UserRole.CONTRACTOR,
    )
    citizen_user = User(
        name="Dave Citizen",
        email="dave@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_user, contractor_a, contractor_b, citizen_user])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-BLR-101",
        road_name="Outer Ring Road Sec 2",
        area="Bellandur",
        latitude=12.9260,
        longitude=77.6762,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    grievance = Grievance(
        citizen_id=citizen_user.id,
        road_id=road.id,
        description="Deep pothole causing traffic slowdowns",
        issue_category="POTHOLE",
        latitude=12.9265,
        longitude=77.6765,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    db_session.add(grievance)
    db_session.flush()

    work_order = WorkOrder(
        grievance_id=grievance.id,
        road_id=road.id,
        created_by=gov_user.id,
        assigned_contractor_id=contractor_a.id,
        title="Repair Pothole on Outer Ring Road",
        description="Asphalt patch and roller compaction required",
        priority="HIGH",
        status=WorkOrderStatus.ASSIGNED,
    )
    db_session.add(work_order)
    db_session.commit()

    return {
        "gov_user": gov_user,
        "contractor_a": contractor_a,
        "contractor_b": contractor_b,
        "citizen_user": citizen_user,
        "road": road,
        "grievance": grievance,
        "work_order": work_order,
    }


def test_list_assigned_work_orders_authorization(api_client: TestClient, test_setup):
    """Verify listing assigned work orders enforces CONTRACTOR role and contractor scoping."""
    contractor_a = test_setup["contractor_a"]
    citizen = test_setup["citizen_user"]

    # Citizen actor -> 403 Forbidden
    citizen_headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    res_citizen = api_client.get("/api/v1/contractor/work-orders", headers=citizen_headers)
    assert res_citizen.status_code == 403

    # Contractor A actor -> 200 OK with list of assigned work orders
    contractor_headers = {"X-Actor-User-ID": contractor_a.id, "X-Actor-Role": "CONTRACTOR"}
    res_contractor = api_client.get("/api/v1/contractor/work-orders", headers=contractor_headers)
    assert res_contractor.status_code == 200
    data = res_contractor.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == test_setup["work_order"].id


def test_work_order_details_ownership_check(api_client: TestClient, test_setup):
    """Verify Contractor B cannot view Contractor A's assigned work order."""
    contractor_a = test_setup["contractor_a"]
    contractor_b = test_setup["contractor_b"]
    work_order_id = test_setup["work_order"].id

    headers_b = {"X-Actor-User-ID": contractor_b.id, "X-Actor-Role": "CONTRACTOR"}
    res_b = api_client.get(f"/api/v1/contractor/work-orders/{work_order_id}", headers=headers_b)
    assert res_b.status_code == 403

    headers_a = {"X-Actor-User-ID": contractor_a.id, "X-Actor-Role": "CONTRACTOR"}
    res_a = api_client.get(f"/api/v1/contractor/work-orders/{work_order_id}", headers=headers_a)
    assert res_a.status_code == 200
    details = res_a.json()
    assert details["id"] == work_order_id
    assert details["road_name"] == "Outer Ring Road Sec 2"


def test_contractor_full_http_workflow(api_client: TestClient, test_setup):
    """Full HTTP API workflow test:
    Accept -> Start -> Progress -> Attach Evidence -> Submit Completion.
    """
    contractor_a = test_setup["contractor_a"]
    gov = test_setup["gov_user"]
    work_order_id = test_setup["work_order"].id
    grievance_id = test_setup["grievance"].id
    headers = {"X-Actor-User-ID": contractor_a.id, "X-Actor-Role": "CONTRACTOR"}

    # 1. Accept work order assignment
    res_accept = api_client.post(f"/api/v1/contractor/work-orders/{work_order_id}/accept", headers=headers)
    assert res_accept.status_code == 200

    # 2. Start work order
    res_start = api_client.post(f"/api/v1/contractor/work-orders/{work_order_id}/start", headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "IN_PROGRESS"

    # 3. Submit progress update (50%)
    res_prog = api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=headers,
        json={"progress_percentage": 50, "note": "Cold mix asphalt laid"},
    )
    assert res_prog.status_code == 201
    assert res_prog.json()["progress_percentage"] == 50

    # 4. Attach completion evidence
    res_ev = api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/evidence",
        headers=headers,
        json={
            "grievance_id": grievance_id,
            "work_order_id": work_order_id,
            "file_name": "completed_road.jpg",
            "file_type": "image/jpeg",
            "storage_path": "/uploads/completed_road.jpg",
            "file_size_bytes": 102400,
        },
    )
    assert res_ev.status_code == 201
    evidence_id = res_ev.json()["id"]

    # 5. Submit completion for verification
    res_sub = api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/submit",
        headers=headers,
        json={
            "completion_note": "Pothole filled and compacted.",
            "actual_work_summary": "1.2 sq meters asphalt repair",
            "evidence_ids": [evidence_id],
        },
    )
    assert res_sub.status_code == 201
    sub_data = res_sub.json()
    assert sub_data["status"] == "PENDING_VERIFICATION"
    assert sub_data["grievance_status"] == "PENDING_VERIFICATION"

    # 6. Verify government officer verification API approves work -> RESOLVED & COMPLETED
    gov_headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}
    res_verify = api_client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=gov_headers,
        json={"decision": "APPROVE", "notes": "Quality inspected and approved."},
    )
    assert res_verify.status_code == 201
    assert res_verify.json()["decision"] == "APPROVE"

    # Check work order status is COMPLETED and grievance is RESOLVED
    res_wo_final = api_client.get(f"/api/v1/government/work-orders/{work_order_id}", headers=gov_headers)
    assert res_wo_final.json()["status"] == "COMPLETED"

    res_gr_final = api_client.get(f"/api/v1/government/grievances/{grievance_id}", headers=gov_headers)
    assert res_gr_final.json()["status"] == "RESOLVED"
