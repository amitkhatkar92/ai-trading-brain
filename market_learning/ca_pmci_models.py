"""
ca_pmci_models.py — Typed models for the MLS CAPMCIEngine.

MLS Phase 5B.

Pure data.  No business logic.  All fields JSON-serialisable.
CA-PMCI = Context-Aware Pre-Movement Consensus Intelligence.

CA-PMCI is read-only.  It never modifies DNA, ARS, strategy, thresholds,
or any persistent store.  It never executes or recommends trades.
It adjusts PMCI evidence scores using current market context only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from market_learning.pmci_models import PMCIResult


# ─── exceptions ───────────────────────────────────────────────────────────────

class CAPMCIError(Exception):
    """Base exception for CAPMCIEngine errors."""


class CAPMCIInputError(CAPMCIError):
    """Invalid input supplied to CAPMCIEngine."""


# ─── context adjustment ───────────────────────────────────────────────────────

@dataclass
class ContextAdjustment:
    """
    One named context-driven adjustment to a raw PMCI score.

    Each adjustment is independently explained and traceable to its
    source values from PMCIResult and MarketContext.

    Five adjustments are computed per evaluation:
        regime_match      — DNA regime stability × regime context quality
        volatility_match  — DNA evidence strength × volatility context quality
        sector_match      — DNA sector stability × sector context quality
        context_stability — DNA evidence confidence × market context stability
        dna_freshness     — DNA recency × overall context quality
    """

    name:        str             # "regime_match" | "volatility_match" | "sector_match" | ...
    delta:       float           # signed adjustment value (positive = reward, negative = penalty)
    explanation: str             # one-line human-readable description including delta
    evidence:    Dict[str, Any]  # raw source values that produced this delta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "delta":       round(self.delta, 6),
            "explanation": self.explanation,
            "evidence":    self.evidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ContextAdjustment:
        return cls(
            name=d["name"],
            delta=float(d["delta"]),
            explanation=d["explanation"],
            evidence=d.get("evidence", {}),
        )


# ─── CA-PMCI result ───────────────────────────────────────────────────────────

@dataclass
class CAPMCIResult:
    """
    Context-Aware PMCI evaluation for one symbol on one trading date.

    ca_pmci ∈ [0, 1]:
        High score → stock closely resembles Winner DNA in the CURRENT market context.
        Low score  → stock shows few winner characteristics OR context is adverse.

    Computation:
        ca_pmci = clamp(raw_pmci + context_adjustment, 0.0, 1.0)

    Every adjustment is individually named and explained in the 'adjustments'
    list.  Full traceability from raw PMCI → context scores → final CA-PMCI.

    CA-PMCI is a similarity measure only.  It is NOT a trading signal.
    """

    result_id:       str   # "CAP-{sha256[:8]}" — deterministic per (symbol, date)
    symbol:          str
    evaluation_date: str   # ISO date

    # ── Raw PMCI (before context adjustment) ──────────────────────────────────
    raw_pmci:        float  # PMCIResult.pmci_score [0, 1]

    # ── Market context at evaluation time ─────────────────────────────────────
    context_score:   float  # MarketContext.context_score [0, 1]
    context_id:      str    # MarketContext.context_id ("MCE-...")
    regime:          str    # current market regime label

    # ── New context components (all [0, 1]) ───────────────────────────────────
    context_match_score:       float  # combined DNA×context alignment across 3 dimensions
    dna_context_stability:     float  # mean consistency across regime, sector, volatility
    dna_regime_match:          float  # DNA regime_consistency from PMCI
    dna_sector_match:          float  # DNA sector_consistency from PMCI
    dna_volatility_match:      float  # DNA evidence_strength (volatility resilience proxy)
    dna_freshness_weight:      float  # DNA recency from PMCI
    context_adjustment_factor: float  # [0, 1] normalized total adjustment (0.5 = neutral)

    # ── Five named context adjustments ────────────────────────────────────────
    adjustments:        List[ContextAdjustment]  # always exactly 5 items
    context_adjustment: float  # sum of deltas, clamped to ±ca_pmci_max_total_adj

    # ── Final output ──────────────────────────────────────────────────────────
    ca_pmci:     float  # clamp(raw_pmci + context_adjustment, 0.0, 1.0)
    confidence:  float  # blended PMCI + MCIE confidence [0, 1]
    explanation: str    # full narrative including every adjustment

    # ── Source references ─────────────────────────────────────────────────────
    pmci_result:   PMCIResult  # the original raw PMCIResult (preserved in full)
    library_id:    str
    feature_count: int
    evaluated_at:  str         # ISO datetime (wall-clock at evaluation time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":               self.result_id,
            "symbol":                  self.symbol,
            "evaluation_date":         self.evaluation_date,
            "raw_pmci":                round(self.raw_pmci, 6),
            "context_score":           round(self.context_score, 6),
            "context_id":              self.context_id,
            "regime":                  self.regime,
            "context_match_score":     round(self.context_match_score, 6),
            "dna_context_stability":   round(self.dna_context_stability, 6),
            "dna_regime_match":        round(self.dna_regime_match, 6),
            "dna_sector_match":        round(self.dna_sector_match, 6),
            "dna_volatility_match":    round(self.dna_volatility_match, 6),
            "dna_freshness_weight":    round(self.dna_freshness_weight, 6),
            "context_adjustment_factor": round(self.context_adjustment_factor, 6),
            "adjustments":             [a.to_dict() for a in self.adjustments],
            "context_adjustment":      round(self.context_adjustment, 6),
            "ca_pmci":                 round(self.ca_pmci, 6),
            "confidence":              round(self.confidence, 6),
            "explanation":             self.explanation,
            "pmci_result":             self.pmci_result.to_dict(),
            "library_id":              self.library_id,
            "feature_count":           self.feature_count,
            "evaluated_at":            self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CAPMCIResult:
        return cls(
            result_id=d["result_id"],
            symbol=d["symbol"],
            evaluation_date=d["evaluation_date"],
            raw_pmci=float(d["raw_pmci"]),
            context_score=float(d["context_score"]),
            context_id=d["context_id"],
            regime=d["regime"],
            context_match_score=float(d["context_match_score"]),
            dna_context_stability=float(d["dna_context_stability"]),
            dna_regime_match=float(d["dna_regime_match"]),
            dna_sector_match=float(d["dna_sector_match"]),
            dna_volatility_match=float(d["dna_volatility_match"]),
            dna_freshness_weight=float(d["dna_freshness_weight"]),
            context_adjustment_factor=float(d["context_adjustment_factor"]),
            adjustments=[ContextAdjustment.from_dict(a) for a in d.get("adjustments", [])],
            context_adjustment=float(d["context_adjustment"]),
            ca_pmci=float(d["ca_pmci"]),
            confidence=float(d["confidence"]),
            explanation=d["explanation"],
            pmci_result=PMCIResult.from_dict(d["pmci_result"]),
            library_id=d["library_id"],
            feature_count=int(d["feature_count"]),
            evaluated_at=d["evaluated_at"],
        )


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class CAPMCIStatistics:
    """Aggregate statistics across a batch of CA-PMCI evaluations."""

    evaluation_date:        str
    total_symbols:          int
    avg_raw_pmci:           float   # mean of raw PMCI scores before adjustment
    avg_ca_pmci:            float   # mean of final CA-PMCI scores
    avg_context_adjustment: float   # mean of context_adjustment values
    avg_context_score:      float   # mean of MarketContext scores across evaluations
    high_ca_pmci_count:     int     # ca_pmci >= ca_pmci_high_threshold
    low_ca_pmci_count:      int     # ca_pmci <= ca_pmci_low_threshold
    top_symbol:             Optional[str]   # symbol with highest ca_pmci
    top_ca_pmci:            float
    most_improved_symbol:   Optional[str]   # symbol with largest positive context_adjustment
    most_degraded_symbol:   Optional[str]   # symbol with largest negative context_adjustment

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_date":        self.evaluation_date,
            "total_symbols":          self.total_symbols,
            "avg_raw_pmci":           round(self.avg_raw_pmci, 6),
            "avg_ca_pmci":            round(self.avg_ca_pmci, 6),
            "avg_context_adjustment": round(self.avg_context_adjustment, 6),
            "avg_context_score":      round(self.avg_context_score, 6),
            "high_ca_pmci_count":     self.high_ca_pmci_count,
            "low_ca_pmci_count":      self.low_ca_pmci_count,
            "top_symbol":             self.top_symbol,
            "top_ca_pmci":            round(self.top_ca_pmci, 6),
            "most_improved_symbol":   self.most_improved_symbol,
            "most_degraded_symbol":   self.most_degraded_symbol,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CAPMCIStatistics:
        return cls(
            evaluation_date=d.get("evaluation_date", ""),
            total_symbols=int(d.get("total_symbols", 0)),
            avg_raw_pmci=float(d.get("avg_raw_pmci", 0.0)),
            avg_ca_pmci=float(d.get("avg_ca_pmci", 0.0)),
            avg_context_adjustment=float(d.get("avg_context_adjustment", 0.0)),
            avg_context_score=float(d.get("avg_context_score", 0.0)),
            high_ca_pmci_count=int(d.get("high_ca_pmci_count", 0)),
            low_ca_pmci_count=int(d.get("low_ca_pmci_count", 0)),
            top_symbol=d.get("top_symbol"),
            top_ca_pmci=float(d.get("top_ca_pmci", 0.0)),
            most_improved_symbol=d.get("most_improved_symbol"),
            most_degraded_symbol=d.get("most_degraded_symbol"),
        )
