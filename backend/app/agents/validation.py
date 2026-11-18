"""Validation loop logic to verify AI-generated or preliminary findings against deterministic facts."""

from __future__ import annotations

from typing import List
from app.agents.agent_tools import AgentToolRegistry
from app.models.finding import DriftFinding, VerificationStatus


class ValidationService:
    """Verifies that findings are strictly grounded in deterministic code facts."""

    def __init__(self, registry: AgentToolRegistry):
        self.registry = registry

    def validate_finding(self, finding: DriftFinding) -> DriftFinding:
        """Validates finding facts against extracted evidence."""
        # 1. If finding claims symbol does not exist, verify with inspect_symbol
        if "does not exist" in finding.title.lower() and finding.symbol:
            sym_info = self.registry.inspect_symbol(finding.symbol)
            if sym_info.get("found"):
                # Symbol actually exists! Finding is invalidated or needs revision
                finding.verification_status = VerificationStatus.UNVERIFIED
                finding.explanation = f"Validation failed: Symbol '{finding.symbol}' was found in '{sym_info['file']}'."
                return finding
            else:
                finding.verification_status = VerificationStatus.VERIFIED

        # 2. If finding specifies a source file, verify the file exists
        if finding.source and finding.source.file:
            matching = [sf for sf in self.registry.analysis.source_files if sf.file_path == finding.source.file]
            if not matching:
                finding.verification_status = VerificationStatus.UNCERTAIN
                return finding

        # 3. If finding has high confidence and valid evidence, mark VERIFIED
        if finding.confidence >= 0.80 and finding.evidence_ids:
            finding.verification_status = VerificationStatus.VERIFIED

        return finding

    def validate_all(self, findings: List[DriftFinding]) -> List[DriftFinding]:
        return [self.validate_finding(f) for f in findings]
