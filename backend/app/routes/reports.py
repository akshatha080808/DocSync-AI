"""API routes for downloading project audit reports in JSON and executive PDF formats."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.core.exceptions import AnalysisError, ProjectNotFoundError
from app.engines.report_engine import report_engine
from app.services.analysis_service import analysis_service
from app.services.drift_service import drift_service
from app.services.project_service import project_service

router = APIRouter(prefix="/api/projects", tags=["reports"])


@router.get("/{project_id}/report/json")
def download_json_report(project_id: str):
    """Generates and returns comprehensive project audit report as JSON."""
    try:
        project = project_service.get_project_detail(project_id)

        analysis = None
        try:
            analysis = analysis_service.get_analysis_result(project_id)
        except Exception:
            pass

        findings = []
        try:
            findings_resp = drift_service.get_findings(project_id)
            findings = findings_resp.findings
        except Exception:
            pass

        corrections = []
        try:
            corrections_resp = drift_service.get_corrections(project_id)
            corrections = corrections_resp.corrections
        except Exception:
            pass

        trace = None
        try:
            trace = drift_service.get_agent_trace(project_id)
        except Exception:
            pass

        report_data = report_engine.generate_json_report(
            project=project,
            analysis=analysis,
            findings=findings,
            corrections=corrections,
            trace=trace,
        )

        return report_data
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate JSON report: {str(e)}")


@router.get("/{project_id}/report/pdf")
def download_pdf_report(project_id: str):
    """Generates and streams an executive PDF audit report."""
    try:
        project = project_service.get_project_detail(project_id)

        analysis = None
        try:
            analysis = analysis_service.get_analysis_result(project_id)
        except Exception:
            pass

        findings = []
        try:
            findings_resp = drift_service.get_findings(project_id)
            findings = findings_resp.findings
        except Exception:
            pass

        corrections = []
        try:
            corrections_resp = drift_service.get_corrections(project_id)
            corrections = corrections_resp.corrections
        except Exception:
            pass

        trace = None
        try:
            trace = drift_service.get_agent_trace(project_id)
        except Exception:
            pass

        pdf_bytes = report_engine.generate_pdf_report(
            project=project,
            analysis=analysis,
            findings=findings,
            corrections=corrections,
            trace=trace,
        )

        filename = f"DocSync_Report_{project.name.replace(' ', '_')}_{project_id[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")
