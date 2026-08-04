"""
mcie_models.py — Typed models for the MLS MCIEngine.

MLS Phase 5A.

Pure data.  No business logic.  All fields JSON-serialisable.
MCIE = Market Context Intelligence Engine.

MCIE is read-only.  It never modifies DNA, ARS, strategies, thresholds,
PMCI scores, or any persistent store.  It never executes or recommends trades.
It evaluates the market environment itself — not individual stocks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─── exceptions ───────────────────────────────────────────────────────────────

class MCIEError(Exception):
    """Base exception for MCIEngine errors."""


class MCIEInputError(MCIEError):
    """Invalid input supplied to MCIEngine."""


# ─── context component ────────────────────────────────────────────────────────

@dataclass
class ContextComponent:
    """Score and explanation for one named context dimension."""

    name:           str             # component identifier
    score:          float           # [0, 1] raw dimension score
    weight:         float           # configured weight in the context formula
    weighted_score: float           # score × weight — contribution to context_score
    confidence:     float           # reliability of this component [0, 1]
    explanation:    str             # one-line human-readable description
    evidence:       Dict[str, Any]  # raw inputs that drove this score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "score":          round(self.score, 6),
            "weight":         self.weight,
            "weighted_score": round(self.weighted_score, 6),
            "confidence":     round(self.confidence, 6),
            "explanation":    self.explanation,
            "evidence":       self.evidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ContextComponent:
        return cls(
            name=d["name"],
            score=float(d["score"]),
            weight=float(d["weight"]),
            weighted_score=float(d["weighted_score"]),
            confidence=float(d["confidence"]),
            explanation=d["explanation"],
            evidence=dict(d.get("evidence", {})),
        )


# ─── market context ───────────────────────────────────────────────────────────

@dataclass
class MarketContext:
    """
    Complete evaluation of the market environment at a point in time.

    Produced by MCIEngine.evaluate().  Read-only after construction.
    """

    context_id:      str                    # "MCE-{sha256[:8]}" — deterministic
    evaluation_date: str                    # ISO date
    evaluation_time: str                    # ISO datetime (from snapshot.timestamp)
    regime:          str                    # regime label at time of evaluation
    context_score:   float                  # [0, 1] — overall market context quality
    confidence:      float                  # [0, 1] — data richness
    stability:       float                  # [0, 1] — similarity to prior context
    freshness:       float                  # [0, 1] — always 1.0 (current snapshot)
    components:      List[ContextComponent] # exactly 8 items
    summary:         str                    # human-readable one-line summary
    raw_inputs:      Dict[str, Any]         # source values used in computation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":      self.context_id,
            "evaluation_date": self.evaluation_date,
            "evaluation_time": self.evaluation_time,
            "regime":          self.regime,
            "context_score":   round(self.context_score, 6),
            "confidence":      round(self.confidence, 6),
            "stability":       round(self.stability, 6),
            "freshness":       round(self.freshness, 6),
            "components":      [c.to_dict() for c in self.components],
            "summary":         self.summary,
            "raw_inputs":      self.raw_inputs,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MarketContext:
        return cls(
            context_id=d["context_id"],
            evaluation_date=d["evaluation_date"],
            evaluation_time=d["evaluation_time"],
            regime=d["regime"],
            context_score=float(d["context_score"]),
            confidence=float(d["confidence"]),
            stability=float(d["stability"]),
            freshness=float(d["freshness"]),
            components=[ContextComponent.from_dict(c) for c in d["components"]],
            summary=d["summary"],
            raw_inputs=dict(d.get("raw_inputs", {})),
        )


# ─── context history ──────────────────────────────────────────────────────────

@dataclass
class ContextHistory:
    """Ordered list of MarketContext evaluations (oldest first)."""

    contexts: List[MarketContext] = field(default_factory=list)

    def latest(self) -> Optional[MarketContext]:
        """Return most recent context, or None if history is empty."""
        return self.contexts[-1] if self.contexts else None

    def to_dict(self) -> Dict[str, Any]:
        return {"contexts": [c.to_dict() for c in self.contexts]}


# ─── context drift ────────────────────────────────────────────────────────────

@dataclass
class ContextDrift:
    """Measured change between two consecutive MarketContext evaluations."""

    from_date:           str        # ISO date of older context
    to_date:             str        # ISO date of newer context
    score_delta:         float      # context_score(new) − context_score(old)
    regime_changed:      bool       # True if regime label changed
    drifting_components: List[str]  # names of components that changed ≥ threshold
    drift_magnitude:     float      # mean absolute component delta [0, 1]
    explanation:         str        # human-readable drift summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_date":           self.from_date,
            "to_date":             self.to_date,
            "score_delta":         round(self.score_delta, 6),
            "regime_changed":      self.regime_changed,
            "drifting_components": self.drifting_components,
            "drift_magnitude":     round(self.drift_magnitude, 6),
            "explanation":         self.explanation,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ContextDrift:
        return cls(
            from_date=d["from_date"],
            to_date=d["to_date"],
            score_delta=float(d["score_delta"]),
            regime_changed=bool(d["regime_changed"]),
            drifting_components=list(d.get("drifting_components", [])),
            drift_magnitude=float(d["drift_magnitude"]),
            explanation=d["explanation"],
        )


# ─── context statistics ───────────────────────────────────────────────────────

@dataclass
class ContextStatistics:
    """Aggregate statistics over a batch of MarketContext evaluations."""

    evaluation_date:        str               # most recent evaluation date
    total_evaluations:      int
    avg_context_score:      float
    max_context_score:      float
    min_context_score:      float
    avg_confidence:         float
    avg_stability:          float
    most_volatile_component: str             # component with highest score range
    regime_distribution:    Dict[str, int]   # regime → count
    high_context_count:     int              # score ≥ high threshold
    low_context_count:      int              # score ≤ low threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_date":         self.evaluation_date,
            "total_evaluations":       self.total_evaluations,
            "avg_context_score":       round(self.avg_context_score, 6),
            "max_context_score":       round(self.max_context_score, 6),
            "min_context_score":       round(self.min_context_score, 6),
            "avg_confidence":          round(self.avg_confidence, 6),
            "avg_stability":           round(self.avg_stability, 6),
            "most_volatile_component": self.most_volatile_component,
            "regime_distribution":     self.regime_distribution,
            "high_context_count":      self.high_context_count,
            "low_context_count":       self.low_context_count,
        }
