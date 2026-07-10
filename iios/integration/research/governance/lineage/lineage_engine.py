"""lineage/lineage_engine.py — Top-level lineage orchestrator."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    ArtifactType,
    LineageEdgeType,
    LineageNodeType,
)
from iios.integration.research.governance.lineage.lineage_graph      import LineageGraph, LineageNode, LineageEdge
from iios.integration.research.governance.lineage.experiment_lineage import ExperimentLineageRecord
from iios.integration.research.governance.lineage.artifact_lineage   import ArtifactLineageRecord
from iios.integration.research.governance.lineage.dependency_tracker import DependencyTracker


class LineageEngine:
    """
    Facade for all lineage operations.

    Owns the LineageGraph, experiment/artifact records, and DependencyTracker.
    """

    def __init__(self) -> None:
        self._graph       = LineageGraph()
        self._dep_tracker = DependencyTracker()
        self._exp_records: dict[str, ExperimentLineageRecord] = {}
        self._art_records: dict[str, ArtifactLineageRecord]  = {}
        self._lock        = threading.RLock()

    # ── Node registration ─────────────────────────────────────────────────────

    def register_entity(
        self,
        entity_id:  str,
        node_type:  LineageNodeType,
        label:      str,
        *,
        version:    Optional[str] = None,
        metadata:   Optional[dict] = None,
    ) -> LineageNode:
        node = LineageNode.create(entity_id, node_type, label, version=version, metadata=metadata)
        self._graph.add_node(node)
        return node

    def link(
        self,
        from_entity: str,
        to_entity:   str,
        edge_type:   LineageEdgeType,
        *,
        label:       Optional[str] = None,
    ) -> LineageEdge:
        """Add a directed lineage edge from_entity → to_entity."""
        from_nodes = self._graph.find_by_entity(from_entity)
        to_nodes   = self._graph.find_by_entity(to_entity)
        if not from_nodes or not to_nodes:
            # Auto-register missing nodes as EXECUTION type
            if not from_nodes:
                self.register_entity(from_entity, LineageNodeType.EXECUTION, from_entity)
                from_nodes = self._graph.find_by_entity(from_entity)
            if not to_nodes:
                self.register_entity(to_entity, LineageNodeType.EXECUTION, to_entity)
                to_nodes = self._graph.find_by_entity(to_entity)
        edge = LineageEdge.create(
            from_node = from_nodes[0].node_id,
            to_node   = to_nodes[0].node_id,
            edge_type = edge_type,
            label     = label,
        )
        self._graph.add_edge(edge)
        self._dep_tracker.add_dependency(to_entity, from_entity)
        return edge

    # ── Experiment lineage ────────────────────────────────────────────────────

    def record_experiment(
        self,
        experiment_id:   str,
        experiment_name: str,
        parent_ids:      Optional[list[str]] = None,
        parent_types:    Optional[list[str]] = None,
        **kwargs: Any,
    ) -> ExperimentLineageRecord:
        record = ExperimentLineageRecord.create(
            experiment_id, experiment_name,
            parent_ids=parent_ids, parent_types=parent_types, **kwargs
        )
        with self._lock:
            self._exp_records[experiment_id] = record
        # Register in graph
        self.register_entity(experiment_id, LineageNodeType.EXPERIMENT, experiment_name)
        for parent_id in (parent_ids or []):
            try:
                self.link(parent_id, experiment_id, LineageEdgeType.DEPENDS_ON)
            except Exception:
                pass
        return record

    def get_experiment_lineage(self, experiment_id: str) -> Optional[ExperimentLineageRecord]:
        with self._lock:
            return self._exp_records.get(experiment_id)

    # ── Artifact lineage ──────────────────────────────────────────────────────

    def record_artifact(
        self,
        artifact_id:      str,
        artifact_type:    ArtifactType,
        artifact_name:    str,
        artifact_version: str = "1.0.0",
        **kwargs: Any,
    ) -> ArtifactLineageRecord:
        record = ArtifactLineageRecord.create(
            artifact_id, artifact_type, artifact_name, artifact_version, **kwargs
        )
        with self._lock:
            self._art_records[artifact_id] = record
        self.register_entity(artifact_id, LineageNodeType.ARTIFACT, artifact_name, version=artifact_version)
        if record.produced_by:
            try:
                self.link(record.produced_by, artifact_id, LineageEdgeType.PRODUCED_BY)
            except Exception:
                pass
        return record

    def get_artifact_lineage(self, artifact_id: str) -> Optional[ArtifactLineageRecord]:
        with self._lock:
            return self._art_records.get(artifact_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def ancestors(self, entity_id: str) -> list[LineageNode]:
        nodes = self._graph.find_by_entity(entity_id)
        if not nodes:
            return []
        return self._graph.ancestors(nodes[0].node_id)

    def descendants(self, entity_id: str) -> list[LineageNode]:
        nodes = self._graph.find_by_entity(entity_id)
        if not nodes:
            return []
        return self._graph.descendants(nodes[0].node_id)

    def impact_of_change(self, entity_id: str) -> list[str]:
        return self._dep_tracker.impact_of_change(entity_id)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "graph":         self._graph.stats(),
            "experiments":   len(self._exp_records),
            "artifacts":     len(self._art_records),
            "dependencies":  self._dep_tracker.stats(),
        }
