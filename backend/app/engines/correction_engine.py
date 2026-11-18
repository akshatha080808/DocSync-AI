"""Documentation correction engine.

Generates proposed corrections and reviewable unified diffs for verified findings:
- Never modifies original documentation files directly
- Produces clean unified diffs
- Persists corrections separately for review and approval
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import List, Optional

from app.models.correction import DocumentationCorrection
from app.models.finding import DriftFinding, VerificationStatus


class CorrectionEngine:
    """Produces proposed replacement text and unified diffs based on verified findings."""

    def generate_correction(
        self,
        finding: DriftFinding,
        project_dir: Optional[Path] = None,
        corr_id: str = "CORR-001",
    ) -> Optional[DocumentationCorrection]:
        if not finding.suggested_correction:
            return None

        # Build original snippet vs proposed replacement
        file_path = finding.documentation.file
        original_text = finding.documented_claim
        proposed = finding.suggested_correction

        # If project_dir is provided and file exists, try reading context
        if project_dir and (project_dir / file_path).exists():
            try:
                full_content = (project_dir / file_path).read_text(encoding="utf-8", errors="replace")
                if original_text in full_content:
                    lines_orig = full_content.splitlines(keepends=True)
                    replaced_content = full_content.replace(original_text, proposed, 1)
                    lines_mod = replaced_content.splitlines(keepends=True)
                    diff = "".join(
                        difflib.unified_diff(
                            lines_orig,
                            lines_mod,
                            fromfile=f"a/{file_path}",
                            tofile=f"b/{file_path}",
                        )
                    )
                else:
                    diff = self._create_snippet_diff(file_path, original_text, proposed)
            except Exception:
                diff = self._create_snippet_diff(file_path, original_text, proposed)
        else:
            diff = self._create_snippet_diff(file_path, original_text, proposed)

        return DocumentationCorrection(
            correction_id=corr_id,
            project_id=finding.project_id,
            file_path=file_path,
            original_text=original_text,
            proposed_replacement=proposed,
            unified_diff=diff,
            line_start=finding.documentation.line,
            section_name=finding.documentation.section,
            reason=finding.explanation,
            supporting_finding_ids=[finding.finding_id],
            supporting_evidence_ids=finding.evidence_ids,
            validation_status="VERIFIED" if finding.verification_status == VerificationStatus.VERIFIED else "UNVERIFIED",
        )

    def _create_snippet_diff(self, file_path: str, orig: str, repl: str) -> str:
        orig_lines = [line + "\n" for line in orig.splitlines()]
        repl_lines = [line + "\n" for line in repl.splitlines()]
        return "".join(
            difflib.unified_diff(
                orig_lines,
                repl_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )

    def generate_all(
        self,
        findings: List[DriftFinding],
        project_dir: Optional[Path] = None,
    ) -> List[DocumentationCorrection]:
        corrections: List[DocumentationCorrection] = []
        for idx, f in enumerate(findings, start=1):
            if f.verification_status == VerificationStatus.VERIFIED and f.suggested_correction:
                corr = self.generate_correction(f, project_dir, corr_id=f"CORR-{idx:03d}")
                if corr:
                    corrections.append(corr)
        return corrections


correction_engine = CorrectionEngine()
