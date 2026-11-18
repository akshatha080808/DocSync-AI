"""Investigation loop logic for resolving ambiguous claims and gathering evidence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.agents.agent_tools import AgentToolRegistry
from app.models.analysis import AnalysisResult
from app.models.finding import DriftFinding, VerificationStatus


class InvestigationService:
    """Coordinates deep dive investigation for uncertain or complex drift findings."""

    def __init__(self, registry: AgentToolRegistry):
        self.registry = registry

    def investigate_finding(self, finding: DriftFinding) -> DriftFinding:
        """Executes targeted tool lookups to upgrade or confirm a finding."""
        # If symbol is specified, inspect source
        if finding.symbol:
            sym_info = self.registry.inspect_symbol(finding.symbol)
            if not sym_info.get("found"):
                # Search if it was renamed or moved
                similar = self.registry.search_source_symbols(finding.symbol)
                if similar:
                    finding.explanation += f" Did you mean '{similar[0]['name']}' in '{similar[0]['file']}'?"

            # Check references
            refs = self.registry.find_symbol_references(finding.symbol)
            if refs.get("documentation_references"):
                doc_count = len(refs["documentation_references"])
                if doc_count > 1:
                    finding.explanation += f" Referenced across {doc_count} documentation locations."

        return finding
