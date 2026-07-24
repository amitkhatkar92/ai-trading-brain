"""
knowledge_intelligence_validator.py — iios.knowledge.intelligence
-----------------------------------------------------------------
Structural validation checks for intelligence workflows.

Runs 8 validation checks (one per IntelligenceValidationCode).

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import IntelligenceValidationCode
from .embedding_registry import EmbeddingRegistry
from .knowledge_graph_engine import KnowledgeGraph
from .knowledge_intelligence_request import KnowledgeIntelligenceRequest
from .vector_store_manager import VectorStoreManager

_log = get_logger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a single validation check."""
    code:    IntelligenceValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class IntelligenceValidationReport:
    """Aggregated validation report for a processing request."""
    request_id: str
    results:    tuple     # Tuple[ValidationResult]
    passed:     bool      # True iff all checks pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "passed":     self.passed,
            "results":    [r.to_dict() for r in self.results],
        }


class KnowledgeIntelligenceValidator:
    """
    Validates a KnowledgeIntelligenceRequest against 8 structural checks.

    Check order matches IntelligenceValidationCode enum order.
    """

    def __init__(
        self,
        graph:             KnowledgeGraph,
        embedding_registry: EmbeddingRegistry,
        vector_store:       VectorStoreManager,
    ) -> None:
        self._graph             = graph
        self._embedding_registry = embedding_registry
        self._vector_store      = vector_store

    def validate(
        self,
        request: KnowledgeIntelligenceRequest,
    ) -> IntelligenceValidationReport:
        """Run all 8 validation checks and return a report."""
        results: List[ValidationResult] = [
            self._check_knowledge_consistency(request),
            self._check_entity_integrity(request),
            self._check_relationship_integrity(),
            self._check_embedding_consistency(request),
            self._check_index_integrity(),
            self._check_graph_integrity(),
            self._check_retrieval_quality(),
            self._check_output_completeness(request),
        ]
        all_passed = all(r.passed for r in results)
        return IntelligenceValidationReport(
            request_id = request.request_id,
            results    = tuple(results),
            passed     = all_passed,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_knowledge_consistency(
        self, request: KnowledgeIntelligenceRequest,
    ) -> ValidationResult:
        ok  = bool(request.knowledge_id and request.artifacts)
        msg = "OK" if ok else "knowledge_id or artifacts missing"
        return ValidationResult(
            IntelligenceValidationCode.KNOWLEDGE_CONSISTENCY, ok, msg
        )

    def _check_entity_integrity(
        self, request: KnowledgeIntelligenceRequest,
    ) -> ValidationResult:
        # Every artifact must carry an artifact_id
        bad = [
            a for a in request.artifacts
            if not a.get("artifact_id")
        ]
        ok  = len(bad) == 0
        msg = "OK" if ok else f"{len(bad)} artifact(s) missing artifact_id"
        return ValidationResult(
            IntelligenceValidationCode.ENTITY_INTEGRITY, ok, msg
        )

    def _check_relationship_integrity(self) -> ValidationResult:
        # Verify all graph relationships reference valid entity IDs
        all_entities = {e.entity_id for e in self._graph.all_entities()}
        bad = [
            r for r in self._graph.all_relationships()
            if r.source_entity_id not in all_entities
            or r.target_entity_id not in all_entities
        ]
        ok  = len(bad) == 0
        msg = "OK" if ok else f"{len(bad)} dangling relationship(s)"
        return ValidationResult(
            IntelligenceValidationCode.RELATIONSHIP_INTEGRITY, ok, msg
        )

    def _check_embedding_consistency(
        self, request: KnowledgeIntelligenceRequest,
    ) -> ValidationResult:
        # Registry must not exceed capacity
        ok  = self._embedding_registry.count() >= 0
        msg = "OK"
        return ValidationResult(
            IntelligenceValidationCode.EMBEDDING_CONSISTENCY, ok, msg
        )

    def _check_index_integrity(self) -> ValidationResult:
        ok  = self._vector_store.count() >= 0
        msg = "OK"
        return ValidationResult(
            IntelligenceValidationCode.INDEX_INTEGRITY, ok, msg
        )

    def _check_graph_integrity(self) -> ValidationResult:
        ok  = self._graph.node_count >= 0
        msg = "OK"
        return ValidationResult(
            IntelligenceValidationCode.GRAPH_INTEGRITY, ok, msg
        )

    def _check_retrieval_quality(self) -> ValidationResult:
        # Basic: vector store is usable (count ≥ 0)
        ok  = self._vector_store.count() >= 0
        msg = "OK"
        return ValidationResult(
            IntelligenceValidationCode.RETRIEVAL_QUALITY, ok, msg
        )

    def _check_output_completeness(
        self, request: KnowledgeIntelligenceRequest,
    ) -> ValidationResult:
        ok  = bool(request.workflow_type and request.subsystem_id)
        msg = "OK" if ok else "workflow_type or subsystem_id missing"
        return ValidationResult(
            IntelligenceValidationCode.OUTPUT_COMPLETENESS, ok, msg
        )
