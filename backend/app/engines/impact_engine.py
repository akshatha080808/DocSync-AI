"""Impact and severity ranking engine.

Computes transparent, deterministic scores for findings across four levels:
- CRITICAL
- HIGH
- MEDIUM
- LOW
(and INFO)

Factors evaluated:
1. Public API exposure (affects external consumers)
2. Broken code examples (causes immediate copy-paste runtime errors)
3. Setup / installation inaccuracy (blocks onboarding and deployments)
4. Configuration & secret security impact
5. Dependency centrality (how many other modules depend on affected symbol)
6. Multi-file documentation contradiction
"""

from __future__ import annotations

from typing import Dict, List, Optional
from app.models.analysis import AnalysisResult
from app.models.finding import DriftCategory, DriftFinding, SeverityLevel


class ImpactEngine:
    """Calculates deterministic severity levels and structured explanations."""

    def evaluate_and_rank(self, finding: DriftFinding, analysis: Optional[AnalysisResult] = None) -> DriftFinding:
        score = 0
        reasons: List[str] = []

        # 1. Broken code examples or invalid parameters
        if finding.category == DriftCategory.INVALID or "example" in finding.title.lower():
            score += 40
            reasons.append("Broken code example will cause immediate runtime failure when executed")

        # 2. Outdated public functions / methods
        if finding.category == DriftCategory.OUTDATED and finding.symbol:
            score += 35
            reasons.append(f"Referenced symbol '{finding.symbol}' does not exist in the codebase")

        # 3. Setup and installation contradictions
        if "setup" in finding.title.lower() or "install" in finding.title.lower():
            score += 35
            reasons.append("Inaccurate setup or installation instructions block developer onboarding")

        # 4. Configuration drift
        if "config" in finding.title.lower() or "variable" in finding.title.lower():
            score += 25
            reasons.append("Configuration drift can lead to misconfigured deployment environments")

        # 5. Contradictory claims (e.g. async vs sync)
        if finding.category == DriftCategory.CONTRADICTORY:
            score += 30
            reasons.append("Contradictory documentation leads to incorrect caller assumptions")

        # 6. Missing documentation
        if finding.category == DriftCategory.MISSING:
            score += 15
            reasons.append("Missing public documentation impedes discoverability and proper usage")

        # 7. Centrality check from dependency graph if available
        if analysis and finding.symbol:
            # Check if symbol is in a module with high incoming dependency degree
            for node in analysis.dependency_graph.nodes:
                if finding.source and finding.source.file in node.file_path:
                    in_edges = [e for e in analysis.dependency_graph.edges if e.target == node.id]
                    if len(in_edges) >= 2:
                        score += 20
                        reasons.append(f"Affected module has {len(in_edges)} incoming internal dependencies")
                        break

        # Map total score to SeverityLevel
        if score >= 60:
            severity = SeverityLevel.CRITICAL
        elif score >= 35:
            severity = SeverityLevel.HIGH
        elif score >= 20:
            severity = SeverityLevel.MEDIUM
        elif score > 0:
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.INFO

        finding.severity = severity
        finding.impact_explanation = "; ".join(reasons) if reasons else "Routine documentation observation"
        return finding

    def rank_all(self, findings: List[DriftFinding], analysis: Optional[AnalysisResult] = None) -> List[DriftFinding]:
        for f in findings:
            self.evaluate_and_rank(f, analysis)
        # Sort CRITICAL -> HIGH -> MEDIUM -> LOW -> INFO
        order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4,
        }
        findings.sort(key=lambda x: (order.get(x.severity, 5), -x.confidence))
        return findings


impact_engine = ImpactEngine()
