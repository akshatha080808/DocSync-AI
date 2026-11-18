"""Pydantic data models for documentation corrections and unified diffs."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentationCorrection(BaseModel):
    correction_id: str
    project_id: str
    file_path: str
    original_text: str
    proposed_replacement: str
    unified_diff: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_name: Optional[str] = None
    reason: str
    supporting_finding_ids: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    validation_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED


class ProjectCorrectionsResponse(BaseModel):
    project_id: str
    total_corrections: int
    corrections: List[DocumentationCorrection] = Field(default_factory=list)
