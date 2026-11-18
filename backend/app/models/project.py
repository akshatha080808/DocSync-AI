"""Data models for Project, Upload, and File listings."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str = Field(..., description="Display name for the project")
    description: Optional[str] = Field(default=None, description="Optional project description")


class ProjectCreate(ProjectBase):
    pass


class ProjectSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    has_source: bool = False
    source_archive_name: Optional[str] = None
    document_count: int = 0
    document_names: List[str] = Field(default_factory=list)
    analysis_status: str = "unprocessed"  # unprocessed, analyzing, completed, failed
    last_analyzed_at: Optional[str] = None


class ProjectDetail(ProjectSummary):
    file_count: int = 0
    total_size_bytes: int = 0


class FileInfo(BaseModel):
    rel_path: str
    size_bytes: int
    category: str  # source, documentation, configuration, other
    language: Optional[str] = None
    extension: str


class ProjectFilesResponse(BaseModel):
    project_id: str
    total_files: int
    files: List[FileInfo] = Field(default_factory=list)


class UploadResponse(BaseModel):
    project_id: str
    message: str
    files_processed: int
    filenames: List[str] = Field(default_factory=list)
