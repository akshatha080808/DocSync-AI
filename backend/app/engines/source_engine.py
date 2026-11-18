"""Source code parsing engine for Python (AST) and JavaScript (Tree-sitter).

Extracts:
- Functions (parameters, defaults, annotations, async status, docstring, lines)
- Classes (bases, methods, docstring, lines)
- Methods (parameters, defaults, annotations, async, static, classmethod, docstrings, lines)
- Imports & Exports
- Docstrings and inline comments
- Handles malformed files without crashing
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Optional

import tree_sitter_language_pack as tslp
from app.core.config import settings
from app.models.source import (
    ClassInfo,
    ExportInfo,
    FunctionInfo,
    ImportInfo,
    MethodInfo,
    ParameterInfo,
    ParsedSourceFile,
)

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
}


class PythonAstVisitor(ast.NodeVisitor):
    """Visits Python AST nodes to extract structural metadata."""

    def __init__(self, code_lines: List[str]):
        self.code_lines = code_lines
        self.functions: List[FunctionInfo] = []
        self.classes: List[ClassInfo] = []
        self.imports: List[ImportInfo] = []
        self.docstrings: List[str] = []
        self._current_class: Optional[ClassInfo] = None

    def _extract_params(self, args: ast.arguments) -> List[ParameterInfo]:
        params: List[ParameterInfo] = []
        # Non-default args length
        non_default_count = len(args.args) - len(args.defaults)

        for idx, arg in enumerate(args.args):
            default_val = None
            if idx >= non_default_count:
                default_node = args.defaults[idx - non_default_count]
                default_val = ast.unparse(default_node) if hasattr(ast, "unparse") else str(default_node)
            ann = ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, "unparse") else None
            params.append(ParameterInfo(name=arg.arg, default_value=default_val, annotation=ann))

        if args.vararg:
            ann = ast.unparse(args.vararg.annotation) if args.vararg.annotation and hasattr(ast, "unparse") else None
            params.append(ParameterInfo(name=f"*{args.vararg.arg}", annotation=ann))

        for idx, kw in enumerate(args.kwonlyargs):
            default_val = None
            if idx < len(args.kw_defaults) and args.kw_defaults[idx]:
                default_val = ast.unparse(args.kw_defaults[idx]) if hasattr(ast, "unparse") else None
            ann = ast.unparse(kw.annotation) if kw.annotation and hasattr(ast, "unparse") else None
            params.append(ParameterInfo(name=kw.arg, default_value=default_val, annotation=ann))

        if args.kwarg:
            ann = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation and hasattr(ast, "unparse") else None
            params.append(ParameterInfo(name=f"**{args.kwarg.arg}", annotation=ann))

        return params

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        doc = ast.get_docstring(node)
        if doc:
            self.docstrings.append(doc)

        params = self._extract_params(node.args)
        ret_ann = ast.unparse(node.returns) if node.returns and hasattr(ast, "unparse") else None

        line_start = node.lineno
        line_end = getattr(node, "end_lineno", node.lineno)

        if self._current_class is not None:
            # Method inside class
            is_static = any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list)
            is_classmethod = any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list)
            self._current_class.methods.append(
                MethodInfo(
                    name=node.name,
                    parameters=params,
                    return_annotation=ret_ann,
                    is_async=is_async,
                    is_static=is_static,
                    is_classmethod=is_classmethod,
                    docstring=doc,
                    line_start=line_start,
                    line_end=line_end,
                )
            )
        else:
            self.functions.append(
                FunctionInfo(
                    name=node.name,
                    parameters=params,
                    return_annotation=ret_ann,
                    is_async=is_async,
                    docstring=doc,
                    line_start=line_start,
                    line_end=line_end,
                )
            )

        # Do not recurse into nested functions when inside a class or outer function to keep top-level clean
        if self._current_class is None:
            # We don't visit internal statements
            pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        doc = ast.get_docstring(node)
        if doc:
            self.docstrings.append(doc)

        bases = [ast.unparse(b) if hasattr(ast, "unparse") else str(b) for b in node.bases]
        line_start = node.lineno
        line_end = getattr(node, "end_lineno", node.lineno)

        cls_info = ClassInfo(
            name=node.name,
            bases=bases,
            docstring=doc,
            methods=[],
            line_start=line_start,
            line_end=line_end,
        )

        prev_class = self._current_class
        self._current_class = cls_info
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(item)
        self._current_class = prev_class

        self.classes.append(cls_info)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    imported_names=[alias.asname or alias.name],
                    is_from_import=False,
                    line_number=node.lineno,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = ("." * node.level) + (node.module or "")
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportInfo(
                module=mod,
                imported_names=names,
                is_from_import=True,
                line_number=node.lineno,
            )
        )


class SourceEngine:
    """Parses Python and JavaScript source files into uniform Pydantic models."""

    def __init__(self, max_parse_bytes: int = settings.max_parse_bytes):
        self.max_parse_bytes = max_parse_bytes
        self._js_parser = None

    def _get_js_parser(self):
        if self._js_parser is None:
            self._js_parser = tslp.get_parser("javascript")
        return self._js_parser

    def parse_python_file(self, file_path: Path, rel_path: str) -> ParsedSourceFile:
        """Parses a Python file using Python's native AST."""
        size = file_path.stat().st_size
        if size > self.max_parse_bytes:
            return ParsedSourceFile(
                file_path=rel_path,
                language="python",
                parse_error=f"File exceeds maximum parse size limit ({size} > {self.max_parse_bytes} bytes)",
            )

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ParsedSourceFile(
                file_path=rel_path,
                language="python",
                parse_error=f"Failed to read file: {str(e)}",
            )

        lines = content.splitlines()
        loc = len(lines)

        # Extract inline comments
        comments: List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                comments.append(stripped.lstrip("#").strip())

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            return ParsedSourceFile(
                file_path=rel_path,
                language="python",
                loc=loc,
                comments=comments,
                parse_error=f"SyntaxError: {e.msg} at line {e.lineno}",
            )
        except Exception as e:
            return ParsedSourceFile(
                file_path=rel_path,
                language="python",
                loc=loc,
                comments=comments,
                parse_error=f"Parse error: {str(e)}",
            )

        visitor = PythonAstVisitor(lines)
        # Module docstring
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            visitor.docstrings.append(mod_doc)

        visitor.visit(tree)

        return ParsedSourceFile(
            file_path=rel_path,
            language="python",
            functions=visitor.functions,
            classes=visitor.classes,
            imports=visitor.imports,
            exports=[],  # Python exports implicitly or via __all__
            docstrings=visitor.docstrings,
            comments=comments,
            loc=loc,
        )

    def parse_javascript_file(self, file_path: Path, rel_path: str) -> ParsedSourceFile:
        """Parses a JavaScript file using Tree-sitter."""
        size = file_path.stat().st_size
        if size > self.max_parse_bytes:
            return ParsedSourceFile(
                file_path=rel_path,
                language="javascript",
                parse_error=f"File exceeds maximum parse size limit ({size} > {self.max_parse_bytes} bytes)",
            )

        try:
            raw_bytes = file_path.read_bytes()
            content = raw_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            return ParsedSourceFile(
                file_path=rel_path,
                language="javascript",
                parse_error=f"Failed to read file: {str(e)}",
            )

        lines = content.splitlines()
        loc = len(lines)

        try:
            parser = self._get_js_parser()
            tree = parser.parse(raw_bytes)
        except Exception as e:
            return ParsedSourceFile(
                file_path=rel_path,
                language="javascript",
                loc=loc,
                parse_error=f"Tree-sitter parse failure: {str(e)}",
            )

        functions: List[FunctionInfo] = []
        classes: List[ClassInfo] = []
        imports: List[ImportInfo] = []
        exports: List[ExportInfo] = []
        docstrings: List[str] = []
        comments: List[str] = []

        root = tree.root_node

        def node_text(node) -> str:
            return raw_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        def extract_js_params(params_node) -> List[ParameterInfo]:
            params: List[ParameterInfo] = []
            if not params_node:
                return params
            for child in params_node.children:
                if child.type in ("identifier", "formal_parameters", "rest_pattern"):
                    params.append(ParameterInfo(name=node_text(child)))
                elif child.type == "assignment_pattern":
                    # default value: left = right
                    left = child.child_by_field_name("left")
                    right = child.child_by_field_name("right")
                    param_name = node_text(left) if left else "arg"
                    def_val = node_text(right) if right else None
                    params.append(ParameterInfo(name=param_name, default_value=def_val))
            return params

        def find_preceding_comment(node) -> Optional[str]:
            prev = node.prev_sibling
            while prev and prev.type in ("\n", " "):
                prev = prev.prev_sibling
            if prev and prev.type == "comment":
                txt = node_text(prev)
                return txt
            return None

        # Traverse AST nodes
        def traverse(node):
            if node.type == "comment":
                c_text = node_text(node)
                comments.append(c_text)
                if c_text.startswith("/**"):
                    docstrings.append(c_text)
                return

            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = node_text(name_node) if name_node else "anonymous"
                is_async = any(c.type == "async" for c in node.children)
                params_node = node.child_by_field_name("parameters")
                params = extract_js_params(params_node)
                doc = find_preceding_comment(node)
                functions.append(
                    FunctionInfo(
                        name=name,
                        parameters=params,
                        is_async=is_async,
                        docstring=doc,
                        line_start=node.start_point.row + 1,
                        line_end=node.end_point.row + 1,
                    )
                )

            elif node.type == "lexical_declaration" or node.type == "variable_declaration":
                # Look for const fn = (...) => ... or const fn = function(...)
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        val_node = declarator.child_by_field_name("value")
                        if val_node and val_node.type in ("arrow_function", "function_expression"):
                            is_async = any(c.type == "async" for c in val_node.children)
                            params_node = val_node.child_by_field_name("parameters")
                            params = extract_js_params(params_node)
                            doc = find_preceding_comment(node)
                            functions.append(
                                FunctionInfo(
                                    name=node_text(name_node) if name_node else "anonymous",
                                    parameters=params,
                                    is_async=is_async,
                                    docstring=doc,
                                    line_start=declarator.start_point.row + 1,
                                    line_end=declarator.end_point.row + 1,
                                )
                            )

            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = node_text(name_node) if name_node else "AnonymousClass"
                doc = find_preceding_comment(node)
                # Heritage / extends
                bases: List[str] = []
                for child in node.children:
                    if child.type == "class_heritage":
                        bases.append(node_text(child).replace("extends", "").strip())

                methods: List[MethodInfo] = []
                body_node = node.child_by_field_name("body")
                if body_node:
                    for member in body_node.children:
                        if member.type == "method_definition":
                            m_name_node = member.child_by_field_name("name")
                            m_name = node_text(m_name_node) if m_name_node else "method"
                            m_is_async = any(c.type == "async" for c in member.children)
                            m_is_static = any(c.type == "static" for c in member.children)
                            m_params_node = member.child_by_field_name("parameters")
                            m_params = extract_js_params(m_params_node)
                            m_doc = find_preceding_comment(member)
                            methods.append(
                                MethodInfo(
                                    name=m_name,
                                    parameters=m_params,
                                    is_async=m_is_async,
                                    is_static=m_is_static,
                                    docstring=m_doc,
                                    line_start=member.start_point.row + 1,
                                    line_end=member.end_point.row + 1,
                                )
                            )

                classes.append(
                    ClassInfo(
                        name=name,
                        bases=bases,
                        docstring=doc,
                        methods=methods,
                        line_start=node.start_point.row + 1,
                        line_end=node.end_point.row + 1,
                    )
                )

            elif node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                source = node_text(source_node).strip("'\"") if source_node else ""
                names = []
                for child in node.children:
                    if child.type == "import_clause":
                        names.append(node_text(child))
                imports.append(
                    ImportInfo(
                        module=source,
                        imported_names=names,
                        is_from_import=True,
                        line_number=node.start_point.row + 1,
                    )
                )

            elif node.type == "call_expression":
                # Check for require('module')
                func_node = node.child_by_field_name("function")
                if func_node and node_text(func_node) == "require":
                    args = node.child_by_field_name("arguments")
                    if args and args.named_child_count > 0:
                        req_mod = node_text(args.named_children[0]).strip("'\"")
                        imports.append(
                            ImportInfo(
                                module=req_mod,
                                imported_names=[],
                                is_from_import=False,
                                line_number=node.start_point.row + 1,
                            )
                        )

            elif node.type == "export_statement":
                is_default = any(c.type == "default" for c in node.children)
                exports.append(
                    ExportInfo(
                        name=node_text(node).split(";")[0],
                        export_type="default" if is_default else "named",
                        line_number=node.start_point.row + 1,
                    )
                )

            # Recurse children
            for child in node.children:
                traverse(child)

        traverse(root)

        return ParsedSourceFile(
            file_path=rel_path,
            language="javascript",
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            docstrings=docstrings,
            comments=comments,
            loc=loc,
        )

    def parse_file(self, file_path: Path, rel_path: str) -> Optional[ParsedSourceFile]:
        """Dispatches parsing based on file extension."""
        ext = file_path.suffix.lower()
        if ext == ".py":
            return self.parse_python_file(file_path, rel_path)
        elif ext in {".js", ".jsx", ".mjs", ".cjs"}:
            return self.parse_javascript_file(file_path, rel_path)
        return None


source_engine = SourceEngine()
