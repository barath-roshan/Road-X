"""API Integration tests for Citizen Chatbot RAG endpoints (/api/v1/citizen/chat/...)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from api.main import app
from backend.database import Base, get_db
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.road import RoadSegment
from backend.models.user import User, UserRole


@pytest.fixture(scope="function")
def db_engine():
    """Create isolated in-memory SQLite engine for test suite."""
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
    """TestClient overriding get_db to use isolated test database session."""
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
def chat_seed_data(db_session: Session):
    """Seed test users and grievance records for chat API testing."""
    citizen_a = User(id="usr_cit_chat_a", name="Chat Citizen A", email="chat_a@roadx.org", role=UserRole.CITIZEN)
    citizen_b = User(id="usr_cit_chat_b", name="Chat Citizen B", email="chat_b@roadx.org", role=UserRole.CITIZEN)
    contractor = User(id="usr_con_chat", name="Contractor User", email="contractor@roadx.org", role=UserRole.CONTRACTOR)


    road = RoadSegment(id="road_chat_1", name="Park Avenue", code="RD-CHAT-1", length_km=1.2, surface_type="asphalt")
    grievance = Grievance(
        id="g_chat_100",
        citizen_id=citizen_a.id,
        road_id=road.id,
        issue_category="POTHOLE",
        description="Pothole near Park Ave crossroad",
        status=GrievanceStatus.SUBMITTED,
    )

    db_session.add_all([citizen_a, citizen_b, contractor, road, grievance])
    db_session.commit()

    return {
        "citizen_a": citizen_a,
        "citizen_b": citizen_b,
        "contractor": contractor,
        "road": road,
        "grievance": grievance,
    }


def test_create_and_list_chat_conversations(api_client: TestClient, chat_seed_data):
    """Test POST and GET conversations endpoints for authenticated citizen."""
    headers_a = {
        "X-User-ID": chat_seed_data["citizen_a"].id,
        "X-User-Role": "CITIZEN",
    }

    # 1. Create conversation
    res_create = api_client.post(
        "/api/v1/citizen/chat/conversations",
        headers=headers_a,
        json={"title": "Road Maintenance Help"},
    )
    assert res_create.status_code == 201
    conv_data = res_create.json()
    assert conv_data["citizen_id"] == chat_seed_data["citizen_a"].id
    assert conv_data["title"] == "Road Maintenance Help"
    conv_id = conv_data["id"]

    # 2. List conversations
    res_list = api_client.get("/api/v1/citizen/chat/conversations", headers=headers_a)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["id"] == conv_id
    assert items[0]["message_count"] == 0


def test_send_message_and_rag_response(api_client: TestClient, chat_seed_data):
    """Test sending user question and receiving grounded RAG answer with source metadata."""
    headers_a = {
        "X-User-ID": chat_seed_data["citizen_a"].id,
        "X-User-Role": "CITIZEN",
    }

    # Create session
    conv = api_client.post(
        "/api/v1/citizen/chat/conversations",
        headers=headers_a,
        json={"title": "Complaint Status Query"},
    ).json()
    conv_id = conv["id"]

    # Send message
    res_msg = api_client.post(
        f"/api/v1/citizen/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "What is the status of my pothole report?"},
    )
    assert res_msg.status_code == 200
    payload = res_msg.json()

    assert payload["conversation_id"] == conv_id
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "What is the status of my pothole report?"

    assert payload["assistant_message"]["role"] == "assistant"
    assert "g_chat_100" in payload["assistant_message"]["content"] or "SUBMITTED" in payload["assistant_message"]["content"]

    assert len(payload["sources"]) >= 1
    source_titles = [s["title"] for s in payload["sources"]]
    assert any("Grievance Records" in t or "RoadX" in t or "FAQ" in t for t in source_titles)

    # Verify conversation history details
    res_history = api_client.get(
        f"/api/v1/citizen/chat/conversations/{conv_id}",
        headers=headers_a,
    )
    assert res_history.status_code == 200
    history_data = res_history.json()
    assert len(history_data["messages"]) == 2


def test_chat_authorization_isolation(api_client: TestClient, chat_seed_data):
    """Test that unauthorized roles or other citizens cannot access another citizen's conversation."""
    headers_a = {
        "X-User-ID": chat_seed_data["citizen_a"].id,
        "X-User-Role": "CITIZEN",
    }
    headers_b = {
        "X-User-ID": chat_seed_data["citizen_b"].id,
        "X-User-Role": "CITIZEN",
    }
    headers_contractor = {
        "X-User-ID": chat_seed_data["contractor"].id,
        "X-User-Role": "CONTRACTOR",
    }

    # Citizen A creates conversation
    conv_a = api_client.post(
        "/api/v1/citizen/chat/conversations",
        headers=headers_a,
        json={"title": "Private Session A"},
    ).json()
    conv_id = conv_a["id"]

    # 1. Citizen B attempts to access Citizen A's conversation
    res_b_get = api_client.get(
        f"/api/v1/citizen/chat/conversations/{conv_id}",
        headers=headers_b,
    )
    assert res_b_get.status_code == 403

    # 2. Citizen B attempts to send message to Citizen A's conversation
    res_b_post = api_client.post(
        f"/api/v1/citizen/chat/conversations/{conv_id}/messages",
        headers=headers_b,
        json={"content": "Intrusion test"},
    )
    assert res_b_post.status_code == 403

    # 3. Contractor role attempts to access citizen chat endpoint
    res_contractor = api_client.post(
        "/api/v1/citizen/chat/conversations",
        headers=headers_contractor,
        json={"title": "Unauthorized Role Test"},
    )
    assert res_contractor.status_code == 403


def test_chat_invalid_payload_validation(api_client: TestClient, chat_seed_data):
    """Test validation rejection of blank or empty chat messages."""
    headers_a = {
        "X-User-ID": chat_seed_data["citizen_a"].id,
        "X-User-Role": "CITIZEN",
    }

    conv = api_client.post(
        "/api/v1/citizen/chat/conversations",
        headers=headers_a,
    ).json()

    # Empty string message
    res_empty = api_client.post(
        f"/api/v1/citizen/chat/conversations/{conv['id']}/messages",
        headers=headers_a,
        json={"content": "   "},
    )
    assert res_empty.status_code in [400, 422]
