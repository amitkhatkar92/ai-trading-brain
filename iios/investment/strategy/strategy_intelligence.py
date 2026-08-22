"""iios/investment/strategy/strategy_intelligence.py
Top-level intelligence product published by the Strategy Intelligence Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import (
    RegimeCompatibility,
    StrategyCategory,
    StrategyGrade,
    StrategyRecommendation,
    StrategyStatus,
)
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_tracker import StrategyStatistics


@dataclass
class StrategyIntelligence:
    """
    Comprehensive intelligence report for a single strategy.

    Produced by StrategyManager.analyze() and consumed by higher IIOS layers
    (Decision, Investment, Portfolio).

    It is NOT a trading signal — it describes the state and quality of a
    strategy for intelligence and decision-making purposes only.
    """

    intelligence_id:      str                   = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:          str                   = ""
    strategy_name:        str                   = ""
    version:              str                   = "1.0.0"
    request_id:           str                   = ""

    # Classification
    category:             StrategyCategory      = StrategyCategory.UNKNOWN
    status:               StrategyStatus        = StrategyStatus.UNKNOWN

    # Evaluation results
    score:                StrategyScore         = field(default_factory=StrategyScore)
    statistics:           StrategyStatistics    = field(default_factory=StrategyStatistics)

    # Market fit
    regime_compatibility: RegimeCompatibility   = RegimeCompatibility.UNKNOWN
    preferred_regimes:    list[str]             = field(default_factory=list)
    active_regime:        str                   = ""

    # Intelligence products (no duplicates enforced)
    strengths:            list[str]             = field(default_factory=list)
    weaknesses:           list[str]             = field(default_factory=list)
    opportunities:        list[str]             = field(default_factory=list)
    risks:                list[str]             = field(default_factory=list)
    observations:         list[str]             = field(default_factory=list)

    # Recommendation
    recommendation:       StrategyRecommendation = StrategyRecommendation.UNKNOWN
    grade:                StrategyGrade          = StrategyGrade.UNKNOWN
    confidence:           float                  = 0.0   # 0–1

    metadata:             dict[str, Any]         = field(default_factory=dict)
    created_at:           float                  = field(default_factory=time.time)
    duration_ms:          float                  = 0.0

    # ── mutation helpers ──────────────────────────────────────────────────────

    def add_strength(self, desc: str) -> None:
        if desc and desc not in self.strengths:
            self.strengths.append(desc)

    def add_weakness(self, desc: str) -> None:
        if desc and desc not in self.weaknesses:
            self.weaknesses.append(desc)

    def add_opportunity(self, desc: str) -> None:
        if desc and desc not in self.opportunities:
            self.opportunities.append(desc)

    def add_risk(self, desc: str) -> None:
        if desc and desc not in self.risks:
            self.risks.append(desc)

    def add_observation(self, obs: str) -> None:
        if obs and obs not in self.observations:
            self.observations.append(obs)

    # ── derived properties ────────────────────────────────────────────────────

    @property
    def is_above_threshold(self) -> bool:
        return self.score.is_above_threshold

    @property
    def is_active(self) -> bool:
        return self.status in (StrategyStatus.APPROVED, StrategyStatus.PRODUCTION)

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "intelligence_id":    self.intelligence_id,
            "strategy_id":        self.strategy_id,
            "strategy_name":      self.strategy_name,
            "version":            self.version,
            "request_id":         self.request_id,
            "category":           self.category.value,
            "status":             self.status.value,
            "score":              self.score.to_dict(),
            "statistics":         self.statistics.to_dict(),
            "regime_compatibility": self.regime_compatibility.value,
            "preferred_regimes":  self.preferred_regimes,
            "active_regime":      self.active_regime,
            "strengths":          self.strengths,
            "weaknesses":         self.weaknesses,
            "opportunities":      self.opportunities,
            "risks":              self.risks,
            "observations":       self.observations,
            "recommendation":     self.recommendation.value,
            "grade":              self.grade.value,
            "confidence":         self.confidence,
            "is_above_threshold": self.is_above_threshold,
            "is_active":          self.is_active,
            "metadata":           self.metadata,
            "created_at":         self.created_at,
            "duration_ms":        self.duration_ms,
        }
