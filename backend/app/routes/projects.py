"""API routes for project management."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import ProjectNotFoundError
from app.models.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectFilesResponse,
    ProjectSummary,
)
from app.services.project_service import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate) -> ProjectSummary:
    """Creates a new project space."""
    return project_service.create_project(name=payload.name, description=payload.description)


@router.get("", response_model=List[ProjectSummary])
def list_projects() -> List[ProjectSummary]:
    """Returns a list of all existing projects."""
    return project_service.list_projects()


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    """Returns details for a specific project."""
    try:
        return project_service.get_project_detail(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/{project_id}/files", response_model=ProjectFilesResponse)
def get_project_files(project_id: str) -> ProjectFilesResponse:
    """Lists files associated with a project."""
    try:
        files = project_service.list_project_files(project_id)
        return ProjectFilesResponse(
            project_id=project_id,
            total_files=len(files),
            files=files,
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(project_id: str):
    """Safely deletes a project and all associated files."""
    try:
        project_service.delete_project(project_id)
        return {"status": "success", "message": f"Project '{project_id}' deleted successfully."}
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
