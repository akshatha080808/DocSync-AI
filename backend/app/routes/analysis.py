"""API routes for deterministic codebase and documentation analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import AnalysisError, ProjectNotFoundError
from app.models.analysis import AnalysisResult, DependencyGraph
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/api/projects", tags=["analysis"])


@router.post("/{project_id}/analyze", response_model=AnalysisResult)
def trigger_analysis(project_id: str) -> AnalysisResult:
    """Runs full deterministic analysis pipeline for the project."""
    try:
        return analysis_service.analyze_project(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected analysis failure: {str(e)}")


@router.get("/{project_id}/analysis", response_model=AnalysisResult)
def get_analysis(project_id: str) -> AnalysisResult:
    """Retrieves existing deterministic analysis results for the project."""
    try:
        return analysis_service.get_analysis_result(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error retrieving analysis: {str(e)}")


@router.get("/{project_id}/dependencies", response_model=DependencyGraph)
def get_dependencies(project_id: str) -> DependencyGraph:
    """Retrieves module dependency graph in React Flow format."""
    try:
        result = analysis_service.get_analysis_result(project_id)
        return result.dependency_graph
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error retrieving dependencies: {str(e)}")
