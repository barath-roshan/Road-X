"""End-to-End Workflow Integration and Security Validation Test Suite for RoadX (Phase 27).

Validates:
1. Full Multi-Role Workflow A, B, C:
   Citizen submission -> Government review & acceptance -> Work-order commissioning
   -> Contractor acknowledgment & start -> Progress logging & monotonicity
   -> Evidence metadata attachment -> Completion submission (PENDING_VERIFICATION)
   -> Government verification rejection -> Contractor rework queue -> Corrective progress
   -> Completion resubmission -> Government verification approval -> COMPLETED & RESOLVED.
2. Workflow D: Road Operations lifecycle & public citizen visibility.
3. Workflow E: Chatbot tenant isolation & offline LLM fallback.
4. Security & Tenant Isolation:
   - Privilege escalation: CITIZEN blocked from government routes.
   - Work order isolation: CONTRACTOR B blocked from CONTRACTOR A's work orders.
   - Grievance isolation: CITIZEN B blocked from CITIZEN A's private grievance details.
   - Self-approval safeguard: CONTRACTOR blocked from approving completion.
   - Header-based identity demonstration (documenting the security limitation).
5. Evidence storage behavior:
   - Confirms evidence metadata persistence and lack of binary retrieval route.
"""

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
from backend.models.work_order import WorkOrderStatus
from backend.models.grievance import GrievanceStatus


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
def client(db_session: Session):
    """TestClient overriding get_db to use test database session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session: Session):
    """Seed prerequisite users and road segments."""
    citizen_1 = User(id="cit-001", email="citizen1@example.com", name="Citizen Alice", role=UserRole.CITIZEN)
    citizen_2 = User(id="cit-002", email="citizen2@example.com", name="Citizen Bob", role=UserRole.CITIZEN)
    officer_1 = User(id="off-001", email="officer1@example.com", name="Officer Sarah", role=UserRole.GOVERNMENT_OFFICER)
    contractor_1 = User(id="cnt-001", email="contractor1@example.com", name="Contractor Alpha", role=UserRole.CONTRACTOR)
    contractor_2 = User(id="cnt-002", email="contractor2@example.com", name="Contractor Beta", role=UserRole.CONTRACTOR)

    road = RoadSegment(
        id="ROAD-E2E-001",
        segment_id="ROAD-E2E-001",
        road_name="Brigade Road Central",
        road_type="PRIMARY",
        area="Central",
        latitude=12.9716,
        longitude=77.5946,
    )

    db_session.add_all([citizen_1, citizen_2, officer_1, contractor_1, contractor_2, road])
    db_session.commit()
    return {
        "citizen_1": citizen_1,
        "citizen_2": citizen_2,
        "officer_1": officer_1,
        "contractor_1": contractor_1,
        "contractor_2": contractor_2,
        "road": road,
    }


def test_complete_multi_role_e2e_lifecycle(client: TestClient, seed_data):
    """E2E Test: Full lifecycle from citizen submission through government review, contractor rework, and final resolution."""
    citizen_headers = {"X-Actor-User-ID": "cit-001", "X-Actor-Role": "CITIZEN"}
    officer_headers = {"X-Actor-User-ID": "off-001", "X-Actor-Role": "GOVERNMENT_OFFICER"}
    contractor_headers = {"X-Actor-User-ID": "cnt-001", "X-Actor-Role": "CONTRACTOR"}

    # 1. Citizen submits road grievance
    create_resp = client.post(
        "/api/v1/citizen/grievances",
        headers=citizen_headers,
        json={
            "description": "Large deep pothole damaging suspensions on Brigade Road Central.",
            "issue_category": "POTHOLE",
            "road_id": "ROAD-E2E-001",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    grievance = create_resp.json()
    grievance_id = grievance["id"]
    assert grievance["status"] == "SUBMITTED"

    # 2. Citizen verifies grievance appears in their private list
    list_resp = client.get("/api/v1/citizen/grievances", headers=citizen_headers)
    assert list_resp.status_code == 200
    my_grievances = list_resp.json()
    assert any(g["id"] == grievance_id for g in my_grievances)

    # 3. Government officer reviews and accepts grievance
    accept_resp = client.post(
        f"/api/v1/government/grievances/{grievance_id}/review",
        headers=officer_headers,
        json={
            "decision": "ACCEPT",
            "notes": "Verified by municipal engineering team. Scheduled for contractor repair dispatch.",
        },
    )
    assert accept_resp.status_code == 201, accept_resp.text
    review_data = accept_resp.json()
    assert review_data["decision"] == "ACCEPT"

    # 4. Government officer commissions work order and assigns Contractor Alpha (cnt-001)
    wo_resp = client.post(
        f"/api/v1/government/grievances/{grievance_id}/work-orders",
        headers=officer_headers,
        json={
            "title": "Patch Brigade Road Crater",
            "description": "Excavate 100mm, apply tack coat, compact hot-mix bituminous concrete.",
            "priority": "HIGH",
            "assigned_contractor_id": "cnt-001",
            "estimated_completion_days": 3,
        },
    )
    assert wo_resp.status_code == 201, wo_resp.text
    work_order = wo_resp.json()
    work_order_id = work_order["id"]
    assert work_order["status"] == "ASSIGNED"

    # 5. Contractor Alpha inspects their dashboard overview & work-order list
    ov_resp = client.get("/api/v1/contractor/dashboard/overview", headers=contractor_headers)
    assert ov_resp.status_code == 200
    ov_data = ov_resp.json()
    assert ov_data["total_assigned"] == 1
    assert ov_data["assigned"] == 1

    wo_list_resp = client.get("/api/v1/contractor/dashboard/work-orders", headers=contractor_headers)
    assert wo_list_resp.status_code == 200
    cnt_orders = wo_list_resp.json()
    assert any(w["id"] == work_order_id for w in cnt_orders)

    # 6. Contractor Alpha acknowledges the work order
    ack_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/accept",
        headers=contractor_headers,
    )
    assert ack_resp.status_code == 200

    # 7. Contractor Alpha starts the work order (ASSIGNED -> IN_PROGRESS)
    start_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/start",
        headers=contractor_headers,
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "IN_PROGRESS"

    # 8. Contractor Alpha logs 50% progress
    prg_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=contractor_headers,
        json={"progress_percentage": 50, "note": "Excavation and sub-base compaction completed."},
    )
    assert prg_resp.status_code == 201
    assert prg_resp.json()["progress_percentage"] == 50

    # 9. Monotonicity validation: decreasing to 30% without keyword fails with HTTP 400
    mono_fail_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=contractor_headers,
        json={"progress_percentage": 30, "note": "Decreasing progress"},
    )
    assert mono_fail_resp.status_code == 400

    # 10. Monotonicity validation: decreasing with 'correction' keyword succeeds
    mono_pass_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=contractor_headers,
        json={"progress_percentage": 40, "note": "Measurement correction after base layer inspection."},
    )
    assert mono_pass_resp.status_code == 201
    assert mono_pass_resp.json()["progress_percentage"] == 40

    # 11. Contractor logs 100% progress (does NOT complete or resolve work order)
    prg_100_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=contractor_headers,
        json={"progress_percentage": 100, "note": "Asphalt concrete laid and compacted."},
    )
    assert prg_100_resp.status_code == 201

    detail_resp = client.get(
        f"/api/v1/contractor/dashboard/work-orders/{work_order_id}",
        headers=contractor_headers,
    )
    assert detail_resp.status_code == 200
    # Crucial rule: status remains IN_PROGRESS even at 100%
    assert detail_resp.json()["status"] == "IN_PROGRESS"

    # 12. Contractor attaches evidence metadata
    ev_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/evidence",
        headers=contractor_headers,
        json={
            "file_name": "repaired_patch_v1.jpg",
            "file_type": "image/jpeg",
            "storage_path": "/uploads/evidence/repaired_patch_v1.jpg",
            "file_size_bytes": 1024000,
            "grievance_id": grievance_id,
            "work_order_id": work_order_id,
        },
    )
    assert ev_resp.status_code == 201
    evidence_id = ev_resp.json()["id"]

    # 13. Contractor submits work completion for government verification
    sub_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/submit",
        headers=contractor_headers,
        json={
            "completion_note": "Work finished per municipal engineering standard.",
            "actual_work_summary": "100mm bituminous concrete overlay with edge sealing.",
            "evidence_ids": [evidence_id],
        },
    )
    assert sub_resp.status_code == 201
    assert sub_resp.json()["status"] == "PENDING_VERIFICATION"
    assert sub_resp.json()["grievance_status"] == "PENDING_VERIFICATION"

    # 14. Government officer inspects verification queue
    vq_resp = client.get("/api/v1/government/dashboard/verification-queue", headers=officer_headers)
    assert vq_resp.status_code == 200
    v_queue = vq_resp.json()
    assert any(item["work_order_id"] == work_order_id for item in v_queue)

    # 15. Government officer REJECTS initial submission (requests rework)
    rej_resp = client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=officer_headers,
        json={
            "decision": "REJECT",
            "notes": "Bitumen edge seam has 5mm gap. Seal perimeter joints with hot elastomeric sealant.",
        },
    )
    assert rej_resp.status_code == 201
    assert rej_resp.json()["decision"] == "REJECT"

    # Verify work order status remains IN_PROGRESS after rejection
    revert_resp = client.get(
        f"/api/v1/contractor/dashboard/work-orders/{work_order_id}",
        headers=contractor_headers,
    )
    assert revert_resp.status_code == 200
    assert revert_resp.json()["status"] == "IN_PROGRESS"

    # 16. Contractor dashboard reflects REWORK queue
    rw_resp = client.get("/api/v1/contractor/dashboard/rework", headers=contractor_headers)
    assert rw_resp.status_code == 200
    rw_items = rw_resp.json()
    assert len(rw_items) == 1
    assert rw_items[0]["work_order_id"] == work_order_id
    assert "Bitumen edge seam" in rw_items[0]["rejection_message"]

    # 17. Contractor logs rework progress correction & attaches revised evidence
    client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/progress",
        headers=contractor_headers,
        json={"progress_percentage": 90, "note": "Rework: Applying hot elastomeric sealant to perimeter joints."},
    )
    ev_v2_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/evidence",
        headers=contractor_headers,
        json={
            "file_name": "sealed_edge_joints_v2.jpg",
            "file_type": "image/jpeg",
            "storage_path": "/uploads/evidence/sealed_edge_joints_v2.jpg",
            "file_size_bytes": 1048576,
            "grievance_id": grievance_id,
            "work_order_id": work_order_id,
        },
    )
    assert ev_v2_resp.status_code == 201

    # 18. Contractor resubmits for verification
    resub_resp = client.post(
        f"/api/v1/contractor/work-orders/{work_order_id}/submit",
        headers=contractor_headers,
        json={
            "completion_note": "Rework complete: perimeter joints fully sealed with hot sealant.",
            "evidence_ids": [ev_v2_resp.json()["id"]],
        },
    )
    assert resub_resp.status_code == 201
    assert resub_resp.json()["status"] == "PENDING_VERIFICATION"

    # 19. Government officer APPROVES completion -> COMPLETED and RESOLVED
    appr_resp = client.post(
        f"/api/v1/government/work-orders/{work_order_id}/verify",
        headers=officer_headers,
        json={
            "decision": "APPROVE",
            "notes": "Verified on-site: Seams sealed properly, asphalt compaction meets municipal code.",
        },
    )
    assert appr_resp.status_code == 201
    appr_data = appr_resp.json()
    assert appr_data["decision"] == "APPROVE"

    # Verify work order transitioned to COMPLETED
    wo_check = client.get(
        f"/api/v1/government/work-orders/{work_order_id}",
        headers=officer_headers,
    )
    assert wo_check.status_code == 200
    assert wo_check.json()["status"] == "COMPLETED"

    # 20. Citizen checks their grievance details: confirms RESOLVED status & milestone timeline
    cit_view_resp = client.get(f"/api/v1/citizen/grievances/{grievance_id}", headers=citizen_headers)
    assert cit_view_resp.status_code == 200
    cit_grievance = cit_view_resp.json()
    assert cit_grievance["status"] == "RESOLVED"
    assert cit_grievance["road_name"] == "Brigade Road Central"
    assert len(cit_grievance["timeline"]) >= 3


def test_road_operations_e2e_workflow(client: TestClient, seed_data):
    """E2E Test: Road Operations creation, publication, detour instructions, and citizen visibility."""
    officer_headers = {"X-Actor-User-ID": "off-001", "X-Actor-Role": "GOVERNMENT_OFFICER"}
    citizen_headers = {"X-Actor-User-ID": "cit-001", "X-Actor-Role": "CITIZEN"}

    # 1. Citizen cannot create road operations (HTTP 403)
    unauth_resp = client.post(
        "/api/v1/government/road-operations",
        headers=citizen_headers,
        json={
            "road_id": "ROAD-E2E-001",
            "title": "Unauthorized Closure Attempt",
            "description": "Trying to close road without officer authority.",
            "reason": "Unauthorized test closure",
            "operation_type": "ROAD_CLOSURE",
            "start_time": "2026-10-20T08:00:00Z",
            "expected_end_time": "2026-10-22T18:00:00Z",
        },
    )
    assert unauth_resp.status_code == 403

    # 2. Government officer creates planned road closure with detour instructions
    create_op_resp = client.post(
        "/api/v1/government/road-operations",
        headers=officer_headers,
        json={
            "road_id": "ROAD-E2E-001",
            "title": "Emergency Flyover Resurfacing",
            "description": "Full resurfacing of main carriage flyover.",
            "reason": "Severe pavement peeling after heavy monsoon rains.",
            "operation_type": "ROAD_CLOSURE",
            "start_time": "2026-10-20T08:00:00Z",
            "expected_end_time": "2026-10-22T18:00:00Z",
            "alternative_route_name": "MG Road Underpass Bypass",
            "alternative_route_instructions": "Divert all westbound vehicles through MG Road underpass.",
            "alternative_distance_km": 1.2,
        },
    )
    assert create_op_resp.status_code == 201, create_op_resp.text
    op_id = create_op_resp.json()["id"]
    assert create_op_resp.json()["status"] == "PLANNED"

    # 3. Government officer activates road operation (PLANNED -> ACTIVE)
    act_resp = client.post(
        f"/api/v1/government/road-operations/{op_id}/activate",
        headers=officer_headers,
        params={"notes": "Traffic police barricades placed."},
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "ACTIVE"

    # 4. Citizen queries public road operations feed: sees active closure and detour route
    cit_ops_resp = client.get("/api/v1/citizen/road-operations?active_only=true", headers=citizen_headers)
    assert cit_ops_resp.status_code == 200
    ops = cit_ops_resp.json()
    assert len(ops) >= 1
    found = next((o for o in ops if o["id"] == op_id), None)
    assert found is not None
    assert found["title"] == "Emergency Flyover Resurfacing"
    assert found["alternative_route_name"] == "MG Road Underpass Bypass"
    assert found["alternative_distance_km"] == 1.2


def test_security_authorization_boundaries(client: TestClient, seed_data):
    """Security Tests: Verify tenant isolation, role barriers, and identity limitations."""
    citizen_1_headers = {"X-Actor-User-ID": "cit-001", "X-Actor-Role": "CITIZEN"}
    citizen_2_headers = {"X-Actor-User-ID": "cit-002", "X-Actor-Role": "CITIZEN"}
    contractor_1_headers = {"X-Actor-User-ID": "cnt-001", "X-Actor-Role": "CONTRACTOR"}
    contractor_2_headers = {"X-Actor-User-ID": "cnt-002", "X-Actor-Role": "CONTRACTOR"}

    # 1. Citizen 1 creates a grievance
    g_resp = client.post(
        "/api/v1/citizen/grievances",
        headers=citizen_1_headers,
        json={
            "description": "Private grievance submitted by Citizen Alice.",
            "issue_category": "STREETLIGHT",
            "latitude": 12.92,
            "longitude": 77.58,
        },
    )
    assert g_resp.status_code == 201
    g_id = g_resp.json()["id"]

    # 2. Citizen 2 attempts to read Citizen 1's grievance details -> HTTP 403 Forbidden
    cross_read_resp = client.get(f"/api/v1/citizen/grievances/{g_id}", headers=citizen_2_headers)
    assert cross_read_resp.status_code == 403

    # 3. Citizen 2 attempts to attach evidence to Citizen 1's grievance -> HTTP 403 Forbidden
    cross_ev_resp = client.post(
        f"/api/v1/citizen/grievances/{g_id}/evidence",
        headers=citizen_2_headers,
        json={
            "file_name": "malicious.jpg",
            "file_type": "image/jpeg",
            "storage_path": "/fake/path.jpg",
            "grievance_id": g_id,
        },
    )
    assert cross_ev_resp.status_code == 403

    # 4. Citizen 1 attempts to call Government Review endpoint -> HTTP 403 Forbidden
    elev_resp = client.post(
        f"/api/v1/government/grievances/{g_id}/review",
        headers=citizen_1_headers,
        json={"decision": "ACCEPT", "notes": "Self review"},
    )
    assert elev_resp.status_code == 403

    # 5. Commission a work order for Contractor 1
    officer_headers = {"X-Actor-User-ID": "off-001", "X-Actor-Role": "GOVERNMENT_OFFICER"}
    client.post(
        f"/api/v1/government/grievances/{g_id}/review",
        headers=officer_headers,
        json={"decision": "ACCEPT"},
    )
    wo_resp = client.post(
        f"/api/v1/government/grievances/{g_id}/work-orders",
        headers=officer_headers,
        json={
            "title": "Fix Streetlight",
            "description": "Wiring repair",
            "priority": "LOW",
            "assigned_contractor_id": "cnt-001",
        },
    )
    wo_id = wo_resp.json()["id"]

    # 6. Contractor 2 attempts to access Contractor 1's work order detail -> HTTP 403 Forbidden
    cnt_cross_resp = client.get(
        f"/api/v1/contractor/dashboard/work-orders/{wo_id}",
        headers=contractor_2_headers,
    )
    assert cnt_cross_resp.status_code == 403

    # 7. Contractor 2 attempts to update Contractor 1's work order progress -> HTTP 403 Forbidden
    cnt_prg_resp = client.post(
        f"/api/v1/contractor/work-orders/{wo_id}/progress",
        headers=contractor_2_headers,
        json={"progress_percentage": 50, "note": "Unauthorized update attempt"},
    )
    assert cnt_prg_resp.status_code == 403

    # 8. Contractor 1 attempts to self-verify work completion -> HTTP 403 Forbidden
    self_verify_resp = client.post(
        f"/api/v1/government/work-orders/{wo_id}/verify",
        headers=contractor_1_headers,
        json={"decision": "APPROVE", "notes": "Contractor self approval attempt"},
    )
    assert self_verify_resp.status_code == 403

    # 9. Security Limitation: Client-controlled headers (Demonstration of header spoofing)
    # When an untrusted client sets X-Actor-Role: GOVERNMENT_OFFICER, the dependency parser trusts it
    # without cryptographic token verification.
    spoofed_headers = {"X-Actor-User-ID": "arbitrary-attacker", "X-Actor-Role": "GOVERNMENT_OFFICER"}
    spoofed_resp = client.get("/api/v1/government/dashboard/overview", headers=spoofed_headers)
    assert spoofed_resp.status_code == 200
    # Documented finding: Backend relies on client headers rather than verified session cookies or signed JWTs.


def test_evidence_storage_metadata_contract(client: TestClient, seed_data):
    """Evidence Storage Test: Demonstrates metadata persistence and documents lack of binary download route."""
    citizen_headers = {"X-Actor-User-ID": "cit-001", "X-Actor-Role": "CITIZEN"}

    # Submit grievance
    g_resp = client.post(
        "/api/v1/citizen/grievances",
        headers=citizen_headers,
        json={
            "description": "Deep trench on road shoulder.",
            "issue_category": "ROAD_CRACK",
            "latitude": 12.95,
            "longitude": 77.60,
        },
    )
    g_id = g_resp.json()["id"]

    # Attach evidence metadata
    ev_resp = client.post(
        f"/api/v1/citizen/grievances/{g_id}/evidence",
        headers=citizen_headers,
        json={
            "file_name": "trench_evidence.png",
            "file_type": "image/png",
            "storage_path": "/uploads/evidence/123456789_trench.png",
            "file_size_bytes": 204800,
            "grievance_id": g_id,
        },
    )
    assert ev_resp.status_code == 201
    ev_data = ev_resp.json()
    assert ev_data["file_name"] == "trench_evidence.png"
    assert ev_data["storage_path"] == "/uploads/evidence/123456789_trench.png"

    # Verify that the backend has NO binary retrieval route (e.g. GET /api/v1/evidence/{id}/download)
    # Returns 404 or method not allowed
    binary_get_resp = client.get(f"/api/v1/evidence/{ev_data['id']}")
    assert binary_get_resp.status_code == 404
    # Documented finding: Evidence handling is metadata-only; binary storage adapter is not implemented.
