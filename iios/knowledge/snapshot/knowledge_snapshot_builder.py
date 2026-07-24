"""
knowledge_snapshot_builder.py — iios.knowledge.snapshot
---------------------------------------------------------
Fluent builder that constructs an immutable KnowledgeSnapshot from
subsystem outputs of M1 through M4.

Usage:
    snapshot = (
        KnowledgeSnapshotBuilder()
        .set_knowledge_session("sess-001")
        .set_knowledge_workflow("wf-001")
        .set_enterprise_session("ent-001")
        .set_knowledge_summary(KnowledgeSummary(...))
        .set_graph_summary(GraphSummary(...))
        ...
        .build()
    )

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    FRAMEWORK_VERSION,
    SCHEMA_VERSION,
    VERSION,
    KnowledgeScope,
    KnowledgeType,
    SnapshotState,
    SnapshotVersionTag,
)
from .exceptions import SnapshotBuildError
from .knowledge_snapshot import (
    EmbeddingSummary,
    GraphSummary,
    KnowledgeSummary,
    KnowledgeSnapshot,
    RecommendationSummary,
    RetrievalSummary,
    SnapshotAudit,
    SnapshotMemorySummary,
    SnapshotMetadata,
    SnapshotStatistics,
    VectorIndexSummary,
)
from .knowledge_snapshot_metadata import SnapshotMetadataBuilder

_log = get_logger(__name__)


class KnowledgeSnapshotBuilder:
    """
    Fluent builder for KnowledgeSnapshot.

    Required fields (must be set before build()):
      - knowledge_session_id
      - knowledge_workflow_id
      - enterprise_session_id

    All summary sections default to their respective .empty() factory
    if not explicitly set.
    """

    def __init__(self) -> None:
        self._t_start = time.monotonic()

        # Core identifiers
        self._snapshot_id:           str = f"snap-{uuid.uuid4().hex[:14]}"
        self._knowledge_session_id:  str = ""
        self._knowledge_workflow_id: str = ""
        self._enterprise_session_id: str = ""

        # Versions
        self._knowledge_version: str = "1.0.0"
        self._framework_version: str = FRAMEWORK_VERSION
        self._snapshot_version:  str = "1.0.0"

        # State
        self._knowledge_scope:  KnowledgeScope      = KnowledgeScope.ENTERPRISE
        self._knowledge_type:   KnowledgeType        = KnowledgeType.OPERATIONAL
        self._lifecycle_state:  str                  = "active"
        self._governance_state: str                  = "compliant"
        self._knowledge_state:  str                  = "ready"

        # Timestamps
        now = datetime.now(tz=timezone.utc).isoformat()
        self._snapshot_timestamp: str = now
        self._created_at:         str = now
        self._updated_at:         str = now

        # Summary sections (all optional — default to empty)
        self._knowledge_summary:         Optional[KnowledgeSummary]      = None
        self._graph_summary:             Optional[GraphSummary]          = None
        self._embedding_summary:         Optional[EmbeddingSummary]      = None
        self._vector_index_summary:      Optional[VectorIndexSummary]    = None
        self._retrieval_summary:         Optional[RetrievalSummary]      = None
        self._recommendation_summary:    Optional[RecommendationSummary] = None
        self._enterprise_memory_summary: Optional[SnapshotMemorySummary] = None
        self._audit:                     Optional[SnapshotAudit]         = None
        self._statistics:                Optional[SnapshotStatistics]    = None
        self._metadata:                  Optional[SnapshotMetadata]      = None

        # Integrity
        self._state:       SnapshotState      = SnapshotState.BUILT
        self._version_tag: SnapshotVersionTag = SnapshotVersionTag.STABLE

    # ------------------------------------------------------------------
    # Core identifiers
    # ------------------------------------------------------------------

    def set_snapshot_id(self, sid: str) -> "KnowledgeSnapshotBuilder":
        self._snapshot_id = sid
        return self

    def set_knowledge_session(self, sid: str) -> "KnowledgeSnapshotBuilder":
        self._knowledge_session_id = sid
        return self

    def set_knowledge_workflow(self, wid: str) -> "KnowledgeSnapshotBuilder":
        self._knowledge_workflow_id = wid
        return self

    def set_enterprise_session(self, eid: str) -> "KnowledgeSnapshotBuilder":
        self._enterprise_session_id = eid
        return self

    # ------------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------------

    def set_knowledge_version(self, v: str) -> "KnowledgeSnapshotBuilder":
        self._knowledge_version = v
        return self

    def set_framework_version(self, v: str) -> "KnowledgeSnapshotBuilder":
        self._framework_version = v
        return self

    def set_snapshot_version(self, v: str) -> "KnowledgeSnapshotBuilder":
        self._snapshot_version = v
        return self

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def set_scope(self, scope: KnowledgeScope) -> "KnowledgeSnapshotBuilder":
        self._knowledge_scope = scope
        return self

    def set_type(self, ktype: KnowledgeType) -> "KnowledgeSnapshotBuilder":
        self._knowledge_type = ktype
        return self

    def set_lifecycle_state(self, state: str) -> "KnowledgeSnapshotBuilder":
        self._lifecycle_state = state
        return self

    def set_governance_state(self, state: str) -> "KnowledgeSnapshotBuilder":
        self._governance_state = state
        return self

    def set_knowledge_state(self, state: str) -> "KnowledgeSnapshotBuilder":
        self._knowledge_state = state
        return self

    def set_state(self, state: SnapshotState) -> "KnowledgeSnapshotBuilder":
        self._state = state
        return self

    def set_version_tag(self, tag: SnapshotVersionTag) -> "KnowledgeSnapshotBuilder":
        self._version_tag = tag
        return self

    # ------------------------------------------------------------------
    # Summary sections
    # ------------------------------------------------------------------

    def set_knowledge_summary(
        self, summary: KnowledgeSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._knowledge_summary = summary
        return self

    def set_graph_summary(
        self, summary: GraphSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._graph_summary = summary
        return self

    def set_embedding_summary(
        self, summary: EmbeddingSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._embedding_summary = summary
        return self

    def set_vector_index_summary(
        self, summary: VectorIndexSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._vector_index_summary = summary
        return self

    def set_retrieval_summary(
        self, summary: RetrievalSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._retrieval_summary = summary
        return self

    def set_recommendation_summary(
        self, summary: RecommendationSummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._recommendation_summary = summary
        return self

    def set_enterprise_memory_summary(
        self, summary: SnapshotMemorySummary,
    ) -> "KnowledgeSnapshotBuilder":
        self._enterprise_memory_summary = summary
        return self

    def set_audit(self, audit: SnapshotAudit) -> "KnowledgeSnapshotBuilder":
        self._audit = audit
        return self

    def set_statistics(
        self, statistics: SnapshotStatistics,
    ) -> "KnowledgeSnapshotBuilder":
        self._statistics = statistics
        return self

    def set_metadata(
        self, metadata: SnapshotMetadata,
    ) -> "KnowledgeSnapshotBuilder":
        self._metadata = metadata
        return self

    # ------------------------------------------------------------------
    # Convenience: build from raw intelligence response dict (M4 output)
    # ------------------------------------------------------------------

    def from_intelligence_response(
        self,
        response: Dict[str, Any],
    ) -> "KnowledgeSnapshotBuilder":
        """Populate summary sections from a KnowledgeIntelligenceResponse.to_dict()."""
        report = response.get("report") or {}

        # Knowledge summary
        self._knowledge_summary = KnowledgeSummary(
            artifacts        = report.get("entities_extracted", 0),
            sources          = ("intelligence_engine",),
            domains          = ("knowledge",),
            categories       = ("intelligence",),
            quality_score    = 0.8,
            coverage_score   = 0.7,
            freshness_score  = 1.0,
            confidence_score = 0.85,
            completeness_score = 0.75,
        )

        # Graph summary from report
        rc = report.get("reasoning_context") or {}
        gs = rc.get("graph_summary") or {}
        self._graph_summary = GraphSummary(
            graph_version        = "1.0.0",
            total_nodes          = gs.get("node_count", 0),
            total_edges          = gs.get("edge_count", 0),
            entity_types         = (),
            relationship_types   = (),
            connected_components = 1 if gs.get("node_count", 0) > 0 else 0,
            graph_health         = "healthy" if gs.get("node_count", 0) > 0 else "empty",
        )

        # Embedding summary
        self._embedding_summary = EmbeddingSummary(
            provider          = "stub",
            model             = "stub",
            model_version     = "1.0.0",
            vector_dimensions = 128,
            embedding_count   = report.get("embeddings_generated", 0),
            embedding_health  = "healthy" if report.get("embeddings_generated", 0) > 0 else "empty",
        )

        # Vector index summary
        self._vector_index_summary = VectorIndexSummary(
            vector_store      = "in_memory",
            index_version     = "1.0.0",
            index_size        = report.get("vectors_indexed", 0),
            indexed_artifacts = report.get("vectors_indexed", 0),
            index_health      = "healthy" if report.get("vectors_indexed", 0) > 0 else "empty",
        )

        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> KnowledgeSnapshot:
        """Validate and construct an immutable KnowledgeSnapshot."""
        if not self._knowledge_session_id:
            raise SnapshotBuildError(
                "knowledge_session_id is required"
            )
        if not self._knowledge_workflow_id:
            raise SnapshotBuildError(
                "knowledge_workflow_id is required"
            )
        if not self._enterprise_session_id:
            raise SnapshotBuildError(
                "enterprise_session_id is required"
            )

        processing_ms = (time.monotonic() - self._t_start) * 1_000

        # Default empty sub-objects
        ks   = self._knowledge_summary      or KnowledgeSummary.empty()
        gs   = self._graph_summary          or GraphSummary.empty()
        es   = self._embedding_summary      or EmbeddingSummary.empty()
        vis  = self._vector_index_summary   or VectorIndexSummary.empty()
        rs   = self._retrieval_summary      or RetrievalSummary.empty()
        recs = self._recommendation_summary or RecommendationSummary.empty()
        ems  = self._enterprise_memory_summary or SnapshotMemorySummary.empty()
        audit = self._audit                 or SnapshotAudit.empty()
        meta  = self._metadata              or SnapshotMetadataBuilder.default()

        stats = self._statistics or SnapshotStatistics(
            processing_duration_ms = round(processing_ms, 3),
            snapshot_size_bytes    = 0,
            artifact_count         = ks.artifacts,
            entity_count           = gs.total_nodes,
            relationship_count     = gs.total_edges,
            embedding_count        = es.embedding_count,
            vector_count           = vis.indexed_artifacts,
        )

        # Build partial snapshot to compute hash
        snap = KnowledgeSnapshot(
            snapshot_id            = self._snapshot_id,
            knowledge_session_id   = self._knowledge_session_id,
            knowledge_workflow_id  = self._knowledge_workflow_id,
            enterprise_session_id  = self._enterprise_session_id,
            knowledge_version      = self._knowledge_version,
            framework_version      = self._framework_version,
            snapshot_version       = self._snapshot_version,
            knowledge_scope        = self._knowledge_scope,
            knowledge_type         = self._knowledge_type,
            lifecycle_state        = self._lifecycle_state,
            governance_state       = self._governance_state,
            knowledge_state        = self._knowledge_state,
            snapshot_timestamp     = self._snapshot_timestamp,
            created_at             = self._created_at,
            updated_at             = self._updated_at,
            knowledge_summary      = ks,
            graph_summary          = gs,
            embedding_summary      = es,
            vector_index_summary   = vis,
            retrieval_summary      = rs,
            recommendation_summary = recs,
            enterprise_memory_summary = ems,
            audit                  = audit,
            statistics             = stats,
            metadata               = meta,
            state                  = self._state,
            version_tag            = self._version_tag,
        )

        # Compute and embed content hash
        content_hash = KnowledgeSnapshot.compute_hash(snap.to_dict())

        # Rebuild with hash (frozen dataclass requires recreation)
        snap = KnowledgeSnapshot(
            snapshot_id            = snap.snapshot_id,
            knowledge_session_id   = snap.knowledge_session_id,
            knowledge_workflow_id  = snap.knowledge_workflow_id,
            enterprise_session_id  = snap.enterprise_session_id,
            knowledge_version      = snap.knowledge_version,
            framework_version      = snap.framework_version,
            snapshot_version       = snap.snapshot_version,
            knowledge_scope        = snap.knowledge_scope,
            knowledge_type         = snap.knowledge_type,
            lifecycle_state        = snap.lifecycle_state,
            governance_state       = snap.governance_state,
            knowledge_state        = snap.knowledge_state,
            snapshot_timestamp     = snap.snapshot_timestamp,
            created_at             = snap.created_at,
            updated_at             = snap.updated_at,
            knowledge_summary      = snap.knowledge_summary,
            graph_summary          = snap.graph_summary,
            embedding_summary      = snap.embedding_summary,
            vector_index_summary   = snap.vector_index_summary,
            retrieval_summary      = snap.retrieval_summary,
            recommendation_summary = snap.recommendation_summary,
            enterprise_memory_summary = snap.enterprise_memory_summary,
            audit                  = snap.audit,
            statistics             = snap.statistics,
            metadata               = snap.metadata,
            content_hash           = content_hash,
            schema_version         = snap.schema_version,
            state                  = snap.state,
            version_tag            = snap.version_tag,
        )

        _log.info(
            f"Snapshot built: id={snap.snapshot_id!r} "
            f"version={snap.snapshot_version!r} "
            f"scope={snap.knowledge_scope.value!r} "
            f"ms={processing_ms:.1f}"
        )
        return snap
