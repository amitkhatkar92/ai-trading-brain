"""
ikn_models.py — Data models for IKN-001 Institutional Knowledge Network.

IKN only records and serves institutional relationships.
IKN never changes knowledge, promotes discoveries, or creates hypotheses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── node types ────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    DNA                = "DNA"
    EDGE               = "EDGE"
    FEATURE            = "FEATURE"
    STUDY              = "STUDY"
    FINDING            = "FINDING"
    HYPOTHESIS         = "HYPOTHESIS"
    DISCOVERY          = "DISCOVERY"
    CLUSTER            = "CLUSTER"
    MARKET_REGIME      = "MARKET_REGIME"
    SECTOR             = "SECTOR"
    MARKET_PERSONALITY = "MARKET_PERSONALITY"
    PMCI_COMPONENT     = "PMCI_COMPONENT"
    CDS_COMPONENT      = "CDS_COMPONENT"
    JOURNAL_ENTRY      = "JOURNAL_ENTRY"
    KNOWLEDGE_PACKAGE  = "KNOWLEDGE_PACKAGE"


# ── relationship types ────────────────────────────────────────────────────────

class RelationshipType(str, Enum):
    SUPPORTED_BY    = "SUPPORTED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    DISCOVERED_IN   = "DISCOVERED_IN"
    VALIDATED_BY    = "VALIDATED_BY"
    GENERATED_BY    = "GENERATED_BY"
    RELATED_TO      = "RELATED_TO"
    DEPENDS_ON      = "DEPENDS_ON"
    WORKS_IN        = "WORKS_IN"
    FAILS_IN        = "FAILS_IN"
    EVOLVED_TO      = "EVOLVED_TO"
    SPECIALIZES     = "SPECIALIZES"
    GENERALIZES     = "GENERALIZES"
    BELONGS_TO      = "BELONGS_TO"
    USES            = "USES"
    REQUIRES        = "REQUIRES"
    SUPERSEDES      = "SUPERSEDES"
    OBSERVED_WITH   = "OBSERVED_WITH"
    CO_OCCURS_WITH  = "CO_OCCURS_WITH"


class IKNError(Exception):
    pass


# ── core models ───────────────────────────────────────────────────────────────

@dataclass
class KnowledgeNode:
    node_id:    str
    node_type:  str
    name:       str
    metadata:   Dict[str, Any]
    created_at: str
    updated_at: str
    version:    int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id":    self.node_id,
            "node_type":  self.node_type,
            "name":       self.name,
            "metadata":   self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version":    self.version,
        }


@dataclass
class KnowledgeRelationship:
    relationship_id:    str
    source_id:          str
    target_id:          str
    relationship_type:  str
    confidence:         float
    evidence_count:     int
    supporting_studies: List[str]
    supporting_years:   List[int]
    supporting_regimes: List[str]
    created_at:         str
    updated_at:         str
    version:            int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id":    self.relationship_id,
            "source_id":          self.source_id,
            "target_id":          self.target_id,
            "relationship_type":  self.relationship_type,
            "confidence":         self.confidence,
            "evidence_count":     self.evidence_count,
            "supporting_studies": self.supporting_studies,
            "supporting_years":   self.supporting_years,
            "supporting_regimes": self.supporting_regimes,
            "created_at":         self.created_at,
            "updated_at":         self.updated_at,
            "version":            self.version,
        }


@dataclass
class KnowledgeEvidence:
    evidence_id:     str
    relationship_id: str
    description:     str
    source:          str
    data_points:     int
    created_at:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id":     self.evidence_id,
            "relationship_id": self.relationship_id,
            "description":     self.description,
            "source":          self.source,
            "data_points":     self.data_points,
            "created_at":      self.created_at,
        }


@dataclass
class KnowledgePath:
    nodes:            List[KnowledgeNode]
    relationships:    List[KnowledgeRelationship]
    length:           int
    total_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes":            [n.to_dict() for n in self.nodes],
            "relationships":    [r.to_dict() for r in self.relationships],
            "length":           self.length,
            "total_confidence": self.total_confidence,
        }


@dataclass
class KnowledgeSubgraph:
    nodes:          Dict[str, KnowledgeNode]
    relationships:  List[KnowledgeRelationship]
    center_node_id: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes":          {k: v.to_dict() for k, v in self.nodes.items()},
            "relationships":  [r.to_dict() for r in self.relationships],
            "center_node_id": self.center_node_id,
        }


@dataclass
class KnowledgeStatistics:
    total_nodes:           int
    total_relationships:   int
    nodes_by_type:         Dict[str, int]
    relationships_by_type: Dict[str, int]
    avg_confidence:        float
    most_connected_nodes:  List[Tuple[str, int]]
    orphan_count:          int
    generated_at:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes":           self.total_nodes,
            "total_relationships":   self.total_relationships,
            "nodes_by_type":         self.nodes_by_type,
            "relationships_by_type": self.relationships_by_type,
            "avg_confidence":        self.avg_confidence,
            "most_connected_nodes":  self.most_connected_nodes,
            "orphan_count":          self.orphan_count,
            "generated_at":          self.generated_at,
        }


@dataclass
class KnowledgeNetworkSnapshot:
    snapshot_id:        str
    generated_at:       str
    statistics:         KnowledgeStatistics
    reports:            List[str]
    node_count:         int
    relationship_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "generated_at":       self.generated_at,
            "statistics":         self.statistics.to_dict(),
            "reports":            self.reports,
            "node_count":         self.node_count,
            "relationship_count": self.relationship_count,
        }


# ── validation sets ────────────────────────────────────────────────────────────

VALID_NODE_TYPES         = frozenset(nt.value for nt in NodeType)
VALID_RELATIONSHIP_TYPES = frozenset(rt.value for rt in RelationshipType)
