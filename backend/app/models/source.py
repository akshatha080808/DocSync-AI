"""Data models for extracted source code elements."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ParameterInfo(BaseModel):
    name: str
    default_value: Optional[str] = None
    annotation: Optional[str] = None


class FunctionInfo(BaseModel):
    name: str
    parameters: List[ParameterInfo] = Field(default_factory=list)
    return_annotation: Optional[str] = None
    is_async: bool = False
    docstring: Optional[str] = None
    line_start: int
    line_end: int


class MethodInfo(BaseModel):
    name: str
    parameters: List[ParameterInfo] = Field(default_factory=list)
    return_annotation: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    docstring: Optional[str] = None
    line_start: int
    line_end: int


class ClassInfo(BaseModel):
    name: str
    bases: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    methods: List[MethodInfo] = Field(default_factory=list)
    line_start: int
    line_end: int


class ImportInfo(BaseModel):
    module: str
    imported_names: List[str] = Field(default_factory=list)
    is_from_import: bool = False
    line_number: int


class ExportInfo(BaseModel):
    name: str
    export_type: str  # default, named
    line_number: int


class ParsedSourceFile(BaseModel):
    file_path: str  # project-relative
    language: str   # python, javascript
    functions: List[FunctionInfo] = Field(default_factory=list)
    classes: List[ClassInfo] = Field(default_factory=list)
    imports: List[ImportInfo] = Field(default_factory=list)
    exports: List[ExportInfo] = Field(default_factory=list)
    docstrings: List[str] = Field(default_factory=list)
    comments: List[str] = Field(default_factory=list)
    loc: int = 0
    parse_error: Optional[str] = None
