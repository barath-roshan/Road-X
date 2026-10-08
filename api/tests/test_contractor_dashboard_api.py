"""API integration tests for Contractor Dashboard endpoints (/api/v1/contractor/dashboard/...)."""

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
from backend.models.work_progress import WorkProgress
from backend.models.government_verification import GovernmentVerification, VerificationDecision


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
def contractor_dashboard_setup(db_session: Session):
    """Seed database with users, grievances, work orders, progress, and verification rejection."""
    gov_officer = User(name="Officer Dave", email="dave@gov.in", role=UserRole.GOVERNMENT_OFFICER)
    contractor_a = User(name="Contractor Alice", email="alice@contractor.com", role=UserRole.CONTRACTOR)
    contractor_b = User(name="Contractor Bob", email="bob@contractor.com", role=UserRole.CONTRACTOR)
    citizen = User(name="Citizen Charlie", email="charlie@citizen.com", role=UserRole.CITIZEN)

    db_session.add_all([gov_officer, contractor_a, contractor_b, citizen])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-101",
        road_name="MG Road",
        area="Indiranagar",
        latitude=12.9716,
        longitude=77.5946,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    # Grievances
    g1 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Big pothole MG Road",
        issue_category="POTHOLE",
        latitude=12.9716,
        longitude=77.5946,
        status=GrievanceStatus.IN_PROGRESS,
    )
    g2 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Drainage block MG Road",
        issue_category="DRAINAGE",
        latitude=12.9720,
        longitude=77.5950,
        status=GrievanceStatus.PENDING_VERIFICATION,
    )
    g3 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Crack on road for Contractor B",
        issue_category="CRACK",
        latitude=12.9730,
        longitude=77.5960,
        status=GrievanceStatus.UNDER_REVIEW,
    )
    db_session.add_all([g1, g2, g3])
    db_session.flush()

    # Work orders for Contractor A
    wo1 = WorkOrder(
        grievance_id=g1.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor_a.id,
        title="Repair Pothole MG Road",
        description="Patch pothole",
        priority="HIGH",
        status=WorkOrderStatus.IN_PROGRESS,
    )
    wo2 = WorkOrder(
        grievance_id=g2.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor_a.id,
        title="Clear Drainage MG Road",
        description="Drain cleaning",
        priority="CRITICAL",
        status=WorkOrderStatus.PENDING_VERIFICATION,
    )

    # Work order for Contractor B
    wo3 = WorkOrder(
        grievance_id=g3.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor_b.id,
        title="Seal Crack Contractor B",
        description="Asphalt sealing",
        priority="LOW",
        status=WorkOrderStatus.ASSIGNED,
    )
    db_session.add_all([wo1, wo2, wo3])
    db_session.flush()

    # Rejection verification for wo1 (causing rework state)
    ver = GovernmentVerification(
        work_order_id=wo1.id,
        grievance_id=g1.id,
        officer_id=gov_officer.id,
        decision=VerificationDecision.REJECT,
        notes="Patching incomplete near edges. Please rework.",
    )
    db_session.add(ver)

    # Progress log for wo1
    p1 = WorkProgress(
        work_order_id=wo1.id,
        contractor_id=contractor_a.id,
        progress_percentage=60,
        note="60% done after rework note",
    )
    db_session.add(p1)

    db_session.commit()

    return {
        "gov": gov_officer,
        "contractor_a": contractor_a,
        "contractor_b": contractor_b,
        "citizen": citizen,
        "road": road,
        "wo1": wo1,
        "wo2": wo2,
        "wo3": wo3,
    }


def test_contractor_dashboard_role_authorization_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify non-contractor roles receive HTTP 403 Forbidden."""
    gov = contractor_dashboard_setup["gov"]
    citizen = contractor_dashboard_setup["citizen"]

    # Government officer trying to access contractor dashboard -> 403
    gov_headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}
    res_g = api_client.get("/api/v1/contractor/dashboard/overview", headers=gov_headers)
    assert res_g.status_code == 403

    # Citizen trying to access contractor dashboard -> 403
    citizen_headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    res_c = api_client.get("/api/v1/contractor/dashboard/overview", headers=citizen_headers)
    assert res_c.status_code == 403


def test_contractor_dashboard_ownership_isolation_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify Contractor A receives 403 when requesting Contractor B's work order."""
    alice = contractor_dashboard_setup["contractor_a"]
    bob = contractor_dashboard_setup["contractor_b"]
    wo3 = contractor_dashboard_setup["wo3"]  # assigned to Bob

    alice_headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    # Alice requests Bob's work order detail -> 403
    res_detail = api_client.get(f"/api/v1/contractor/dashboard/work-orders/{wo3.id}", headers=alice_headers)
    assert res_detail.status_code == 403

    # Bob requests Bob's work order detail -> 200
    bob_headers = {"X-Actor-User-ID": bob.id, "X-Actor-Role": "CONTRACTOR"}
    res_bob = api_client.get(f"/api/v1/contractor/dashboard/work-orders/{wo3.id}", headers=bob_headers)
    assert res_bob.status_code == 200
    assert res_bob.json()["id"] == wo3.id


def test_contractor_dashboard_overview_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/overview returns statistics for authenticated contractor."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    res = api_client.get("/api/v1/contractor/dashboard/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_assigned"] == 2
    assert data["in_progress"] == 1
    assert data["pending_verification"] == 1
    assert data["rework"] == 1
    # wo1 progress = 60%, wo2 progress = 0% -> avg = 30.0
    assert data["average_progress"] == 30.0


def test_contractor_dashboard_work_orders_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/work-orders filtering and sorting."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    # All assigned to Alice
    res_all = api_client.get("/api/v1/contractor/dashboard/work-orders", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Status filter
    res_filt = api_client.get("/api/v1/contractor/dashboard/work-orders?status=IN_PROGRESS", headers=headers)
    assert res_filt.status_code == 200
    items = res_filt.json()
    assert len(items) == 1
    assert items[0]["id"] == contractor_dashboard_setup["wo1"].id
    assert items[0]["rework_required"] is True


def test_contractor_dashboard_work_order_detail_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/work-orders/{id} returns detailed contractor view."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}
    wo1_id = contractor_dashboard_setup["wo1"].id

    res = api_client.get(f"/api/v1/contractor/dashboard/work-orders/{wo1_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == wo1_id
    assert data["road_name"] == "MG Road"
    assert data["grievance_issue_category"] == "POTHOLE"
    assert data["current_progress"] == 60
    assert data["rework_required"] is True
    assert "edges" in data["latest_rejection_notes"]


def test_contractor_dashboard_pending_verification_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/pending-verification returns pending verification queue."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    res = api_client.get("/api/v1/contractor/dashboard/pending-verification", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["work_order_id"] == contractor_dashboard_setup["wo2"].id


def test_contractor_dashboard_rework_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/rework returns rework queue with rejection notes."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    res = api_client.get("/api/v1/contractor/dashboard/rework", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["work_order_id"] == contractor_dashboard_setup["wo1"].id
    assert "edges" in items[0]["rejection_message"]


def test_contractor_dashboard_workload_api(api_client: TestClient, contractor_dashboard_setup):
    """Verify GET /api/v1/contractor/dashboard/workload returns personal workload statistics."""
    alice = contractor_dashboard_setup["contractor_a"]
    headers = {"X-Actor-User-ID": alice.id, "X-Actor-Role": "CONTRACTOR"}

    res = api_client.get("/api/v1/contractor/dashboard/workload", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_assignments"] == 2
    assert data["active_assignments"] == 1
    assert data["pending_verification"] == 1
    assert data["rework_required"] == 1
    assert data["resolved_completed"] == 0
    assert data["average_completion_percentage"] == 30.0
