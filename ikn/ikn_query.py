"""
ikn_query.py — Read-only query engine for IKN-001.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .ikn_models import (
    KnowledgePath, KnowledgeRelationship, KnowledgeStatistics,
    KnowledgeSubgraph, NodeType, RelationshipType,
)
from .ikn_store import IKNStore


class IKNQueryEngine:
    """
    Read-only interface over IKNStore.

    Implements the full IKN Query API:
        get_node, get_relationships, related, shortest_path,
        supports, contradictions, history, statistics, coverage
    """

    def __init__(self, store: IKNStore, max_path_length: int = 10) -> None:
        self._store           = store
        self._max_path_length = max_path_length

    # ── simple lookups ────────────────────────────────────────────────────────

    def get_node(self, node_id: str):
        return self._store.get_node(node_id)

    def get_relationships(
        self,
        node_id:   str,
        rel_type:  Optional[str] = None,
        direction: str = "both",
    ) -> List[KnowledgeRelationship]:
        return self._store.get_relationships_for_node(
            node_id, rel_type=rel_type, direction=direction
        )

    # ── graph traversal ───────────────────────────────────────────────────────

    def related(self, node_id: str, depth: int = 1) -> KnowledgeSubgraph:
        """Return all nodes and relationships reachable within `depth` hops."""
        depth = max(1, min(depth, self._max_path_length))

        visited_node_ids: set = {node_id}
        visited_rel_ids:  set = set()
        subgraph_nodes:   Dict = {}
        subgraph_rels:    List[KnowledgeRelationship] = []
        queue = deque([(node_id, 0)])

        center = self._store.get_node(node_id)
        if center:
            subgraph_nodes[node_id] = center

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= depth:
                continue
            for rel in self._store.get_relationships_for_node(curr_id):
                if rel.relationship_id not in visited_rel_ids:
                    visited_rel_ids.add(rel.relationship_id)
                    subgraph_rels.append(rel)
                neighbour = rel.target_id if rel.source_id == curr_id else rel.source_id
                if neighbour not in visited_node_ids:
                    visited_node_ids.add(neighbour)
                    node = self._store.get_node(neighbour)
                    if node:
                        subgraph_nodes[neighbour] = node
                    queue.append((neighbour, curr_depth + 1))

        return KnowledgeSubgraph(
            nodes=subgraph_nodes,
            relationships=subgraph_rels,
            center_node_id=node_id,
        )

    def shortest_path(self, source_id: str, target_id: str) -> Optional[KnowledgePath]:
        """BFS shortest undirected path between two nodes."""
        if source_id == target_id:
            node = self._store.get_node(source_id)
            if node is None:
                return None
            return KnowledgePath(nodes=[node], relationships=[], length=0, total_confidence=1.0)

        prev: Dict[str, Tuple[Optional[str], Optional[KnowledgeRelationship]]] = {
            source_id: (None, None)
        }
        queue   = deque([(source_id, 0)])
        found   = False
        visited = {source_id}

        while queue and not found:
            curr, depth = queue.popleft()
            if depth >= self._max_path_length:
                continue
            for rel in self._store.get_relationships_for_node(curr):
                neighbour = rel.target_id if rel.source_id == curr else rel.source_id
                if neighbour not in visited:
                    visited.add(neighbour)
                    prev[neighbour] = (curr, rel)
                    if neighbour == target_id:
                        found = True
                        break
                    queue.append((neighbour, depth + 1))

        if target_id not in prev:
            return None

        # reconstruct path from target back to source
        path_ids:  List[str] = []
        path_rels: List[KnowledgeRelationship] = []
        curr = target_id
        while curr is not None:
            path_ids.append(curr)
            predecessor, rel = prev[curr]
            if rel is not None:
                path_rels.append(rel)
            curr = predecessor

        path_ids.reverse()
        path_rels.reverse()

        nodes = [self._store.get_node(nid) for nid in path_ids]
        nodes = [n for n in nodes if n is not None]

        conf = 1.0
        for r in path_rels:
            conf *= r.confidence

        return KnowledgePath(
            nodes=nodes, relationships=path_rels,
            length=len(path_rels), total_confidence=round(conf, 6),
        )

    # ── semantic queries ──────────────────────────────────────────────────────

    def supports(self, node_id: str) -> List[KnowledgeRelationship]:
        return self._store.get_relationships_for_node(
            node_id, rel_type=RelationshipType.SUPPORTED_BY.value, direction="both"
        )

    def contradictions(self, node_id: str) -> List[KnowledgeRelationship]:
        return self._store.get_relationships_for_node(
            node_id, rel_type=RelationshipType.CONTRADICTED_BY.value, direction="both"
        )

    def history(self, node_id: str) -> List[KnowledgeRelationship]:
        """Return EVOLVED_TO + SUPERSEDES relationships (evolutionary lineage)."""
        evolved    = self._store.get_relationships_for_node(
            node_id, rel_type=RelationshipType.EVOLVED_TO.value, direction="both"
        )
        supersedes = self._store.get_relationships_for_node(
            node_id, rel_type=RelationshipType.SUPERSEDES.value, direction="both"
        )
        return evolved + supersedes

    # ── statistics & coverage ─────────────────────────────────────────────────

    def statistics(self) -> KnowledgeStatistics:
        raw = self._store.get_raw_statistics()
        return KnowledgeStatistics(
            total_nodes           = raw["total_nodes"],
            total_relationships   = raw["total_rels"],
            nodes_by_type         = raw["by_node_type"],
            relationships_by_type = raw["by_rel_type"],
            avg_confidence        = raw["avg_conf"],
            most_connected_nodes  = raw["top_nodes"],
            orphan_count          = raw["orphan_count"],
            generated_at          = datetime.now(timezone.utc).isoformat(),
        )

    def coverage(self) -> Dict[str, Any]:
        """
        Network coverage metrics:
        - node_type_coverage:        fraction of NodeType values present
        - relationship_type_coverage: fraction of RelationshipType values present
        - traceability_score:        fraction of DISCOVERY nodes with evidence chain
        """
        stats = self.statistics()

        node_type_coverage = round(
            len(stats.nodes_by_type) / len(NodeType), 3
        )
        rel_type_coverage  = round(
            len(stats.relationships_by_type) / len(RelationshipType), 3
        )

        discovery_nodes = self._store.get_nodes_by_type(NodeType.DISCOVERY.value)
        _trace_types    = {
            RelationshipType.DISCOVERED_IN.value,
            RelationshipType.SUPPORTED_BY.value,
            RelationshipType.GENERATED_BY.value,
        }
        traceable = sum(
            1 for dn in discovery_nodes
            if any(
                r.relationship_type in _trace_types
                for r in self._store.get_relationships_for_node(dn.node_id)
            )
        )
        traceability_score = (
            round(traceable / len(discovery_nodes), 3)
            if discovery_nodes else 1.0
        )

        return {
            "node_type_coverage":          node_type_coverage,
            "relationship_type_coverage":  rel_type_coverage,
            "traceability_score":          traceability_score,
            "total_nodes":                 stats.total_nodes,
            "total_relationships":         stats.total_relationships,
        }
