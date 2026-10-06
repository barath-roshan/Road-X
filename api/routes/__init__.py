"""API Routes package for RoadX FastAPI Service."""

from api.routes.health import router as health_router
from api.routes.ml import router as ml_router
from api.routes.grievance import router as grievance_router
from api.routes.government import router as government_router

__all__ = ["health_router", "ml_router", "grievance_router", "government_router"]
