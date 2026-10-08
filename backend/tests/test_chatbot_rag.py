"""Unit tests for Phase 19 Citizen Chatbot RAG components, chunker, vector store, retriever, context builder, and service."""

from __future__ import annotations

import pytest
import numpy as np
from sqlalchemy.orm import Session

from backend.chatbot.chunker import DocumentChunk, DocumentChunker
from backend.chatbot.embeddings import RoadXEmbeddingProvider
from backend.chatbot.vector_store import VectorStore
from backend.chatbot.retriever import KnowledgeRetriever
from backend.chatbot.context_builder import ContextBuilder
from backend.chatbot.llm_provider import MockLLMProvider
from backend.models.chat import ChatRole
from backend.models.user import User, UserRole
from backend.models.road import RoadSegment
from backend.models.grievance import Grievance, GrievanceStatus
from backend.models.road_operation import RoadOperation, RoadOperationType, RoadOperationStatus
from backend.repositories.chat_repository import ChatRepository
from backend.security import UserContext, UnauthorizedError
from backend.services.chatbot_service import CitizenChatbotService
from ml.common.exceptions import RoadXDataError


def test_document_chunker_basic():
    """Test deterministic document chunking and metadata preservation."""
    chunker = DocumentChunker(max_chunk_chars=150, overlap_chars=20)
    doc = {
        "document_id": "doc_test_1",
        "title": "Test Maintenance Policy",
        "source": "Municipal Dept",
        "category": "Policy",
        "version": "1.0",
        "content": "Potholes are repaired within 48 hours. Crack sealing occurs during autumn. Major road resurfacing requires structural engineering approval.",
    }

    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.document_id == "doc_test_1"
        assert chunk.title == "Test Maintenance Policy"
        assert chunk.source == "Municipal Dept"
        assert chunk.category == "Policy"
        assert chunk.version == "1.0"
        assert len(chunk.text) <= 180


def test_embedding_provider():
    """Test RoadXEmbeddingProvider vector dimensions and normalization."""
    provider = RoadXEmbeddingProvider(embedding_dim=300)
    vec = provider.embed_text("Pothole repair on Main Street")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (300,)
    assert vec.dtype == np.float32

    # Verify L2 normalization
    norm = float(np.linalg.norm(vec))
    assert pytest.approx(norm, abs=1e-4) == 1.0 or norm == 0.0

    batch = provider.embed_batch(["Pothole", "Road closure detour"])
    assert batch.shape == (2, 300)


def test_vector_store_similarity_search():
    """Test VectorStore chunk indexing and similarity ranking."""
    vs = VectorStore(embedding_dim=300)
    provider = RoadXEmbeddingProvider(embedding_dim=300)

    c1 = DocumentChunk("c1", "doc1", "Pothole FAQ", "Source", "Cat", "1.0", "Pothole repairs take 48 hours")
    c2 = DocumentChunk("c2", "doc2", "Detour Info", "Source", "Cat", "1.0", "Traffic detour through North Avenue")
    
    vecs = provider.embed_batch([c1.text, c2.text])
    vs.add_chunks([c1, c2], vecs)

    q_vec = provider.embed_text("How long for pothole fixing?")
    results = vs.similarity_search(q_vec, top_k=2, min_score=0.0)

    assert len(results) > 0
    assert results[0].chunk.title in ["Pothole FAQ", "Detour Info"]
    assert 0.0 <= results[0].score <= 1.0


def test_knowledge_retriever(tmp_path):
    """Test KnowledgeRetriever document ingestion and query retrieval."""
    test_json = tmp_path / "test_faq.json"
    test_json.write_text(
        '['
        '{"document_id": "d1", "title": "Pothole Guide", "source": "City", "category": "FAQ", "version": "1.0", "content": "Potholes are filled using hot asphalt mixture."}'
        ']',
        encoding="utf-8"
    )

    retriever = KnowledgeRetriever(knowledge_file_path=test_json)
    results = retriever.retrieve("pothole asphalt", top_k=1)
    assert len(results) == 1
    assert results[0].chunk.document_id == "d1"
    assert "asphalt" in results[0].chunk.text


def test_citizen_data_isolation(db_session: Session):
    """Test strict database retrieval isolation ensuring citizen A cannot view citizen B records."""
    cit1 = User(id="cit_a_100", name="Citizen A", email="cit1@roadx.org", role=UserRole.CITIZEN)
    cit2 = User(id="cit_b_200", name="Citizen B", email="cit2@roadx.org", role=UserRole.CITIZEN)
    road = RoadSegment(id="road_isolation_1", name="Broadway St", code="RD-ISO-1", length_km=2.5, surface_type="asphalt")
    
    g1 = Grievance(
        id="g_cit_a_1",
        citizen_id=cit1.id,
        road_id=road.id,
        issue_category="POTHOLE",
        description="Pothole near Cit A house",
        status=GrievanceStatus.SUBMITTED,
    )
    g2 = Grievance(
        id="g_cit_b_2",
        citizen_id=cit2.id,
        road_id=road.id,
        issue_category="CRACK",
        description="Crack near Cit B house",
        status=GrievanceStatus.IN_PROGRESS,
    )

    db_session.add_all([cit1, cit2, road, g1, g2])
    db_session.commit()

    cb = ContextBuilder()
    actor_a = UserContext(user_id=cit1.id, role=UserRole.CITIZEN)
    context_a = cb.get_citizen_db_context(db_session, actor_a)

    grievance_ids = [g["grievance_id"] for g in context_a["grievances"]]
    assert "g_cit_a_1" in grievance_ids
    assert "g_cit_b_2" not in grievance_ids


def test_mock_llm_provider_grounding():
    """Test MockLLMProvider response generation against context."""
    llm = MockLLMProvider()
    
    context = (
        "### CITIZEN ACCOUNT GRIEVANCES:\n"
        "Grievance #1 [ID: g100]: Category=POTHOLE, Status=IN_PROGRESS, Road=Main St. Description: \"Large pothole\". Work Order Status=IN_PROGRESS. Progress: 50% (Paving underlying layer)\n"
        "\n### ACTIVE/PLANNED MUNICIPAL ROAD OPERATIONS:\n"
        "Operation #1 [ID: op200]: Title=\"Main St Resurfacing\", Type=MAINTENANCE, Status=ACTIVE, Road=Main St. Reason: Road repair. Detour Route: Detour via 5th Ave.\n"
        "\n### ROADX KNOWLEDGE BASE GUIDANCE & FAQS:\n"
        "Knowledge #1 [Pothole FAQ - Guidance]:\nPotholes are scheduled by severity priority."
    )

    res_grievance = llm.generate_response("What is the status of my pothole complaint?", context)
    assert "g100" in res_grievance or "IN_PROGRESS" in res_grievance

    res_closure = llm.generate_response("Is Main St closed for maintenance?", context)
    assert "Main St Resurfacing" in res_closure or "Detour via 5th Ave" in res_closure

    res_unknown = llm.generate_response("Who is the mayor of New York?", context)
    assert "don't have enough information" in res_unknown or "RoadX" in res_unknown


def test_chatbot_service_flow(db_session: Session):
    """Test end-to-end CitizenChatbotService conversation creation, message processing, and history."""
    cit = User(id="cit_service_test", name="Service Test Cit", email="service@roadx.org", role=UserRole.CITIZEN)
    db_session.add(cit)
    db_session.commit()

    actor = UserContext(user_id=cit.id, role=UserRole.CITIZEN)
    service = CitizenChatbotService(db_session)

    # 1. Create conversation
    conv = service.create_conversation(actor, title="My Grievance Questions")
    assert conv.citizen_id == cit.id
    assert conv.title == "My Grievance Questions"

    # 2. Process user message
    resp = service.process_message(actor, conv.id, "How are potholes fixed in RoadX?")
    assert resp.conversation_id == conv.id
    assert resp.user_message.content == "How are potholes fixed in RoadX?"
    assert resp.assistant_message.content is not None
    assert len(resp.sources) >= 1

    # 3. Retrieve conversation history
    conv_detail = service.get_conversation(actor, conv.id)
    assert len(conv_detail.messages) == 2
    assert conv_detail.messages[0].role == ChatRole.USER
    assert conv_detail.messages[1].role == ChatRole.ASSISTANT


def test_chatbot_service_unauthorized_conversation_access(db_session: Session):
    """Test that citizen B cannot access or post messages to citizen A's conversation."""
    cit_a = User(id="cit_owner_a", name="Owner A", email="owner_a@roadx.org", role=UserRole.CITIZEN)
    cit_b = User(id="cit_intruder_b", name="Intruder B", email="intruder_b@roadx.org", role=UserRole.CITIZEN)
    db_session.add_all([cit_a, cit_b])
    db_session.commit()


    service = CitizenChatbotService(db_session)
    actor_a = UserContext(user_id=cit_a.id, role=UserRole.CITIZEN)
    actor_b = UserContext(user_id=cit_b.id, role=UserRole.CITIZEN)

    conv_a = service.create_conversation(actor_a, title="Private Chat A")

    with pytest.raises(UnauthorizedError):
        service.get_conversation(actor_b, conv_a.id)

    with pytest.raises(UnauthorizedError):
        service.process_message(actor_b, conv_a.id, "Attempted intrusion message")
