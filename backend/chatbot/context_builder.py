"""Hybrid Context Builder combining PostgreSQL Citizen Account data and Vector Knowledge Base RAG chunks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.chatbot.retriever import KnowledgeRetriever
from backend.chatbot.vector_store import SearchResult
from backend.models.grievance import Grievance
from backend.models.road import RoadSegment
from backend.models.road_operation import RoadOperation, RoadOperationStatus
from backend.models.user import UserRole
from backend.models.work_order import WorkOrder
from backend.models.work_progress import WorkProgress
from backend.models.government_verification import GovernmentVerification
from backend.security import UserContext, UnauthorizedError


class ContextBuilder:
    """Assembles grounded hybrid context for Citizen Chatbot execution."""

    def __init__(self, retriever: Optional[KnowledgeRetriever] = None) -> None:
        self.retriever = retriever or KnowledgeRetriever()

    def get_citizen_db_context(self, db: Session, actor: UserContext) -> Dict[str, Any]:
        """Query PostgreSQL DB for authenticated citizen's own grievances and active road operations.

        Enforces strict authorization: grievance.citizen_id == actor.user_id.
        """
        actor.require_role(UserRole.CITIZEN)
        if not actor.user_id:
            raise UnauthorizedError("Citizen user_id is required.")

        # 1. Fetch citizen's owned grievances
        grievances = (
            db.query(Grievance)
            .filter(Grievance.citizen_id == actor.user_id)
            .order_by(Grievance.created_at.desc())
            .all()
        )

        grievance_summaries: List[Dict[str, Any]] = []
        for g in grievances:
            road = db.query(RoadSegment).filter(RoadSegment.id == g.road_id).first()
            road_name = road.road_name if road else g.road_id

            # Work Order info
            wo = db.query(WorkOrder).filter(WorkOrder.grievance_id == g.id).first()
            wo_status = wo.status.value if wo else "NOT_ASSIGNED"
            
            # Progress info
            latest_progress = None
            if wo:
                wp = (
                    db.query(WorkProgress)
                    .filter(WorkProgress.work_order_id == wo.id)
                    .order_by(WorkProgress.created_at.desc())
                    .first()
                )
                if wp:
                    latest_progress = {
                        "completion_percentage": wp.completion_percentage,
                        "notes": wp.notes,
                    }

            # Verification info
            latest_verification = None
            if wo:
                gv = (
                    db.query(GovernmentVerification)
                    .filter(GovernmentVerification.work_order_id == wo.id)
                    .order_by(GovernmentVerification.created_at.desc())
                    .first()
                )
                if gv:
                    latest_verification = {
                        "decision": gv.decision.value,
                        "notes": gv.notes,
                    }

            grievance_summaries.append({
                "grievance_id": g.id,
                "category": g.issue_category,
                "description": g.description,
                "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                "road": road_name,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "work_order_status": wo_status,
                "latest_progress": latest_progress,
                "latest_verification": latest_verification,
            })

        # 2. Fetch public active and planned road operations
        active_ops = (
            db.query(RoadOperation)
            .filter(
                RoadOperation.status.in_([
                    RoadOperationStatus.ACTIVE,
                    RoadOperationStatus.PLANNED,
                ])
            )
            .order_by(RoadOperation.start_time.asc())
            .all()
        )

        op_summaries: List[Dict[str, Any]] = []
        for op in active_ops:
            road = db.query(RoadSegment).filter(RoadSegment.id == op.road_id).first()
            road_name = road.road_name if road else op.road_id

            alt_route_str = "No alternative route specified."
            if op.alternative_route_name or op.alternative_route_instructions:
                alt_parts = [p for p in [op.alternative_route_name, op.alternative_route_instructions] if p]
                alt_route_str = " - ".join(alt_parts)

            op_summaries.append({
                "operation_id": op.id,
                "title": op.title,
                "operation_type": op.operation_type.value if hasattr(op.operation_type, "value") else str(op.operation_type),
                "status": op.status.value if hasattr(op.status, "value") else str(op.status),
                "road": road_name,
                "reason": op.reason,
                "alternative_route": alt_route_str,
                "scheduled_start": op.start_time.isoformat() if op.start_time else None,
                "scheduled_end": op.expected_end_time.isoformat() if op.expected_end_time else None,
            })


        return {
            "citizen_id": actor.user_id,
            "grievances": grievance_summaries,
            "road_operations": op_summaries,
        }

    def build_hybrid_context(
        self,
        db: Session,
        actor: UserContext,
        query: str,
    ) -> Dict[str, Any]:
        """Assemble hybrid context containing Citizen Database Context and Knowledge Base RAG Search Results.

        Returns dict with formatted_context_str and sources_list.
        """
        # 1. Citizen Account DB Data
        db_context = self.get_citizen_db_context(db, actor)

        # 2. Knowledge RAG Search Results
        rag_results: List[SearchResult] = self.retriever.retrieve(query)

        # Format Context String
        formatted_db_parts = []
        
        # Format Grievance Context
        if db_context["grievances"]:
            formatted_db_parts.append("### CITIZEN ACCOUNT GRIEVANCES:")
            for idx, g in enumerate(db_context["grievances"], 1):
                progress_str = ""
                if g["latest_progress"]:
                    progress_str = f" Progress: {g['latest_progress']['completion_percentage']}% ({g['latest_progress']['notes'] or ''})"
                verif_str = ""
                if g["latest_verification"]:
                    verif_str = f" Verification: {g['latest_verification']['decision']} ({g['latest_verification']['notes'] or ''})"

                formatted_db_parts.append(
                    f"Grievance #{idx} [ID: {g['grievance_id']}]: Category={g['category']}, Status={g['status']}, Road={g['road']}. Description: \"{g['description']}\". Work Order Status={g['work_order_status']}.{progress_str}{verif_str}"
                )
        else:
            formatted_db_parts.append("### CITIZEN ACCOUNT GRIEVANCES:\nNo grievances reported by this citizen account.")

        # Format Road Operations Context
        if db_context["road_operations"]:
            formatted_db_parts.append("\n### ACTIVE/PLANNED MUNICIPAL ROAD OPERATIONS:")
            for idx, op in enumerate(db_context["road_operations"], 1):
                formatted_db_parts.append(
                    f"Operation #{idx} [ID: {op['operation_id']}]: Title=\"{op['title']}\", Type={op['operation_type']}, Status={op['status']}, Road={op['road']}. Reason: {op['reason']}. Detour Route: {op['alternative_route']}."
                )
        else:
            formatted_db_parts.append("\n### ACTIVE/PLANNED MUNICIPAL ROAD OPERATIONS:\nNo active public road operations currently reported.")

        # Format Knowledge Base Context
        formatted_rag_parts = ["\n### ROADX KNOWLEDGE BASE GUIDANCE & FAQS:"]
        sources: List[Dict[str, Any]] = []

        if rag_results:
            for idx, res in enumerate(rag_results, 1):
                chunk = res.chunk
                formatted_rag_parts.append(
                    f"Knowledge #{idx} [{chunk.title} - {chunk.category}]:\n{chunk.text}"
                )
                sources.append({
                    "title": chunk.title,
                    "category": chunk.category,
                    "source": chunk.source,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "relevance_score": round(res.score, 4),
                })
        else:
            formatted_rag_parts.append("No specific knowledge base guidance matching query.")

        # Tag account information in sources list if citizen grievances exist
        if db_context["grievances"]:
            sources.append({
                "title": "Citizen Account Grievance Records",
                "category": "Account Context",
                "source": "RoadX PostgreSQL Database",
                "document_id": f"account_grievances_{actor.user_id}",
                "chunk_id": f"account_grievances_{actor.user_id}",
                "relevance_score": 1.0,
            })

        full_context_str = "\n".join(formatted_db_parts + formatted_rag_parts)

        return {
            "context_text": full_context_str,
            "sources": sources,
            "db_context": db_context,
            "rag_results": rag_results,
        }
