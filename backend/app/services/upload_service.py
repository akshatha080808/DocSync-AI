"""Service handling ZIP and PDF file uploads."""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import UploadRejectedError
from app.engines.archive_engine import archive_engine
from app.models.project import UploadResponse
from app.services.project_service import project_service


class UploadService:
    """Orchestrates upload validation, extraction, and project association."""

    async def handle_zip_upload(self, project_id: str, file: UploadFile) -> UploadResponse:
        """Processes repository ZIP upload: saves safely, extracts, and updates project metadata."""
        project = project_service.get_project(project_id)

        filename = file.filename or "archive.zip"
        if not filename.lower().endswith(".zip"):
            raise UploadRejectedError("Uploaded file must be a .zip archive.")

        # Stage in temporary file
        temp_dir = Path(tempfile.mkdtemp(prefix="docsync_zip_upload_"))
        temp_zip = temp_dir / filename

        try:
            total_bytes = 0
            with open(temp_zip, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    total_bytes += len(chunk)
                    if total_bytes > settings.max_upload_bytes:
                        raise UploadRejectedError(
                            f"Uploaded ZIP file exceeds maximum allowed size of {settings.max_upload_bytes} bytes."
                        )
                    buffer.write(chunk)

            # Safely extract into project's source directory
            source_dir = project_service.get_source_dir(project_id)
            # Clear previous source contents if any
            if source_dir.exists():
                for item in source_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            source_dir.mkdir(parents=True, exist_ok=True)

            extracted_count, uncompressed_size = archive_engine.validate_and_extract_zip(temp_zip, source_dir)

            # Update project metadata
            project.has_source = True
            project.source_archive_name = filename
            project.analysis_status = "unprocessed"
            project.updated_at = datetime.now(timezone.utc).isoformat()
            project_service.save_project_summary(project)

            return UploadResponse(
                project_id=project_id,
                message=f"Successfully extracted {extracted_count} files ({uncompressed_size} bytes).",
                files_processed=extracted_count,
                filenames=[filename],
            )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def handle_document_upload(self, project_id: str, files: List[UploadFile]) -> UploadResponse:
        """Processes document uploads (PDF, MD, etc.), saving into documents/ directory."""
        project = project_service.get_project(project_id)

        if not files:
            raise UploadRejectedError("No files were provided for document upload.")

        docs_dir = project_service.get_documents_dir(project_id)
        docs_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[str] = []

        for file in files:
            filename = file.filename or "document.pdf"
            # Normalize filename
            clean_name = Path(filename).name
            if not clean_name:
                continue

            # Target path
            target_path = docs_dir / clean_name
            total_bytes = 0

            with open(target_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > settings.max_upload_bytes:
                        if target_path.exists():
                            target_path.unlink()
                        raise UploadRejectedError(
                            f"Uploaded document '{clean_name}' exceeds size limit of {settings.max_upload_bytes} bytes."
                        )
                    buffer.write(chunk)

            if clean_name not in project.document_names:
                project.document_names.append(clean_name)
            saved_files.append(clean_name)

        project.document_count = len(project.document_names)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        project_service.save_project_summary(project)

        return UploadResponse(
            project_id=project_id,
            message=f"Successfully uploaded {len(saved_files)} documents.",
            files_processed=len(saved_files),
            filenames=saved_files,
        )


upload_service = UploadService()
