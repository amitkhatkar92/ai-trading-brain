"""
knowledge_snapshot.py — iios.knowledge.snapshot
-------------------------------------------------
Immutable, versioned, canonical published representation of Enterprise
Knowledge Intelligence.

Defines:
    KnowledgeSummary
    GraphSummary
    EmbeddingSummary
    VectorIndexSummary
    RetrievalSummary
    RecommendationSummary
    SnapshotMemorySummary
    SnapshotAudit
    SnapshotStatistics
    SnapshotMetadata
    KnowledgeSnapshot                 ← the top-level immutable snapshot

Serialization:
    snapshot.to_dict()  → Dict[str, Any]
    snapshot.to_json()  → str (compact JSON)
    KnowledgeSnapshot.from_dict(d)  → KnowledgeSnapshot
    KnowledgeSnapshot.from_json(s)  → KnowledgeSnapshot

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    FRAMEWORK_VERSION,
    SCHEMA_VERSION,
    VERSION,
    KnowledgeScope,
    KnowledgeType,
    SnapshotState,
    SnapshotVersionTag,
)


# ════════════════════════════════════════════════════════════════════════
# Sub-section frozen dataclasses
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class KnowledgeSummary:
    """Aggregate summary of the knowledge artifacts captured in the snapshot."""
    artifacts:           int
    sources:             tuple    # Tuple[str]
    domains:             tuple    # Tuple[str]
    categories:          tuple    # Tuple[str]
    quality_score:       float    # [0.0 – 1.0]
    coverage_score:      float    # [0.0 – 1.0]
    freshness_score:     float    # [0.0 – 1.0]
    confidence_score:    float    # [0.0 – 1.0]
    completeness_score:  float    # [0.0 – 1.0]

    @classmethod
    def empty(cls) -> "KnowledgeSummary":
        return cls(
            artifacts        = 0,
            sources          = (),
            domains          = (),
            categories       = (),
            quality_score    = 0.0,
            coverage_score   = 0.0,
            freshness_score  = 0.0,
            confidence_score = 0.0,
            completeness_score = 0.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifacts":         self.artifacts,
            "sources":           list(self.sources),
            "domains":           list(self.domains),
            "categories":        list(self.categories),
            "quality_score":     self.quality_score,
            "coverage_score":    self.coverage_score,
            "freshness_score":   self.freshness_score,
            "confidence_score":  self.confidence_score,
            "completeness_score": self.completeness_score,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeSummary":
        return cls(
            artifacts          = d.get("artifacts", 0),
            sources            = tuple(d.get("sources", [])),
            domains            = tuple(d.get("domains", [])),
            categories         = tuple(d.get("categories", [])),
            quality_score      = d.get("quality_score", 0.0),
            coverage_score     = d.get("coverage_score", 0.0),
            freshness_score    = d.get("freshness_score", 0.0),
            confidence_score   = d.get("confidence_score", 0.0),
            completeness_score = d.get("completeness_score", 0.0),
        )


@dataclass(frozen=True)
class GraphSummary:
    """Summary of the knowledge graph captured in the snapshot."""
    graph_version:        str
    total_nodes:          int
    total_edges:          int
    entity_types:         tuple    # Tuple[str]
    relationship_types:   tuple    # Tuple[str]
    connected_components: int
    graph_health:         str      # "healthy" | "degraded" | "empty" | "unknown"

    @classmethod
    def empty(cls) -> "GraphSummary":
        return cls(
            graph_version        = "0.0.0",
            total_nodes          = 0,
            total_edges          = 0,
            entity_types         = (),
            relationship_types   = (),
            connected_components = 0,
            graph_health         = "empty",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_version":        self.graph_version,
            "total_nodes":          self.total_nodes,
            "total_edges":          self.total_edges,
            "entity_types":         list(self.entity_types),
            "relationship_types":   list(self.relationship_types),
            "connected_components": self.connected_components,
            "graph_health":         self.graph_health,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphSummary":
        return cls(
            graph_version        = d.get("graph_version", "0.0.0"),
            total_nodes          = d.get("total_nodes", 0),
            total_edges          = d.get("total_edges", 0),
            entity_types         = tuple(d.get("entity_types", [])),
            relationship_types   = tuple(d.get("relationship_types", [])),
            connected_components = d.get("connected_components", 0),
            graph_health         = d.get("graph_health", "unknown"),
        )


@dataclass(frozen=True)
class EmbeddingSummary:
    """Summary of embedding vectors captured in the snapshot."""
    provider:         str
    model:            str
    model_version:    str
    vector_dimensions: int
    embedding_count:  int
    embedding_health: str    # "healthy" | "degraded" | "empty" | "unknown"

    @classmethod
    def empty(cls) -> "EmbeddingSummary":
        return cls(
            provider          = "stub",
            model             = "stub",
            model_version     = "1.0.0",
            vector_dimensions = 128,
            embedding_count   = 0,
            embedding_health  = "empty",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider":          self.provider,
            "model":             self.model,
            "model_version":     self.model_version,
            "vector_dimensions": self.vector_dimensions,
            "embedding_count":   self.embedding_count,
            "embedding_health":  self.embedding_health,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EmbeddingSummary":
        return cls(
            provider          = d.get("provider", "stub"),
            model             = d.get("model", "stub"),
            model_version     = d.get("model_version", "1.0.0"),
            vector_dimensions = d.get("vector_dimensions", 128),
            embedding_count   = d.get("embedding_count", 0),
            embedding_health  = d.get("embedding_health", "unknown"),
        )


@dataclass(frozen=True)
class VectorIndexSummary:
    """Summary of the vector index captured in the snapshot."""
    vector_store:      str
    index_version:     str
    index_size:        int
    indexed_artifacts: int
    index_health:      str    # "healthy" | "degraded" | "empty" | "unknown"

    @classmethod
    def empty(cls) -> "VectorIndexSummary":
        return cls(
            vector_store      = "in_memory",
            index_version     = "1.0.0",
            index_size        = 0,
            indexed_artifacts = 0,
            index_health      = "empty",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector_store":      self.vector_store,
            "index_version":     self.index_version,
            "index_size":        self.index_size,
            "indexed_artifacts": self.indexed_artifacts,
            "index_health":      self.index_health,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VectorIndexSummary":
        return cls(
            vector_store      = d.get("vector_store", "in_memory"),
            index_version     = d.get("index_version", "1.0.0"),
            index_size        = d.get("index_size", 0),
            indexed_artifacts = d.get("indexed_artifacts", 0),
            index_health      = d.get("index_health", "unknown"),
        )


@dataclass(frozen=True)
class RetrievalSummary:
    """Summary of retrieval capabilities captured in the snapshot."""
    strategy:              str
    hybrid_search_enabled: bool
    average_retrieval_ms:  float
    quality_score:         float    # [0.0 – 1.0]

    @classmethod
    def empty(cls) -> "RetrievalSummary":
        return cls(
            strategy              = "semantic",
            hybrid_search_enabled = False,
            average_retrieval_ms  = 0.0,
            quality_score         = 0.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy":              self.strategy,
            "hybrid_search_enabled": self.hybrid_search_enabled,
            "average_retrieval_ms":  self.average_retrieval_ms,
            "quality_score":         self.quality_score,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RetrievalSummary":
        return cls(
            strategy              = d.get("strategy", "semantic"),
            hybrid_search_enabled = d.get("hybrid_search_enabled", False),
            average_retrieval_ms  = d.get("average_retrieval_ms", 0.0),
            quality_score         = d.get("quality_score", 0.0),
        )


@dataclass(frozen=True)
class RecommendationSummary:
    """Summary of recommendation outputs captured in the snapshot."""
    recommendations_generated: int
    categories:                tuple    # Tuple[str]
    confidence_score:          float    # [0.0 – 1.0]

    @classmethod
    def empty(cls) -> "RecommendationSummary":
        return cls(
            recommendations_generated = 0,
            categories                = (),
            confidence_score          = 0.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations_generated": self.recommendations_generated,
            "categories":                list(self.categories),
            "confidence_score":          self.confidence_score,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RecommendationSummary":
        return cls(
            recommendations_generated = d.get("recommendations_generated", 0),
            categories                = tuple(d.get("categories", [])),
            confidence_score          = d.get("confidence_score", 0.0),
        )


@dataclass(frozen=True)
class SnapshotMemorySummary:
    """Summary of enterprise memory captured in the snapshot."""
    memory_objects:       int
    memory_domains:       tuple    # Tuple[str]
    cross_subsystem_links: int
    historical_references: int

    @classmethod
    def empty(cls) -> "SnapshotMemorySummary":
        return cls(
            memory_objects        = 0,
            memory_domains        = (),
            cross_subsystem_links = 0,
            historical_references = 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_objects":        self.memory_objects,
            "memory_domains":        list(self.memory_domains),
            "cross_subsystem_links": self.cross_subsystem_links,
            "historical_references": self.historical_references,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotMemorySummary":
        return cls(
            memory_objects        = d.get("memory_objects", 0),
            memory_domains        = tuple(d.get("memory_domains", [])),
            cross_subsystem_links = d.get("cross_subsystem_links", 0),
            historical_references = d.get("historical_references", 0),
        )


@dataclass(frozen=True)
class SnapshotAudit:
    """Audit record embedded within a knowledge snapshot."""
    governance_version:  str
    graph_version:       str
    embedding_version:   str
    validation_summary:  Dict[str, Any]    # {check_code: passed}
    audit_trail:         tuple             # Tuple[str]  — ordered audit entries

    @classmethod
    def empty(cls) -> "SnapshotAudit":
        return cls(
            governance_version = "1.0.0",
            graph_version      = "1.0.0",
            embedding_version  = "1.0.0",
            validation_summary = {},
            audit_trail        = (),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governance_version": self.governance_version,
            "graph_version":      self.graph_version,
            "embedding_version":  self.embedding_version,
            "validation_summary": self.validation_summary,
            "audit_trail":        list(self.audit_trail),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotAudit":
        return cls(
            governance_version = d.get("governance_version", "1.0.0"),
            graph_version      = d.get("graph_version", "1.0.0"),
            embedding_version  = d.get("embedding_version", "1.0.0"),
            validation_summary = dict(d.get("validation_summary", {})),
            audit_trail        = tuple(d.get("audit_trail", [])),
        )


@dataclass(frozen=True)
class SnapshotStatistics:
    """Processing statistics embedded within a knowledge snapshot."""
    processing_duration_ms: float
    snapshot_size_bytes:     int
    artifact_count:          int
    entity_count:            int
    relationship_count:      int
    embedding_count:         int
    vector_count:            int

    @classmethod
    def empty(cls) -> "SnapshotStatistics":
        return cls(
            processing_duration_ms = 0.0,
            snapshot_size_bytes    = 0,
            artifact_count         = 0,
            entity_count           = 0,
            relationship_count     = 0,
            embedding_count        = 0,
            vector_count           = 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processing_duration_ms": self.processing_duration_ms,
            "snapshot_size_bytes":    self.snapshot_size_bytes,
            "artifact_count":         self.artifact_count,
            "entity_count":           self.entity_count,
            "relationship_count":     self.relationship_count,
            "embedding_count":        self.embedding_count,
            "vector_count":           self.vector_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotStatistics":
        return cls(
            processing_duration_ms = d.get("processing_duration_ms", 0.0),
            snapshot_size_bytes    = d.get("snapshot_size_bytes", 0),
            artifact_count         = d.get("artifact_count", 0),
            entity_count           = d.get("entity_count", 0),
            relationship_count     = d.get("relationship_count", 0),
            embedding_count        = d.get("embedding_count", 0),
            vector_count           = d.get("vector_count", 0),
        )


@dataclass(frozen=True)
class SnapshotMetadata:
    """Operational metadata embedded within a knowledge snapshot."""
    environment:       str
    framework_version: str
    build_version:     str
    source_components: tuple    # Tuple[str]
    correlation_ids:   tuple    # Tuple[str]
    trace_ids:         tuple    # Tuple[str]

    @classmethod
    def empty(cls) -> "SnapshotMetadata":
        return cls(
            environment       = "production",
            framework_version = FRAMEWORK_VERSION,
            build_version     = VERSION,
            source_components = (),
            correlation_ids   = (),
            trace_ids         = (),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment":       self.environment,
            "framework_version": self.framework_version,
            "build_version":     self.build_version,
            "source_components": list(self.source_components),
            "correlation_ids":   list(self.correlation_ids),
            "trace_ids":         list(self.trace_ids),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotMetadata":
        return cls(
            environment       = d.get("environment", "production"),
            framework_version = d.get("framework_version", FRAMEWORK_VERSION),
            build_version     = d.get("build_version", VERSION),
            source_components = tuple(d.get("source_components", [])),
            correlation_ids   = tuple(d.get("correlation_ids", [])),
            trace_ids         = tuple(d.get("trace_ids", [])),
        )


# ════════════════════════════════════════════════════════════════════════
# KnowledgeSnapshot — the canonical immutable published representation
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """
    The immutable, versioned, canonical published representation of
    Enterprise Knowledge Intelligence.

    Aggregates validated outputs from:
      - M1: Knowledge Lifecycle (lifecycle_state)
      - M2: Knowledge Engine (knowledge_workflow_id, knowledge_summary)
      - M3: Knowledge Governance Policy Framework (governance_state, audit)
      - M4: Knowledge Intelligence Framework (graph_summary, embedding_summary,
            vector_index_summary, retrieval_summary, recommendation_summary,
            enterprise_memory_summary)

    Downstream components MUST consume KnowledgeSnapshot rather than
    directly accessing any individual sub-framework.
    """

    # --- Core identifiers ---
    snapshot_id:           str
    knowledge_session_id:  str
    knowledge_workflow_id: str
    enterprise_session_id: str

    # --- Versions ---
    knowledge_version:  str
    framework_version:  str
    snapshot_version:   str

    # --- State ---
    knowledge_scope:  KnowledgeScope
    knowledge_type:   KnowledgeType
    lifecycle_state:  str
    governance_state: str
    knowledge_state:  str

    # --- Timestamps ---
    snapshot_timestamp: str    # ISO-8601: when the snapshot was taken
    created_at:         str    # ISO-8601: when this record was created
    updated_at:         str    # ISO-8601: most recent modification

    # --- Summary sections ---
    knowledge_summary:         KnowledgeSummary
    graph_summary:             GraphSummary
    embedding_summary:         EmbeddingSummary
    vector_index_summary:      VectorIndexSummary
    retrieval_summary:         RetrievalSummary
    recommendation_summary:    RecommendationSummary
    enterprise_memory_summary: SnapshotMemorySummary
    audit:                     SnapshotAudit
    statistics:                SnapshotStatistics
    metadata:                  SnapshotMetadata

    # --- Integrity ---
    content_hash:   str = ""       # SHA-256 of canonical content (set by builder)
    schema_version: str = SCHEMA_VERSION
    state:          SnapshotState  = SnapshotState.BUILT
    version_tag:    SnapshotVersionTag = SnapshotVersionTag.STABLE

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":             self.snapshot_id,
            "knowledge_session_id":    self.knowledge_session_id,
            "knowledge_workflow_id":   self.knowledge_workflow_id,
            "enterprise_session_id":   self.enterprise_session_id,
            "knowledge_version":       self.knowledge_version,
            "framework_version":       self.framework_version,
            "snapshot_version":        self.snapshot_version,
            "knowledge_scope":         self.knowledge_scope.value,
            "knowledge_type":          self.knowledge_type.value,
            "lifecycle_state":         self.lifecycle_state,
            "governance_state":        self.governance_state,
            "knowledge_state":         self.knowledge_state,
            "snapshot_timestamp":      self.snapshot_timestamp,
            "created_at":              self.created_at,
            "updated_at":              self.updated_at,
            "knowledge_summary":       self.knowledge_summary.to_dict(),
            "graph_summary":           self.graph_summary.to_dict(),
            "embedding_summary":       self.embedding_summary.to_dict(),
            "vector_index_summary":    self.vector_index_summary.to_dict(),
            "retrieval_summary":       self.retrieval_summary.to_dict(),
            "recommendation_summary":  self.recommendation_summary.to_dict(),
            "enterprise_memory_summary": self.enterprise_memory_summary.to_dict(),
            "audit":                   self.audit.to_dict(),
            "statistics":              self.statistics.to_dict(),
            "metadata":                self.metadata.to_dict(),
            "content_hash":            self.content_hash,
            "schema_version":          self.schema_version,
            "state":                   self.state.value,
            "version_tag":             self.version_tag.value,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        try:
            return json.dumps(self.to_dict(), sort_keys=True, indent=indent)
        except Exception as exc:
            from .exceptions import SnapshotSerializationError
            raise SnapshotSerializationError(f"JSON serialization failed: {exc}") from exc

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeSnapshot":
        try:
            return cls(
                snapshot_id            = d["snapshot_id"],
                knowledge_session_id   = d["knowledge_session_id"],
                knowledge_workflow_id  = d["knowledge_workflow_id"],
                enterprise_session_id  = d["enterprise_session_id"],
                knowledge_version      = d["knowledge_version"],
                framework_version      = d["framework_version"],
                snapshot_version       = d["snapshot_version"],
                knowledge_scope        = KnowledgeScope(d["knowledge_scope"]),
                knowledge_type         = KnowledgeType(d["knowledge_type"]),
                lifecycle_state        = d["lifecycle_state"],
                governance_state       = d["governance_state"],
                knowledge_state        = d["knowledge_state"],
                snapshot_timestamp     = d["snapshot_timestamp"],
                created_at             = d["created_at"],
                updated_at             = d["updated_at"],
                knowledge_summary      = KnowledgeSummary.from_dict(d["knowledge_summary"]),
                graph_summary          = GraphSummary.from_dict(d["graph_summary"]),
                embedding_summary      = EmbeddingSummary.from_dict(d["embedding_summary"]),
                vector_index_summary   = VectorIndexSummary.from_dict(d["vector_index_summary"]),
                retrieval_summary      = RetrievalSummary.from_dict(d["retrieval_summary"]),
                recommendation_summary = RecommendationSummary.from_dict(d["recommendation_summary"]),
                enterprise_memory_summary = SnapshotMemorySummary.from_dict(
                    d["enterprise_memory_summary"]
                ),
                audit          = SnapshotAudit.from_dict(d["audit"]),
                statistics     = SnapshotStatistics.from_dict(d["statistics"]),
                metadata       = SnapshotMetadata.from_dict(d["metadata"]),
                content_hash   = d.get("content_hash", ""),
                schema_version = d.get("schema_version", SCHEMA_VERSION),
                state          = SnapshotState(d.get("state", SnapshotState.BUILT.value)),
                version_tag    = SnapshotVersionTag(
                    d.get("version_tag", SnapshotVersionTag.STABLE.value)
                ),
            )
        except KeyError as exc:
            from .exceptions import SnapshotSerializationError
            raise SnapshotSerializationError(f"Missing required field: {exc}") from exc
        except Exception as exc:
            from .exceptions import SnapshotSerializationError
            raise SnapshotSerializationError(f"Deserialization failed: {exc}") from exc

    @classmethod
    def from_json(cls, json_str: str) -> "KnowledgeSnapshot":
        try:
            d = json.loads(json_str)
        except Exception as exc:
            from .exceptions import SnapshotSerializationError
            raise SnapshotSerializationError(f"Invalid JSON: {exc}") from exc
        return cls.from_dict(d)

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(d: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of a canonical dict (excluding 'content_hash')."""
        d_copy = {k: v for k, v in d.items() if k != "content_hash"}
        canonical = json.dumps(d_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Return True if the stored content_hash matches a freshly computed one."""
        if not self.content_hash:
            return True    # no hash stored → skip check
        d         = self.to_dict()
        expected  = self.compute_hash(d)
        return self.content_hash == expected
