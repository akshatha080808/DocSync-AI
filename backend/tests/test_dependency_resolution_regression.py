from pathlib import Path
import pytest
from app.engines.dependency_engine import DependencyEngine
from app.models.source import ParsedSourceFile, ImportInfo


def test_controlled_python_internal_dependency_edges():
    """Controlled Phase 3 Test:
    main.py -> imports auth.py, payment.py
    auth.py -> imports database.py
    payment.py -> imports database.py
    Expected: 4 nodes, 4 directed edges.
    """
    engine = DependencyEngine()

    files = [
        ParsedSourceFile(
            file_path="main.py",
            language="python",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="auth", imported_names=[], is_from_import=False, line_number=1),
                ImportInfo(module="payment", imported_names=[], is_from_import=False, line_number=2),
                ImportInfo(module="os", imported_names=[], is_from_import=False, line_number=3),  # external/stdlib
            ],
            exports=[], docstrings=[], comments=[], loc=10, parse_error=None
        ),
        ParsedSourceFile(
            file_path="auth.py",
            language="python",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="database", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=10, parse_error=None
        ),
        ParsedSourceFile(
            file_path="payment.py",
            language="python",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="database", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=10, parse_error=None
        ),
        ParsedSourceFile(
            file_path="database.py",
            language="python",
            functions=[], classes=[],
            imports=[],
            exports=[], docstrings=[], comments=[], loc=10, parse_error=None
        ),
    ]

    graph = engine.build_graph(files)

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4

    edge_pairs = {(e.source, e.target) for e in graph.edges}
    assert ("main.py", "auth.py") in edge_pairs
    assert ("main.py", "payment.py") in edge_pairs
    assert ("auth.py", "database.py") in edge_pairs
    assert ("payment.py", "database.py") in edge_pairs
    assert "os" in graph.external_dependencies


def test_javascript_relative_import_resolution_regression():
    """Verifies that relative JavaScript imports (../models/User, ./config/db)
    correctly resolve to their target internal modules instead of producing 0 edges.
    """
    engine = DependencyEngine()

    files = [
        ParsedSourceFile(
            file_path="src/server.js",
            language="javascript",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="./config/db", imported_names=[], is_from_import=False, line_number=1),
                ImportInfo(module="./routes/itemRoutes", imported_names=[], is_from_import=False, line_number=2),
                ImportInfo(module="express", imported_names=[], is_from_import=False, line_number=3),
            ],
            exports=[], docstrings=[], comments=[], loc=20, parse_error=None
        ),
        ParsedSourceFile(
            file_path="src/config/db.js",
            language="javascript",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="mongoose", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=15, parse_error=None
        ),
        ParsedSourceFile(
            file_path="src/routes/itemRoutes.js",
            language="javascript",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="../controllers/itemController", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=15, parse_error=None
        ),
        ParsedSourceFile(
            file_path="src/controllers/itemController.js",
            language="javascript",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="../models/Item", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=25, parse_error=None
        ),
        ParsedSourceFile(
            file_path="src/models/Item.js",
            language="javascript",
            functions=[], classes=[],
            imports=[
                ImportInfo(module="mongoose", imported_names=[], is_from_import=False, line_number=1),
            ],
            exports=[], docstrings=[], comments=[], loc=12, parse_error=None
        ),
    ]

    graph = engine.build_graph(files)

    assert len(graph.nodes) == 5
    assert len(graph.edges) == 4

    edge_pairs = {(e.source, e.target) for e in graph.edges}
    assert ("src/server.js", "src/config/db.js") in edge_pairs
    assert ("src/server.js", "src/routes/itemRoutes.js") in edge_pairs
    assert ("src/routes/itemRoutes.js", "src/controllers/itemController.js") in edge_pairs
    assert ("src/controllers/itemController.js", "src/models/Item.js") in edge_pairs

    assert "express" in graph.external_dependencies
    assert "mongoose" in graph.external_dependencies


def test_independent_files_legitimately_have_zero_edges():
    """A project with independent files legitimately has nodes without connecting edges."""
    engine = DependencyEngine()

    files = [
        ParsedSourceFile(
            file_path="script_a.py",
            language="python",
            functions=[], classes=[],
            imports=[ImportInfo(module="json", imported_names=[], is_from_import=False, line_number=1)],
            exports=[], docstrings=[], comments=[], loc=5, parse_error=None
        ),
        ParsedSourceFile(
            file_path="script_b.py",
            language="python",
            functions=[], classes=[],
            imports=[ImportInfo(module="math", imported_names=[], is_from_import=False, line_number=1)],
            exports=[], docstrings=[], comments=[], loc=5, parse_error=None
        ),
    ]

    graph = engine.build_graph(files)
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 0
    assert set(graph.isolated_modules) == {"script_a.py", "script_b.py"}
