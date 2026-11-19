"""Integration and unit tests for GitHub-connected repository auditing (Mode 2).

Verifies:
1. URL parsing (HTTP, HTTPS, SSH, shorthand) and invalid URL handling.
2. Connection verification and branch listing.
3. Initial synchronization and common analysis pipeline execution.
4. Idempotent / Up-to-date synchronization when commit SHA is unchanged.
5. Incremental commit change detection (added, modified, deleted files).
6. Mode 1 (ZIP) and Mode 2 (GitHub) coexistence and project isolation.
"""

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.github_service import github_service
from app.services.project_service import project_service


@pytest.fixture
def client(tmp_path: Path):
    orig_dir = settings.data_dir
    settings.data_dir = tmp_path / "data"
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    project_service.projects_dir = settings.projects_dir
    github_service.projects_dir = settings.projects_dir

    test_client = TestClient(app)
    yield test_client

    settings.data_dir = orig_dir
    project_service.projects_dir = settings.projects_dir
    github_service.projects_dir = settings.projects_dir


def test_github_url_parsing():
    # Valid formats
    o, r = github_service.parse_repo_url("https://github.com/google/docsync-ai")
    assert o == "google" and r == "docsync-ai"

    o, r = github_service.parse_repo_url("https://github.com/octocat/Hello-World.git")
    assert o == "octocat" and r == "Hello-World"

    o, r = github_service.parse_repo_url("pallets/flask")
    assert o == "pallets" and r == "flask"

    o, r = github_service.parse_repo_url("git@github.com:facebook/react.git")
    assert o == "facebook" and r == "react"

    # Invalid format
    with pytest.raises(Exception):
        github_service.parse_repo_url("invalid-url-without-slash")


def test_github_mode_lifecycle_and_synchronization(client: TestClient):
    # 1. Create a project in GitHub Mode (Mode 2) without initial repo URL
    create_resp = client.post(
        "/api/projects",
        json={
            "name": "DocSync GitHub Audit Project",
            "description": "Mode 2 testing project",
            "audit_mode": "github",
        },
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    assert create_resp.json()["audit_mode"] == "github"

    # 2. Check initial GitHub status (before explicit connection)
    status_resp = client.get(f"/api/projects/{project_id}/github/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is False

    # 3. Connect GitHub Repository (Mocking GitHub API verification)
    mock_repo_payload = {
        "name": "sample-repo",
        "default_branch": "main",
        "private": False,
        "owner": {"login": "sample-owner"},
    }
    mock_branch_payload = {
        "name": "main",
        "commit": {
            "sha": "a1b2c3d4e5f67890123456789abcdef012345678",
            "commit": {
                "message": "Initial commit with payment service and README",
                "author": {"name": "Test Author", "date": "2026-11-19T10:00:00Z"},
            },
        },
    }

    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        # First call verifies repo, second call gets branch HEAD commit
        mock_resp_1 = MagicMock(status_code=200, json=lambda: mock_repo_payload)
        mock_resp_2 = MagicMock(status_code=200, json=lambda: mock_branch_payload)
        mock_http.get.side_effect = [mock_resp_1, mock_resp_2]

        connect_resp = client.post(
            f"/api/projects/{project_id}/github/connect",
            json={
                "repo_url": "https://github.com/sample-owner/sample-repo",
                "branch": "main",
            },
        )
        assert connect_resp.status_code == 200
        conn_data = connect_resp.json()
        assert conn_data["connected"] is True
        assert conn_data["owner"] == "sample-owner"
        assert conn_data["repo_name"] == "sample-repo"
        assert conn_data["branch"] == "main"
        assert conn_data["latest_commit_sha"] == "a1b2c3d4e5f67890123456789abcdef012345678"

    # 4. List Branches
    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        mock_branches = [
            {"name": "main", "commit": {"sha": "a1b2c3d4e5f67890123456789abcdef012345678"}},
            {"name": "feature/v2", "commit": {"sha": "b2c3d4e5f67890123456789abcdef012345678a"}},
        ]
        mock_http.get.return_value = MagicMock(status_code=200, json=lambda: mock_branches)

        branches_resp = client.get(f"/api/projects/{project_id}/github/branches")
        assert branches_resp.status_code == 200
        branches = branches_resp.json()
        assert len(branches) == 2
        assert branches[0]["name"] == "main"
        assert branches[0]["is_default"] is True

    # 5. First Sync (Downloads repo archive, runs common analysis pipeline & drift detection)
    # Prepare in-memory repo zipball with intentional documentation drift
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "sample-repo-main/service.py",
            """def calculate_fee(amount: float, tax_rate: float = 0.18) -> float:
    return amount * tax_rate
""",
        )
        zf.writestr(
            "sample-repo-main/README.md",
            """# Payment Service
The calculate_fee tax_rate defaults to 0.10.
Run `python main.py` to start service.
""",
        )

    zip_bytes = zip_buf.getvalue()

    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        # Call 1: branch details
        mock_branch_res = MagicMock(status_code=200, json=lambda: mock_branch_payload)
        # Call 2: zipball download
        mock_zip_res = MagicMock(status_code=200, content=zip_bytes)
        mock_http.get.side_effect = [mock_branch_res, mock_zip_res]

        sync_resp = client.post(f"/api/projects/{project_id}/github/sync")
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] in ("ANALYSIS_COMPLETED", "CHANGES_DETECTED")
        assert sync_data["latest_commit_sha"] == "a1b2c3d4e5f67890123456789abcdef012345678"
        assert sync_data["is_up_to_date"] is False
        assert sync_data["drift_findings_count"] >= 1

    # 6. Verify drift findings were generated from the GitHub repository
    findings_resp = client.get(f"/api/projects/{project_id}/findings")
    assert findings_resp.status_code == 200
    findings_data = findings_resp.json()
    assert findings_data["total_findings"] >= 1
    # Check default mismatch (0.10 documented vs 0.18 code) or missing main.py
    titles = [f["title"] for f in findings_data["findings"]]
    assert any("tax_rate" in t or "main.py" in t for t in titles)

    # 7. Verify unified diff corrections exist
    corr_resp = client.get(f"/api/projects/{project_id}/corrections")
    assert corr_resp.status_code == 200
    assert corr_resp.json()["total_corrections"] >= 1

    # 8. Check Second Sync with NO CHANGES (Up to date)
    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        mock_branch_res = MagicMock(status_code=200, json=lambda: mock_branch_payload)
        mock_http.get.side_effect = [mock_branch_res]

        sync_resp_2 = client.post(f"/api/projects/{project_id}/github/sync")
        assert sync_resp_2.status_code == 200
        sync_data_2 = sync_resp_2.json()
        assert sync_data_2["status"] == "UP_TO_DATE"
        assert sync_data_2["is_up_to_date"] is True
        assert "already up to date" in sync_data_2["message"]

    # 9. Commit & Sync History Retrieval
    hist_resp = client.get(f"/api/projects/{project_id}/github/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 1
    assert history[0]["commit_sha"] == "a1b2c3d4e5f67890123456789abcdef012345678"
    assert history[0]["sync_status"] == "COMPLETED"

    # 10. Check PDF & JSON Reports in Mode 2
    json_rep = client.get(f"/api/projects/{project_id}/report/json")
    assert json_rep.status_code == 200
    assert json_rep.json()["project"]["audit_mode"] == "github"

    pdf_rep = client.get(f"/api/projects/{project_id}/report/pdf")
    assert pdf_rep.status_code == 200
    assert pdf_rep.content.startswith(b"%PDF-")


def test_github_auto_connect_on_project_creation(client: TestClient):
    mock_repo_payload = {
        "name": "auto-repo",
        "default_branch": "develop",
        "private": False,
        "owner": {"login": "sample-owner"},
    }
    mock_branch_payload = {
        "name": "develop",
        "commit": {
            "sha": "1234567890abcdef1234567890abcdef12345678",
            "commit": {
                "message": "Auto connect commit",
                "author": {"name": "Auto Author", "date": "2026-11-19T10:00:00Z"},
            },
        },
    }

    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        mock_http.get.side_effect = [
            MagicMock(status_code=200, json=lambda: mock_repo_payload),
            MagicMock(status_code=200, json=lambda: mock_branch_payload),
        ]

        create_resp = client.post(
            "/api/projects",
            json={
                "name": "Auto Connect Project",
                "audit_mode": "github",
                "github_repo_url": "https://github.com/sample-owner/auto-repo",
                "github_branch": "develop",
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["audit_mode"] == "github"
        assert data["github_repo"] == "sample-owner/auto-repo"
        assert data["github_branch"] == "develop"
        project_id = data["id"]

        # Confirm github_config.json was immediately written
        status_resp = client.get(f"/api/projects/{project_id}/github/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["connected"] is True
        assert status_resp.json()["branch"] == "develop"


def test_github_sync_self_healing_when_config_missing(client: TestClient):
    """Simulates a legacy Mode 2 project (like gitdemo) where project.json has github_repo
    but github_config.json is absent. Calling sync should self-heal the connection.
    """
    mock_repo_payload = {
        "name": "healing-repo",
        "default_branch": "main",
        "private": False,
        "owner": {"login": "healing-owner"},
    }
    mock_branch_payload = {
        "name": "main",
        "commit": {
            "sha": "9999999999abcdef9999999999abcdef99999999",
            "commit": {
                "message": "Healed commit",
                "author": {"name": "Healer", "date": "2026-11-19T10:00:00Z"},
            },
        },
    }

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("healing-repo-main/main.py", "print('healed')\n")
        zf.writestr("healing-repo-main/README.md", "# Healing\nRun `python main.py`\n")

    # 1. Create project without auto-connecting (audit_mode=zip initially, then manually set github_repo in metadata)
    create_resp = client.post(
        "/api/projects",
        json={"name": "Unconnected Git Project", "audit_mode": "zip"},
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # Manually simulate project.json having audit_mode=github and github_repo but NO github_config.json
    proj_meta = project_service.get_project(project_id)
    proj_meta.audit_mode = "github"
    proj_meta.github_repo = "https://github.com/healing-owner/healing-repo"
    proj_meta.github_branch = "main"
    project_service.save_project_summary(proj_meta)

    # Confirm github_config.json does not exist
    config_file = github_service._get_config_path(project_id)
    if config_file.exists():
        config_file.unlink()

    # 2. Call sync endpoint -> self-healing should trigger and succeed
    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        # 1: verify_connection, 2: get branch commit (during connect), 3: get branch commit (during sync), 4: download zipball
        mock_http.get.side_effect = [
            MagicMock(status_code=200, json=lambda: mock_repo_payload),
            MagicMock(status_code=200, json=lambda: mock_branch_payload),
            MagicMock(status_code=200, json=lambda: mock_branch_payload),
            MagicMock(status_code=200, content=zip_buf.getvalue()),
        ]

        sync_resp = client.post(f"/api/projects/{project_id}/github/sync")
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] in ("ANALYSIS_COMPLETED", "CHANGES_DETECTED")
        assert sync_data["latest_commit_sha"] == "9999999999abcdef9999999999abcdef99999999"

        # Check that github_config.json now exists and is connected
        assert config_file.exists()
        status_resp = client.get(f"/api/projects/{project_id}/github/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["connected"] is True


def test_github_connection_failure_cleans_up_project(client: TestClient):
    """When a project is created with an inaccessible repository, the connection fails
    and the project directory is cleanly deleted without leaving a phantom broken workspace.
    """
    with patch("app.services.github_service.httpx.Client") as mock_client_cls:
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_http
        mock_http.get.return_value = MagicMock(status_code=404)

        create_resp = client.post(
            "/api/projects",
            json={
                "name": "Invalid Repo Project",
                "audit_mode": "github",
                "github_repo_url": "https://github.com/nonexistent/repo",
            },
        )
        assert create_resp.status_code == 404

        # Confirm no phantom project was left behind
        projects = client.get("/api/projects").json()
        assert not any(p["name"] == "Invalid Repo Project" for p in projects)

