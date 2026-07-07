"""
iios/ontology/compiler/dependency_resolver.py
================================================
Dependency graph construction and topological sort for ontology documents.

Supports:
- Explicit import declarations
- Cross-document parent type detection
- Relationship source/target cross-references
- Circular dependency detection (DFS with GREY/BLACK colouring)
- Full topological ordering (compilation order)
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from .compiler_constants import DependencyKind, MAX_DEPENDENCY_DEPTH, MAX_IMPORT_CHAIN
from .compiler_exceptions import CircularDependencyError, DependencyDepthError, UnresolvedDependencyError
from ..runtime.runtime_object import OntologyDocument, OntologyTypeDef

__all__ = [
    "DependencyEdge",
    "DependencyGraph",
    "DependencyResolver",
    "get_dependency_resolver",
    "reset_dependency_resolver",
]

_LOG = logging.getLogger("iios.ontology.compiler.dependency")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class DependencyEdge:
    """A single dependency relationship between two ontology documents."""
    source:    str           # ontology name that has the dependency
    target:    str           # ontology name being depended on
    kind:      DependencyKind
    detail:    str = ""      # e.g. the type URI that caused the dependency

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "kind":   self.kind.value,
            "detail": self.detail,
        }


@dataclass
class DependencyGraph:
    """
    Directed dependency graph for a set of ontology documents.

    Nodes  = ontology names
    Edges  = dependency edges (source depends on target)
    """
    nodes:     set[str]               = field(default_factory=set)
    edges:     list[DependencyEdge]   = field(default_factory=list)
    # adjacency: name → set of names it depends on
    adj:       dict[str, set[str]]    = field(default_factory=lambda: defaultdict(set))
    # reverse:  name → set of names that depend on it
    rev:       dict[str, set[str]]    = field(default_factory=lambda: defaultdict(set))

    def add_edge(self, edge: DependencyEdge) -> None:
        self.nodes.add(edge.source)
        self.nodes.add(edge.target)
        self.edges.append(edge)
        self.adj[edge.source].add(edge.target)
        self.rev[edge.target].add(edge.source)

    def direct_dependencies(self, name: str) -> set[str]:
        return set(self.adj.get(name, set()))

    def dependents_of(self, name: str) -> set[str]:
        """All ontologies that directly depend on *name*."""
        return set(self.rev.get(name, set()))

    def stats(self) -> dict:
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
        }


# ── Resolver ──────────────────────────────────────────────────────────────────

class DependencyResolver:
    """
    Builds a DependencyGraph and computes a topological compilation order
    for a set of ontology documents.

    Usage::

        resolver = DependencyResolver()
        graph    = resolver.build_graph(documents)
        order    = resolver.topological_order(graph)
    """

    # ── Graph construction ────────────────────────────────────────────────────

    def build_graph(
        self,
        documents: dict[str, OntologyDocument],
    ) -> DependencyGraph:
        """
        Build a DependencyGraph from a mapping of name → OntologyDocument.

        Discovers dependencies from:
        1. Explicit `imports` list on each document
        2. `parent_uri` fields on types that reference external namespaces
        3. Relationship `source_type_uri` / `target_type_uri` that cross documents
        """
        graph = DependencyGraph()

        # Register all documents as nodes
        for name in documents:
            graph.nodes.add(name)

        ns_to_name: dict[str, str] = {
            doc.namespace.uri: name for name, doc in documents.items()
        }

        for name, doc in documents.items():
            # 1. Explicit imports
            for imported_uri in doc.imports:
                owner = ns_to_name.get(imported_uri)
                if owner and owner != name:
                    graph.add_edge(DependencyEdge(
                        source=name, target=owner,
                        kind=DependencyKind.IMPORT,
                        detail=imported_uri,
                    ))

            # 2. Cross-document parent types
            own_ns = doc.namespace.uri
            for typedef in doc.types.values():
                if typedef.parent_uri:
                    parent_ns = ".".join(typedef.parent_uri.split(".")[:-1])
                    if parent_ns != own_ns:
                        owner = ns_to_name.get(parent_ns)
                        if owner and owner != name:
                            graph.add_edge(DependencyEdge(
                                source=name, target=owner,
                                kind=DependencyKind.INHERITANCE,
                                detail=typedef.parent_uri,
                            ))

            # 3. Cross-document relationship references
            for rel in doc.relationships.values():
                for type_uri in (rel.source_type_uri, rel.target_type_uri):
                    ref_ns = ".".join(type_uri.split(".")[:-1])
                    if ref_ns != own_ns:
                        owner = ns_to_name.get(ref_ns)
                        if owner and owner != name:
                            graph.add_edge(DependencyEdge(
                                source=name, target=owner,
                                kind=DependencyKind.RELATIONSHIP,
                                detail=type_uri,
                            ))

        return graph

    # ── Circular dependency detection ─────────────────────────────────────────

    def check_circular(self, graph: DependencyGraph) -> None:
        """
        DFS cycle detection on the dependency graph.
        Raises CircularDependencyError if a cycle is found.
        """
        GREY, BLACK = 1, 2
        colour: dict[str, int] = {}

        def dfs(node: str, path: list[str]) -> None:
            if colour.get(node) == BLACK:
                return
            if colour.get(node) == GREY:
                raise CircularDependencyError(path + [node])
            colour[node] = GREY
            for dep in graph.adj.get(node, set()):
                dfs(dep, path + [node])
            colour[node] = BLACK

        for node in graph.nodes:
            dfs(node, [])

    # ── Topological sort ──────────────────────────────────────────────────────

    def topological_order(
        self,
        graph:     DependencyGraph,
        check:     bool = True,
    ) -> list[str]:
        """
        Return ontology names in topological compilation order
        (dependencies before dependents).

        Uses Kahn's algorithm for stability.

        Args:
            graph: The dependency graph.
            check: If True, first check for circular dependencies.

        Returns:
            List of ontology names in valid compilation order.
        """
        if check:
            self.check_circular(graph)

        # Kahn's algorithm: process nodes with in-degree 0 first
        in_degree: dict[str, int] = {node: 0 for node in graph.nodes}
        for node in graph.nodes:
            for dep in graph.adj.get(node, set()):
                in_degree[dep] = in_degree.get(dep, 0)  # ensure key exists
        for node in graph.nodes:
            for dep in graph.adj.get(node, set()):
                in_degree[dep] = in_degree.get(dep, 0)

        # Reset and recompute in-degree properly
        in_degree = {node: 0 for node in graph.nodes}
        for node in graph.nodes:
            for dep in graph.adj.get(node, set()):
                if dep in in_degree:
                    in_degree[dep] += 1  # dep is pointed at BY node

        # Actually: in Kahn's, in-degree = number of incoming edges
        # Edge: source → target means source depends on target
        # We want: compile target before source
        # So: in-degree of a node = number of nodes that depend on IT
        # Nodes with in-degree 0 have no dependents yet → compile first
        # Wait, let me think again:
        # source depends on target → edge source→target
        # We want to compile target before source
        # So we process nodes that have no DEPENDENCIES first (out-degree=0 in dependency sense)
        # Kahn's on reversed graph: in-degree = number of dependencies
        in_degree = {node: 0 for node in graph.nodes}
        for node in graph.nodes:
            for dep in graph.adj.get(node, set()):
                in_degree[node] = in_degree.get(node, 0)
        # in_degree[node] = number of things node depends on
        in_degree = {node: len(graph.adj.get(node, set())) for node in graph.nodes}

        queue   = deque(n for n, d in in_degree.items() if d == 0)
        result:  list[str] = []
        visited: set[str]  = set()

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            result.append(node)
            # All nodes that depend on *node* can now reduce their in-degree
            for dependent in graph.rev.get(node, set()):
                in_degree[dependent] = in_degree.get(dependent, 1) - 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(graph.nodes):
            remaining = graph.nodes - set(result)
            _LOG.warning("Topological sort incomplete — possible cycle in: %s", remaining)

        return result

    # ── Transitive dependencies ───────────────────────────────────────────────

    def transitive_dependencies(
        self,
        graph: DependencyGraph,
        name:  str,
        depth: int = 0,
    ) -> set[str]:
        """
        Return the full set of transitive dependencies for *name*
        (everything that must be compiled before *name*).
        """
        if depth > MAX_DEPENDENCY_DEPTH:
            raise DependencyDepthError(depth, MAX_DEPENDENCY_DEPTH)

        result: set[str] = set()
        direct  = graph.direct_dependencies(name)
        for dep in direct:
            result.add(dep)
            result.update(self.transitive_dependencies(graph, dep, depth + 1))
        return result

    # ── External type accumulation ────────────────────────────────────────────

    def build_external_types_map(
        self,
        order:     list[str],
        compiled:  dict[str, "CompiledOntology"],  # type: ignore[name-defined]
    ) -> dict[str, dict]:
        """
        For each ontology in *order*, build the external_types dict it
        needs during compilation (all types from already-compiled ontologies).

        Returns a mapping: ontology_name → external_types dict.
        """
        from ..runtime.runtime_object import OntologyTypeDef
        accumulated: dict[str, OntologyTypeDef] = {}
        result: dict[str, dict] = {}

        for name in order:
            result[name] = dict(accumulated)
            if name in compiled:
                accumulated.update(compiled[name].types)

        return result


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading as _threading
_lock = _threading.Lock()
_resolver: Optional["DependencyResolver"] = None


def get_dependency_resolver() -> DependencyResolver:
    global _resolver
    if _resolver is None:
        with _lock:
            if _resolver is None:
                _resolver = DependencyResolver()
    return _resolver


def reset_dependency_resolver() -> None:
    global _resolver
    with _lock:
        _resolver = None
