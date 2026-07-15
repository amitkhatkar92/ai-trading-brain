"""iios/investment/portfolio/integration/portfolio_summary.py

Human-readable summary and state flags derived from a PortfolioIntelligenceSnapshot.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from iios.investment.portfolio.integration.integration_types import (
    HealthStatus, now_utc,
)
from iios.investment.portfolio.integration.portfolio_snapshot import (
    PortfolioIntelligenceSnapshot,
)


@dataclass(frozen=True)
class PortfolioState:
    """Boolean flag summary of the current portfolio state."""
    portfolio_id:              str         = ""
    is_diversified:            bool        = False
    is_risk_within_budget:     bool        = True
    is_construction_sound:     bool        = False
    is_optimized:              bool        = False
    is_rebalance_needed:       bool        = False
    has_active_recommendation: bool        = False
    is_consistent:             bool        = True
    is_ready:                  bool        = False
    health_status:             HealthStatus = HealthStatus.DEGRADED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":               self.portfolio_id,
            "is_diversified":             self.is_diversified,
            "is_risk_within_budget":      self.is_risk_within_budget,
            "is_construction_sound":      self.is_construction_sound,
            "is_optimized":               self.is_optimized,
            "is_rebalance_needed":        self.is_rebalance_needed,
            "has_active_recommendation":  self.has_active_recommendation,
            "is_consistent":              self.is_consistent,
            "is_ready":                   self.is_ready,
            "health_status":              self.health_status.value,
        }


@dataclass(frozen=True)
class PortfolioSummary:
    """Narrative summary of a portfolio intelligence snapshot."""
    summary_id:        str              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str              = ""
    generated_at:      str              = field(default_factory=now_utc)
    headline:          str              = ""
    quality_narrative: str              = ""
    risk_narrative:    str              = ""
    action_narrative:  str              = ""
    warnings:          Tuple[str, ...]  = field(default_factory=tuple)
    highlights:        Tuple[str, ...]  = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline":            self.headline,
            "quality_narrative":   self.quality_narrative,
            "risk_narrative":      self.risk_narrative,
            "action_narrative":    self.action_narrative,
            "warnings":            list(self.warnings),
            "highlights":          list(self.highlights),
        }


def build_state(snap: PortfolioIntelligenceSnapshot) -> PortfolioState:
    """Derive PortfolioState flags from a snapshot."""
    is_diversified = snap.hhi < 0.25 and snap.effective_positions >= 5.0
    health = HealthStatus.HEALTHY if snap.is_ready else HealthStatus.DEGRADED
    return PortfolioState(
        portfolio_id              = snap.portfolio_id,
        is_diversified            = is_diversified,
        is_risk_within_budget     = snap.is_risk_within_budget,
        is_construction_sound     = snap.construction_quality >= 0.60,
        is_optimized              = snap.optimization_quality >= 0.60,
        is_rebalance_needed       = snap.rebalance_recommended,
        has_active_recommendation = snap.primary_action != "no_action",
        is_consistent             = snap.is_consistent,
        is_ready                  = snap.is_ready,
        health_status             = health,
    )


def build_summary(snap: PortfolioIntelligenceSnapshot) -> PortfolioSummary:
    """Build a narrative summary from a snapshot."""
    warnings:   list = []
    highlights: list = []

    # Quality narrative
    qs = snap.quality_score
    if qs >= 0.85:
        quality_narrative = f"Portfolio intelligence is high quality (score {qs:.2f})."
        highlights.append("High-quality intelligence")
    elif qs >= 0.70:
        quality_narrative = f"Portfolio intelligence quality is acceptable (score {qs:.2f})."
    else:
        quality_narrative = f"Portfolio intelligence quality is insufficient (score {qs:.2f})."
        warnings.append(f"Intelligence quality below threshold: {qs:.2f}")

    # Risk narrative
    rb = snap.risk_budget_utilization
    if rb > 0.90:
        risk_narrative = f"Risk budget critically utilized at {rb:.1%}."
        warnings.append("Risk budget near limit")
    elif rb > 0.75:
        risk_narrative = f"Risk budget elevated at {rb:.1%} — monitor closely."
    else:
        risk_narrative = f"Risk budget {rb:.1%} within normal range."
        if rb < 0.50:
            highlights.append("Risk within budget")

    # Action narrative
    act = snap.primary_action
    if act == "no_action":
        action_narrative = "No portfolio action required at this time."
    elif act == "rebalance_portfolio":
        action_narrative = "Portfolio rebalancing is recommended."
    else:
        action_narrative = f"Recommended action: {act.replace('_', ' ').title()}."

    if snap.n_unresolved_conflicts > 0:
        warnings.append(f"{snap.n_unresolved_conflicts} unresolved intelligence conflict(s)")

    # Headline
    if snap.is_ready:
        headline = (
            f"Portfolio intelligence ready — "
            f"quality {snap.quality_grade.value}, action: {act}"
        )
    else:
        headline = (
            f"Portfolio intelligence not ready — "
            f"completeness {snap.completeness:.0%}"
        )

    return PortfolioSummary(
        portfolio_id       = snap.portfolio_id,
        headline           = headline,
        quality_narrative  = quality_narrative,
        risk_narrative     = risk_narrative,
        action_narrative   = action_narrative,
        warnings           = tuple(warnings),
        highlights         = tuple(highlights),
    )
