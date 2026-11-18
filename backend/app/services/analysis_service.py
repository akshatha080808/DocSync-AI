"""Analysis service orchestrating all deterministic engines.

Pipeline stages:
1. Load and validate project structure
2. Identify source, documentation, and configuration files
3. Parse Python and JavaScript source files (SourceEngine)
4. Extract documentation and PDF documents (DocumentationEngine)
5. Extract configuration files and cross-reference code env refs (ConfigEngine)
6. Build module dependency graph (DependencyEngine)
7. Save analysis results to analysis/analysis.json
8. Return structured analysis result
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.core.exceptions import AnalysisError, ProjectNotFoundError
from app.engines.config_engine import config_engine
from app.engines.dependency_engine import dependency_engine
from app.engines.documentation_engine import documentation_engine
from app.engines.source_engine import IGNORED_DIRECTORIES, source_engine
from app.models.analysis import (
    AnalysisResult,
    AnalysisSummary,
    ExtractedConfigFile,
    ExtractedDocFile,
)
from app.models.source import ParsedSourceFile
from app.services.project_service import project_service


class AnalysisService:
    """Coordinates deterministic codebase analysis across all engines."""

    def analyze_project(self, project_id: str) -> AnalysisResult:
        """Executes full deterministic analysis pipeline for the given project."""
        project = project_service.get_project(project_id)
        source_dir = project_service.get_source_dir(project_id)
        docs_dir = project_service.get_documents_dir(project_id)
        analysis_dir = project_service.get_analysis_dir(project_id)
        analysis_dir.mkdir(parents=True, exist_ok=True)

        if not project.has_source and project.document_count == 0:
            raise AnalysisError("Cannot analyze empty project: no source code or documents have been uploaded.")

        warnings: List[str] = []
        parsed_sources: List[ParsedSourceFile] = []
        extracted_docs: List[ExtractedDocFile] = []
        extracted_configs: List[ExtractedConfigFile] = []

        # Track referenced environment variables in source code: key -> list of source file paths
        source_env_refs: Dict[str, List[str]] = {}

        # 1. Scan source directory
        if source_dir.exists():
            for p in sorted(source_dir.rglob("*")):
                if not p.is_file():
                    continue

                rel_path = p.relative_to(source_dir).as_posix()
                parts = set(rel_path.split("/"))
                if any(ignored in parts for ignored in IGNORED_DIRECTORIES):
                    continue

                ext = p.suffix.lower()
                name = p.name.lower()

                # Source code
                if ext in {".py", ".js", ".jsx", ".mjs", ".cjs"}:
                    parsed = source_engine.parse_file(p, rel_path)
                    if parsed:
                        parsed_sources.append(parsed)
                        if parsed.parse_error:
                            warnings.append(f"Source parse warning in '{rel_path}': {parsed.parse_error}")

                        # Scan for env variable references
                        try:
                            content = p.read_text(encoding="utf-8", errors="replace")
                            lang = "python" if ext == ".py" else "javascript"
                            env_keys = config_engine.scan_source_code_env_refs(content, lang)
                            for k in env_keys:
                                source_env_refs.setdefault(k, []).append(rel_path)
                        except Exception:
                            pass

                # In-repo Documentation
                elif ext in {".md", ".markdown", ".rst", ".txt", ".pdf"}:
                    doc = documentation_engine.extract_file(p, rel_path)
                    if doc:
                        extracted_docs.append(doc)
                        if doc.extraction_note:
                            warnings.append(f"Document note for '{rel_path}': {doc.extraction_note}")

                # Configuration
                if (
                    ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
                    or "example" in name
                    or "sample" in name
                    or "template" in name
                    or name.startswith(".env")
                ):
                    cfg = config_engine.extract_file(p, rel_path)
                    if cfg and (cfg.items or cfg.parse_error):
                        extracted_configs.append(cfg)
                        if cfg.parse_error:
                            warnings.append(f"Config parse warning in '{rel_path}': {cfg.parse_error}")

        # 2. Scan uploaded documents directory
        if docs_dir.exists():
            for p in sorted(docs_dir.rglob("*")):
                if not p.is_file():
                    continue
                rel_path = f"documents/{p.name}"
                doc = documentation_engine.extract_file(p, rel_path)
                if doc:
                    extracted_docs.append(doc)
                    if doc.extraction_note:
                        warnings.append(f"Document note for '{rel_path}': {doc.extraction_note}")

        # 3. Cross-reference configuration items with source code references
        for cfg in extracted_configs:
            for item in cfg.items:
                # Key might be dot-separated or direct
                leaf_key = item.key.split(".")[-1]
                if leaf_key in source_env_refs:
                    item.source_code_references = source_env_refs[leaf_key]
                elif item.key in source_env_refs:
                    item.source_code_references = source_env_refs[item.key]

        # 4. Build Dependency Graph
        dep_graph = dependency_engine.build_graph(parsed_sources)

        # 5. Calculate Summary metrics
        total_functions = sum(len(sf.functions) for sf in parsed_sources)
        total_classes = sum(len(sf.classes) for sf in parsed_sources)
        total_methods = sum(sum(len(c.methods) for c in sf.classes) for sf in parsed_sources)
        total_loc = sum(sf.loc for sf in parsed_sources)
        now_str = datetime.now(timezone.utc).isoformat()

        summary = AnalysisSummary(
            project_id=project_id,
            analyzed_at=now_str,
            source_files_count=len(parsed_sources),
            total_functions=total_functions,
            total_classes=total_classes,
            total_methods=total_methods,
            total_loc=total_loc,
            documentation_files_count=len(extracted_docs),
            configuration_files_count=len(extracted_configs),
            dependency_nodes_count=len(dep_graph.nodes),
            dependency_edges_count=len(dep_graph.edges),
            circular_dependency_count=len(dep_graph.cycles),
            warnings=warnings,
        )

        result = AnalysisResult(
            project_id=project_id,
            summary=summary,
            source_files=parsed_sources,
            documentation_files=extracted_docs,
            configuration_files=extracted_configs,
            dependency_graph=dep_graph,
        )

        # 6. Save results to disk
        analysis_file = analysis_dir / "analysis.json"
        analysis_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # 7. Update project summary
        project.analysis_status = "completed"
        project.last_analyzed_at = now_str
        project.updated_at = now_str
        project_service.save_project_summary(project)

        return result

    def get_analysis_result(self, project_id: str) -> AnalysisResult:
        """Loads existing analysis results from disk."""
        project_service.get_project(project_id)  # verify existence
        analysis_file = project_service.get_analysis_dir(project_id) / "analysis.json"
        if not analysis_file.exists():
            raise AnalysisError(f"No analysis results found for project '{project_id}'. Run /analyze first.")

        try:
            data = json.loads(analysis_file.read_text(encoding="utf-8"))
            return AnalysisResult(**data)
        except Exception as e:
            raise AnalysisError(f"Failed to read analysis results: {str(e)}")


analysis_service = AnalysisService()
