"""Data models for GitHub-connected repository auditing (Mode 2)."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class GitHubConnectRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL (e.g. https://github.com/owner/repo or owner/repo)")
    branch: Optional[str] = Field(default=None, description="Branch to track (defaults to repository default branch)")
    access_token: Optional[str] = Field(default=None, description="Optional Personal Access Token for private repositories")
    github_token: Optional[str] = Field(default=None, description="Alias for access_token")

    @property
    def token(self) -> Optional[str]:
        return self.access_token or self.github_token


class GitHubBranchInfo(BaseModel):
    name: str
    commit_sha: str
    is_default: bool = False


class GitHubRepoStatus(BaseModel):
    connected: bool = False
    repo_url: Optional[str] = None
    owner: Optional[str] = None
    repo_name: Optional[str] = None
    branch: Optional[str] = None
    default_branch: Optional[str] = None
    latest_commit_sha: Optional[str] = None
    previous_commit_sha: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    total_commits_tracked: int = 0
    drift_status: Optional[str] = None


class GitHubCommitHistoryItem(BaseModel):
    commit_sha: str
    commit_message: str
    author: str
    committed_at: str
    files_changed: List[str] = Field(default_factory=list)
    added_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    deleted_files: List[str] = Field(default_factory=list)
    doc_changes_count: int = 0
    code_changes_count: int = 0
    findings_count: int = 0
    synced_at: str
    sync_status: str = "COMPLETED"


class GitHubSyncResponse(BaseModel):
    project_id: str
    status: str  # UP_TO_DATE, CHANGES_DETECTED, ANALYSIS_COMPLETED, SYNC_FAILED
    previous_commit_sha: Optional[str] = None
    latest_commit_sha: str
    is_up_to_date: bool = False
    commits_ahead: int = 0
    files_changed: List[str] = Field(default_factory=list)
    added_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    deleted_files: List[str] = Field(default_factory=list)
    doc_files_changed: List[str] = Field(default_factory=list)
    code_files_changed: List[str] = Field(default_factory=list)
    drift_findings_count: int = 0
    message: str
