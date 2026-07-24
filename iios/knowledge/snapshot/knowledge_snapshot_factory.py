"""
knowledge_snapshot_factory.py — iios.knowledge.snapshot
---------------------------------------------------------
Factory for creating KnowledgeSnapshot instances with sensible defaults.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    FRAMEWORK_VERSION,
    KnowledgeScope,
    KnowledgeType,
    SnapshotState,
    SnapshotVersionTag,
)
from .knowledge_snapshot import (
    EmbeddingSummary,
    GraphSummary,
    KnowledgeSummary,
    KnowledgeSnapshot,
    RecommendationSummary,
    RetrievalSummary,
    SnapshotAudit,
    SnapshotMemorySummary,
    SnapshotStatistics,
    VectorIndexSummary,
)
from .knowledge_snapshot_builder import KnowledgeSnapshotBuilder
from .knowledge_snapshot_metadata import SnapshotMetadataBuilder
from .knowledge_snapshot_validation import KnowledgeSnapshotValidation

_log = get_logger(__name__)


class KnowledgeSnapshotFactory:
    """
    Factory that creates KnowledgeSnapshot objects.

    Provides methods for creating snapshots from:
      - Raw builder parameters
      - Intelligence response dicts (M4 output)
      - Minimal defaults (for testing)
    """

    def __init__(self) -> None:
        self._validator = KnowledgeSnapshotValidation()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def create(
        self,
        knowledge_session_id:  str,
        knowledge_workflow_id: str,
        enterprise_session_id: str,
        *,
        knowledge_summary:         Optional[KnowledgeSummary]      = None,
        graph_summary:             Optional[GraphSummary]          = None,
        embedding_summary:         Optional[EmbeddingSummary]      = None,
        vector_index_summary:      Optional[VectorIndexSummary]    = None,
        retrieval_summary:         Optional[RetrievalSummary]      = None,
        recommendation_summary:    Optional[RecommendationSummary] = None,
        enterprise_memory_summary: Optional[SnapshotMemorySummary] = None,
        audit:                     Optional[SnapshotAudit]         = None,
        statistics:                Optional[SnapshotStatistics]    = None,
        knowledge_scope:           KnowledgeScope                  = KnowledgeScope.ENTERPRISE,
        knowledge_type:            KnowledgeType                   = KnowledgeType.OPERATIONAL,
        lifecycle_state:           str                             = "active",
        governance_state:          str                             = "compliant",
        knowledge_state:           str                             = "ready",
        knowledge_version:         str                             = "1.0.0",
        snapshot_version:          str                             = "1.0.0",
        state:                     SnapshotState                   = SnapshotState.BUILT,
        version_tag:               SnapshotVersionTag              = SnapshotVersionTag.STABLE,
        validate:                  bool                            = True,
    ) -> KnowledgeSnapshot:
        """Build and optionally validate a KnowledgeSnapshot."""
        builder = (
            KnowledgeSnapshotBuilder()
            .set_knowledge_session(knowledge_session_id)
            .set_knowledge_workflow(knowledge_workflow_id)
            .set_enterprise_session(enterprise_session_id)
            .set_knowledge_version(knowledge_version)
            .set_snapshot_version(snapshot_version)
            .set_scope(knowledge_scope)
            .set_type(knowledge_type)
            .set_lifecycle_state(lifecycle_state)
            .set_governance_state(governance_state)
            .set_knowledge_state(knowledge_state)
            .set_state(state)
            .set_version_tag(version_tag)
            .set_metadata(SnapshotMetadataBuilder.default())
        )
        if knowledge_summary:
            builder.set_knowledge_summary(knowledge_summary)
        if graph_summary:
            builder.set_graph_summary(graph_summary)
        if embedding_summary:
            builder.set_embedding_summary(embedding_summary)
        if vector_index_summary:
            builder.set_vector_index_summary(vector_index_summary)
        if retrieval_summary:
            builder.set_retrieval_summary(retrieval_summary)
        if recommendation_summary:
            builder.set_recommendation_summary(recommendation_summary)
        if enterprise_memory_summary:
            builder.set_enterprise_memory_summary(enterprise_memory_summary)
        if audit:
            builder.set_audit(audit)
        if statistics:
            builder.set_statistics(statistics)

        snapshot = builder.build()

        if validate:
            report = self._validator.validate(snapshot)
            if not report.passed:
                _log.warning(
                    f"Snapshot validation warnings: "
                    f"id={snapshot.snapshot_id!r} "
                    f"failed={[r.code.value for r in report.results if not r.passed]!r}"
                )

        return snapshot

    # ------------------------------------------------------------------
    # From intelligence response (M4 output)
    # ------------------------------------------------------------------

    def from_intelligence_response(
        self,
        response:             Dict[str, Any],
        enterprise_session_id: str = "",
    ) -> KnowledgeSnapshot:
        """Create a snapshot from a KnowledgeIntelligenceResponse.to_dict()."""
        kid   = response.get("knowledge_id", f"k-{uuid.uuid4().hex[:8]}")
        eid   = enterprise_session_id or f"ent-{uuid.uuid4().hex[:8]}"
        builder = (
            KnowledgeSnapshotBuilder()
            .set_knowledge_session(kid)
            .set_knowledge_workflow(kid)
            .set_enterprise_session(eid)
            .from_intelligence_response(response)
            .set_metadata(SnapshotMetadataBuilder.default())
        )
        return builder.build()

    # ------------------------------------------------------------------
    # Minimal default (useful for testing)
    # ------------------------------------------------------------------

    def create_default(
        self,
        knowledge_session_id:  str = "",
        knowledge_workflow_id: str = "",
        enterprise_session_id: str = "",
    ) -> KnowledgeSnapshot:
        """Return a minimal snapshot with default (empty) summaries."""
        return self.create(
            knowledge_session_id  = knowledge_session_id  or f"sess-{uuid.uuid4().hex[:8]}",
            knowledge_workflow_id = knowledge_workflow_id or f"wf-{uuid.uuid4().hex[:8]}",
            enterprise_session_id = enterprise_session_id or f"ent-{uuid.uuid4().hex[:8]}",
            validate              = False,
        )
