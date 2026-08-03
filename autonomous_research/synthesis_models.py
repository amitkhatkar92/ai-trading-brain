"""
synthesis_models.py — Typed models for the CrossStudySynthesizer.

ARS Phase 1.3.

Pure data.  No business logic.  All fields serialisable for JSON round-trip.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import FindingClassification


# ─── classification of synthesized conclusions ────────────────────────────────

class SynthesisClassification(str, Enum):
    CONFIRMED             = "CONFIRMED"              # ≥3 studies, conf≥0.85, zero contradictions
    VERIFIED              = "VERIFIED"               # ≥2 studies, conf≥0.75, zero contradictions
    SUPPORTED             = "SUPPORTED"              # ≥2 studies, conf≥0.60, zero contradictions
    PARTIAL               = "PARTIAL"                # single source OR supporters > contradictors
    CONTRADICTED          = "CONTRADICTED"           # contradictors ≥ supporters
    UNRESOLVED            = "UNRESOLVED"             # multi-study, inconclusive evidence
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # too few data points


# ─── relationship types ───────────────────────────────────────────────────────

class RelationshipType(str, Enum):
    STUDY_TO_FINDING        = "STUDY_TO_FINDING"
    FINDING_TO_FINDING      = "FINDING_TO_FINDING"      # cross-study agreement
    FINDING_TO_EDGE         = "FINDING_TO_EDGE"
    FINDING_TO_METRIC       = "FINDING_TO_METRIC"
    HYPOTHESIS_TO_FINDING   = "HYPOTHESIS_TO_FINDING"
    HYPOTHESIS_TO_STUDY     = "HYPOTHESIS_TO_STUDY"
    EDGE_TO_CERTIFICATION   = "EDGE_TO_CERTIFICATION"
    STUDY_TO_STUDY          = "STUDY_TO_STUDY"          # temporal or regime overlap


# ─── contradiction types ──────────────────────────────────────────────────────

class ContradictionType(str, Enum):
    CONFLICTING_VALUES    = "CONFLICTING_VALUES"     # same metric, values diverge >50%
    CONFLICTING_DIRECTION = "CONFLICTING_DIRECTION"  # opposite sign (lift / return)
    CONFLICTING_REGIME    = "CONFLICTING_REGIME"     # same regime, incompatible findings
    CONFLICTING_FINDINGS  = "CONFLICTING_FINDINGS"   # qualitatively incompatible
    CONFLICTING_METRIC    = "CONFLICTING_METRIC"     # same metric_id, different numeric values


# ─── relationship ─────────────────────────────────────────────────────────────

@dataclass
class KnowledgeRelationship:
    relationship_id:   str
    relationship_type: RelationshipType
    from_id:           str
    from_type:         str      # STUDY | FINDING | EDGE | HYPOTHESIS | METRIC | CERTIFICATION
    to_id:             str
    to_type:           str
    description:       str
    confidence:        float = 1.0
    discovered_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id":   self.relationship_id,
            "relationship_type": self.relationship_type.value,
            "from_id":           self.from_id,
            "from_type":         self.from_type,
            "to_id":             self.to_id,
            "to_type":           self.to_type,
            "description":       self.description,
            "confidence":        self.confidence,
            "discovered_at":     self.discovered_at.isoformat(),
        }


# ─── evidence chain ───────────────────────────────────────────────────────────

@dataclass
class EvidenceChain:
    chain_id:       str
    root_study_ids: List[str]
    finding_ids:    List[str]
    edge_ids:       List[str]
    metric_ids:     List[str]
    hypothesis_ids: List[str]
    cert_ids:       List[str]
    description:    str
    completeness:   float   # 0.0–1.0: fraction of chain links that are non-empty

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":       self.chain_id,
            "root_study_ids": self.root_study_ids,
            "finding_ids":    self.finding_ids,
            "edge_ids":       self.edge_ids,
            "metric_ids":     self.metric_ids,
            "hypothesis_ids": self.hypothesis_ids,
            "cert_ids":       self.cert_ids,
            "description":    self.description,
            "completeness":   self.completeness,
        }


# ─── contradiction record ─────────────────────────────────────────────────────

@dataclass
class ContradictionRecord:
    contradiction_id:   str
    contradiction_type: ContradictionType
    finding_a_id:       str
    study_a_id:         str
    finding_b_id:       str
    study_b_id:         str
    metric:             str
    value_a:            Any
    value_b:            Any
    description:        str
    severity:           float    # 0.0–1.0
    auto_resolved:      bool = False   # always False — contradictions are never auto-resolved
    detected_at:        datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_id":   self.contradiction_id,
            "contradiction_type": self.contradiction_type.value,
            "finding_a_id":       self.finding_a_id,
            "study_a_id":         self.study_a_id,
            "finding_b_id":       self.finding_b_id,
            "study_b_id":         self.study_b_id,
            "metric":             self.metric,
            "value_a":            self.value_a,
            "value_b":            self.value_b,
            "description":        self.description,
            "severity":           self.severity,
            "auto_resolved":      self.auto_resolved,
            "detected_at":        self.detected_at.isoformat(),
        }


# ─── synthesized finding ──────────────────────────────────────────────────────

@dataclass
class SynthesizedFinding:
    synthesis_id:               str
    title:                      str
    classification:             SynthesisClassification
    finding_classification:     FindingClassification
    metric:                     str
    regime:                     Optional[str]
    description:                str
    source_study_ids:           List[str]
    source_finding_ids:         List[str]
    related_edge_ids:           List[str]
    related_hypothesis_ids:     List[str]
    related_metric_ids:         List[str]
    related_cert_ids:           List[str]
    synthesis_confidence:       float
    confidence_breakdown:       Dict[str, float]
    evidence_count:             int
    supporting_study_count:     int
    contradicting_study_count:  int
    regime_coverage:            List[str]
    sector_coverage:            List[str]
    time_coverage:              Optional[Dict[str, str]]   # {"start": ..., "end": ...}
    contradiction_ids:          List[str]
    evidence_chain:             Optional[EvidenceChain]
    synthesized_at:             datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id":               self.synthesis_id,
            "title":                      self.title,
            "classification":             self.classification.value,
            "finding_classification":     self.finding_classification.value,
            "metric":                     self.metric,
            "regime":                     self.regime,
            "description":                self.description,
            "source_study_ids":           self.source_study_ids,
            "source_finding_ids":         self.source_finding_ids,
            "related_edge_ids":           self.related_edge_ids,
            "related_hypothesis_ids":     self.related_hypothesis_ids,
            "related_metric_ids":         self.related_metric_ids,
            "related_cert_ids":           self.related_cert_ids,
            "synthesis_confidence":       self.synthesis_confidence,
            "confidence_breakdown":       self.confidence_breakdown,
            "evidence_count":             self.evidence_count,
            "supporting_study_count":     self.supporting_study_count,
            "contradicting_study_count":  self.contradicting_study_count,
            "regime_coverage":            self.regime_coverage,
            "sector_coverage":            self.sector_coverage,
            "time_coverage":              self.time_coverage,
            "contradiction_ids":          self.contradiction_ids,
            "evidence_chain":             self.evidence_chain.to_dict() if self.evidence_chain else None,
            "synthesized_at":             self.synthesized_at.isoformat(),
        }


# ─── knowledge consensus ─────────────────────────────────────────────────────

@dataclass
class KnowledgeConsensus:
    consensus_id:    str
    topic:           str
    classification:  SynthesisClassification
    findings_count:  int
    studies_count:   int
    agreement_rate:  float
    key_metrics:     List[str]
    regime_coverage: List[str]
    summary:         str
    synthesized_at:  datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus_id":   self.consensus_id,
            "topic":          self.topic,
            "classification": self.classification.value,
            "findings_count": self.findings_count,
            "studies_count":  self.studies_count,
            "agreement_rate": self.agreement_rate,
            "key_metrics":    self.key_metrics,
            "regime_coverage": self.regime_coverage,
            "summary":        self.summary,
            "synthesized_at": self.synthesized_at.isoformat(),
        }


# ─── synthesis statistics ─────────────────────────────────────────────────────

@dataclass
class SynthesisStatistics:
    total_findings_processed:    int
    total_synthesized_findings:  int
    total_relationships:         int
    total_contradictions:        int
    by_classification:           Dict[str, int]
    by_finding_type:             Dict[str, int]
    avg_synthesis_confidence:    float
    avg_evidence_count:          float
    studies_processed:           int
    edges_correlated:            int
    hypotheses_correlated:       int
    certifications_correlated:   int
    metrics_correlated:          int
    synthesis_duration_ms:       float
    synthesized_at:              datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_findings_processed":   self.total_findings_processed,
            "total_synthesized_findings": self.total_synthesized_findings,
            "total_relationships":        self.total_relationships,
            "total_contradictions":       self.total_contradictions,
            "by_classification":          self.by_classification,
            "by_finding_type":            self.by_finding_type,
            "avg_synthesis_confidence":   self.avg_synthesis_confidence,
            "avg_evidence_count":         self.avg_evidence_count,
            "studies_processed":          self.studies_processed,
            "edges_correlated":           self.edges_correlated,
            "hypotheses_correlated":      self.hypotheses_correlated,
            "certifications_correlated":  self.certifications_correlated,
            "metrics_correlated":         self.metrics_correlated,
            "synthesis_duration_ms":      self.synthesis_duration_ms,
            "synthesized_at":             self.synthesized_at.isoformat(),
        }


# ─── complete synthesis report ────────────────────────────────────────────────

@dataclass
class SynthesisReport:
    report_id:            str
    synthesized_at:       datetime
    synthesized_findings: List[SynthesizedFinding]
    relationships:        List[KnowledgeRelationship]
    contradictions:       List[ContradictionRecord]
    consensus_blocks:     List[KnowledgeConsensus]
    statistics:           SynthesisStatistics
    warnings:             List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":            self.report_id,
            "synthesized_at":       self.synthesized_at.isoformat(),
            "synthesized_findings": [sf.to_dict() for sf in self.synthesized_findings],
            "relationships":        [r.to_dict() for r in self.relationships],
            "contradictions":       [c.to_dict() for c in self.contradictions],
            "consensus_blocks":     [c.to_dict() for c in self.consensus_blocks],
            "statistics":           self.statistics.to_dict(),
            "warnings":             self.warnings,
        }
