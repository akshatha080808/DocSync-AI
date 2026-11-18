from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.project_service import project_service
from app.engines.report_engine import report_engine
from app.models.finding import DriftFinding, DriftCategory, SeverityLevel, VerificationStatus, DetectionMethod
from app.models.correction import DocumentationCorrection


@pytest.fixture
def client(tmp_path: Path):
    orig_dir = settings.data_dir
    settings.data_dir = tmp_path / "data"
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    project_service.projects_dir = settings.projects_dir

    test_client = TestClient(app)
    yield test_client

    settings.data_dir = orig_dir
    project_service.projects_dir = settings.projects_dir


def test_quarter3_report_endpoints_and_engine(client: TestClient):
    # 1. Create a project via API
    create_resp = client.post(
        "/api/projects",
        json={"name": "Q3 Report Verification Project", "description": "Verifying PDF and JSON report generation"}
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # 2. Check JSON report endpoint
    json_resp = client.get(f"/api/projects/{project_id}/report/json")
    assert json_resp.status_code == 200
    data = json_resp.json()
    assert data["report_version"] == "1.0.0"
    assert data["project"]["id"] == project_id
    assert data["project"]["name"] == "Q3 Report Verification Project"
    assert "summary" in data

    # 3. Check PDF report endpoint
    pdf_resp = client.get(f"/api/projects/{project_id}/report/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 500
    assert pdf_resp.content.startswith(b"%PDF-")

    # 4. Direct ReportEngine verification with populated findings
    project = project_service.get_project_detail(project_id)
    sample_finding = DriftFinding(
        finding_id="test-finding-1",
        project_id=project_id,
        category=DriftCategory.CONTRADICTORY,
        title="Parameter mismatch in connect()",
        description="Doc lists timeout_ms, code expects timeout_sec",
        severity=SeverityLevel.HIGH,
        confidence=0.95,
        verification_status=VerificationStatus.VERIFIED,
        documentation={"file": "docs/api.md", "line": 42},
        source={"file": "app/client.py", "line_start": 15},
        symbol="connect",
        documented_claim="connect(host, timeout_ms=5000)",
        actual_fact="def connect(host: str, timeout_sec: int = 5)",
        explanation="Timeout units changed from ms to sec.",
        suggested_correction="Update timeout parameter to timeout_sec",
        detection_method=DetectionMethod.DETERMINISTIC,
        evidence_ids=["ev-1"],
        impact_explanation="Users passing timeout_ms will experience TypeError.",
    )
    sample_correction = DocumentationCorrection(
        correction_id="corr-1",
        project_id=project_id,
        file_path="docs/api.md",
        original_text="connect(host, timeout_ms=5000)",
        proposed_replacement="connect(host, timeout_sec=5)",
        unified_diff="--- docs/api.md\n+++ docs/api.md\n@@ -42,1 +42,1 @@\n-connect(host, timeout_ms=5000)\n+connect(host, timeout_sec=5)",
        line_start=42,
        line_end=42,
        section_name="Connection API",
        reason="Fix parameter name",
        supporting_finding_ids=["test-finding-1"],
        supporting_evidence_ids=[],
        validation_status="VERIFIED",
    )

    pdf_bytes = report_engine.generate_pdf_report(
        project=project,
        analysis=None,
        findings=[sample_finding],
        corrections=[sample_correction],
        trace=None,
    )
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
