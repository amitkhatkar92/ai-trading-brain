"""iios/investment/portfolio/integration/portfolio_snapshot.py

PortfolioIntelligenceSnapshot — the canonical output of the integration engine.
Every downstream IIOS component must consume ONLY this type.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, QualityGrade, SnapshotStatus, now_utc,
)


@dataclass(frozen=True)
class PortfolioIntelligenceSnapshot:
    """
    Single canonical Portfolio Intelligence Snapshot.
    Produced by the integration engine after aggregation, validation,
    conflict resolution, and quality scoring.

    Downstream consumers must not bypass this type.
    """
    # ── Identity ───────────────────────────────────────────────────────────────
    snapshot_id:   str  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:  str  = ""
    version:       int  = 1
    created_at:    str  = field(default_factory=now_utc)
    published_at:  Optional[str] = None
    status:        SnapshotStatus = SnapshotStatus.DRAFT

    # ── Aggregation ────────────────────────────────────────────────────────────
    aggregation_status:    AggregationStatus = AggregationStatus.INVALID
    n_engines_contributed: int   = 0
    completeness:          float = 0.0
    freshness_score:       float = 0.0

    # ── Construction ──────────────────────────────────────────────────────────
    portfolio_name:        str   = ""
    portfolio_value:       float = 0.0
    n_positions:           int   = 0
    construction_quality:  float = 0.0

    # ── Allocation ────────────────────────────────────────────────────────────
    equity_weight:         float = 0.0
    bond_weight:           float = 0.0
    cash_weight:           float = 0.0
    alternative_weight:    float = 0.0
    international_weight:  float = 0.0
    equity_drift:          float = 0.0

    # ── Optimization ──────────────────────────────────────────────────────────
    optimization_quality:     float = 0.0
    is_at_efficient_frontier: bool  = False
    optimization_score:       float = 0.0

    # ── Diversification ───────────────────────────────────────────────────────
    hhi:                   float = 0.0
    effective_positions:   float = 0.0
    sector_concentration:  float = 0.0
    n_sectors:             int   = 0

    # ── Risk ──────────────────────────────────────────────────────────────────
    portfolio_risk_score:    float = 0.0
    risk_budget_utilization: float = 0.0
    var_utilization:         float = 0.0
    is_risk_within_budget:   bool  = True
    max_drawdown:            float = 0.0

    # ── Performance ───────────────────────────────────────────────────────────
    sharpe_ratio:          float = 0.0
    alpha:                 float = 0.0
    information_ratio:     float = 0.0
    ytd_return:            float = 0.0
    calmar_ratio:          float = 0.0

    # ── Rebalancing ───────────────────────────────────────────────────────────
    rebalance_recommended: bool  = False
    rebalance_score:       float = 0.0
    drift_level:           str   = "minor"

    # ── Recommendation ────────────────────────────────────────────────────────
    primary_action:              str   = "no_action"
    recommendation_priority:     str   = "informational"
    recommendation_score:        float = 0.0
    recommendation_confidence:   float = 0.0

    # ── Quality / Validation ──────────────────────────────────────────────────
    quality_score:            float       = 0.0
    quality_grade:            QualityGrade = QualityGrade.F
    consistency_score:        float       = 0.0
    confidence_score:         float       = 0.0
    n_conflicts:              int         = 0
    n_unresolved_conflicts:   int         = 0
    is_consistent:            bool        = True
    is_ready:                 bool        = False

    # ── Context ───────────────────────────────────────────────────────────────
    market_regime:  str = "unknown"
    macro_signal:   str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":             self.snapshot_id,
            "portfolio_id":            self.portfolio_id,
            "version":                 self.version,
            "created_at":              self.created_at,
            "status":                  self.status.value,
            "aggregation_status":      self.aggregation_status.value,
            "completeness":            round(self.completeness, 4),
            "freshness_score":         round(self.freshness_score, 4),
            "quality_score":           round(self.quality_score, 4),
            "quality_grade":           self.quality_grade.value,
            "consistency_score":       round(self.consistency_score, 4),
            "confidence_score":        round(self.confidence_score, 4),
            "n_conflicts":             self.n_conflicts,
            "n_unresolved_conflicts":  self.n_unresolved_conflicts,
            "is_consistent":           self.is_consistent,
            "is_ready":                self.is_ready,
            "primary_action":          self.primary_action,
            "equity_weight":           round(self.equity_weight, 4),
            "risk_budget_utilization": round(self.risk_budget_utilization, 4),
            "sharpe_ratio":            round(self.sharpe_ratio, 4),
            "max_drawdown":            round(self.max_drawdown, 4),
            "rebalance_recommended":   self.rebalance_recommended,
        }
