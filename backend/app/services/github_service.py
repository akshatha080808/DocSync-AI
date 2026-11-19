"""GitHub integration service managing repository connections, branch tracking,
archive download, commit comparison, and synchronization (Mode 2).
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.exceptions import ProjectNotFoundError, UploadRejectedError
from app.engines.archive_engine import archive_engine
from app.models.github import (
    GitHubBranchInfo,
    GitHubCommitHistoryItem,
    GitHubConnectRequest,
    GitHubRepoStatus,
    GitHubSyncResponse,
)
from app.services.analysis_service import analysis_service
from app.services.drift_service import drift_service
from app.services.project_service import project_service


class GitHubService:
    """Manages GitHub repository connection, synchronization, and change tracking."""

    def __init__(self, projects_dir: Path = settings.projects_dir):
        self.projects_dir = projects_dir

    def _get_config_path(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id).parent / "github_config.json"

    def _get_history_path(self, project_id: str) -> Path:
        return project_service.get_analysis_dir(project_id).parent / "github_history.json"

    def parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """Extracts (owner, repo) from various GitHub URL formats."""
        cleaned = repo_url.strip()
        # Handle SSH format: git@github.com:owner/repo.git
        ssh_match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", cleaned)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        # Handle HTTPS format: https://github.com/owner/repo(.git)?
        https_match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git|/)?$", cleaned)
        if https_match:
            return https_match.group(1), https_match.group(2)

        # Handle shorthand: owner/repo
        short_match = re.match(r"^([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$", cleaned)
        if short_match:
            return short_match.group(1), short_match.group(2)

        raise HTTPException(
            status_code=400,
            detail=f"Invalid GitHub repository URL: '{repo_url}'. Use 'https://github.com/owner/repo' or 'owner/repo'.",
        )

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DocSync-AI-Auditor/1.0",
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def verify_connection(self, owner: str, repo: str, token: Optional[str] = None) -> Dict[str, any]:
        """Validates that repository exists and is accessible, returning basic repo info."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = self._get_headers(token)

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(api_url, headers=headers)
                if res.status_code == 404:
                    msg = f"GitHub repository '{owner}/{repo}' not found. If it is private, provide a valid Personal Access Token."
                    raise HTTPException(status_code=404, detail=msg)
                elif res.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid GitHub Personal Access Token.")
                elif res.status_code == 403:
                    rate_limit_reset = res.headers.get("x-ratelimit-reset")
                    raise HTTPException(
                        status_code=403,
                        detail="GitHub API rate limit exceeded or access forbidden. Check token permissions.",
                    )
                elif res.status_code != 200:
                    raise HTTPException(
                        status_code=res.status_code,
                        detail=f"GitHub API error: {res.text}",
                    )
                return res.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to connect to GitHub API: {str(e)}")

    def list_branches(self, project_id: str) -> List[GitHubBranchInfo]:
        """Lists available branches for the connected repository."""
        config = self.get_config(project_id)
        if not config or not config.get("connected"):
            # Self-healing for projects where project.json has audit_mode == "github"
            project = project_service.get_project(project_id)
            if project.audit_mode == "github" and project.github_repo:
                try:
                    self.connect_repository(
                        project_id,
                        GitHubConnectRequest(
                            repo_url=project.github_repo,
                            branch=project.github_branch,
                        ),
                    )
                    config = self.get_config(project_id)
                except Exception:
                    pass

        if not config or not config.get("connected"):
            raise HTTPException(status_code=400, detail="No GitHub repository connected for this project.")

        owner = config.get("owner")
        repo = config.get("repo_name")
        token = config.get("access_token")
        default_branch = config.get("default_branch", "main")

        api_url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=30"
        headers = self._get_headers(token)

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(api_url, headers=headers)
                if res.status_code != 200:
                    raise HTTPException(status_code=res.status_code, detail="Failed to fetch branches from GitHub.")

                data = res.json()
                branches: List[GitHubBranchInfo] = []
                for b in data:
                    name = b.get("name", "")
                    sha = b.get("commit", {}).get("sha", "")
                    branches.append(
                        GitHubBranchInfo(
                            name=name,
                            commit_sha=sha,
                            is_default=(name == default_branch),
                        )
                    )
                return branches
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Network error connecting to GitHub: {str(e)}")

    def get_config(self, project_id: str) -> Optional[Dict[str, any]]:
        cfg_file = self._get_config_path(project_id)
        if not cfg_file.exists():
            return None
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_config(self, project_id: str, config: Dict[str, any]) -> None:
        cfg_file = self._get_config_path(project_id)
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def get_history(self, project_id: str) -> List[GitHubCommitHistoryItem]:
        hist_file = self._get_history_path(project_id)
        if not hist_file.exists():
            return []
        try:
            items = json.loads(hist_file.read_text(encoding="utf-8"))
            return [GitHubCommitHistoryItem(**item) for item in items]
        except Exception:
            return []

    def save_history(self, project_id: str, history: List[GitHubCommitHistoryItem]) -> None:
        hist_file = self._get_history_path(project_id)
        hist_file.parent.mkdir(parents=True, exist_ok=True)
        data = [item.model_dump() for item in history]
        hist_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def connect_repository(self, project_id: str, req: GitHubConnectRequest) -> GitHubRepoStatus:
        """Connects a project to a GitHub repository, validates access, and stores configuration."""
        project = project_service.get_project(project_id)
        owner, repo_name = self.parse_repo_url(req.repo_url)

        token = req.token
        # Verify access via GitHub API
        repo_data = self.verify_connection(owner, repo_name, token)
        default_branch = repo_data.get("default_branch", "main")
        selected_branch = req.branch.strip() if (req.branch and req.branch.strip()) else default_branch

        # Fetch latest commit on selected branch
        branch_api = f"https://api.github.com/repos/{owner}/{repo_name}/branches/{selected_branch}"
        headers = self._get_headers(token)
        latest_sha = ""
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(branch_api, headers=headers)
                if res.status_code == 200:
                    latest_sha = res.json().get("commit", {}).get("sha", "")
        except Exception:
            pass

        # Update and save config
        config = {
            "connected": True,
            "repo_url": f"https://github.com/{owner}/{repo_name}",
            "owner": owner,
            "repo_name": repo_name,
            "branch": selected_branch,
            "default_branch": default_branch,
            "access_token": token if token else None,
            "latest_commit_sha": latest_sha or None,
            "previous_commit_sha": None,
            "last_sync_at": None,
            "last_sync_status": "NEVER_SYNCED",
        }
        self.save_config(project_id, config)

        # Update project summary to GitHub mode
        project.audit_mode = "github"
        project.github_repo = f"{owner}/{repo_name}"
        project.github_branch = selected_branch
        project.latest_commit_sha = latest_sha or None
        project_service.save_project_summary(project)

        return self.get_status(project_id)

    def get_status(self, project_id: str) -> GitHubRepoStatus:
        """Returns the current connection and synchronization status of the GitHub repository."""
        project = project_service.get_project(project_id)
        config = self.get_config(project_id)
        if (not config or not config.get("connected")) and project.audit_mode == "github" and project.github_repo:
            # Self-healing attempt
            try:
                self.connect_repository(
                    project_id,
                    GitHubConnectRequest(
                        repo_url=project.github_repo,
                        branch=project.github_branch,
                    ),
                )
                config = self.get_config(project_id)
            except Exception:
                pass

        if not config:
            return GitHubRepoStatus(
                connected=False,
                repo_url=project.github_repo if project.audit_mode == "github" else None,
                owner=None,
                repo_name=None,
                branch=project.github_branch if project.audit_mode == "github" else None,
                default_branch=None,
                latest_commit_sha=None,
                previous_commit_sha=None,
                last_sync_at=None,
                last_sync_status="NOT_CONNECTED",
                total_commits_tracked=0,
                drift_status=project.drift_status,
            )

        history = self.get_history(project_id)
        return GitHubRepoStatus(
            connected=config.get("connected", False),
            repo_url=config.get("repo_url"),
            owner=config.get("owner"),
            repo_name=config.get("repo_name"),
            branch=config.get("branch"),
            default_branch=config.get("default_branch"),
            latest_commit_sha=config.get("latest_commit_sha"),
            previous_commit_sha=config.get("previous_commit_sha"),
            last_sync_at=config.get("last_sync_at"),
            last_sync_status=config.get("last_sync_status", "NEVER_SYNCED"),
            total_commits_tracked=len(history),
            drift_status=project.drift_status,
        )

    def sync_repository(self, project_id: str) -> GitHubSyncResponse:
        """Fetches the latest repository state, compares commit SHAs, updates code/docs,
        runs deterministic analysis and drift detection, and records commit history.
        """
        config = self.get_config(project_id)
        if not config or not config.get("connected"):
            # Self-healing: if project is in GitHub mode and has a repo URL, attempt connection
            project = project_service.get_project(project_id)
            if project.audit_mode == "github" and project.github_repo:
                try:
                    self.connect_repository(
                        project_id,
                        GitHubConnectRequest(
                            repo_url=project.github_repo,
                            branch=project.github_branch,
                        ),
                    )
                    config = self.get_config(project_id)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to automatically establish GitHub connection: {str(e)}",
                    )

        if not config or not config.get("connected"):
            raise HTTPException(status_code=400, detail="No GitHub repository is connected for this project.")

        owner = config["owner"]
        repo = config["repo_name"]
        branch = config["branch"]
        token = config.get("access_token")
        previous_sha = config.get("latest_commit_sha")

        headers = self._get_headers(token)

        # 1. Fetch current branch HEAD commit details
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        try:
            with httpx.Client(timeout=15.0) as client:
                b_res = client.get(branch_url, headers=headers)
                if b_res.status_code != 200:
                    raise HTTPException(
                        status_code=b_res.status_code,
                        detail=f"Failed to fetch branch '{branch}' from GitHub API.",
                    )
                b_data = b_res.json()
                latest_sha = b_data.get("commit", {}).get("sha", "")
                commit_info = b_data.get("commit", {}).get("commit", {})
                commit_message = commit_info.get("message", "Synchronized repository")
                author_name = commit_info.get("author", {}).get("name", "Unknown")
                committed_at = commit_info.get("author", {}).get("date", datetime.now(timezone.utc).isoformat())
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Network error querying branch commit: {str(e)}")

        now_str = datetime.now(timezone.utc).isoformat()

        # Check if already up to date
        source_dir = project_service.get_source_dir(project_id)
        has_existing_source = any(source_dir.iterdir()) if source_dir.exists() else False

        if previous_sha and latest_sha and previous_sha == latest_sha and has_existing_source:
            # Already synchronized to this exact commit
            config["last_sync_at"] = now_str
            config["last_sync_status"] = "UP_TO_DATE"
            self.save_config(project_id, config)

            findings_count = 0
            try:
                findings_resp = drift_service.get_findings(project_id)
                findings_count = findings_resp.total_findings
            except Exception:
                pass

            return GitHubSyncResponse(
                project_id=project_id,
                status="UP_TO_DATE",
                previous_commit_sha=previous_sha,
                latest_commit_sha=latest_sha,
                is_up_to_date=True,
                commits_ahead=0,
                files_changed=[],
                added_files=[],
                modified_files=[],
                deleted_files=[],
                doc_files_changed=[],
                code_files_changed=[],
                drift_findings_count=findings_count,
                message=f"Repository '{owner}/{repo}' is already up to date at commit {latest_sha[:7]}.",
            )

        # 2. Compare commits if previous_sha exists, else first sync
        added_files: List[str] = []
        modified_files: List[str] = []
        deleted_files: List[str] = []
        files_changed: List[str] = []

        if previous_sha and previous_sha != latest_sha:
            compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{previous_sha}...{latest_sha}"
            try:
                with httpx.Client(timeout=15.0) as client:
                    c_res = client.get(compare_url, headers=headers)
                    if c_res.status_code == 200:
                        c_data = c_res.json()
                        for f in c_data.get("files", []):
                            fname = f.get("filename", "")
                            status = f.get("status", "")
                            files_changed.append(fname)
                            if status == "added":
                                added_files.append(fname)
                            elif status == "removed":
                                deleted_files.append(fname)
                            else:
                                modified_files.append(fname)
            except Exception:
                pass

        # 3. Download repository archive from GitHub API
        archive_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{latest_sha}"
        temp_zip_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp_zip_path = Path(temp_zip_file.name)
        temp_zip_file.close()

        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                res = client.get(archive_url, headers=headers)
                if res.status_code != 200:
                    raise HTTPException(
                        status_code=res.status_code,
                        detail=f"Failed to download repository zipball: HTTP {res.status_code}",
                    )
                temp_zip_path.write_bytes(res.content)

            # Safely extract archive into project source directory using ArchiveEngine
            # Clear old source content first
            if source_dir.exists():
                shutil.rmtree(source_dir)
            source_dir.mkdir(parents=True, exist_ok=True)

            archive_engine.validate_and_extract_zip(temp_zip_path, source_dir)

            # Automatically copy/link top-level documentation files to documents_dir
            docs_dir = project_service.get_documents_dir(project_id)
            docs_dir.mkdir(parents=True, exist_ok=True)
            doc_names: List[str] = []

            for root, _, files in os.walk(source_dir):
                for f in files:
                    lower_f = f.lower()
                    if lower_f.startswith("readme") or lower_f.endswith((".md", ".rst", ".pdf", ".txt")):
                        src_doc = Path(root) / f
                        dst_doc = docs_dir / f
                        # Copy to documents folder if not present
                        if not dst_doc.exists():
                            shutil.copy2(src_doc, dst_doc)
                        if f not in doc_names:
                            doc_names.append(f)

            # Mark project as having source and documents before running analysis
            project = project_service.get_project(project_id)
            project.has_source = True
            project.document_count = len(doc_names)
            project.document_names = doc_names
            project_service.save_project_summary(project)

            # 4. Trigger Common Analysis Pipeline
            analysis = analysis_service.analyze_project(project_id)

            # 5. Trigger Drift Detection & Ranking
            findings_resp = drift_service.detect_and_save_drift(project_id)
            findings_count = findings_resp.total_findings

            # Classify changed files
            doc_exts = {".md", ".rst", ".txt", ".pdf"}
            doc_files_changed = [f for f in files_changed if any(f.lower().endswith(ext) for ext in doc_exts)]
            code_files_changed = [f for f in files_changed if f not in doc_files_changed]

            # 6. Update History
            history = self.get_history(project_id)
            history_item = GitHubCommitHistoryItem(
                commit_sha=latest_sha,
                commit_message=commit_message.splitlines()[0] if commit_message else "Repository update",
                author=author_name,
                committed_at=committed_at,
                files_changed=files_changed,
                added_files=added_files,
                modified_files=modified_files,
                deleted_files=deleted_files,
                doc_changes_count=len(doc_files_changed),
                code_changes_count=len(code_files_changed),
                findings_count=findings_count,
                synced_at=now_str,
                sync_status="COMPLETED",
            )
            # Insert at beginning
            history.insert(0, history_item)
            self.save_history(project_id, history)

            # 7. Update Configuration and Project Metadata
            config["previous_commit_sha"] = previous_sha
            config["latest_commit_sha"] = latest_sha
            config["last_sync_at"] = now_str
            config["last_sync_status"] = "ANALYSIS_COMPLETED"
            self.save_config(project_id, config)

            project = project_service.get_project(project_id)
            project.has_source = True
            project.latest_commit_sha = latest_sha
            project.document_count = len(doc_names)
            project.document_names = doc_names
            project.analysis_status = "completed"
            project.last_analyzed_at = now_str
            project.drift_status = "completed"
            project.last_drift_detected_at = now_str
            project_service.save_project_summary(project)

            status_str = "CHANGES_DETECTED" if previous_sha else "ANALYSIS_COMPLETED"
            msg = (
                f"Synchronized {len(files_changed)} changed files from commit {latest_sha[:7]} ({findings_count} drift findings detected)."
                if previous_sha
                else f"Initial synchronization completed at commit {latest_sha[:7]} with {findings_count} drift findings detected."
            )

            return GitHubSyncResponse(
                project_id=project_id,
                status=status_str,
                previous_commit_sha=previous_sha,
                latest_commit_sha=latest_sha,
                is_up_to_date=False,
                commits_ahead=1 if previous_sha else 0,
                files_changed=files_changed,
                added_files=added_files,
                modified_files=modified_files,
                deleted_files=deleted_files,
                doc_files_changed=doc_files_changed,
                code_files_changed=code_files_changed,
                drift_findings_count=findings_count,
                message=msg,
            )

        finally:
            if temp_zip_path.exists():
                temp_zip_path.unlink(missing_ok=True)


github_service = GitHubService()
