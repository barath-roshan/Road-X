"""Pydantic schemas package for backend DTO validation."""

from backend.schemas.user import UserCreate, UserRead, UserUpdate
from backend.schemas.road import RoadCreate, RoadRead, RoadUpdate
from backend.schemas.grievance import GrievanceCreate, GrievanceRead, GrievanceUpdate
from backend.schemas.evidence import EvidenceCreate, EvidenceRead
from backend.schemas.ml_analysis import MLAnalysisCreate, MLAnalysisRead
from backend.schemas.government_review import GovernmentReviewCreate, GovernmentReviewRead
from backend.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderRead,
    WorkOrderUpdate,
    ContractorWorkOrderDetailsRead,
)
from backend.schemas.government_verification import GovernmentVerificationCreate, GovernmentVerificationRead
from backend.schemas.workflow_event import WorkflowEventRead
from backend.schemas.work_progress import WorkProgressCreate, WorkProgressRead
from backend.schemas.completion_submission import CompletionSubmissionCreate, CompletionSubmissionRead
from backend.schemas.citizen import (
    CitizenGrievanceCreate,
    CitizenMLSummaryRead,
    CitizenWorkProgressRead,
    CitizenRejectionInfoRead,
    CitizenTimelineItemRead,
    CitizenGrievanceDetailsRead,
)
from backend.schemas.government_dashboard import (
    GovernmentDashboardOverviewRead,
    GovernmentDashboardGrievanceItemRead,
    GovernmentDashboardGrievanceDetailRead,
    GovernmentDashboardPriorityItemRead,
    GovernmentDashboardVerificationItemRead,
    GovernmentDashboardWorkOrderItemRead,
    GovernmentDashboardContractorSummaryRead,
)
from backend.schemas.contractor_dashboard import (
    ContractorDashboardOverviewRead,
    ContractorDashboardWorkOrderItemRead,
    ContractorDashboardWorkOrderDetailRead,
    ContractorDashboardPendingVerificationItemRead,
    ContractorDashboardReworkItemRead,
    ContractorDashboardWorkloadSummaryRead,
)
from backend.schemas.road_operation import (
    RoadOperationCreate,
    RoadOperationUpdate,
    RoadOperationEventRead,
    GovernmentRoadOperationRead,
    CitizenRoadOperationRead,
)
from backend.schemas.notification import (
    NotificationRead,
    NotificationListResponse,
    MarkReadResponse,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "RoadCreate",
    "RoadRead",
    "RoadUpdate",
    "GrievanceCreate",
    "GrievanceRead",
    "GrievanceUpdate",
    "EvidenceCreate",
    "EvidenceRead",
    "MLAnalysisCreate",
    "MLAnalysisRead",
    "GovernmentReviewCreate",
    "GovernmentReviewRead",
    "WorkOrderCreate",
    "WorkOrderRead",
    "WorkOrderUpdate",
    "ContractorWorkOrderDetailsRead",
    "GovernmentVerificationCreate",
    "GovernmentVerificationRead",
    "WorkflowEventRead",
    "WorkProgressCreate",
    "WorkProgressRead",
    "CompletionSubmissionCreate",
    "CompletionSubmissionRead",
    "CitizenGrievanceCreate",
    "CitizenMLSummaryRead",
    "CitizenWorkProgressRead",
    "CitizenRejectionInfoRead",
    "CitizenTimelineItemRead",
    "CitizenGrievanceDetailsRead",
    "GovernmentDashboardOverviewRead",
    "GovernmentDashboardGrievanceItemRead",
    "GovernmentDashboardGrievanceDetailRead",
    "GovernmentDashboardPriorityItemRead",
    "GovernmentDashboardVerificationItemRead",
    "GovernmentDashboardWorkOrderItemRead",
    "GovernmentDashboardContractorSummaryRead",
    "ContractorDashboardOverviewRead",
    "ContractorDashboardWorkOrderItemRead",
    "ContractorDashboardWorkOrderDetailRead",
    "ContractorDashboardPendingVerificationItemRead",
    "ContractorDashboardReworkItemRead",
    "ContractorDashboardWorkloadSummaryRead",
    "RoadOperationCreate",
    "RoadOperationUpdate",
    "RoadOperationEventRead",
    "GovernmentRoadOperationRead",
    "CitizenRoadOperationRead",
    "NotificationRead",
    "NotificationListResponse",
    "MarkReadResponse",
]

