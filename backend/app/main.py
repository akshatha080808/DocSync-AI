"""FastAPI application entry point for DocSync AI."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import DocSyncError
from app.routes.analysis import router as analysis_router
from app.routes.drift import router as drift_router
from app.routes.projects import router as projects_router
from app.routes.reports import router as reports_router
from app.routes.uploads import router as uploads_router

app = FastAPI(
    title=settings.app_name,
    description="DocSync AI — Deterministic Codebase Analysis & Documentation Drift Detection Backend",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DocSyncError)
async def docsync_exception_handler(request: Request, exc: DocSyncError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# Register API Routers
app.include_router(projects_router)
app.include_router(uploads_router)
app.include_router(analysis_router)
app.include_router(drift_router)
app.include_router(reports_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint indicating service status."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "gemini_configured": settings.gemini_configured,
        "data_dir_ready": settings.projects_dir.exists(),
    }
