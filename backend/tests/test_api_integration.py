"""Integration tests for all FastAPI endpoints:
- GET /health
- POST /api/projects
- GET /api/projects
- GET /api/projects/{project_id}
- POST /api/projects/{project_id}/upload-zip
- POST /api/projects/{project_id}/upload-documents
- GET /api/projects/{project_id}/files
- POST /api/projects/{project_id}/analyze
- GET /api/projects/{project_id}/analysis
- GET /api/projects/{project_id}/dependencies
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
    # Route storage to temporary folder during tests
    orig_dir = settings.data_dir
    settings.data_dir = tmp_path / "data"
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    project_service.projects_dir = settings.projects_dir

    test_client = TestClient(app)
    yield test_client

    # Reset
    settings.data_dir = orig_dir
    project_service.projects_dir = settings.projects_dir


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "DocSync" in data["app"]


def test_project_crud_and_not_found(client: TestClient):
    # 1. Create project
    create_resp = client.post("/api/projects", json={"name": "Test Project", "description": "Demo desc"})
    assert create_resp.status_code == 201
    project = create_resp.json()
    assert project["name"] == "Test Project"
    project_id = project["id"]

    # 2. List projects
    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == project_id for p in projects)

    # 3. Get single project
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id

    # 4. Non-existent project
    missing_resp = client.get("/api/projects/non-existent-id")
    assert missing_resp.status_code == 404


def test_full_upload_and_analysis_pipeline(client: TestClient):
    # 1. Create Project
    create_resp = client.post("/api/projects", json={"name": "End2End Project"})
    project_id = create_resp.json()["id"]

    # 2. Build in-memory ZIP repository with Python, JS, and config
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "repo/src/service.py",
            """import os
from .utils import add_numbers

def calculate(x: int) -> int:
    '''Calculate docstring.'''
    secret = os.getenv('DB_PASSWORD')
    return add_numbers(x, 10)
""",
        )
        zf.writestr(
            "repo/src/utils.py",
            """def add_numbers(a: int, b: int) -> int:
    return a + b
""",
        )
        zf.writestr(
            "repo/src/web.js",
            """function renderApp(mountNode) {
    console.log('Rendering...');
}
module.exports = { renderApp };
""",
        )
        zf.writestr(
            "repo/README.md",
            """# E2E Project
This is an end-to-end test project.
## Installation
```bash
pip install -r requirements.txt
```
""",
        )
        zf.writestr(
            "repo/.env.example",
            """DB_PASSWORD=secret_db_pass
PORT=8000
""",
        )

    zip_buf.seek(0)

    # 3. Upload ZIP
    upload_resp = client.post(
        f"/api/projects/{project_id}/upload-zip",
        files={"file": ("repo.zip", zip_buf, "application/zip")},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["files_processed"] == 5

    # 4. Upload Documentation Document
    doc_buf = io.BytesIO(b"# Manual\nSystem Manual details\n")
    upload_doc_resp = client.post(
        f"/api/projects/{project_id}/upload-documents",
        files=[("files", ("manual.md", doc_buf, "text/markdown"))],
    )
    assert upload_doc_resp.status_code == 200
    assert upload_doc_resp.json()["files_processed"] == 1

    # 5. List project files
    files_resp = client.get(f"/api/projects/{project_id}/files")
    assert files_resp.status_code == 200
    files_data = files_resp.json()
    assert files_data["total_files"] == 6

    # 6. Trigger Analysis
    analyze_resp = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()

    assert analysis["project_id"] == project_id
    summary = analysis["summary"]
    assert summary["source_files_count"] == 3  # service.py, utils.py, web.js
    assert summary["total_functions"] >= 3
    assert summary["documentation_files_count"] >= 2  # README.md + manual.md
    assert summary["configuration_files_count"] >= 1  # .env.example

    # Verify secret was redacted in analysis result
    cfg_files = analysis["configuration_files"]
    assert len(cfg_files) >= 1
    env_cfg = next(c for c in cfg_files if ".env" in c["file_path"])
    db_pass_item = next(i for i in env_cfg["items"] if "PASSWORD" in i["key"])
    assert db_pass_item["is_secret"] is True
    assert db_pass_item["default_value"] is None
    # Verify source reference detected
    assert any("service.py" in ref for ref in db_pass_item["source_code_references"])

    # 7. Get Analysis Results
    get_analysis_resp = client.get(f"/api/projects/{project_id}/analysis")
    assert get_analysis_resp.status_code == 200
    assert get_analysis_resp.json()["summary"]["total_functions"] == summary["total_functions"]

    # 8. Get Dependencies (React Flow schema)
    dep_resp = client.get(f"/api/projects/{project_id}/dependencies")
    assert dep_resp.status_code == 200
    dep_data = dep_resp.json()
    assert "nodes" in dep_data
    assert "edges" in dep_data
    assert "cycles" in dep_data
    assert len(dep_data["nodes"]) == 3
    # Check that service.py imports utils.py edge exists
    edge_pairs = [(e["source"], e["target"]) for e in dep_data["edges"]]
    assert any("service.py" in s and "utils.py" in t for s, t in edge_pairs)
