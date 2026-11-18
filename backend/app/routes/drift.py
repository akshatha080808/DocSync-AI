"""API routes for drift detection, agent investigation, findings, traces, and corrections."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import AnalysisError, ProjectNotFoundError
from app.models.agent import AgentExecutionTrace, AgentRunResponse
from app.models.correction import DocumentationCorrection, ProjectCorrectionsResponse
from app.models.finding import DriftFinding, ProjectFindingsResponse
from app.services.drift_service import drift_service

router = APIRouter(prefix="/api/projects", tags=["drift"])


@router.post("/{project_id}/detect-drift", response_model=ProjectFindingsResponse)
def detect_drift(project_id: str) -> ProjectFindingsResponse:
    """Runs deterministic drift detection and impact ranking for a project."""
    try:
        return drift_service.detect_and_save_drift(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect drift: {str(e)}")


@router.get("/{project_id}/findings", response_model=ProjectFindingsResponse)
def get_findings(project_id: str) -> ProjectFindingsResponse:
    """Retrieves all drift findings and evidence references for a project."""
    try:
        return drift_service.get_findings(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve findings: {str(e)}")


@router.get("/{project_id}/findings/{finding_id}", response_model=DriftFinding)
def get_finding_detail(project_id: str, finding_id: str) -> DriftFinding:
    """Retrieves a specific drift finding by ID."""
    try:
        return drift_service.get_finding(project_id, finding_id)
    except (ProjectNotFoundError, AnalysisError) as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve finding: {str(e)}")


@router.post("/{project_id}/run-agent", response_model=AgentRunResponse)
def run_agent_investigation(project_id: str) -> AgentRunResponse:
    """Triggers controlled agentic investigation loop with tool-calling and validation."""
    try:
        return drift_service.run_agent_investigation(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent investigation failed: {str(e)}")


@router.get("/{project_id}/agent-trace", response_model=AgentExecutionTrace)
def get_agent_trace(project_id: str) -> AgentExecutionTrace:
    """Retrieves the execution trace showing tool calls, inputs, and observable reasoning."""
    try:
        return drift_service.get_agent_trace(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent trace: {str(e)}")


@router.get("/{project_id}/corrections", response_model=ProjectCorrectionsResponse)
def get_corrections(project_id: str) -> ProjectCorrectionsResponse:
    """Retrieves all proposed documentation corrections with unified diffs."""
    try:
        return drift_service.get_corrections(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve corrections: {str(e)}")


@router.get("/{project_id}/corrections/{correction_id}", response_model=DocumentationCorrection)
def get_correction_detail(project_id: str, correction_id: str) -> DocumentationCorrection:
    """Retrieves a specific documentation correction and its unified diff."""
    try:
        return drift_service.get_correction(project_id, correction_id)
    except (ProjectNotFoundError, AnalysisError) as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve correction: {str(e)}")
