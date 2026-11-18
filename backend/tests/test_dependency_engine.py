"""Unit and integration tests for DependencyEngine:
- Direct imports between internal modules
- External dependency isolation
- Circular dependency detection
- Isolated modules detection
- React Flow output format
"""

from app.engines.dependency_engine import DependencyEngine
from app.models.source import ImportInfo, ParsedSourceFile


def test_dependency_engine_graph_and_cycles():
    # Module A imports Module B
    # Module B imports Module C
    # Module C imports Module A (forming a cycle!)
    # Module D is isolated
    # Module E imports external package 'requests'

    file_a = ParsedSourceFile(
        file_path="src/module_a.py",
        language="python",
        imports=[ImportInfo(module="src.module_b", imported_names=["b_func"], is_from_import=True, line_number=1)],
    )
    file_b = ParsedSourceFile(
        file_path="src/module_b.py",
        language="python",
        imports=[ImportInfo(module="src.module_c", imported_names=["c_func"], is_from_import=True, line_number=1)],
    )
    file_c = ParsedSourceFile(
        file_path="src/module_c.py",
        language="python",
        imports=[ImportInfo(module="src.module_a", imported_names=["a_func"], is_from_import=True, line_number=1)],
    )
    file_d = ParsedSourceFile(
        file_path="src/module_d.py",
        language="python",
        imports=[],
    )
    file_e = ParsedSourceFile(
        file_path="src/module_e.py",
        language="python",
        imports=[ImportInfo(module="requests", imported_names=["get"], is_from_import=True, line_number=1)],
    )

    engine = DependencyEngine()
    graph = engine.build_graph([file_a, file_b, file_c, file_d, file_e])

    # Nodes check
    node_ids = [n.id for n in graph.nodes]
    assert len(graph.nodes) == 5
    assert "src/module_a.py" in node_ids
    assert "src/module_d.py" in node_ids

    # Edges check
    assert len(graph.edges) == 3
    edge_pairs = [(e.source, e.target) for e in graph.edges]
    assert ("src/module_a.py", "src/module_b.py") in edge_pairs
    assert ("src/module_b.py", "src/module_c.py") in edge_pairs
    assert ("src/module_c.py", "src/module_a.py") in edge_pairs

    # Cycles check
    assert len(graph.cycles) >= 1
    cycle_nodes = set()
    for cycle in graph.cycles:
        cycle_nodes.update(cycle)
    assert "src/module_a.py" in cycle_nodes
    assert "src/module_b.py" in cycle_nodes
    assert "src/module_c.py" in cycle_nodes

    # Isolated modules
    assert "src/module_d.py" in graph.isolated_modules

    # External dependencies
    assert "requests" in graph.external_dependencies
