"""Pydantic data models for documentation drift findings, evidence, and severities."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DriftCategory(str, Enum):
    OUTDATED = "OUTDATED"
    MISSING = "MISSING"
    CONTRADICTORY = "CONTRADICTORY"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNCERTAIN = "UNCERTAIN"


class DetectionMethod(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    AI_ASSISTED = "AI_ASSISTED"
    HYBRID = "HYBRID"


class EvidenceReference(BaseModel):
    evidence_id: str
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    page_number: Optional[int] = None
    snippet: str
    source_type: str  # "code", "doc", "config"


class DocumentLocation(BaseModel):
    file: str
    line: Optional[int] = None
    page: Optional[int] = None
    section: Optional[str] = None


class SourceLocation(BaseModel):
    file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class DriftFinding(BaseModel):
    finding_id: str
    project_id: str
    category: DriftCategory
    title: str
    description: str
    severity: SeverityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    verification_status: VerificationStatus
    documentation: DocumentLocation
    source: Optional[SourceLocation] = None
    symbol: Optional[str] = None
    documented_claim: str
    actual_fact: str
    explanation: str
    suggested_correction: Optional[str] = None
    detection_method: DetectionMethod = DetectionMethod.DETERMINISTIC
    evidence_ids: List[str] = Field(default_factory=list)
    impact_explanation: Optional[str] = None


class ProjectFindingsResponse(BaseModel):
    project_id: str
    total_findings: int
    findings: List[DriftFinding] = Field(default_factory=list)
    evidence_pool: List[EvidenceReference] = Field(default_factory=list)
