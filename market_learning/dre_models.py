"""
dre_models.py — Pure data models for the DNA Reinforcement Engine.

O-002: DNA Reinforcement Engine (DRE).

Pure data.  No business logic.  All fields JSON-serialisable.
DRE = DNA Reinforcement Engine — the live-learning reinforcement engine of IIOS.

DRE is READ-ONLY at the discovery level:
    It never creates new DNA.
    It never invokes discovery or consensus engines.
    It only reinforces (strengthens or weakens) existing institutional DNA
    using verified closed-trade outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── exceptions ───────────────────────────────────────────────────────────────

class DREError(Exception):
    """Base exception for DRE errors."""


class DREInputError(DREError):
    """Invalid input supplied to DNAReinforcementEngine."""


class DREProcessingError(DREError):
    """Error during reinforcement computation."""


# ─── enumerations ─────────────────────────────────────────────────────────────

class ReinforcementType(str, Enum):
    """Classification of a reinforcement event by its outcome relationship to DNA."""
    POSITIVE              = "POSITIVE"              # win confirms DNA alignment
    NEGATIVE              = "NEGATIVE"              # loss contradicts DNA alignment
    NEUTRAL               = "NEUTRAL"               # near-zero outcome — insufficient signal
    CONTRADICTORY         = "CONTRADICTORY"         # won despite conflicting DNA
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE" # DNA below minimum evidence threshold


class OutcomeQuality(str, Enum):
    """Quality classification of a trade outcome used to weight reinforcement."""
    EXCELLENT = "EXCELLENT"   # R >= 2.0 and won
    GOOD      = "GOOD"        # R >= 1.0 and won
    FAIR      = "FAIR"        # 0 <= R < 1.0  OR  small loss R in [-0.5, 0)
    POOR      = "POOR"        # R in [-1.5, -0.5)
    BAD       = "BAD"         # R < -1.5


# ─── ReinforcementEvidence ────────────────────────────────────────────────────

@dataclass
class ReinforcementEvidence:
    """
    Full evidence bundle backing one reinforcement decision.

    Enables complete reproduction of every reinforcement from first principles.
    Every field is sourced from a real trade, PMCI result, or CDS evaluation.
    """

    trade_id:         str
    symbol:           str
    trade_direction:  str    # "LONG" | "SHORT"
    strategy:         str
    regime_at_entry:  str
    pmci_score:       float  # PMCIResult.pmci_score at decision time [0, 1]
    ca_pmci_score:    float  # CAPMCIResult.ca_pmci — 0.0 if not available
    cds_score:        float  # ContextualDNAScore.cds for this DNA — 0.0 if unavailable
    dna_alignment:    float  # PMCIEvidence.alignment for this feature [0, 1]
    dna_contribution: float  # PMCIEvidence.contribution for this feature
    r_multiple:       float  # trade R-multiple (pnl / 1R risk)
    pnl:              float  # realised PnL in rupees
    holding_period_h: float  # hours from entry to close
    won:              bool
    outcome_quality:  str    # OutcomeQuality.value
    confidence_score: float  # DecisionEngine score at entry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id":         self.trade_id,
            "symbol":           self.symbol,
            "trade_direction":  self.trade_direction,
            "strategy":         self.strategy,
            "regime_at_entry":  self.regime_at_entry,
            "pmci_score":       round(self.pmci_score, 6),
            "ca_pmci_score":    round(self.ca_pmci_score, 6),
            "cds_score":        round(self.cds_score, 6),
            "dna_alignment":    round(self.dna_alignment, 6),
            "dna_contribution": round(self.dna_contribution, 6),
            "r_multiple":       round(self.r_multiple, 4),
            "pnl":              round(self.pnl, 2),
            "holding_period_h": round(self.holding_period_h, 3),
            "won":              self.won,
            "outcome_quality":  self.outcome_quality,
            "confidence_score": round(self.confidence_score, 6),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReinforcementEvidence":
        return cls(
            trade_id=d["trade_id"],
            symbol=d["symbol"],
            trade_direction=d["trade_direction"],
            strategy=d["strategy"],
            regime_at_entry=d["regime_at_entry"],
            pmci_score=float(d["pmci_score"]),
            ca_pmci_score=float(d["ca_pmci_score"]),
            cds_score=float(d["cds_score"]),
            dna_alignment=float(d["dna_alignment"]),
            dna_contribution=float(d["dna_contribution"]),
            r_multiple=float(d["r_multiple"]),
            pnl=float(d["pnl"]),
            holding_period_h=float(d["holding_period_h"]),
            won=bool(d["won"]),
            outcome_quality=d["outcome_quality"],
            confidence_score=float(d["confidence_score"]),
        )


# ─── DNAReinforcement ─────────────────────────────────────────────────────────

@dataclass
class DNAReinforcement:
    """
    One reinforcement event: a single DNA record updated by a single trade.

    Immutable once written.  Every field is traceable to its source.
    Identifies exactly which DNA changed, which trade caused it, and what changed.
    """

    reinforcement_id:      str               # "DRE-{sha256[:12]}"
    dna_id:                str               # InstitutionalDNA.id
    feature_name:          str
    direction:             str
    trade_id:              str               # OrderRecord.order_id
    reinforcement_type:    str               # ReinforcementType.value
    evidence:              ReinforcementEvidence
    confidence_before:     float             # DNA.confidence before update
    confidence_after:      float             # DNA.confidence after update
    confidence_delta:      float             # after − before (signed)
    stability_before:      float             # DNA.temporal_stability before update
    stability_after:       float             # DNA.temporal_stability after update
    stability_delta:       float             # after − before (signed)
    evidence_count_before: int
    evidence_count_after:  int
    reason:                str               # human-readable explanation
    idr_revision:          Optional[int]     # IDR version created; None for dry-run
    processed_at:          str               # ISO datetime
    dre_version:           str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reinforcement_id":    self.reinforcement_id,
            "dna_id":              self.dna_id,
            "feature_name":        self.feature_name,
            "direction":           self.direction,
            "trade_id":            self.trade_id,
            "reinforcement_type":  self.reinforcement_type,
            "evidence":            self.evidence.to_dict(),
            "confidence_before":   round(self.confidence_before, 6),
            "confidence_after":    round(self.confidence_after, 6),
            "confidence_delta":    round(self.confidence_delta, 6),
            "stability_before":    round(self.stability_before, 6),
            "stability_after":     round(self.stability_after, 6),
            "stability_delta":     round(self.stability_delta, 6),
            "evidence_count_before": self.evidence_count_before,
            "evidence_count_after":  self.evidence_count_after,
            "reason":              self.reason,
            "idr_revision":        self.idr_revision,
            "processed_at":        self.processed_at,
            "dre_version":         self.dre_version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DNAReinforcement":
        return cls(
            reinforcement_id=d["reinforcement_id"],
            dna_id=d["dna_id"],
            feature_name=d["feature_name"],
            direction=d["direction"],
            trade_id=d["trade_id"],
            reinforcement_type=d["reinforcement_type"],
            evidence=ReinforcementEvidence.from_dict(d["evidence"]),
            confidence_before=float(d["confidence_before"]),
            confidence_after=float(d["confidence_after"]),
            confidence_delta=float(d["confidence_delta"]),
            stability_before=float(d["stability_before"]),
            stability_after=float(d["stability_after"]),
            stability_delta=float(d["stability_delta"]),
            evidence_count_before=int(d["evidence_count_before"]),
            evidence_count_after=int(d["evidence_count_after"]),
            reason=d["reason"],
            idr_revision=int(d["idr_revision"]) if d.get("idr_revision") is not None else None,
            processed_at=d["processed_at"],
            dre_version=d.get("dre_version", "1.0"),
        )


# ─── DNAConfidenceUpdate ──────────────────────────────────────────────────────

@dataclass
class DNAConfidenceUpdate:
    """
    Summary of all confidence changes applied to one DNA across one batch cycle.
    """

    dna_id:               str
    feature_name:         str
    direction:            str
    lifecycle:            str
    reinforcements:       List[DNAReinforcement]
    net_confidence_delta: float
    net_stability_delta:  float
    final_confidence:     float
    final_stability:      float
    dominant_type:        str    # most frequent ReinforcementType.value
    explanation:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dna_id":               self.dna_id,
            "feature_name":         self.feature_name,
            "direction":            self.direction,
            "lifecycle":            self.lifecycle,
            "reinforcements":       [r.to_dict() for r in self.reinforcements],
            "net_confidence_delta": round(self.net_confidence_delta, 6),
            "net_stability_delta":  round(self.net_stability_delta, 6),
            "final_confidence":     round(self.final_confidence, 6),
            "final_stability":      round(self.final_stability, 6),
            "dominant_type":        self.dominant_type,
            "explanation":          self.explanation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DNAConfidenceUpdate":
        return cls(
            dna_id=d["dna_id"],
            feature_name=d["feature_name"],
            direction=d["direction"],
            lifecycle=d["lifecycle"],
            reinforcements=[DNAReinforcement.from_dict(r) for r in d.get("reinforcements", [])],
            net_confidence_delta=float(d["net_confidence_delta"]),
            net_stability_delta=float(d["net_stability_delta"]),
            final_confidence=float(d["final_confidence"]),
            final_stability=float(d["final_stability"]),
            dominant_type=d["dominant_type"],
            explanation=d["explanation"],
        )


# ─── ReinforcementStatistics ──────────────────────────────────────────────────

@dataclass
class ReinforcementStatistics:
    """Aggregate statistics across all reinforcement events since DRE init."""

    total_reinforcements:        int
    positive_count:              int
    negative_count:              int
    neutral_count:               int
    contradictory_count:         int
    insufficient_evidence_count: int
    trades_processed:            int
    dna_updated:                 int
    dna_skipped:                 int
    avg_confidence_delta:        float
    avg_stability_delta:         float
    max_confidence_delta:        float
    min_confidence_delta:        float
    total_idr_writes:            int
    first_reinforcement_at:      Optional[str]
    last_reinforcement_at:       Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reinforcements":        self.total_reinforcements,
            "positive_count":              self.positive_count,
            "negative_count":              self.negative_count,
            "neutral_count":               self.neutral_count,
            "contradictory_count":         self.contradictory_count,
            "insufficient_evidence_count": self.insufficient_evidence_count,
            "trades_processed":            self.trades_processed,
            "dna_updated":                 self.dna_updated,
            "dna_skipped":                 self.dna_skipped,
            "avg_confidence_delta":        round(self.avg_confidence_delta, 6),
            "avg_stability_delta":         round(self.avg_stability_delta, 6),
            "max_confidence_delta":        round(self.max_confidence_delta, 6),
            "min_confidence_delta":        round(self.min_confidence_delta, 6),
            "total_idr_writes":            self.total_idr_writes,
            "first_reinforcement_at":      self.first_reinforcement_at,
            "last_reinforcement_at":       self.last_reinforcement_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReinforcementStatistics":
        return cls(
            total_reinforcements=int(d["total_reinforcements"]),
            positive_count=int(d["positive_count"]),
            negative_count=int(d["negative_count"]),
            neutral_count=int(d["neutral_count"]),
            contradictory_count=int(d["contradictory_count"]),
            insufficient_evidence_count=int(d["insufficient_evidence_count"]),
            trades_processed=int(d["trades_processed"]),
            dna_updated=int(d["dna_updated"]),
            dna_skipped=int(d["dna_skipped"]),
            avg_confidence_delta=float(d["avg_confidence_delta"]),
            avg_stability_delta=float(d["avg_stability_delta"]),
            max_confidence_delta=float(d["max_confidence_delta"]),
            min_confidence_delta=float(d["min_confidence_delta"]),
            total_idr_writes=int(d["total_idr_writes"]),
            first_reinforcement_at=d.get("first_reinforcement_at"),
            last_reinforcement_at=d.get("last_reinforcement_at"),
        )


# ─── DNAReinforcementHistory ──────────────────────────────────────────────────

@dataclass
class DNAReinforcementHistory:
    """
    Complete reinforcement audit trail.

    Persisted atomically to data/mls/dre/history.json.
    Never modified in place — fully rebuilt on each save.
    """

    reinforcements: List[DNAReinforcement]
    statistics:     ReinforcementStatistics
    generated_at:   str
    dre_version:    str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reinforcements": [r.to_dict() for r in self.reinforcements],
            "statistics":     self.statistics.to_dict(),
            "generated_at":   self.generated_at,
            "dre_version":    self.dre_version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DNAReinforcementHistory":
        stats_raw = d.get("statistics")
        if stats_raw:
            stats = ReinforcementStatistics.from_dict(stats_raw)
        else:
            stats = ReinforcementStatistics(
                total_reinforcements=0, positive_count=0, negative_count=0,
                neutral_count=0, contradictory_count=0,
                insufficient_evidence_count=0, trades_processed=0,
                dna_updated=0, dna_skipped=0,
                avg_confidence_delta=0.0, avg_stability_delta=0.0,
                max_confidence_delta=0.0, min_confidence_delta=0.0,
                total_idr_writes=0, first_reinforcement_at=None,
                last_reinforcement_at=None,
            )
        return cls(
            reinforcements=[DNAReinforcement.from_dict(r) for r in d.get("reinforcements", [])],
            statistics=stats,
            generated_at=d.get("generated_at", ""),
            dre_version=d.get("dre_version", "1.0"),
        )
