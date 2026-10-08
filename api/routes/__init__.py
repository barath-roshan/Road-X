"""API Routes package for RoadX FastAPI Service."""

from api.routes.health import router as health_router
from api.routes.ml import router as ml_router
from api.routes.grievance import router as grievance_router
from api.routes.government import router as government_router
from api.routes.contractor import router as contractor_router
from api.routes.citizen import router as citizen_router
from api.routes.notification import router as notification_router
from api.routes.chat import router as chat_router

__all__ = [
    "health_router",
    "ml_router",
    "grievance_router",
    "government_router",
    "contractor_router",
    "citizen_router",
    "notification_router",
    "chat_router",
]

