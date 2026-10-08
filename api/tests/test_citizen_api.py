"""API integration tests for Citizen Platform routes (/api/v1/citizen/...)."""

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
def citizen_api_setup(db_session: Session):
    """Seed test database with users and road segment."""
    gov_user = User(
        name="Officer Bob",
        email="officer.bob@city.gov.in",
        role=UserRole.GOVERNMENT_OFFICER,
    )
    contractor_user = User(
        name="Contractor Alice",
        email="alice@buildcorp.com",
        role=UserRole.CONTRACTOR,
    )
    citizen_a = User(
        name="Dave Citizen",
        email="dave@example.com",
        role=UserRole.CITIZEN,
    )
    citizen_b = User(
        name="Eve Citizen",
        email="eve@example.com",
        role=UserRole.CITIZEN,
    )
    db_session.add_all([gov_user, contractor_user, citizen_a, citizen_b])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-BLR-303",
        road_name="100 Feet Road Sec 1",
        area="Indiranagar",
        latitude=12.9784,
        longitude=77.6408,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.commit()

    return {
        "gov_user": gov_user,
        "contractor_user": contractor_user,
        "citizen_a": citizen_a,
        "citizen_b": citizen_b,
        "road": road,
    }


def test_citizen_create_grievance_api(api_client: TestClient, citizen_api_setup):
    """Verify POST /api/v1/citizen/grievances creates report with SUBMITTED status."""
    citizen = citizen_api_setup["citizen_a"]
    headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}

    payload = {
        "issue_category": "POTHOLE",
        "description": "Large pothole causing traffic disruption near metro station",
        "latitude": 12.9785,
        "longitude": 77.6409,
        "road_segment_id": "SEG-BLR-303",
    }
    res = api_client.post("/api/v1/citizen/grievances", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["citizen_id"] == citizen.id
    assert data["status"] == "SUBMITTED"
    assert data["road_id"] == citizen_api_setup["road"].id


def test_citizen_list_and_details_ownership_protection_api(api_client: TestClient, citizen_api_setup):
    """Verify citizen listing is scoped and details return 403 for unauthorized citizen."""
    citizen_a = citizen_api_setup["citizen_a"]
    citizen_b = citizen_api_setup["citizen_b"]
    headers_a = {"X-Actor-User-ID": citizen_a.id, "X-Actor-Role": "CITIZEN"}
    headers_b = {"X-Actor-User-ID": citizen_b.id, "X-Actor-Role": "CITIZEN"}

    # Citizen A creates grievance
    res_create = api_client.post(
        "/api/v1/citizen/grievances",
        headers=headers_a,
        json={
            "issue_category": "ROAD_CRACK",
            "description": "Deep alligator cracking along lane 2",
            "latitude": 12.9786,
            "longitude": 77.6410,
        },
    )
    assert res_create.status_code == 201
    grievance_id = res_create.json()["id"]

    # Citizen A lists grievances -> 1 item
    res_list_a = api_client.get("/api/v1/citizen/grievances", headers=headers_a)
    assert res_list_a.status_code == 200
    assert len(res_list_a.json()) == 1

    # Citizen B lists grievances -> 0 items
    res_list_b = api_client.get("/api/v1/citizen/grievances", headers=headers_b)
    assert res_list_b.status_code == 200
    assert len(res_list_b.json()) == 0

    # Citizen B accesses Citizen A's grievance -> 403 Forbidden
    res_det_b = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_b)
    assert res_det_b.status_code == 403

    # Citizen A accesses details -> 200 OK
    res_det_a = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_a)
    assert res_det_a.status_code == 200
    details = res_det_a.json()
    assert details["id"] == grievance_id
    assert details["status"] == "SUBMITTED"
    assert isinstance(details["timeline"], list)


def test_citizen_attach_evidence_api(api_client: TestClient, citizen_api_setup):
    """Verify POST /api/v1/citizen/grievances/{id}/evidence attaches evidence metadata."""
    citizen_a = citizen_api_setup["citizen_a"]
    headers_a = {"X-Actor-User-ID": citizen_a.id, "X-Actor-Role": "CITIZEN"}

    res_create = api_client.post(
        "/api/v1/citizen/grievances",
        headers=headers_a,
        json={
            "issue_category": "WATERLOGGING",
            "description": "Severe waterlogging after monsoon rain",
            "latitude": 12.9787,
            "longitude": 77.6411,
        },
    )
    grievance_id = res_create.json()["id"]

    res_ev = api_client.post(
        f"/api/v1/citizen/grievances/{grievance_id}/evidence",
        headers=headers_a,
        json={
            "grievance_id": grievance_id,
            "file_name": "flooded_street.jpg",
            "file_type": "image/jpeg",
            "storage_path": "/uploads/flooded_street.jpg",
            "file_size_bytes": 312000,
        },
    )
    assert res_ev.status_code == 201
    ev_data = res_ev.json()
    assert ev_data["file_name"] == "flooded_street.jpg"


def test_end_to_end_citizen_to_resolution_lifecycle(api_client: TestClient, citizen_api_setup):
    """Full end-to-end integration test:
    Citizen submits -> Government accepts & creates work order -> Contractor starts & updates progress ->
    Contractor submits completion -> Government REJECTS (rework) -> Citizen views rework message ->
    Contractor re-submits completion -> Government APPROVES -> Grievance RESOLVED.
    """
    citizen = citizen_api_setup["citizen_a"]
    gov = citizen_api_setup["gov_user"]
    contractor = citizen_api_setup["contractor_user"]

    headers_c = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    headers_g = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}
    headers_k = {"X-Actor-User-ID": contractor.id, "X-Actor-Role": "CONTRACTOR"}

    # 1. Citizen submits grievance
    res_sub = api_client.post(
        "/api/v1/citizen/grievances",
        headers=headers_c,
        json={
            "issue_category": "POTHOLE",
            "description": "Deep crater on 100 Feet Road",
            "latitude": 12.9784,
            "longitude": 77.6408,
            "road_segment_id": "SEG-BLR-303",
        },
    )
    grievance_id = res_sub.json()["id"]

    # 2. Government accepts & creates work order
    api_client.post(
        f"/api/v1/government/grievances/{grievance_id}/review",
        headers=headers_g,
        json={"decision": "ACCEPT", "notes": "Road damage verified on site."},
    )
    res_wo = api_client.post(
        f"/api/v1/government/grievances/{grievance_id}/work-orders",
        headers=headers_g,
        json={
            "title": "Repair crater on 100 Feet Road",
            "description": "Asphalt fill and compaction",
            "priority": "HIGH",
            "assigned_contractor_id": contractor.id,
        },
    )
    work_order_id = res_wo.json()["id"]

    # 3. Contractor accepts, starts & updates progress (50%)
    api_client.post(f"/api/v1/contractor/work-orders/{work_order_id}/accept", headers=headers_k)
    api_client.post(f"/api/v1/contractor/work-orders/{work_order_id}/start", headers=headers_k)
    api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=headers_k,
        json={"progress_percentage": 50, "note": "Sub-base laid"},
    )

    # Citizen checks progress
    res_det1 = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_c)
    assert res_det1.status_code == 200
    det1 = res_det1.json()
    assert det1["status"] == "IN_PROGRESS"
    assert det1["work_progress"]["progress_percentage"] == 50

    # 4. Contractor submits completion for verification
    api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/submit",
        headers=headers_k,
        json={"completion_note": "Asphalt patch completed."},
    )

    # Citizen checks status (PENDING_VERIFICATION, NOT RESOLVED)
    res_det2 = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_c)
    det2 = res_det2.json()
    assert det2["status"] == "PENDING_VERIFICATION"
    assert det2["status"] != "RESOLVED"

    # 5. Government officer REJECTS completion (requests rework)
    api_client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=headers_g,
        json={"decision": "REJECT", "notes": "Compaction insufficient at edges. Please re-roll."},
    )

    # Citizen checks details -> sees rework status
    res_det3 = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_c)
    det3 = res_det3.json()
    assert det3["status"] == "IN_PROGRESS"
    assert det3["rejection_info"] is not None
    assert det3["rejection_info"]["is_reverted_for_rework"] is True

    # 6. Contractor re-submits completion after rework
    api_client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/submit",
        headers=headers_k,
        json={"completion_note": "Edges re-rolled and sealed."},
    )

    # 7. Government officer APPROVES completion
    api_client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=headers_g,
        json={"decision": "APPROVE", "notes": "Verified. Quality approved."},
    )

    # 8. Citizen checks final status -> RESOLVED!
    res_det_final = api_client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=headers_c)
    assert res_det_final.status_code == 200
    det_final = res_det_final.json()
    assert det_final["status"] == "RESOLVED"
    assert "verified" in det_final["work_progress"]["status_display"].lower()
