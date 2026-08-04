"""
pmci_models.py — Typed models for the MLS PMCIEngine.

MLS Phase 5.

Pure data.  No business logic.  All fields JSON-serialisable.
PMCI = Pre-Movement Consensus Intelligence.

PMCI is read-only.  It never modifies DNA, ARS, strategy, thresholds,
or any persistent store.  It never executes or recommends trades.
It measures evidence similarity only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── exceptions ───────────────────────────────────────────────────────────────

class PMCIError(Exception):
    """Base exception for PMCIEngine errors."""


class PMCIInputError(PMCIError):
    """Invalid input supplied to PMCIEngine."""


# ─── component ────────────────────────────────────────────────────────────────

@dataclass
class PMCIComponent:
    """Score and explanation for one named PMCI component."""

    name:           str    # component identifier
    value:          float  # [0, 1] raw component value
    weight:         float  # configured weight in the PMCI formula
    weighted_value: float  # value * weight — contribution to pmci_score
    matched_count:  int    # number of DNA features contributing
    explanation:    str    # one-line human-readable description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "value":          round(self.value, 6),
            "weight":         self.weight,
            "weighted_value": round(self.weighted_value, 6),
            "matched_count":  self.matched_count,
            "explanation":    self.explanation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PMCIComponent:
        return cls(
            name=d["name"],
            value=float(d["value"]),
            weight=float(d["weight"]),
            weighted_value=float(d["weighted_value"]),
            matched_count=int(d["matched_count"]),
            explanation=d["explanation"],
        )


# ─── evidence ─────────────────────────────────────────────────────────────────

@dataclass
class PMCIEvidence:
    """
    Evidence record for one (feature_name, direction) DNA match or conflict.

    Provides full traceability: which DNA feature, what value the stock showed,
    how strongly it aligned with the winner direction, and what evidence backs it.
    """

    feature_name:    str    # e.g. "rsi"
    direction:       str    # SeparationDirection.value
    stock_value:     float  # feature value from MarketObservation
    alignment:       float  # [0, 1]: how closely stock value matches winner direction
    consensus_score: float  # DNA evidence strength [0, 1]
    evidence_count:  int    # observation days backing this DNA
    last_seen:       str    # ISO date of most recent DNA observation
    consensus_state: str    # ConsensusState.value
    contribution:    float  # alignment × consensus_score
    is_match:        bool   # True when alignment >= feature_midpoint
    is_contradiction: bool  # True when alignment < (1 − feature_midpoint)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name":    self.feature_name,
            "direction":       self.direction,
            "stock_value":     round(self.stock_value, 6),
            "alignment":       round(self.alignment, 6),
            "consensus_score": round(self.consensus_score, 6),
            "evidence_count":  self.evidence_count,
            "last_seen":       self.last_seen,
            "consensus_state": self.consensus_state,
            "contribution":    round(self.contribution, 6),
            "is_match":        self.is_match,
            "is_contradiction": self.is_contradiction,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PMCIEvidence:
        return cls(
            feature_name=d["feature_name"],
            direction=d["direction"],
            stock_value=float(d["stock_value"]),
            alignment=float(d["alignment"]),
            consensus_score=float(d["consensus_score"]),
            evidence_count=int(d["evidence_count"]),
            last_seen=d["last_seen"],
            consensus_state=d["consensus_state"],
            contribution=float(d["contribution"]),
            is_match=bool(d["is_match"]),
            is_contradiction=bool(d["is_contradiction"]),
        )


# ─── breakdown ────────────────────────────────────────────────────────────────

@dataclass
class PMCIBreakdown:
    """
    Full explainability record for one PMCI evaluation.

    Every PMCI score can be reproduced from this breakdown:
        matched_dna     — features present and winner-aligned
        missing_dna     — DNA features absent from the observation
        conflicting_dna — features present but counter-winner
        neutral_dna     — NEUTRALS_HIGHER / NEUTRALS_LOWER DNA
    """

    matched_dna:             List[PMCIEvidence]  # winner-aligned, sorted by contribution desc
    missing_dna:             List[str]           # feature names absent from observation
    conflicting_dna:         List[PMCIEvidence]  # counter-winner
    neutral_dna:             List[PMCIEvidence]  # neutral DNA alignment
    total_institutional_dna: int                 # INSTITUTIONAL entries in library
    coverage_fraction:       float               # observed features / total active DNA features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched_dna":             [e.to_dict() for e in self.matched_dna],
            "missing_dna":             self.missing_dna,
            "conflicting_dna":         [e.to_dict() for e in self.conflicting_dna],
            "neutral_dna":             [e.to_dict() for e in self.neutral_dna],
            "total_institutional_dna": self.total_institutional_dna,
            "coverage_fraction":       round(self.coverage_fraction, 6),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PMCIBreakdown:
        return cls(
            matched_dna=[PMCIEvidence.from_dict(e) for e in d.get("matched_dna", [])],
            missing_dna=list(d.get("missing_dna", [])),
            conflicting_dna=[PMCIEvidence.from_dict(e) for e in d.get("conflicting_dna", [])],
            neutral_dna=[PMCIEvidence.from_dict(e) for e in d.get("neutral_dna", [])],
            total_institutional_dna=int(d.get("total_institutional_dna", 0)),
            coverage_fraction=float(d.get("coverage_fraction", 0.0)),
        )


# ─── result ───────────────────────────────────────────────────────────────────

@dataclass
class PMCIResult:
    """
    Complete PMCI evaluation for one symbol on one trading date.

    pmci_score ∈ [0, 1]:
        High score  → stock closely resembles institutional Winner DNA.
        Low score   → stock shows few winner characteristics or many loser ones.

    PMCI is a similarity measure only.  It is NOT a trading signal.
    """

    result_id:       str                # PMC-{sha256[:8]}
    symbol:          str
    evaluation_date: str                # ISO date
    regime:          str                # market regime at evaluation time
    pmci_score:      float              # final score [0, 1]
    components:      List[PMCIComponent]
    breakdown:       PMCIBreakdown
    confidence:      float              # meta-confidence in this score [0, 1]
    explanation:     str                # human-readable one-paragraph summary
    library_id:      str                # which ConsensusLibrary was used
    feature_count:   int                # features in the input observation
    evaluated_at:    str                # ISO datetime (wall clock)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "symbol":          self.symbol,
            "evaluation_date": self.evaluation_date,
            "regime":          self.regime,
            "pmci_score":      round(self.pmci_score, 6),
            "components":      [c.to_dict() for c in self.components],
            "breakdown":       self.breakdown.to_dict(),
            "confidence":      round(self.confidence, 6),
            "explanation":     self.explanation,
            "library_id":      self.library_id,
            "feature_count":   self.feature_count,
            "evaluated_at":    self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PMCIResult:
        return cls(
            result_id=d["result_id"],
            symbol=d["symbol"],
            evaluation_date=d["evaluation_date"],
            regime=d["regime"],
            pmci_score=float(d["pmci_score"]),
            components=[PMCIComponent.from_dict(c) for c in d.get("components", [])],
            breakdown=PMCIBreakdown.from_dict(d["breakdown"]),
            confidence=float(d["confidence"]),
            explanation=d["explanation"],
            library_id=d["library_id"],
            feature_count=int(d["feature_count"]),
            evaluated_at=d["evaluated_at"],
        )


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class PMCIStatistics:
    """Aggregate statistics across a batch of PMCI evaluations."""

    evaluation_date:       str
    total_symbols:         int
    avg_pmci:              float
    max_pmci:              float
    min_pmci:              float
    high_similarity_count: int    # pmci_score >= pmci_high_similarity_threshold
    low_similarity_count:  int    # pmci_score <= pmci_low_similarity_threshold
    avg_winner_match:      float
    avg_loser_match:       float
    avg_coverage:          float
    top_symbol:            Optional[str]
    top_pmci:              float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_date":       self.evaluation_date,
            "total_symbols":         self.total_symbols,
            "avg_pmci":              round(self.avg_pmci, 6),
            "max_pmci":              round(self.max_pmci, 6),
            "min_pmci":              round(self.min_pmci, 6),
            "high_similarity_count": self.high_similarity_count,
            "low_similarity_count":  self.low_similarity_count,
            "avg_winner_match":      round(self.avg_winner_match, 6),
            "avg_loser_match":       round(self.avg_loser_match, 6),
            "avg_coverage":          round(self.avg_coverage, 6),
            "top_symbol":            self.top_symbol,
            "top_pmci":              round(self.top_pmci, 6),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PMCIStatistics:
        return cls(
            evaluation_date=d.get("evaluation_date", ""),
            total_symbols=int(d.get("total_symbols", 0)),
            avg_pmci=float(d.get("avg_pmci", 0.0)),
            max_pmci=float(d.get("max_pmci", 0.0)),
            min_pmci=float(d.get("min_pmci", 0.0)),
            high_similarity_count=int(d.get("high_similarity_count", 0)),
            low_similarity_count=int(d.get("low_similarity_count", 0)),
            avg_winner_match=float(d.get("avg_winner_match", 0.0)),
            avg_loser_match=float(d.get("avg_loser_match", 0.0)),
            avg_coverage=float(d.get("avg_coverage", 0.0)),
            top_symbol=d.get("top_symbol"),
            top_pmci=float(d.get("top_pmci", 0.0)),
        )
