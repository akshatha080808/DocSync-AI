"""Service managing project lifecycles, metadata storage, and project retrieval.

Storage Structure:
<data_dir>/projects/<project_id>/
    project.json           # Metadata (ProjectSummary)
    source/                # Extracted repository source code
    documents/             # Uploaded PDF and documentation files
    analysis/              # Deterministic analysis output (analysis.json)
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import ProjectNotFoundError
from app.models.project import FileInfo, ProjectDetail, ProjectSummary


class ProjectService:
    """Manages project creation, listing, file querying, and metadata persistence."""

    def __init__(self, projects_dir: Path = settings.projects_dir):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _get_project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _meta_file(self, project_id: str) -> Path:
        return self._get_project_dir(project_id) / "project.json"

    def get_source_dir(self, project_id: str) -> Path:
        return self._get_project_dir(project_id) / "source"

    def get_documents_dir(self, project_id: str) -> Path:
        return self._get_project_dir(project_id) / "documents"

    def get_analysis_dir(self, project_id: str) -> Path:
        return self._get_project_dir(project_id) / "analysis"

    def create_project(self, name: str, description: Optional[str] = None) -> ProjectSummary:
        project_id = str(uuid.uuid4())
        pdir = self._get_project_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        self.get_source_dir(project_id).mkdir(exist_ok=True)
        self.get_documents_dir(project_id).mkdir(exist_ok=True)
        self.get_analysis_dir(project_id).mkdir(exist_ok=True)

        now_str = datetime.now(timezone.utc).isoformat()
        summary = ProjectSummary(
            id=project_id,
            name=name,
            description=description,
            created_at=now_str,
            updated_at=now_str,
            has_source=False,
            document_count=0,
            document_names=[],
            analysis_status="unprocessed",
        )
        self.save_project_summary(summary)
        return summary

    def get_project(self, project_id: str) -> ProjectSummary:
        meta_file = self._meta_file(project_id)
        if not meta_file.exists():
            raise ProjectNotFoundError(project_id)
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return ProjectSummary(**data)
        except Exception:
            raise ProjectNotFoundError(project_id)

    def get_project_detail(self, project_id: str) -> ProjectDetail:
        summary = self.get_project(project_id)
        files = self.list_project_files(project_id)
        total_size = sum(f.size_bytes for f in files)
        return ProjectDetail(
            **summary.model_dump(),
            file_count=len(files),
            total_size_bytes=total_size,
        )

    def list_projects(self) -> List[ProjectSummary]:
        results: List[ProjectSummary] = []
        if not self.projects_dir.exists():
            return results

        for item in self.projects_dir.iterdir():
            if item.is_dir():
                meta = item / "project.json"
                if meta.exists():
                    try:
                        data = json.loads(meta.read_text(encoding="utf-8"))
                        results.append(ProjectSummary(**data))
                    except Exception:
                        continue
        # Sort newest first
        results.sort(key=lambda p: p.created_at, reverse=True)
        return results

    def save_project_summary(self, summary: ProjectSummary) -> None:
        pdir = self._get_project_dir(summary.id)
        pdir.mkdir(parents=True, exist_ok=True)
        meta_file = self._meta_file(summary.id)
        meta_file.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    def update_project_timestamp(self, project_id: str) -> None:
        summary = self.get_project(project_id)
        summary.updated_at = datetime.now(timezone.utc).isoformat()
        self.save_project_summary(summary)

    def delete_project(self, project_id: str) -> None:
        """Safely deletes a project and all its files, validating path constraints."""
        if not project_id or not isinstance(project_id, str):
            raise ValueError("Invalid project ID")

        # Sanitize against path traversal: no slashes, backslashes, or relative components
        if "/" in project_id or "\\" in project_id or ".." in project_id:
            raise ValueError("Invalid project ID format (path traversal attempt rejected)")

        pdir = self._get_project_dir(project_id).resolve()
        base_dir = self.projects_dir.resolve()

        # Strict containment check
        try:
            pdir.relative_to(base_dir)
        except ValueError:
            raise ValueError("Target deletion directory is outside project storage root")

        if pdir == base_dir:
            raise ValueError("Cannot delete root projects directory")

        if not pdir.exists() or not (pdir / "project.json").exists():
            raise ProjectNotFoundError(project_id)

        shutil.rmtree(pdir)

    def list_project_files(self, project_id: str) -> List[FileInfo]:
        """Lists files in the project's source and document directories without exposing disk paths."""
        self.get_project(project_id)  # verify exists
        file_list: List[FileInfo] = []

        source_dir = self.get_source_dir(project_id)
        if source_dir.exists():
            for p in source_dir.rglob("*"):
                if p.is_file():
                    # check if inside ignored directory
                    rel = p.relative_to(source_dir).as_posix()
                    parts = set(rel.split("/"))
                    if any(ignored in parts for ignored in {".git", "node_modules", ".venv", "venv", "__pycache__"}):
                        continue

                    ext = p.suffix.lower()
                    cat = "source"
                    lang = None
                    if ext == ".py":
                        lang = "python"
                    elif ext in {".js", ".jsx", ".mjs", ".cjs"}:
                        lang = "javascript"
                    elif ext in {".md", ".rst", ".txt", ".pdf"}:
                        cat = "documentation"
                    elif ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"} or p.name.startswith(".env"):
                        cat = "configuration"
                    else:
                        cat = "other"

                    file_list.append(
                        FileInfo(
                            rel_path=f"source/{rel}",
                            size_bytes=p.stat().st_size,
                            category=cat,
                            language=lang,
                            extension=ext,
                        )
                    )

        docs_dir = self.get_documents_dir(project_id)
        if docs_dir.exists():
            for p in docs_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(docs_dir).as_posix()
                    ext = p.suffix.lower()
                    file_list.append(
                        FileInfo(
                            rel_path=f"documents/{rel}",
                            size_bytes=p.stat().st_size,
                            category="documentation",
                            language=None,
                            extension=ext,
                        )
                    )

        return file_list


project_service = ProjectService()
