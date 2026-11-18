"""Module dependency engine using NetworkX.

Constructs directed graph representing project module dependencies:
- Distinguishes internal imports from external third-party dependencies
- Detects circular dependencies (cycles) using strongly connected components
- Identifies isolated modules (nodes with degree 0)
- Outputs standard React Flow JSON schema (nodes, edges, cycles, external_dependencies, isolated_modules)
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, List, Set, Tuple

import networkx as nx
from app.models.analysis import (
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
)
from app.models.source import ParsedSourceFile


class DependencyEngine:
    """Builds and analyzes module dependency graphs using NetworkX."""

    def build_graph(self, parsed_files: List[ParsedSourceFile]) -> DependencyGraph:
        """Constructs a directed graph from parsed source file import statements."""
        G = nx.DiGraph()

        # Map relative path and module identifiers to node IDs
        # Key: module identifiers like "app.core.config", "utils", "src/foo.py"
        path_to_id: Dict[str, str] = {}
        id_to_file: Dict[str, ParsedSourceFile] = {}

        # 1. Register all internal modules as nodes
        for sf in parsed_files:
            # Canonicalize relative path with forward slashes
            norm_path = sf.file_path.replace("\\", "/")
            # Node ID: strip extension and use as identifier or use path
            node_id = norm_path
            path_to_id[norm_path] = node_id

            # Also index by Python module dot-notation (e.g., app/core/config.py -> app.core.config)
            p = Path(norm_path)
            dot_path = ".".join(p.with_suffix("").parts)
            path_to_id[dot_path] = node_id
            path_to_id[p.stem] = node_id  # single module stem lookup

            id_to_file[node_id] = sf
            G.add_node(
                node_id,
                label=p.name,
                file_path=norm_path,
                language=sf.language,
            )

        external_deps: Set[str] = set()

        # 2. Add edges from imports
        for sf in parsed_files:
            source_id = sf.file_path.replace("\\", "/")
            source_dir = Path(source_id).parent.as_posix()

            for imp in sf.imports:
                raw_mod = imp.module
                if not raw_mod:
                    continue

                target_id = None

                # JS/TS relative imports (e.g. ./utils, ../service)
                if raw_mod.startswith("./") or raw_mod.startswith("../"):
                    cand_base = source_dir if source_dir and source_dir != "." else ""
                    for ext in ("", ".js", ".jsx", ".ts", ".tsx", ".mjs", "/index.js", "/index.ts"):
                        combined = os.path.join(cand_base, raw_mod + ext)
                        test_p = os.path.normpath(combined).replace(os.sep, "/")
                        if test_p in path_to_id:
                            target_id = path_to_id[test_p]
                            break

                # Python relative imports (e.g. .config, ..utils)
                elif raw_mod.startswith("."):
                    level = len(raw_mod) - len(raw_mod.lstrip("."))
                    remainder = raw_mod.lstrip(".")
                    parts = list(Path(source_id).parts[:-1])
                    for _ in range(level - 1):
                        if parts:
                            parts.pop()
                    if remainder:
                        parts.extend(remainder.split("."))
                    resolved_mod = ".".join(parts)

                    # Lookup resolved
                    if resolved_mod in path_to_id:
                        target_id = path_to_id[resolved_mod]
                    else:
                        # try with .py
                        cand = "/".join(parts) + ".py"
                        if cand in path_to_id:
                            target_id = path_to_id[cand]

                # Absolute module imports (could be internal e.g. app.core.config or external e.g. fastapi)
                else:
                    if raw_mod in path_to_id:
                        target_id = path_to_id[raw_mod]
                    else:
                        # Check if matches any internal node path or stem
                        found = False
                        for p_key, n_id in path_to_id.items():
                            if p_key == raw_mod or p_key.endswith(f".{raw_mod}") or p_key == f"{raw_mod}.py":
                                target_id = n_id
                                found = True
                                break
                        if not found:
                            # External dependency
                            top_level = raw_mod.split(".")[0].split("/")[0]
                            if top_level and not top_level.startswith("."):
                                external_deps.add(top_level)

                if target_id and target_id in G and target_id != source_id:
                    G.add_edge(source_id, target_id, relationship="imports")

        # 3. Detect Cycles (Circular Dependencies) using simple_cycles
        cycles: List[List[str]] = []
        try:
            cycles = list(nx.simple_cycles(G))
        except Exception:
            pass

        # 4. Identify Isolated Modules (in_degree == 0 and out_degree == 0)
        isolated: List[str] = []
        for node in G.nodes():
            if G.in_degree(node) == 0 and G.out_degree(node) == 0:
                isolated.append(node)

        # 5. Build React Flow compliant output
        flow_nodes = [
            DependencyNode(
                id=node_id,
                label=data.get("label", node_id),
                file_path=data.get("file_path", node_id),
                language=data.get("language", "unknown"),
            )
            for node_id, data in G.nodes(data=True)
        ]

        flow_edges = [
            DependencyEdge(
                source=u,
                target=v,
                relationship=data.get("relationship", "imports"),
            )
            for u, v, data in G.edges(data=True)
        ]

        return DependencyGraph(
            nodes=flow_nodes,
            edges=flow_edges,
            cycles=cycles,
            external_dependencies=sorted(list(external_deps)),
            isolated_modules=sorted(isolated),
        )


dependency_engine = DependencyEngine()
