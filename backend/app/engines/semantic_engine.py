"""Semantic documentation analysis engine powered by Google Gemini SDK.

Capabilities:
- Validates and analyzes natural language documentation claims against deterministic codebase evidence
- Defends against prompt injection via core/security.py (UNTRUSTED_DATA_NOTICE)
- Redacts credentials before prompt construction
- Returns structured JSON validated via Pydantic
- Handles missing GEMINI_API_KEY gracefully without crashing
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.security import UNTRUSTED_DATA_NOTICE, redact_text_secrets
from app.models.analysis import AnalysisResult
from app.models.finding import (
    DetectionMethod,
    DocumentLocation,
    DriftCategory,
    DriftFinding,
    EvidenceReference,
    SeverityLevel,
    SourceLocation,
    VerificationStatus,
)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class SemanticEngine:
    """Uses Gemini 2.0 Flash to detect nuanced semantic documentation drift."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model or "gemini-2.0-flash"
        self._client = None
        if self.api_key and genai is not None:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def analyze_semantic_drift(
        self,
        analysis: AnalysisResult,
        doc_claim: str,
        doc_file: str,
        related_symbol: Optional[str] = None,
    ) -> Optional[DriftFinding]:
        """Analyzes a single documentation claim against codebase evidence using Gemini."""
        if not self.is_available:
            return None

        # Build evidence context
        evidence_summary = self._build_evidence_summary(analysis, related_symbol)
        safe_claim = redact_text_secrets(doc_claim)

        prompt = f"""{UNTRUSTED_DATA_NOTICE}

You are an expert documentation drift detector. Compare the following documentation claim against the extracted codebase facts.

=== DOCUMENTATION CLAIM ===
File: {doc_file}
Claim: {safe_claim}

=== EXTRACTED CODEBASE FACTS ===
{evidence_summary}

Determine if there is a contradiction, invalid statement, or drift between the claim and the codebase facts.
Respond with ONLY a valid JSON object matching this schema:
{{
  "has_drift": true/false,
  "category": "OUTDATED" | "MISSING" | "CONTRADICTORY" | "INVALID" | "INCOMPLETE",
  "title": "short title",
  "explanation": "concise explanation why the claim drifts from facts",
  "actual_fact": "what the codebase actually does",
  "suggested_correction": "how to reword the documentation accurately",
  "confidence": 0.0 to 1.0,
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
}}

If the facts are insufficient to verify or disprove the claim, respond with {{"has_drift": false, "uncertain": true}}.
"""

        try:
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            if not response.text:
                return None

            data = json.loads(response.text)
            if not data.get("has_drift"):
                return None

            cat_str = data.get("category", "CONTRADICTORY").upper()
            try:
                category = DriftCategory(cat_str)
            except ValueError:
                category = DriftCategory.CONTRADICTORY

            sev_str = data.get("severity", "MEDIUM").upper()
            try:
                severity = SeverityLevel(sev_str)
            except ValueError:
                severity = SeverityLevel.MEDIUM

            return DriftFinding(
                finding_id=f"SEM-{abs(hash(doc_claim)) % 10000:04d}",
                project_id=analysis.project_id,
                category=category,
                title=data.get("title", "Semantic documentation discrepancy"),
                description=data.get("explanation", ""),
                severity=severity,
                confidence=float(data.get("confidence", 0.85)),
                verification_status=VerificationStatus.VERIFIED,
                documentation=DocumentLocation(file=doc_file),
                symbol=related_symbol,
                documented_claim=doc_claim,
                actual_fact=data.get("actual_fact", "Documented statement does not match codebase reality"),
                explanation=data.get("explanation", ""),
                suggested_correction=data.get("suggested_correction"),
                detection_method=DetectionMethod.AI_ASSISTED,
                impact_explanation="Semantic inconsistency identified between prose description and actual implementation.",
            )

        except Exception:
            return None

    def _build_evidence_summary(self, analysis: AnalysisResult, symbol: Optional[str] = None) -> str:
        lines: List[str] = []
        lines.append(f"Source Files: {len(analysis.source_files)}")
        for sf in analysis.source_files:
            fn_summaries = []
            for f in sf.functions:
                params_str = ", ".join(p.name for p in f.parameters)
                fn_summaries.append(f"{f.name}({params_str})")
            cls_names = [c.name for c in sf.classes]
            lines.append(f"- {sf.file_path} (lang: {sf.language}): Functions={fn_summaries}, Classes={cls_names}")

        if analysis.configuration_files:
            lines.append("Configuration items:")
            for cf in analysis.configuration_files:
                keys = [item.key for item in cf.items]
                lines.append(f"- {cf.file_path}: {keys}")

        return "\n".join(lines[:40])


semantic_engine = SemanticEngine()
