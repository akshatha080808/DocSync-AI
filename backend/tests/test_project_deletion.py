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


def test_project_deletion_lifecycle_and_security(client: TestClient):
    # 1. Create two projects
    p1 = client.post("/api/projects", json={"name": "Project To Delete"}).json()
    p2 = client.post("/api/projects", json={"name": "Project To Keep"}).json()

    p1_id = p1["id"]
    p2_id = p2["id"]

    p1_dir = project_service._get_project_dir(p1_id)
    p2_dir = project_service._get_project_dir(p2_id)

    assert p1_dir.exists()
    assert (p1_dir / "project.json").exists()
    assert p2_dir.exists()

    # 2. Delete p1
    del_resp = client.delete(f"/api/projects/{p1_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # 3. Verify p1 is deleted from disk
    assert not p1_dir.exists()

    # 4. Verify p2 is completely untouched
    assert p2_dir.exists()
    assert (p2_dir / "project.json").exists()

    # 5. Verify p1 no longer appears in project list
    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200
    project_ids = [p["id"] for p in list_resp.json()]
    assert p1_id not in project_ids
    assert p2_id in project_ids

    # 6. Verify deleting nonexistent project returns 404
    del_again = client.delete(f"/api/projects/{p1_id}")
    assert del_again.status_code == 404

    # 7. Security: Verify path traversal attempt is rejected
    traversal_resp = client.delete("/api/projects/..%2F..%2Fetc")
    assert traversal_resp.status_code in (400, 404)

    # 8. Clean up p2
    client.delete(f"/api/projects/{p2_id}")
    assert not p2_dir.exists()
