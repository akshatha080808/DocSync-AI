"""Package initialization for routes."""

from app.routes.analysis import router as analysis_router
from app.routes.drift import router as drift_router
from app.routes.projects import router as projects_router
from app.routes.reports import router as reports_router
from app.routes.uploads import router as uploads_router

__all__ = ["projects_router", "uploads_router", "analysis_router", "drift_router", "reports_router"]
