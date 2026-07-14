"""iios/investment/strategy/integration/strategy_summary.py
StrategySummary — high-level aggregated intelligence view for one strategy.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
)
from iios.investment.strategy.integration.integration_constants import IntelligenceSource


@dataclass(frozen=True)
class StrategySummary:
    """
    High-level narrative summary of all integrated strategy intelligence.
    One per strategy; produced after aggregation, validation, and conflict resolution.
    This is NOT a trading recommendation.
    """
    summary_id:             str
    strategy_id:            str
    overall_score:          float               # 0–100 composite intelligence score
    risk_level:             str                 # from risk source
    lifecycle_phase:        str                 # from lifecycle source
    evaluation_status:      str                 # from evaluation source
    opportunity_quality:    str                 # from opportunity source
    portfolio_utilisation:  str                 # from portfolio source
    learning_maturity:      str                 # from learning source
    migration_phase:        str                 # from migration source (or "not_started")
    debate_consensus:       str                 # from debate source (or "not_run")
    key_strengths:          Tuple[str, ...]
    key_risks:              Tuple[str, ...]
    intelligence_gaps:      Tuple[str, ...]     # missing or stale sources
    completeness:           float               # 0–1
    generated_at:           datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":            self.summary_id,
            "strategy_id":           self.strategy_id,
            "overall_score":         round(self.overall_score, 2),
            "risk_level":            self.risk_level,
            "lifecycle_phase":       self.lifecycle_phase,
            "evaluation_status":     self.evaluation_status,
            "opportunity_quality":   self.opportunity_quality,
            "portfolio_utilisation": self.portfolio_utilisation,
            "learning_maturity":     self.learning_maturity,
            "migration_phase":       self.migration_phase,
            "debate_consensus":      self.debate_consensus,
            "key_strengths":         list(self.key_strengths),
            "key_risks":             list(self.key_risks),
            "intelligence_gaps":     list(self.intelligence_gaps),
            "completeness":          round(self.completeness, 4),
            "generated_at":          self.generated_at.isoformat(),
        }


def build_strategy_summary(
    state:          StrategyAggregationState,
    overall_score:  float,
    completeness:   float,
    active_conflicts: int = 0,
) -> StrategySummary:
    latest = state.all_latest()

    def _get(src: IntelligenceSource, key: str, default: str = "unknown") -> str:
        upd = latest.get(src)
        return str(upd.payload.get(key, default)) if upd else default

    def _get_float(src: IntelligenceSource, key: str, default: float = 0.0) -> float:
        upd = latest.get(src)
        if not upd:
            return default
        try:
            return float(upd.payload.get(key, default))
        except (TypeError, ValueError):
            return default

    risk_level           = _get(IntelligenceSource.RISK,               "risk_level",    "unknown")
    lifecycle_phase      = _get(IntelligenceSource.LIFECYCLE,           "phase",         "unknown")
    eval_status          = _get(IntelligenceSource.EVALUATION,          "status",        "unknown")
    opp_quality          = _get(IntelligenceSource.OPPORTUNITY,         "quality",       "unknown")
    portfolio_util       = _get(IntelligenceSource.PORTFOLIO,           "utilisation",   "unknown")
    learning_maturity    = _get(IntelligenceSource.LEARNING,            "maturity",      "unknown")
    migration_phase      = _get(IntelligenceSource.MIGRATION,           "phase",         "not_started")
    debate_consensus     = _get(IntelligenceSource.DEBATE,              "consensus_level", "not_run")

    # Strengths from high-confidence sources
    strengths = []
    for src in [IntelligenceSource.EVALUATION, IntelligenceSource.LEARNING, IntelligenceSource.OPPORTUNITY]:
        upd = latest.get(src)
        if upd and upd.confidence >= 70:
            headline = str(upd.payload.get("headline", f"{src.display_name}: positive signal"))
            strengths.append(headline)

    # Risks from risk source and active conflicts
    risks = []
    risk_upd = latest.get(IntelligenceSource.RISK)
    if risk_upd:
        for flag in risk_upd.payload.get("risk_flags", [])[:3]:
            risks.append(str(flag))
    if active_conflicts > 0:
        risks.append(f"{active_conflicts} unresolved intelligence conflict(s) detected.")

    # Intelligence gaps
    all_sources  = list(IntelligenceSource)
    present_srcs = set(latest.keys())
    gaps = [s.display_name for s in all_sources if s not in present_srcs and s.is_required]

    return StrategySummary(
        summary_id=str(uuid.uuid4()),
        strategy_id=state.strategy_id,
        overall_score=round(overall_score, 2),
        risk_level=risk_level,
        lifecycle_phase=lifecycle_phase,
        evaluation_status=eval_status,
        opportunity_quality=opp_quality,
        portfolio_utilisation=portfolio_util,
        learning_maturity=learning_maturity,
        migration_phase=migration_phase,
        debate_consensus=debate_consensus,
        key_strengths=tuple(strengths[:5]),
        key_risks=tuple(risks[:5]),
        intelligence_gaps=tuple(gaps[:5]),
        completeness=round(completeness, 4),
        generated_at=datetime.now(timezone.utc),
    )
