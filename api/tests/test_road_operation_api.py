"""API integration tests for Road Operations endpoints (/api/v1/government/road-operations and /api/v1/citizen/road-operations)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from api.main import app
from backend.database import Base, get_db
from backend.models.user import User, UserRole
from backend.models.road import RoadSegment
from backend.models.road_operation import RoadOperationStatus, RoadOperationType


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
def road_op_setup(db_session: Session):
    """Seed database with users and road segment for API testing."""
    gov = User(name="Officer Alice", email="alice@city.gov.in", role=UserRole.GOVERNMENT_OFFICER)
    contractor = User(name="BuildCorp", email="build@contractor.com", role=UserRole.CONTRACTOR)
    citizen = User(name="Bob Citizen", email="bob@citizen.com", role=UserRole.CITIZEN)

    db_session.add_all([gov, contractor, citizen])
    db_session.flush()

    road = RoadSegment(
        segment_id="SEG-OUTER-RING",
        road_name="Outer Ring Road",
        area="Marathahalli",
        latitude=12.9568,
        longitude=77.7011,
        road_type="ASPHALT",
    )
    alt_road = RoadSegment(
        segment_id="SEG-OLD-AIRPORT",
        road_name="Old Airport Road",
        area="Domlur",
        latitude=12.9600,
        longitude=77.6500,
        road_type="ASPHALT",
    )
    db_session.add_all([road, alt_road])
    db_session.commit()

    return {
        "gov": gov,
        "contractor": contractor,
        "citizen": citizen,
        "road": road,
        "alt_road": alt_road,
    }


def test_road_operation_authorization_api(api_client: TestClient, road_op_setup):
    """Verify non-government roles receive HTTP 403 Forbidden for mutation operations."""
    citizen = road_op_setup["citizen"]
    contractor = road_op_setup["contractor"]
    now = datetime.now(timezone.utc).isoformat()
    exp_end = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    payload = {
        "title": "Unauthorized Closure Attempt",
        "description": "Attempting to create closure",
        "reason": "Testing auth",
        "start_time": now,
        "expected_end_time": exp_end,
    }

    # Citizen -> 403
    c_headers = {"X-Actor-User-ID": citizen.id, "X-Actor-Role": "CITIZEN"}
    res_c = api_client.post("/api/v1/government/road-operations", json=payload, headers=c_headers)
    assert res_c.status_code == 403

    # Contractor -> 403
    k_headers = {"X-Actor-User-ID": contractor.id, "X-Actor-Role": "CONTRACTOR"}
    res_k = api_client.post("/api/v1/government/road-operations", json=payload, headers=k_headers)
    assert res_k.status_code == 403


def test_road_operation_government_crud_api(api_client: TestClient, road_op_setup):
    """Verify government officer can create, list, view, update, activate, and complete road operations."""
    gov = road_op_setup["gov"]
    road = road_op_setup["road"]
    alt_road = road_op_setup["alt_road"]
    headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    now_dt = datetime.now(timezone.utc)
    now_str = now_dt.isoformat()
    exp_str = (now_dt + timedelta(days=2)).isoformat()

    # 1. Create Operation
    create_payload = {
        "title": "Outer Ring Road Resurfacing",
        "description": "Full lane closure for flyover joint repair",
        "reason": "Flyover expansion joint damage",
        "operation_type": "ROAD_CLOSURE",
        "road_id": road.id,
        "start_time": now_str,
        "expected_end_time": exp_str,
        "alternative_route_name": "Old Airport Road Detour",
        "alternative_route_instructions": "Divert via Kadubeesanahalli to Old Airport Road",
        "alternative_road_id": alt_road.id,
        "alternative_distance_km": 4.2,
    }
    res_create = api_client.post("/api/v1/government/road-operations", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    op_data = res_create.json()
    op_id = op_data["id"]
    assert op_data["status"] == "PLANNED"
    assert op_data["road_name"] == "Outer Ring Road"
    assert op_data["alternative_road_name"] == "Old Airport Road"

    # 2. List Operations
    res_list = api_client.get("/api/v1/government/road-operations", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. Get Detail
    res_detail = api_client.get(f"/api/v1/government/road-operations/{op_id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == op_id
    assert len(res_detail.json()["history"]) > 0

    # 4. Activate Operation
    res_act = api_client.post(f"/api/v1/government/road-operations/{op_id}/activate", headers=headers)
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "ACTIVE"

    # 5. Update Operation Details
    patch_payload = {"description": "Updated closure description: Crews operating 24/7"}
    res_patch = api_client.patch(f"/api/v1/government/road-operations/{op_id}", json=patch_payload, headers=headers)
    assert res_patch.status_code == 200
    assert "24/7" in res_patch.json()["description"]

    # 6. Complete Operation
    res_comp = api_client.post(f"/api/v1/government/road-operations/{op_id}/complete", headers=headers)
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"
    assert res_comp.json()["actual_end_time"] is not None


def test_road_operation_citizen_public_api(api_client: TestClient, road_op_setup):
    """Verify citizen public listing and detail reading without mutation authority."""
    gov = road_op_setup["gov"]
    road = road_op_setup["road"]
    gov_headers = {"X-Actor-User-ID": gov.id, "X-Actor-Role": "GOVERNMENT_OFFICER"}

    now_dt = datetime.now(timezone.utc)
    create_payload = {
        "title": "Public Waterlogging Hazard Block",
        "description": "Waterlogging under bridge",
        "reason": "Heavy rainfall drainage overflow",
        "operation_type": "HAZARD_BLOCK",
        "road_id": road.id,
        "start_time": now_dt.isoformat(),
        "expected_end_time": (now_dt + timedelta(hours=12)).isoformat(),
        "alternative_route_name": "Service Road Detour",
        "alternative_route_instructions": "Use left service lane",
    }
    res_create = api_client.post("/api/v1/government/road-operations", json=create_payload, headers=gov_headers)
    op_id = res_create.json()["id"]

    # Activate
    api_client.post(f"/api/v1/government/road-operations/{op_id}/activate", headers=gov_headers)

    # Citizen list public active operations
    res_citizen_list = api_client.get("/api/v1/citizen/road-operations")
    assert res_citizen_list.status_code == 200
    ops = res_citizen_list.json()
    assert len(ops) >= 1
    assert ops[0]["title"] == "Public Waterlogging Hazard Block"

    # Citizen detail view
    res_citizen_detail = api_client.get(f"/api/v1/citizen/road-operations/{op_id}")
    assert res_citizen_detail.status_code == 200
    assert res_citizen_detail.json()["alternative_route_name"] == "Service Road Detour"
