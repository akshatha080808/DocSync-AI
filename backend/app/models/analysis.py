"""Data models for documentation, configuration, dependency graph, and analysis results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.source import ParsedSourceFile


class DocSection(BaseModel):
    heading: str
    level: int
    content: str
    code_examples: List[str] = Field(default_factory=list)
    page_number: Optional[int] = None


class ExtractedDocFile(BaseModel):
    file_path: str  # project-relative
    doc_type: str   # markdown, rst, text, pdf
    title: Optional[str] = None
    sections: List[DocSection] = Field(default_factory=list)
    code_examples: List[str] = Field(default_factory=list)
    function_references: List[str] = Field(default_factory=list)
    class_references: List[str] = Field(default_factory=list)
    parameter_references: List[str] = Field(default_factory=list)
    setup_instructions: List[str] = Field(default_factory=list)
    cli_commands: List[str] = Field(default_factory=list)
    config_references: List[str] = Field(default_factory=list)
    total_pages: Optional[int] = None
    extraction_note: Optional[str] = None


class ExtractedConfigItem(BaseModel):
    key: str
    value_type: str
    default_value: Optional[str] = None
    is_secret: bool = False
    file_path: str
    line_number: Optional[int] = None
    source_code_references: List[str] = Field(default_factory=list)


class ExtractedConfigFile(BaseModel):
    file_path: str
    format: str  # json, yaml, toml, ini, env_example
    items: List[ExtractedConfigItem] = Field(default_factory=list)
    parse_error: Optional[str] = None


class DependencyNode(BaseModel):
    id: str
    label: str
    file_path: str
    language: str


class DependencyEdge(BaseModel):
    source: str
    target: str
    relationship: str = "imports"


class DependencyGraph(BaseModel):
    nodes: List[DependencyNode] = Field(default_factory=list)
    edges: List[DependencyEdge] = Field(default_factory=list)
    cycles: List[List[str]] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)
    isolated_modules: List[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    project_id: str
    analyzed_at: str
    source_files_count: int
    total_functions: int
    total_classes: int
    total_methods: int
    total_loc: int
    documentation_files_count: int
    configuration_files_count: int
    dependency_nodes_count: int
    dependency_edges_count: int
    circular_dependency_count: int
    warnings: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    project_id: str
    summary: AnalysisSummary
    source_files: List[ParsedSourceFile] = Field(default_factory=list)
    documentation_files: List[ExtractedDocFile] = Field(default_factory=list)
    configuration_files: List[ExtractedConfigFile] = Field(default_factory=list)
    dependency_graph: DependencyGraph
