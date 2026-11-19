import io
from pathlib import Path
import zipfile
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


def create_sample_zip() -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("main.py", "def calculate_total(price, tax):\n    return price + tax\n")
    buf.seek(0)
    return buf


def test_document_deletion_success(client: TestClient):
    # 1. Create project
    p = client.post("/api/projects", json={"name": "Doc Delete Test"}).json()
    p_id = p["id"]

    # 2. Upload two documentation files
    doc1 = io.BytesIO(b"# Doc 1\nContent 1")
    doc2 = io.BytesIO(b"# Doc 2\nContent 2")

    r1 = client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("README.md", doc1, "text/markdown"))],
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("ARCH.md", doc2, "text/markdown"))],
    )
    assert r2.status_code == 200

    docs_dir = project_service.get_documents_dir(p_id)
    assert (docs_dir / "README.md").exists()
    assert (docs_dir / "ARCH.md").exists()

    # Verify project summary
    proj_resp = client.get(f"/api/projects/{p_id}").json()
    assert proj_resp["document_count"] == 2
    assert "README.md" in proj_resp["document_names"]
    assert "ARCH.md" in proj_resp["document_names"]

    # 3. Delete README.md
    del_resp = client.delete(f"/api/projects/{p_id}/documents/README.md")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["filename"] == "README.md"
    assert del_data["remaining_documents"] == ["ARCH.md"]
    assert del_data["document_count"] == 1

    # Verify disk
    assert not (docs_dir / "README.md").exists()
    assert (docs_dir / "ARCH.md").exists()

    # Verify project summary refreshed
    proj_resp_after = client.get(f"/api/projects/{p_id}").json()
    assert proj_resp_after["document_count"] == 1
    assert proj_resp_after["document_names"] == ["ARCH.md"]


def test_document_deletion_not_found(client: TestClient):
    # Create project
    p = client.post("/api/projects", json={"name": "Not Found Test"}).json()
    p_id = p["id"]

    # Delete non-existent file
    del_resp = client.delete(f"/api/projects/{p_id}/documents/nonexistent.md")
    assert del_resp.status_code == 404
    assert "not found" in del_resp.json()["detail"].lower()

    # Delete from non-existent project
    del_resp_proj = client.delete("/api/projects/invalid-project-id/documents/any.md")
    assert del_resp_proj.status_code == 404


def test_document_deletion_path_traversal_protection(client: TestClient):
    p = client.post("/api/projects", json={"name": "Traversal Test"}).json()
    p_id = p["id"]

    # Upload valid document and source zip
    client.post(
        f"/api/projects/{p_id}/upload-zip",
        files={"file": ("source.zip", create_sample_zip(), "application/zip")},
    )
    client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("guide.md", io.BytesIO(b"# Guide"), "text/markdown"))],
    )

    source_file = project_service.get_source_dir(p_id) / "main.py"
    assert source_file.exists()

    # Attempt path traversal variations
    traversal_attempts = [
        "../source/main.py",
        "..%2Fsource%2Fmain.py",
        "../../project.json",
        "..\\source\\main.py",
        "documents/../../../etc/passwd",
        "sub/file.md",
    ]

    for attempt in traversal_attempts:
        del_resp = client.delete(f"/api/projects/{p_id}/documents/{attempt}")
        assert del_resp.status_code in (400, 404), f"Failed to reject traversal: {attempt}"

    # Source code and project metadata must remain completely untouched
    assert source_file.exists()
    assert (project_service._get_project_dir(p_id) / "project.json").exists()


def test_document_deletion_invalidates_analysis(client: TestClient):
    p = client.post("/api/projects", json={"name": "Invalidation Test"}).json()
    p_id = p["id"]

    # Upload source and doc
    client.post(
        f"/api/projects/{p_id}/upload-zip",
        files={"file": ("source.zip", create_sample_zip(), "application/zip")},
    )
    client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("README.md", io.BytesIO(b"# API\ncalculate_total(price, tax, discount)"), "text/markdown"))],
    )

    # Run analysis & drift
    analysis_resp = client.post(f"/api/projects/{p_id}/analyze")
    assert analysis_resp.status_code == 200

    drift_resp = client.post(f"/api/projects/{p_id}/detect-drift")
    assert drift_resp.status_code == 200

    analysis_dir = project_service.get_analysis_dir(p_id)
    assert (analysis_dir / "analysis.json").exists()
    assert (analysis_dir / "findings.json").exists()
    assert (analysis_dir / "corrections.json").exists()

    p_before = client.get(f"/api/projects/{p_id}").json()
    assert p_before["analysis_status"] == "completed"

    # Delete README.md
    del_resp = client.delete(f"/api/projects/{p_id}/documents/README.md")
    assert del_resp.status_code == 200

    # Verify artifacts purged
    assert not (analysis_dir / "analysis.json").exists()
    assert not (analysis_dir / "findings.json").exists()
    assert not (analysis_dir / "corrections.json").exists()

    # Verify project status reset to unprocessed
    p_after = client.get(f"/api/projects/{p_id}").json()
    assert p_after["analysis_status"] == "unprocessed"
    assert p_after["drift_status"] == "unprocessed"
    assert p_after["last_analyzed_at"] is None

    # Verify findings and corrections return empty cleanly (no 422 crash)
    findings_resp = client.get(f"/api/projects/{p_id}/findings")
    assert findings_resp.status_code == 200
    assert findings_resp.json()["total_findings"] == 0

    corrections_resp = client.get(f"/api/projects/{p_id}/corrections")
    assert corrections_resp.status_code == 200
    assert corrections_resp.json()["total_corrections"] == 0


def test_reupload_and_reanalyze_after_deletion(client: TestClient):
    p = client.post("/api/projects", json={"name": "Reupload Test"}).json()
    p_id = p["id"]

    client.post(
        f"/api/projects/{p_id}/upload-zip",
        files={"file": ("source.zip", create_sample_zip(), "application/zip")},
    )
    # Upload outdated doc
    client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("README.md", io.BytesIO(b"# API\ncalculate_total(price, tax, discount)"), "text/markdown"))],
    )
    client.post(f"/api/projects/{p_id}/analyze")
    client.post(f"/api/projects/{p_id}/detect-drift")

    # Delete outdated doc
    del_r = client.delete(f"/api/projects/{p_id}/documents/README.md")
    assert del_r.status_code == 200

    # Re-upload updated doc with identical filename
    reup = client.post(
        f"/api/projects/{p_id}/upload-documents",
        files=[("files", ("README.md", io.BytesIO(b"# API\ncalculate_total(price, tax)"), "text/markdown"))],
    )
    assert reup.status_code == 200

    # Re-analyze and detect drift cleanly
    re_analysis = client.post(f"/api/projects/{p_id}/analyze")
    assert re_analysis.status_code == 200

    re_drift = client.post(f"/api/projects/{p_id}/detect-drift")
    assert re_drift.status_code == 200

    p_final = client.get(f"/api/projects/{p_id}").json()
    assert p_final["analysis_status"] == "completed"
    assert p_final["document_count"] == 1


def test_project_isolation_on_document_deletion(client: TestClient):
    # Two projects with identical filename README.md
    p1 = client.post("/api/projects", json={"name": "Project Alpha"}).json()
    p2 = client.post("/api/projects", json={"name": "Project Beta"}).json()

    client.post(
        f"/api/projects/{p1['id']}/upload-documents",
        files=[("files", ("README.md", io.BytesIO(b"# Alpha Readme"), "text/markdown"))],
    )
    client.post(
        f"/api/projects/{p2['id']}/upload-documents",
        files=[("files", ("README.md", io.BytesIO(b"# Beta Readme"), "text/markdown"))],
    )

    docs1 = project_service.get_documents_dir(p1["id"])
    docs2 = project_service.get_documents_dir(p2["id"])

    assert (docs1 / "README.md").exists()
    assert (docs2 / "README.md").exists()

    # Delete from Project Alpha
    del_resp = client.delete(f"/api/projects/{p1['id']}/documents/README.md")
    assert del_resp.status_code == 200

    # Alpha is deleted, Beta remains intact with original content
    assert not (docs1 / "README.md").exists()
    assert (docs2 / "README.md").exists()
    assert (docs2 / "README.md").read_text(encoding="utf-8") == "# Beta Readme"
