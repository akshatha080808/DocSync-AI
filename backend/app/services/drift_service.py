"""Service managing drift detection, agent investigation, findings, traces, and proposed corrections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from app.agents.orchestrator import orchestrator
from app.core.exceptions import AnalysisError, ProjectNotFoundError
from app.engines.correction_engine import correction_engine
from app.engines.drift_engine import drift_engine
from app.engines.impact_engine import impact_engine
from app.models.agent import AgentExecutionTrace, AgentRunResponse
from app.models.correction import DocumentationCorrection, ProjectCorrectionsResponse
from app.models.finding import (
    DriftFinding,
    EvidenceReference,
    ProjectFindingsResponse,
)
from app.services.analysis_service import analysis_service
from app.services.project_service import project_service


class DriftService:
    """Coordinates persistence and retrieval of findings, agent traces, and corrections."""

    def _get_findings_file(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id) / "findings.json"

    def _get_evidence_file(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id) / "evidence.json"

    def _get_trace_file(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id) / "agent_trace.json"

    def _get_corrections_file(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id) / "corrections.json"

    def detect_and_save_drift(self, project_id: str) -> ProjectFindingsResponse:
        """Runs deterministic drift detection and impact ranking, saving findings."""
        analysis = analysis_service.get_analysis_result(project_id)
        findings, evidence = drift_engine.detect_drift(analysis)
        ranked_findings = impact_engine.rank_all(findings, analysis)

        # Generate corresponding corrections
        corrections = correction_engine.generate_all(ranked_findings)

        # Persist separately (preserving analysis.json intact)
        self._save_findings(project_id, ranked_findings)
        self._save_evidence(project_id, evidence)
        self._save_corrections(project_id, corrections)

        return ProjectFindingsResponse(
            project_id=project_id,
            total_findings=len(ranked_findings),
            findings=ranked_findings,
            evidence_pool=evidence,
        )

    def run_agent_investigation(self, project_id: str) -> AgentRunResponse:
        """Executes full agentic investigation loop with tool calling and validation."""
        analysis = analysis_service.get_analysis_result(project_id)

        # Load existing or run fresh
        existing_findings = None
        existing_evidence = None
        f_file = self._get_findings_file(project_id)
        if f_file.exists():
            try:
                data = json.loads(f_file.read_text(encoding="utf-8"))
                existing_findings = [DriftFinding(**item) for item in data]
            except Exception:
                pass

        ranked_findings, evidence, corrections, trace = orchestrator.run_investigation(
            analysis,
            existing_findings=existing_findings,
            existing_evidence=existing_evidence,
        )

        # Persist updated state
        self._save_findings(project_id, ranked_findings)
        self._save_evidence(project_id, evidence)
        self._save_corrections(project_id, corrections)
        self._save_trace(project_id, trace)

        return AgentRunResponse(
            project_id=project_id,
            status=trace.status,
            message="Agent investigation completed successfully.",
            total_findings_generated=len(ranked_findings),
            total_corrections_generated=len(corrections),
            trace=trace,
        )

    def get_findings(self, project_id: str) -> ProjectFindingsResponse:
        project = project_service.get_project(project_id)
        f_file = self._get_findings_file(project_id)
        e_file = self._get_evidence_file(project_id)

        findings: List[DriftFinding] = []
        evidence: List[EvidenceReference] = []

        if f_file.exists():
            try:
                data = json.loads(f_file.read_text(encoding="utf-8"))
                findings = [DriftFinding(**item) for item in data]
            except Exception:
                pass

        if e_file.exists():
            try:
                data = json.loads(e_file.read_text(encoding="utf-8"))
                evidence = [EvidenceReference(**item) for item in data]
            except Exception:
                pass

        # If findings don't exist yet, run detection only if analysis is completed
        if not f_file.exists():
            analysis_file = project_service.get_analysis_dir(project_id) / "analysis.json"
            if project.analysis_status != "completed" or not analysis_file.exists():
                return ProjectFindingsResponse(
                    project_id=project_id,
                    total_findings=0,
                    findings=[],
                    evidence_pool=[],
                )
            return self.detect_and_save_drift(project_id)

        return ProjectFindingsResponse(
            project_id=project_id,
            total_findings=len(findings),
            findings=findings,
            evidence_pool=evidence,
        )

    def get_finding(self, project_id: str, finding_id: str) -> DriftFinding:
        resp = self.get_findings(project_id)
        for f in resp.findings:
            if f.finding_id == finding_id:
                return f
        raise AnalysisError(f"Finding '{finding_id}' not found for project '{project_id}'.")

    def get_agent_trace(self, project_id: str) -> AgentExecutionTrace:
        project = project_service.get_project(project_id)
        t_file = self._get_trace_file(project_id)
        if not t_file.exists():
            analysis_file = project_service.get_analysis_dir(project_id) / "analysis.json"
            if project.analysis_status != "completed" or not analysis_file.exists():
                from datetime import datetime, timezone
                now_str = datetime.now(timezone.utc).isoformat()
                return AgentExecutionTrace(
                    project_id=project_id,
                    started_at=now_str,
                    completed_at=now_str,
                    total_steps=0,
                    steps=[],
                    termination_reason="Analysis not yet completed or invalidated",
                    status="PARTIAL",
                )
            # If trace does not exist, run agent to produce initial trace
            run_resp = self.run_agent_investigation(project_id)
            return run_resp.trace

        data = json.loads(t_file.read_text(encoding="utf-8"))
        return AgentExecutionTrace(**data)

    def get_corrections(self, project_id: str) -> ProjectCorrectionsResponse:
        project = project_service.get_project(project_id)
        c_file = self._get_corrections_file(project_id)
        if not c_file.exists():
            analysis_file = project_service.get_analysis_dir(project_id) / "analysis.json"
            if project.analysis_status != "completed" or not analysis_file.exists():
                return ProjectCorrectionsResponse(
                    project_id=project_id,
                    total_corrections=0,
                    corrections=[],
                )
            # Generate corrections from findings
            findings_resp = self.get_findings(project_id)
            corrections = correction_engine.generate_all(findings_resp.findings)
            self._save_corrections(project_id, corrections)
            return ProjectCorrectionsResponse(
                project_id=project_id,
                total_corrections=len(corrections),
                corrections=corrections,
            )

        data = json.loads(c_file.read_text(encoding="utf-8"))
        corrections = [DocumentationCorrection(**item) for item in data]
        return ProjectCorrectionsResponse(
            project_id=project_id,
            total_corrections=len(corrections),
            corrections=corrections,
        )

    def get_correction(self, project_id: str, correction_id: str) -> DocumentationCorrection:
        resp = self.get_corrections(project_id)
        for c in resp.corrections:
            if c.correction_id == correction_id:
                return c
        raise AnalysisError(f"Correction '{correction_id}' not found for project '{project_id}'.")

    def _save_findings(self, project_id: str, findings: List[DriftFinding]) -> None:
        pdir = project_service.get_analysis_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        self._get_findings_file(project_id).write_text(
            json.dumps([f.model_dump() for f in findings], indent=2), encoding="utf-8"
        )

    def _save_evidence(self, project_id: str, evidence: List[EvidenceReference]) -> None:
        pdir = project_service.get_analysis_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        self._get_evidence_file(project_id).write_text(
            json.dumps([e.model_dump() for e in evidence], indent=2), encoding="utf-8"
        )

    def _save_corrections(self, project_id: str, corrections: List[DocumentationCorrection]) -> None:
        pdir = project_service.get_analysis_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        self._get_corrections_file(project_id).write_text(
            json.dumps([c.model_dump() for c in corrections], indent=2), encoding="utf-8"
        )

    def _save_trace(self, project_id: str, trace: AgentExecutionTrace) -> None:
        pdir = project_service.get_analysis_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        self._get_trace_file(project_id).write_text(
            trace.model_dump_json(indent=2), encoding="utf-8"
        )


drift_service = DriftService()
