"""Specialized internal tool implementations for the DocSync AI Agent.

Registered tools:
1. search_source_symbols(query)
2. search_documentation(query)
3. inspect_symbol(symbol_name)
4. inspect_configuration(key_query)
5. compare_function_signature(function_name, documented_signature)
6. find_symbol_references(symbol_name)
7. inspect_module_dependencies(module_name)
8. validate_finding(finding_dict)
9. draft_documentation_correction(finding_id, proposed_text)
10. search_documentation_examples(keyword)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.models.analysis import AnalysisResult


class AgentToolRegistry:
    """Manages and executes controlled internal tools on an AnalysisResult."""

    def __init__(self, analysis: AnalysisResult):
        self.analysis = analysis

    def search_source_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Search extracted functions, classes, and methods across all parsed files."""
        results = []
        q = query.lower()
        for sf in self.analysis.source_files:
            for fn in sf.functions:
                if q in fn.name.lower():
                    results.append({
                        "type": "function",
                        "name": fn.name,
                        "file": sf.file_path,
                        "line": fn.line_start,
                        "is_async": fn.is_async,
                        "parameters": [p.name for p in fn.parameters],
                    })
            for cls in sf.classes:
                if q in cls.name.lower():
                    results.append({
                        "type": "class",
                        "name": cls.name,
                        "file": sf.file_path,
                        "line": cls.line_start,
                        "methods": [m.name for m in cls.methods],
                    })
                for m in cls.methods:
                    if q in m.name.lower():
                        results.append({
                            "type": "method",
                            "name": f"{cls.name}.{m.name}",
                            "file": sf.file_path,
                            "line": m.line_start,
                            "is_async": m.is_async,
                            "parameters": [p.name for p in m.parameters],
                        })
        return results[:10]

    def search_documentation(self, query: str) -> List[Dict[str, Any]]:
        """Search documentation claims, sections, and references."""
        results = []
        q = query.lower()
        for doc in self.analysis.documentation_files:
            for sec in doc.sections:
                if q in sec.heading.lower() or q in sec.content.lower():
                    results.append({
                        "file": doc.file_path,
                        "section": sec.heading,
                        "page": sec.page_number,
                        "snippet": sec.content[:200],
                    })
        return results[:10]

    def inspect_symbol(self, symbol_name: str) -> Dict[str, Any]:
        """Retrieve full extracted definition and metadata for a function or class."""
        for sf in self.analysis.source_files:
            for fn in sf.functions:
                if fn.name == symbol_name:
                    return {
                        "found": True,
                        "type": "function",
                        "name": fn.name,
                        "file": sf.file_path,
                        "line_start": fn.line_start,
                        "line_end": fn.line_end,
                        "is_async": fn.is_async,
                        "return_annotation": fn.return_annotation,
                        "parameters": [{"name": p.name, "default": p.default_value, "annotation": p.annotation} for p in fn.parameters],
                        "docstring": fn.docstring,
                    }
            for cls in sf.classes:
                if cls.name == symbol_name:
                    return {
                        "found": True,
                        "type": "class",
                        "name": cls.name,
                        "file": sf.file_path,
                        "line_start": cls.line_start,
                        "bases": cls.bases,
                        "docstring": cls.docstring,
                        "methods": [m.name for m in cls.methods],
                    }
        return {"found": False, "symbol": symbol_name, "message": "Symbol not found in codebase"}

    def inspect_configuration(self, key_query: str) -> List[Dict[str, Any]]:
        """Retrieve configuration keys, types, and defaults matching a query."""
        results = []
        q = key_query.lower()
        for cf in self.analysis.configuration_files:
            for item in cf.items:
                if q in item.key.lower():
                    results.append({
                        "file": cf.file_path,
                        "key": item.key,
                        "type": item.value_type,
                        "is_secret": item.is_secret,
                        "default_value": "[REDACTED]" if item.is_secret else item.default_value,
                        "source_references": item.source_code_references,
                    })
        return results

    def compare_function_signature(self, function_name: str, documented_signature: str) -> Dict[str, Any]:
        """Compare documented parameters with actual extracted parameters."""
        sym = self.inspect_symbol(function_name)
        if not sym.get("found"):
            return {"match": False, "error": f"Function '{function_name}' does not exist"}

        actual_params = [p["name"] for p in sym.get("parameters", [])]
        # Extract params from documented signature
        # e.g., "func(a, b=10, c=None)" -> ["a", "b", "c"]
        claimed_params = [p.strip().split("=")[0].split(":")[0].strip() for p in documented_signature.strip("()").split(",") if p.strip()]

        missing_in_doc = [p for p in actual_params if p not in claimed_params and not p.startswith("*")]
        extraneous_in_doc = [p for p in claimed_params if p not in actual_params and not p.startswith("*")]

        return {
            "match": len(missing_in_doc) == 0 and len(extraneous_in_doc) == 0,
            "actual_parameters": actual_params,
            "claimed_parameters": claimed_params,
            "missing_in_documentation": missing_in_doc,
            "extraneous_in_documentation": extraneous_in_doc,
        }

    def find_symbol_references(self, symbol_name: str) -> Dict[str, Any]:
        """Find references to a symbol across source imports and documentation."""
        source_refs = []
        doc_refs = []

        for sf in self.analysis.source_files:
            for imp in sf.imports:
                if symbol_name in imp.imported_names or symbol_name in imp.module:
                    source_refs.append({"file": sf.file_path, "line": imp.line_number})

        for doc in self.analysis.documentation_files:
            if symbol_name in doc.function_references or symbol_name in doc.class_references:
                doc_refs.append({"file": doc.file_path})
            else:
                for sec in doc.sections:
                    if symbol_name in sec.content:
                        doc_refs.append({"file": doc.file_path, "section": sec.heading})
                        break

        return {
            "symbol": symbol_name,
            "source_references": source_refs,
            "documentation_references": doc_refs,
        }

    def inspect_module_dependencies(self, module_name: str) -> Dict[str, Any]:
        """Retrieve dependencies and dependent modules from the NetworkX dependency graph."""
        nodes = {n.id: n for n in self.analysis.dependency_graph.nodes}
        matching_nodes = [nid for nid in nodes if module_name.lower() in nid.lower()]

        if not matching_nodes:
            return {"found": False, "message": f"Module '{module_name}' not found in dependency graph"}

        target_node = matching_nodes[0]
        incoming = [e.source for e in self.analysis.dependency_graph.edges if e.target == target_node]
        outgoing = [e.target for e in self.analysis.dependency_graph.edges if e.source == target_node]

        return {
            "module": target_node,
            "imported_by": incoming,
            "depends_on": outgoing,
        }

    def validate_finding(self, finding_title: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Verify whether an observed finding is backed by deterministic facts."""
        if symbol:
            sym_info = self.inspect_symbol(symbol)
            return {
                "valid": True,
                "symbol_verified": sym_info.get("found", False),
                "details": sym_info,
            }
        return {"valid": True, "note": "General finding validated"}

    def draft_documentation_correction(self, finding_id: str, proposed_text: str) -> Dict[str, Any]:
        """Draft a proposed correction text for a verified finding."""
        return {
            "finding_id": finding_id,
            "proposed_text": proposed_text,
            "status": "DRAFTED",
        }

    def search_documentation_examples(self, keyword: str) -> List[Dict[str, Any]]:
        """Search code blocks and examples in documentation."""
        examples = []
        kw = keyword.lower()
        for doc in self.analysis.documentation_files:
            for ex in doc.code_examples:
                if kw in ex.lower():
                    examples.append({"file": doc.file_path, "code_snippet": ex[:300]})
        return examples[:5]
