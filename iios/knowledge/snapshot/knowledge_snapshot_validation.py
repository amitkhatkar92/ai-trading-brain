"""
knowledge_snapshot_validation.py — iios.knowledge.snapshot
-----------------------------------------------------------
Validates snapshot integrity against 8 structural checks.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import SnapshotValidationCode
from .knowledge_snapshot import KnowledgeSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Outcome of one validation check."""
    code:    SnapshotValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class SnapshotValidationReport:
    """Aggregated validation report for a KnowledgeSnapshot."""
    snapshot_id: str
    results:     tuple      # Tuple[SnapshotValidationResult]
    passed:      bool       # True iff ALL checks pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "passed":      self.passed,
            "results":     [r.to_dict() for r in self.results],
        }


class KnowledgeSnapshotValidation:
    """
    Validates a KnowledgeSnapshot against 8 structural checks.

    Checks run in the order defined by SnapshotValidationCode.
    """

    def validate(self, snapshot: KnowledgeSnapshot) -> SnapshotValidationReport:
        """Run all 8 checks and return an aggregated report."""
        results: List[SnapshotValidationResult] = [
            self._check_identifier_consistency(snapshot),
            self._check_version_consistency(snapshot),
            self._check_knowledge_consistency(snapshot),
            self._check_graph_consistency(snapshot),
            self._check_embedding_consistency(snapshot),
            self._check_index_consistency(snapshot),
            self._check_metadata_integrity(snapshot),
            self._check_snapshot_completeness(snapshot),
        ]
        all_passed = all(r.passed for r in results)
        if not all_passed:
            failed = [r.code.value for r in results if not r.passed]
            _log.warning(
                f"Snapshot validation failed: id={snapshot.snapshot_id!r} "
                f"failed_checks={failed!r}"
            )
        return SnapshotValidationReport(
            snapshot_id = snapshot.snapshot_id,
            results     = tuple(results),
            passed      = all_passed,
        )

    # ------------------------------------------------------------------
    # Individual checks (8)
    # ------------------------------------------------------------------

    def _check_identifier_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        ok = bool(
            snap.snapshot_id
            and snap.knowledge_session_id
            and snap.knowledge_workflow_id
            and snap.enterprise_session_id
        )
        return SnapshotValidationResult(
            SnapshotValidationCode.IDENTIFIER_CONSISTENCY,
            ok,
            "OK" if ok else "One or more required IDs are empty",
        )

    def _check_version_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        ok = bool(
            snap.knowledge_version
            and snap.framework_version
            and snap.snapshot_version
        )
        return SnapshotValidationResult(
            SnapshotValidationCode.VERSION_CONSISTENCY,
            ok,
            "OK" if ok else "One or more version fields are empty",
        )

    def _check_knowledge_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        ks  = snap.knowledge_summary
        ok  = (
            ks.artifacts >= 0
            and 0.0 <= ks.quality_score <= 1.0
            and 0.0 <= ks.confidence_score <= 1.0
        )
        msg = "OK" if ok else "Knowledge summary scores out of range"
        return SnapshotValidationResult(
            SnapshotValidationCode.KNOWLEDGE_CONSISTENCY, ok, msg
        )

    def _check_graph_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        gs  = snap.graph_summary
        ok  = gs.total_nodes >= 0 and gs.total_edges >= 0
        msg = "OK" if ok else "Graph node/edge counts negative"
        return SnapshotValidationResult(
            SnapshotValidationCode.GRAPH_CONSISTENCY, ok, msg
        )

    def _check_embedding_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        es  = snap.embedding_summary
        ok  = es.embedding_count >= 0 and es.vector_dimensions > 0
        msg = "OK" if ok else "Embedding count or dimensions invalid"
        return SnapshotValidationResult(
            SnapshotValidationCode.EMBEDDING_CONSISTENCY, ok, msg
        )

    def _check_index_consistency(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        vis = snap.vector_index_summary
        ok  = vis.index_size >= 0 and vis.indexed_artifacts >= 0
        msg = "OK" if ok else "Vector index counts negative"
        return SnapshotValidationResult(
            SnapshotValidationCode.INDEX_CONSISTENCY, ok, msg
        )

    def _check_metadata_integrity(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        meta = snap.metadata
        ok   = bool(meta.environment and meta.framework_version)
        msg  = "OK" if ok else "Metadata environment or framework_version missing"
        return SnapshotValidationResult(
            SnapshotValidationCode.METADATA_INTEGRITY, ok, msg
        )

    def _check_snapshot_completeness(
        self, snap: KnowledgeSnapshot,
    ) -> SnapshotValidationResult:
        ok = bool(
            snap.snapshot_timestamp
            and snap.created_at
            and snap.lifecycle_state
            and snap.governance_state
        )
        msg = "OK" if ok else "Required timestamp or state fields missing"
        return SnapshotValidationResult(
            SnapshotValidationCode.SNAPSHOT_COMPLETENESS, ok, msg
        )
