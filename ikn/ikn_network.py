"""
ikn_network.py — IKNNetwork: the main public API for IKN-001.

IKN only records and serves institutional relationships.
IKN never changes knowledge, promotes discoveries, or creates hypotheses.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ikn_config import IKNConfig
from .ikn_models import (
    IKNError, KnowledgeEvidence, KnowledgeNetworkSnapshot,
    KnowledgeNode, KnowledgeRelationship,
    VALID_NODE_TYPES, VALID_RELATIONSHIP_TYPES,
)
from .ikn_query import IKNQueryEngine
from .ikn_store import IKNStore


class IKNNetwork:
    """
    Institutional Knowledge Network.

    Writers: ResearchCoordinator, KDE, HKAP, CrossStudySynthesizer.
    Readers: Scientific Director, KnowledgeProvider, Trading Platform (read-only).
    """

    def __init__(self, config: Optional[IKNConfig] = None) -> None:
        self._config       = config or IKNConfig()
        self._store        = IKNStore(self._config)
        self._query        = IKNQueryEngine(self._store, self._config.max_path_length)
        self._lock         = threading.Lock()
        self._rel_counter  = 0
        self._ev_counter   = 0

    # ── node registration ─────────────────────────────────────────────────────

    def register_node(
        self,
        node_id:  str,
        node_type: str,
        name:     str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeNode:
        """
        Register a new node or update metadata of an existing one.
        version is incremented on each update.
        """
        if not node_id:
            raise IKNError("node_id cannot be empty")
        if node_type not in VALID_NODE_TYPES:
            raise IKNError(f"Unknown node_type: {node_type!r}")

        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            existing = self._store.get_node(node_id)
            if existing is None:
                node = KnowledgeNode(
                    node_id=node_id, node_type=node_type, name=name,
                    metadata=metadata or {}, created_at=now, updated_at=now, version=1,
                )
                self._store.add_node(node)
                return node

            existing.name       = name
            existing.metadata   = metadata if metadata is not None else existing.metadata
            existing.updated_at = now
            existing.version   += 1
            self._store.update_node(existing)
            return existing

    # ── relationship creation ─────────────────────────────────────────────────

    def add_relationship(
        self,
        source_id:          str,
        target_id:          str,
        rel_type:           str,
        confidence:         float = 1.0,
        evidence_count:     int   = 1,
        supporting_studies: Optional[List[str]] = None,
        supporting_years:   Optional[List[int]]  = None,
        supporting_regimes: Optional[List[str]] = None,
    ) -> KnowledgeRelationship:
        if not self._store.node_exists(source_id):
            raise IKNError(f"Source node not found: {source_id!r}")
        if not self._store.node_exists(target_id):
            raise IKNError(f"Target node not found: {target_id!r}")
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            raise IKNError(f"Unknown relationship_type: {rel_type!r}")
        if confidence < 0.0 or confidence > 1.0:
            raise IKNError("confidence must be in [0.0, 1.0]")

        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._rel_counter += 1
            counter = self._rel_counter

        rel_id = (
            f"IKN-REL-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            f"-{counter:06d}"
        )

        rel = KnowledgeRelationship(
            relationship_id   = rel_id,
            source_id         = source_id,
            target_id         = target_id,
            relationship_type = rel_type,
            confidence        = confidence,
            evidence_count    = evidence_count,
            supporting_studies = supporting_studies or [],
            supporting_years   = supporting_years   or [],
            supporting_regimes = supporting_regimes or [],
            created_at        = now,
            updated_at        = now,
            version           = 1,
        )
        self._store.add_relationship(rel)
        return rel

    def update_relationship(
        self,
        relationship_id:    str,
        confidence:         Optional[float] = None,
        evidence_count:     Optional[int]   = None,
        supporting_studies: Optional[List[str]] = None,
        supporting_years:   Optional[List[int]]  = None,
        supporting_regimes: Optional[List[str]] = None,
    ) -> KnowledgeRelationship:
        with self._lock:
            rel = self._store.get_relationship(relationship_id)
            if rel is None:
                raise IKNError(f"Relationship not found: {relationship_id!r}")

            now = datetime.now(timezone.utc).isoformat()
            if confidence is not None:
                if confidence < 0.0 or confidence > 1.0:
                    raise IKNError("confidence must be in [0.0, 1.0]")
                rel.confidence = confidence
            if evidence_count is not None:
                rel.evidence_count = evidence_count
            if supporting_studies is not None:
                rel.supporting_studies = supporting_studies
            if supporting_years is not None:
                rel.supporting_years = supporting_years
            if supporting_regimes is not None:
                rel.supporting_regimes = supporting_regimes

            rel.updated_at = now
            rel.version   += 1
            self._store.update_relationship(rel)
            return rel

    # ── evidence ──────────────────────────────────────────────────────────────

    def add_evidence(
        self,
        relationship_id: str,
        description:     str,
        source:          str,
        data_points:     int = 0,
    ) -> KnowledgeEvidence:
        if not self._store.relationship_exists(relationship_id):
            raise IKNError(f"Relationship not found: {relationship_id!r}")

        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._ev_counter += 1
            counter = self._ev_counter

        ev_id = (
            f"IKN-EV-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            f"-{counter:06d}"
        )
        ev = KnowledgeEvidence(
            evidence_id=ev_id, relationship_id=relationship_id,
            description=description, source=source,
            data_points=data_points, created_at=now,
        )
        self._store.add_evidence(ev)
        return ev

    # ── snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> KnowledgeNetworkSnapshot:
        from .report_generator import IKNReportGenerator  # avoid circular at module level
        stats   = self._query.statistics()
        reports = IKNReportGenerator(self._config).generate(self)
        now     = datetime.now(timezone.utc)
        snap_id = f"IKN-SNAP-{now.strftime('%Y%m%d%H%M%S')}"
        return KnowledgeNetworkSnapshot(
            snapshot_id        = snap_id,
            generated_at       = now.isoformat(),
            statistics         = stats,
            reports            = reports,
            node_count         = stats.total_nodes,
            relationship_count = stats.total_relationships,
        )

    # ── query delegation ──────────────────────────────────────────────────────

    @property
    def query(self) -> IKNQueryEngine:
        return self._query

    def get_node(self, node_id: str):
        return self._query.get_node(node_id)

    def get_relationships(self, node_id: str, rel_type=None, direction="both"):
        return self._query.get_relationships(node_id, rel_type=rel_type, direction=direction)

    def related(self, node_id: str, depth: int = 1):
        return self._query.related(node_id, depth=depth)

    def shortest_path(self, source_id: str, target_id: str):
        return self._query.shortest_path(source_id, target_id)

    def supports(self, node_id: str):
        return self._query.supports(node_id)

    def contradictions(self, node_id: str):
        return self._query.contradictions(node_id)

    def history(self, node_id: str):
        return self._query.history(node_id)

    def statistics(self):
        return self._query.statistics()

    def coverage(self):
        return self._query.coverage()

    def close(self) -> None:
        self._store.close()
