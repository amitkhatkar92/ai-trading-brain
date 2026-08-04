"""
pig_models.py — Pure data models for the Platform Intelligence Gateway.

R-001 Phase 1: Platform Intelligence Gateway (PIG).

Pure data.  No business logic.  All fields JSON-serialisable.
PIG = Platform Intelligence Gateway — the ONLY public entry point
between the Trading Platform and the institutional intelligence stack.

PIG is read-only.  It never modifies DNA, PMCI, CDS, strategies,
or any persistent store.  It collects, aggregates, and normalises
intelligence from PMCI, CA-PMCI, CDS, MCIE, and IDR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---- exceptions --------------------------------------------------------------

class PlatformGatewayError(Exception):
    """Base exception for PlatformIntelligenceGateway errors."""


class PlatformGatewayInputError(PlatformGatewayError):
    """Invalid input supplied to PlatformIntelligenceGateway."""


class PlatformGatewaySymbolNotFoundError(PlatformGatewayError):
    """Requested symbol is not present in the provided DailyMarketSnapshot."""


# ---- platform evidence -------------------------------------------------------

@dataclass
class PlatformEvidence:
    """
    One traceable evidence item explaining a single PlatformIntelligence score.

    Every required output field in PlatformIntelligence is backed by at least
    one PlatformEvidence item naming the source engine, the component within
    that engine, and the raw inputs that drove the value.

    Consumers can audit any score by inspecting the evidence list.
    """

    source:      str             # "PMCI" | "CA-PMCI" | "CDS" | "IDR" | "MCIE"
    component:   str             # e.g. "winner_match", "regime_adjustment", "avg_cds"
    value:       float           # the score or metric value
    explanation: str             # one-line human-readable description
    raw:         Dict[str, Any]  # original values from source engine

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":      self.source,
            "component":   self.component,
            "value":       round(self.value, 6),
            "explanation": self.explanation,
            "raw":         self.raw,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlatformEvidence":
        return cls(
            source=d["source"],
            component=d["component"],
            value=float(d["value"]),
            explanation=d["explanation"],
            raw=d.get("raw", {}),
        )


# ---- confidence breakdown ----------------------------------------------------

@dataclass
class PlatformConfidence:
    """
    Confidence breakdown by source engine.

    overall = 0.40*pmci + 0.35*ca_pmci + 0.15*context + 0.10*institutional

    Each component confidence is independently sourced and explained.
    """

    overall:       float   # [0, 1] blended
    pmci:          float   # PMCIResult.confidence
    ca_pmci:       float   # CAPMCIResult.confidence
    context:       float   # MarketContext.confidence
    institutional: float   # IDR statistics avg_confidence
    explanation:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":       round(self.overall, 6),
            "pmci":          round(self.pmci, 6),
            "ca_pmci":       round(self.ca_pmci, 6),
            "context":       round(self.context, 6),
            "institutional": round(self.institutional, 6),
            "explanation":   self.explanation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlatformConfidence":
        return cls(
            overall=float(d["overall"]),
            pmci=float(d["pmci"]),
            ca_pmci=float(d["ca_pmci"]),
            context=float(d["context"]),
            institutional=float(d["institutional"]),
            explanation=d["explanation"],
        )


# ---- recommendation context --------------------------------------------------

@dataclass
class PlatformRecommendationContext:
    """
    Simplified, normalised intelligence context for trading module consumption.

    Hides all MLS engine details.  Trading modules should consume only this
    object, not raw PMCI/CDS/IDR results.

    Phase 2 will wire this into the trading decision path.
    """

    symbol:               str
    evaluation_date:      str
    regime:               str
    context_stability:    str   # ContextStabilityLabel value

    # Signal quality classification
    winner_alignment:     str   # "HIGH" (ca_pmci>=0.70) | "MEDIUM" (>=0.45) | "LOW"
    context_support:      str   # "STRONG" (context_score>=0.65) | "MODERATE" (>=0.35) | "WEAK"
    intelligence_quality: str   # "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT"

    # Key scores safe for trading module consumption
    raw_pmci:                float
    ca_pmci:                 float
    confidence:              float
    institutional_confidence: float

    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":                  self.symbol,
            "evaluation_date":         self.evaluation_date,
            "regime":                  self.regime,
            "context_stability":       self.context_stability,
            "winner_alignment":        self.winner_alignment,
            "context_support":         self.context_support,
            "intelligence_quality":    self.intelligence_quality,
            "raw_pmci":                round(self.raw_pmci, 6),
            "ca_pmci":                 round(self.ca_pmci, 6),
            "confidence":              round(self.confidence, 6),
            "institutional_confidence": round(self.institutional_confidence, 6),
            "explanation":             self.explanation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlatformRecommendationContext":
        return cls(
            symbol=d["symbol"],
            evaluation_date=d["evaluation_date"],
            regime=d["regime"],
            context_stability=d["context_stability"],
            winner_alignment=d["winner_alignment"],
            context_support=d["context_support"],
            intelligence_quality=d["intelligence_quality"],
            raw_pmci=float(d["raw_pmci"]),
            ca_pmci=float(d["ca_pmci"]),
            confidence=float(d["confidence"]),
            institutional_confidence=float(d["institutional_confidence"]),
            explanation=d["explanation"],
        )


# ---- platform intelligence ---------------------------------------------------

@dataclass
class PlatformIntelligence:
    """
    Aggregated platform intelligence for one symbol on one trading date.

    This is the primary output of the PlatformIntelligenceGateway.
    All continuous scores are [0, 1] unless otherwise noted.
    Every required output field is backed by at least one PlatformEvidence item.

    PlatformIntelligence is read-only after construction.
    It is NOT a trade signal.  It is normalised, explainable intelligence.
    """

    # ---- identity ------------------------------------------------------------
    result_id:       str     # "PIG-{sha256[:8]}" — deterministic per (symbol, date)
    symbol:          str
    evaluation_date: str     # ISO date
    evaluated_at:    str     # ISO datetime (wall clock)

    # ---- R-001 required output fields ----------------------------------------
    raw_pmci:               float   # PMCIResult.pmci_score
    ca_pmci:                float   # CAPMCIResult.ca_pmci
    cds_score:              float   # CDSLibraryResult statistics avg_cds
    winner_dna_match:       float   # PMCI "winner_match" component value
    loser_dna_match:        float   # PMCI "loser_match" component value
    evidence_count:         int     # matched DNA features in PMCI breakdown
    confidence:             float   # PlatformConfidence.overall
    dna_freshness:          float   # PMCI "dna_freshness" component value
    dna_drift:              float   # 1 - CAPMCIResult.dna_context_stability
    institutional_confidence: float # IDR statistics avg_confidence

    # ---- market context ------------------------------------------------------
    context_score:      float   # MarketContext.context_score
    regime:             str     # current market regime label
    context_adjustment: float   # CAPMCIResult.context_adjustment (signed delta)

    # ---- CDS summary ---------------------------------------------------------
    cds_highly_relevant_count: int
    cds_relevant_count:        int
    cds_total_dna:             int

    # ---- explainability ------------------------------------------------------
    evidence:               List["PlatformEvidence"]
    platform_confidence:    "PlatformConfidence"
    recommendation_context: "PlatformRecommendationContext"
    explanation:            str

    # ---- source results (for advanced consumers) -----------------------------
    pmci_result:    Any     # PMCIResult — for direct PMCI component access
    ca_pmci_result: Any     # CAPMCIResult — for named adjustment details
    market_context: Any     # MarketContext — for full context component detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":                  self.result_id,
            "symbol":                     self.symbol,
            "evaluation_date":            self.evaluation_date,
            "evaluated_at":               self.evaluated_at,
            "raw_pmci":                   round(self.raw_pmci, 6),
            "ca_pmci":                    round(self.ca_pmci, 6),
            "cds_score":                  round(self.cds_score, 6),
            "winner_dna_match":           round(self.winner_dna_match, 6),
            "loser_dna_match":            round(self.loser_dna_match, 6),
            "evidence_count":             self.evidence_count,
            "confidence":                 round(self.confidence, 6),
            "dna_freshness":              round(self.dna_freshness, 6),
            "dna_drift":                  round(self.dna_drift, 6),
            "institutional_confidence":   round(self.institutional_confidence, 6),
            "context_score":              round(self.context_score, 6),
            "regime":                     self.regime,
            "context_adjustment":         round(self.context_adjustment, 6),
            "cds_highly_relevant_count":  self.cds_highly_relevant_count,
            "cds_relevant_count":         self.cds_relevant_count,
            "cds_total_dna":              self.cds_total_dna,
            "evidence":                   [e.to_dict() for e in self.evidence],
            "platform_confidence":        self.platform_confidence.to_dict(),
            "recommendation_context":     self.recommendation_context.to_dict(),
            "explanation":                self.explanation,
        }


# ---- gateway statistics ------------------------------------------------------

@dataclass
class PlatformGatewayStatistics:
    """Aggregate statistics over a batch of PlatformIntelligence results."""

    evaluation_date:              str
    total_symbols:                int
    avg_raw_pmci:                 float
    avg_ca_pmci:                  float
    avg_confidence:               float
    avg_cds_score:                float
    avg_evidence_count:           float
    high_quality_count:           int    # ca_pmci >= pig_high_threshold
    low_quality_count:            int    # ca_pmci <= pig_low_threshold
    avg_institutional_confidence: float
    top_symbol:                   Optional[str]
    top_ca_pmci:                  float
    context_score:                float
    regime:                       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_date":              self.evaluation_date,
            "total_symbols":                self.total_symbols,
            "avg_raw_pmci":                 round(self.avg_raw_pmci, 6),
            "avg_ca_pmci":                  round(self.avg_ca_pmci, 6),
            "avg_confidence":               round(self.avg_confidence, 6),
            "avg_cds_score":                round(self.avg_cds_score, 6),
            "avg_evidence_count":           round(self.avg_evidence_count, 3),
            "high_quality_count":           self.high_quality_count,
            "low_quality_count":            self.low_quality_count,
            "avg_institutional_confidence": round(self.avg_institutional_confidence, 6),
            "top_symbol":                   self.top_symbol,
            "top_ca_pmci":                  round(self.top_ca_pmci, 6),
            "context_score":                round(self.context_score, 6),
            "regime":                       self.regime,
        }

    @classmethod
    def empty(cls) -> "PlatformGatewayStatistics":
        return cls(
            evaluation_date="",
            total_symbols=0,
            avg_raw_pmci=0.0, avg_ca_pmci=0.0, avg_confidence=0.0,
            avg_cds_score=0.0, avg_evidence_count=0.0,
            high_quality_count=0, low_quality_count=0,
            avg_institutional_confidence=0.0,
            top_symbol=None, top_ca_pmci=0.0,
            context_score=0.0, regime="unknown",
        )
