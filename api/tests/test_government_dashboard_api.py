"""API integration tests for Government Dashboard endpoints (/api/v1/government/dashboard/...)."""

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
from backend.models.ml_analysis import MLAnalysisResult
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress


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
def dashboard_api_setup(db_session: Session):
    """Seed test database with users, road segment, grievance, ML analysis, and work orders."""
    gov_officer = User(
        name="Officer Alice",
        email="officer.alice@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor = User(
        name="BuildCorp Contractors",
        email="buildcorp@contractor.com",
        role=UserRole.CONTRACTOR,
    )
    citizen = User(
        name="Bob Citizen",
        email="bob@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_officer, contractor, citizen])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-BLR-505",
        road_name="Bannerghatta Road Sec 3",
        area="Jayanagar",
        latitude=12.9250,
        longitude=77.5938,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    # Grievances
    g1 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Pothole near Jayanagar 4th block",
        issue_category="POTHOLE",
        latitude=12.9255,
        longitude=77.5940,
        status=GrievanceStatus.IN_PROGRESS,
    )
    g2 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Streetlight failure near park",
        issue_category="STREETLIGHT",
        latitude=12.9260,
        longitude=77.5945,
        status=GrievanceStatus.PENDING_VERIFICATION,
    )
    db_session.add_all([g1, g2])
    db_session.flush()

    # ML Analysis
    ml1 = MLAnalysisResult(
        grievance_id=g1.id,
        pipeline_version="v1",
        overall_status="SUCCESS",
        severity_prediction={"severity_score": 88.0, "severity_level": "CRITICAL"},
        failure_prediction={"failure_probability": 0.91, "risk_level": "CRITICAL"},
        maintenance_priority={"priority_score": 95.0, "priority_level": "CRITICAL", "reasons": ["Severe pothole damage"]},
    )
    db_session.add(ml1)

    # Work orders
    wo1 = WorkOrder(
        grievance_id=g1.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor.id,
        title="Repair Pothole Jayanagar",
        description="Asphalt compaction",
        priority="CRITICAL",
        status=WorkOrderStatus.IN_PROGRESS,
    )
    wo2 = WorkOrder(
        grievance_id=g2.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor.id,
        title="Fix Streetlight",
        description="Replace lamp assembly",
        priority="HIGH",
        status=WorkOrderStatus.PENDING_VERIFICATION,
    )
    db_session.add_all([wo1, wo2])
    db_session.flush()

    p1 = WorkProgress(
        work_order_id=wo1.id,
        contractor_id=contractor.id,
        progress_percentage=75,
        note="75% finished",
    )
    db_session.add(p1)
    db_session.commit()

    return {
        "gov_officer": gov_officer,
        "contractor": contractor,
        "citizen": citizen,
        "road": road,
        "g1": g1,
        "g2": g2,
        "wo1": wo1,
        "wo2": wo2,
    }


def test_dashboard_authorization_rejection(api_client: TestClient, dashboard_api_setup):
    """Verify non-government role access yields 403 Forbidden."""
    citizen = dashboard_api_setup["citizen"]
    contractor = dashboard_api_setup["contractor"]

    # Citizen actor -> 403
    citizen_headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    res_c = api_client.get("/api/v1/government/dashboard/overview", headers=citizen_headers)
    assert res_c.status_code == 403

    # Contractor actor -> 403
    contractor_headers = {"X-Actor-User-ID": contractor.id, "X-Actor-Role": "CONTRACTOR"}
    res_k = api_client.get("/api/v1/government/dashboard/overview", headers=contractor_headers)
    assert res_k.status_code == 403


def test_dashboard_overview_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/overview returns aggregate stats."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    res = api_client.get("/api/v1/government/dashboard/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_grievances"] == 2
    assert data["active_contractors_count"] == 1
    assert data["pending_verifications_count"] == 1


def test_dashboard_grievances_list_and_search_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/grievances filtering and search."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    # Search filter
    res_search = api_client.get("/api/v1/government/dashboard/grievances?search=Jayanagar", headers=headers)
    assert res_search.status_code == 200
    items = res_search.json()
    assert len(items) == 1
    assert items[0]["issue_category"] == "POTHOLE"

    # Category filter
    res_cat = api_client.get("/api/v1/government/dashboard/grievances?issue_category=STREETLIGHT", headers=headers)
    assert res_cat.status_code == 200
    assert len(res_cat.json()) == 1


def test_dashboard_grievance_detail_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/grievances/{id} returns complete case detail."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}
    g1_id = dashboard_api_setup["g1"].id

    res = api_client.get(f"/api/v1/government/dashboard/grievances/{g1_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == g1_id
    assert data["citizen_name"] == "Bob Citizen"
    assert data["road_name"] == "Bannerghatta Road Sec 3"
    assert data["ml_analysis"] is not None
    assert data["work_order"]["title"] == "Repair Pothole Jayanagar"


def test_dashboard_priority_queue_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/priority-queue returns prioritized queue."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    res = api_client.get("/api/v1/government/dashboard/priority-queue", headers=headers)
    assert res.status_code == 200
    queue = res.json()
    assert len(queue) == 1
    assert queue[0]["priority_score"] == 95.0
    assert queue[0]["priority_level"] == "CRITICAL"


def test_dashboard_verification_queue_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/verification-queue returns pending verifications."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    res = api_client.get("/api/v1/government/dashboard/verification-queue", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["work_order_id"] == dashboard_api_setup["wo2"].id


def test_dashboard_work_orders_monitoring_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/work-orders returns monitoring list."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    res = api_client.get("/api/v1/government/dashboard/work-orders", headers=headers)
    assert res.status_code == 200
    wos = res.json()
    assert len(wos) == 2


def test_dashboard_contractors_summary_api(api_client: TestClient, dashboard_api_setup):
    """Verify GET /api/v1/government/dashboard/contractors returns workload metrics."""
    gov = dashboard_api_setup["gov_officer"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    res = api_client.get("/api/v1/government/dashboard/contractors", headers=headers)
    assert res.status_code == 200
    contractors = res.json()
    assert len(contractors) == 1
    assert contractors[0]["assigned_work_orders_count"] == 2
