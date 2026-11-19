"""API routes for GitHub repository integration (Mode 2)."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import ProjectNotFoundError
from app.models.github import (
    GitHubBranchInfo,
    GitHubCommitHistoryItem,
    GitHubConnectRequest,
    GitHubRepoStatus,
    GitHubSyncResponse,
)
from app.services.github_service import github_service

router = APIRouter(prefix="/api/projects", tags=["github"])


@router.post("/{project_id}/github/connect", response_model=GitHubRepoStatus)
def connect_github_repository(project_id: str, req: GitHubConnectRequest) -> GitHubRepoStatus:
    """Connects project to a GitHub repository, verifying accessibility."""
    try:
        return github_service.connect_repository(project_id, req)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect GitHub repository: {str(e)}")


@router.get("/{project_id}/github/status", response_model=GitHubRepoStatus)
def get_github_status(project_id: str) -> GitHubRepoStatus:
    """Retrieves current GitHub repository connection and sync status."""
    try:
        return github_service.get_status(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve GitHub status: {str(e)}")


@router.get("/{project_id}/github/branches", response_model=List[GitHubBranchInfo])
def list_github_branches(project_id: str) -> List[GitHubBranchInfo]:
    """Lists available branches for the connected GitHub repository."""
    try:
        return github_service.list_branches(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list branches: {str(e)}")


@router.post("/{project_id}/github/sync", response_model=GitHubSyncResponse)
def sync_github_repository(project_id: str) -> GitHubSyncResponse:
    """Triggers 'Sync Now' on the connected repository, detecting commit changes,
    re-running analysis and drift detection, and updating audit history.
    """
    try:
        return github_service.sync_repository(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub synchronization failed: {str(e)}")


@router.get("/{project_id}/github/history", response_model=List[GitHubCommitHistoryItem])
def get_github_history(project_id: str) -> List[GitHubCommitHistoryItem]:
    """Retrieves synchronization and commit audit history."""
    try:
        return github_service.get_history(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve GitHub history: {str(e)}")
