"""
iios/ontology/services/hierarchy_service.py
=============================================
Hierarchy traversal service — walks the inheritance tree and provides
human-readable and machine-readable views of the type hierarchy.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from ..registry.ontology_registry_manager import get_registry_manager
from ..runtime.runtime_object import OntologyTypeDef

__all__ = [
    "HierarchyNode",
    "HierarchyService",
    "get_hierarchy_service",
    "reset_hierarchy_service",
]

_LOG  = logging.getLogger("iios.ontology.services.hierarchy")
_lock = threading.Lock()
_svc: Optional["HierarchyService"] = None


@dataclass
class HierarchyNode:
    """A node in the type hierarchy tree."""
    uri:         str
    name:        str
    namespace:   str
    depth:       int
    abstract:    bool
    children:    list["HierarchyNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":       self.uri,
            "name":      self.name,
            "namespace": self.namespace,
            "depth":     self.depth,
            "abstract":  self.abstract,
            "children":  [c.to_dict() for c in self.children],
        }

    def flat(self) -> list["HierarchyNode"]:
        """Flatten the subtree to a list (BFS order)."""
        result = [self]
        for child in self.children:
            result.extend(child.flat())
        return result


class HierarchyService:
    """Tree-view helpers over the type inheritance graph."""

    @property
    def _mgr(self):
        return get_registry_manager()

    # ── Tree building ──────────────────────────────────────────────────────────

    def build_tree(
        self,
        root_uri:  str,
        max_depth: int = 10,
    ) -> HierarchyNode:
        """Build a HierarchyNode tree starting at *root_uri*."""
        td = self._mgr.get_type_or_none(root_uri)
        if td is None:
            return HierarchyNode(
                uri       = root_uri,
                name      = root_uri.split(".")[-1],
                namespace = "",
                depth     = 0,
                abstract  = False,
            )
        return self._build_node(td, depth=0, max_depth=max_depth)

    def _build_node(
        self,
        td:        OntologyTypeDef,
        depth:     int,
        max_depth: int,
    ) -> HierarchyNode:
        node = HierarchyNode(
            uri       = td.uri,
            name      = td.name,
            namespace = td.namespace_uri,
            depth     = depth,
            abstract  = td.abstract,
        )
        if depth < max_depth:
            for child_uri in sorted(self._mgr.children_of(td.uri)):
                child_td = self._mgr.get_type_or_none(child_uri)
                if child_td:
                    node.children.append(
                        self._build_node(child_td, depth + 1, max_depth)
                    )
        return node

    def namespace_tree(self, ns_uri: str) -> list[HierarchyNode]:
        """Return root-level trees for all types in a namespace."""
        types_in_ns   = self._mgr.types_in_namespace(ns_uri)
        ns_uris       = {t.uri for t in types_in_ns}
        # Find roots: types whose parent is not in this namespace
        root_nodes: list[HierarchyNode] = []
        for td in types_in_ns:
            if td.parent_uri is None or td.parent_uri not in ns_uris:
                root_nodes.append(self.build_tree(td.uri))
        return root_nodes

    # ── Inspection helpers ─────────────────────────────────────────────────────

    def sibling_types(self, uri: str) -> list[OntologyTypeDef]:
        """All types that share the same parent as *uri*."""
        td = self._mgr.get_type_or_none(uri)
        if td is None or td.parent_uri is None:
            return []
        siblings = []
        for sibling_uri in self._mgr.children_of(td.parent_uri):
            if sibling_uri != uri:
                sibling = self._mgr.get_type_or_none(sibling_uri)
                if sibling:
                    siblings.append(sibling)
        return siblings

    def inheritance_chain(self, uri: str) -> list[OntologyTypeDef]:
        """Full chain from root to *uri* (root first)."""
        ancestors = self._mgr.ancestors_of(uri, include_self=True)
        chain     = [self._mgr.get_type_or_none(a) for a in reversed(ancestors)]
        return [t for t in chain if t is not None]

    def max_depth(self) -> int:
        """Maximum inheritance depth across all registered types."""
        from ..graph.ontology_graph import get_ontology_graph
        graph  = get_ontology_graph()
        leaves = graph.leaves()
        if not leaves:
            return 0
        return max(graph.depth_of(t.uri) for t in leaves)


def get_hierarchy_service() -> HierarchyService:
    global _svc
    if _svc is None:
        with _lock:
            if _svc is None:
                _svc = HierarchyService()
    return _svc


def reset_hierarchy_service() -> None:
    global _svc
    with _lock:
        _svc = None
