"""API routes for uploading project ZIP archives and documentation files."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.exceptions import DocSyncError, ProjectNotFoundError, UploadRejectedError
from app.models.project import DocumentDeleteResponse, UploadResponse
from app.services.upload_service import upload_service

router = APIRouter(prefix="/api/projects", tags=["uploads"])


@router.post("/{project_id}/upload-zip", response_model=UploadResponse)
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(..., description="ZIP archive containing repository source code"),
) -> UploadResponse:
    """Safely unpacks repository ZIP archive into project source directory."""
    try:
        return await upload_service.handle_zip_upload(project_id, file)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UploadRejectedError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected upload failure: {str(e)}")


@router.post("/{project_id}/upload-documents", response_model=UploadResponse)
async def upload_project_documents(
    project_id: str,
    files: List[UploadFile] = File(..., description="One or more PDF or documentation files"),
) -> UploadResponse:
    """Stores one or more PDF or documentation files into project documents directory."""
    try:
        return await upload_service.handle_document_upload(project_id, files)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UploadRejectedError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected upload failure: {str(e)}")


@router.delete("/{project_id}/documents/{filename}", response_model=DocumentDeleteResponse)
def delete_project_document(project_id: str, filename: str) -> DocumentDeleteResponse:
    """Safely deletes an individual uploaded documentation file and invalidates analysis results."""
    try:
        return upload_service.delete_document_file(project_id, filename)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected document deletion failure: {str(e)}")
