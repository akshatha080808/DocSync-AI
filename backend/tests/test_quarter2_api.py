"""Integration tests for Quarter 2 API endpoints:
- POST /api/projects/{project_id}/detect-drift
- GET /api/projects/{project_id}/findings
- GET /api/projects/{project_id}/findings/{finding_id}
- POST /api/projects/{project_id}/run-agent
- GET /api/projects/{project_id}/agent-trace
- GET /api/projects/{project_id}/corrections
- GET /api/projects/{project_id}/corrections/{correction_id}
"""

import io
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.project_service import project_service


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


def test_drift_and_agent_api_endpoints(client: TestClient):
    # 1. Create a project
    create_resp = client.post("/api/projects", json={"name": "Drift API Test"})
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # 2. Upload ZIP with intentional drift
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "repo/src/service.py",
            """def start_worker(concurrency: int = 4):
    print("starting worker...")
""",
        )
        zf.writestr(
            "repo/README.md",
            """# Service
Run `stop_worker()` to shutdown.
Call `start_worker(concurrency=4, max_retries=3)`.
""",
        )

    zip_buf.seek(0)
    upload_resp = client.post(
        f"/api/projects/{project_id}/upload-zip",
        files={"file": ("repo.zip", zip_buf, "application/zip")},
    )
    assert upload_resp.status_code == 200

    # 3. Analyze Project
    analyze_resp = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_resp.status_code == 200

    # 4. Trigger Drift Detection: POST /api/projects/{id}/detect-drift
    drift_resp = client.post(f"/api/projects/{project_id}/detect-drift")
    assert drift_resp.status_code == 200
    drift_data = drift_resp.json()
    assert drift_data["total_findings"] >= 1
    finding_id = drift_data["findings"][0]["finding_id"]

    # 5. Get Findings: GET /api/projects/{id}/findings
    findings_resp = client.get(f"/api/projects/{project_id}/findings")
    assert findings_resp.status_code == 200
    assert findings_resp.json()["total_findings"] == drift_data["total_findings"]

    # 6. Get Finding Detail: GET /api/projects/{id}/findings/{finding_id}
    detail_resp = client.get(f"/api/projects/{project_id}/findings/{finding_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["finding_id"] == finding_id

    # 7. Run Agent Investigation: POST /api/projects/{id}/run-agent
    agent_resp = client.post(f"/api/projects/{project_id}/run-agent")
    assert agent_resp.status_code == 200
    agent_data = agent_resp.json()
    assert agent_data["status"] == "COMPLETED"
    assert "trace" in agent_data

    # 8. Get Agent Trace: GET /api/projects/{id}/agent-trace
    trace_resp = client.get(f"/api/projects/{project_id}/agent-trace")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["total_steps"] >= 3

    # 9. Get Proposed Corrections: GET /api/projects/{id}/corrections
    corr_resp = client.get(f"/api/projects/{project_id}/corrections")
    assert corr_resp.status_code == 200
    corr_data = corr_resp.json()
    assert corr_data["total_corrections"] >= 1
    corr_id = corr_data["corrections"][0]["correction_id"]

    # 10. Get Correction Detail: GET /api/projects/{id}/corrections/{correction_id}
    c_detail_resp = client.get(f"/api/projects/{project_id}/corrections/{corr_id}")
    assert c_detail_resp.status_code == 200
    c_detail = c_detail_resp.json()
    assert c_detail["correction_id"] == corr_id
    assert "---" in c_detail["unified_diff"]
