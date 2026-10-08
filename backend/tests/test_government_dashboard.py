"""Unit tests for Government Dashboard Service, analytics, queues, and role enforcement."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.ml_analysis import MLAnalysisResult
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole
from backend.models.work_order import WorkOrder, WorkOrderStatus
from backend.models.work_progress import WorkProgress
from backend.security import UserContext, UnauthorizedError
from backend.services.government_dashboard_service import GovernmentDashboardService


@pytest.fixture
def dashboard_setup_data(db_session: Session):
    """Seed test database with users, road segment, grievances, ML analysis, work orders, and progress."""
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
        segment_id="SEG-BLR-404",
        road_name="Hosur Main Road",
        area="Silk Board",
        latitude=12.9172,
        longitude=77.6228,
        road_type="ASPHALT",
    )
    db_session.add(road)
    db_session.flush()

    # Create 2 Grievances
    g1 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Pothole near Silk Board junction",
        issue_category="POTHOLE",
        latitude=12.9175,
        longitude=77.6230,
        status=GrievanceStatus.IN_PROGRESS,
    )
    g2 = Grievance(
        citizen_id=citizen.id,
        road_id=road.id,
        description="Flooding near bus stop",
        issue_category="WATERLOGGING",
        latitude=12.9180,
        longitude=77.6235,
        status=GrievanceStatus.PENDING_VERIFICATION,
    )
    db_session.add_all([g1, g2])
    db_session.flush()

    # ML Analysis for G1 (High Priority)
    ml1 = MLAnalysisResult(
        grievance_id=g1.id,
        pipeline_version="v1",
        overall_status="SUCCESS",
        severity_prediction={"severity_score": 85.0, "severity_level": "HIGH"},
        failure_prediction={"failure_probability": 0.88, "risk_level": "HIGH"},
        maintenance_priority={"priority_score": 92.5, "priority_level": "CRITICAL", "reasons": ["High failure probability"]},
    )
    db_session.add(ml1)

    # Work orders
    wo1 = WorkOrder(
        grievance_id=g1.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor.id,
        title="Pothole patch",
        description="Patch asphalt",
        priority="CRITICAL",
        status=WorkOrderStatus.IN_PROGRESS,
    )
    wo2 = WorkOrder(
        grievance_id=g2.id,
        road_id=road.id,
        created_by=gov_officer.id,
        assigned_contractor_id=contractor.id,
        title="Drainage clearance",
        description="Clear storm drain",
        priority="HIGH",
        status=WorkOrderStatus.PENDING_VERIFICATION,
    )
    db_session.add_all([wo1, wo2])
    db_session.flush()

    # Progress entry
    p1 = WorkProgress(
        work_order_id=wo1.id,
        contractor_id=contractor.id,
        progress_percentage=50,
        note="Half complete",
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


def test_dashboard_role_enforcement(db_session: Session, dashboard_setup_data):
    """Verify non-government roles get UnauthorizedError (403)."""
    service = GovernmentDashboardService(db_session)
    citizen_actor = UserContext(user_id=dashboard_setup_data["citizen"].id, role=UserRole.CITIZEN)
    contractor_actor = UserContext(user_id=dashboard_setup_data["contractor"].id, role=UserRole.CONTRACTOR)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    # Citizen access fails
    with pytest.raises(UnauthorizedError):
        service.get_overview(actor=citizen_actor)

    # Contractor access fails
    with pytest.raises(UnauthorizedError):
        service.get_overview(actor=contractor_actor)

    # Government officer access succeeds
    overview = service.get_overview(actor=gov_actor)
    assert overview.total_grievances == 2


def test_dashboard_overview_metrics(db_session: Session, dashboard_setup_data):
    """Verify aggregate metrics for total grievances, statuses, contractors, and pending verifications."""
    service = GovernmentDashboardService(db_session)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    overview = service.get_overview(actor=gov_actor)

    assert overview.total_grievances == 2
    assert overview.status_counts["IN_PROGRESS"] == 1
    assert overview.status_counts["PENDING_VERIFICATION"] == 1
    assert overview.work_order_counts["IN_PROGRESS"] == 1
    assert overview.work_order_counts["PENDING_VERIFICATION"] == 1
    assert overview.active_contractors_count == 1
    assert overview.pending_verifications_count == 1
    assert overview.priority_counts["CRITICAL"] == 1
    assert overview.severity_counts["HIGH"] == 1


def test_dashboard_grievance_listing_filtering_and_search(db_session: Session, dashboard_setup_data):
    """Verify searching and filtering dashboard grievances list."""
    service = GovernmentDashboardService(db_session)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    # Filter by category
    items_pothole = service.list_dashboard_grievances(actor=gov_actor, issue_category="POTHOLE")
    assert len(items_pothole) == 1
    assert items_pothole[0].issue_category == "POTHOLE"

    # Search query
    items_search = service.list_dashboard_grievances(actor=gov_actor, search="Flooding")
    assert len(items_search) == 1
    assert items_search[0].issue_category == "WATERLOGGING"


def test_dashboard_priority_queue(db_session: Session, dashboard_setup_data):
    """Verify priority queue orders items by Phase 8 maintenance priority score descending."""
    service = GovernmentDashboardService(db_session)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    queue = service.get_priority_queue(actor=gov_actor)
    assert len(queue) == 1  # Only G1 has ML analysis record
    assert queue[0].grievance_id == dashboard_setup_data["g1"].id
    assert queue[0].priority_score == 92.5
    assert queue[0].priority_level == "CRITICAL"


def test_dashboard_verification_queue(db_session: Session, dashboard_setup_data):
    """Verify verification queue contains only work orders in PENDING_VERIFICATION status."""
    service = GovernmentDashboardService(db_session)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    v_queue = service.get_verification_queue(actor=gov_actor)
    assert len(v_queue) == 1
    assert v_queue[0].work_order_id == dashboard_setup_data["wo2"].id
    assert v_queue[0].contractor_name == "BuildCorp Contractors"


def test_dashboard_contractors_summary(db_session: Session, dashboard_setup_data):
    """Verify contractor summary metrics calculation."""
    service = GovernmentDashboardService(db_session)
    gov_actor = UserContext(user_id=dashboard_setup_data["gov_officer"].id, role=UserRole.GOVERNMENT_OFFICER)

    contractors = service.get_contractors_summary(actor=gov_actor)
    assert len(contractors) == 1
    c = contractors[0]
    assert c.contractor_id == dashboard_setup_data["contractor"].id
    assert c.assigned_work_orders_count == 2
    assert c.in_progress_count == 1
    assert c.pending_verification_count == 1
