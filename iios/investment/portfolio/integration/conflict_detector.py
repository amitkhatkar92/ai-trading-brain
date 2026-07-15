"""iios/investment/portfolio/integration/conflict_detector.py

Detects cross-engine conflicts in merged portfolio intelligence.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.integration_types import (
    ConflictSeverity, now_utc,
)


@dataclass(frozen=True)
class DetectedConflict:
    conflict_id:    str
    portfolio_id:   str
    detected_at:    str
    severity:       ConflictSeverity
    engine_pair:    str
    conflict_type:  str
    description:    str
    engine_a_value: Optional[str] = None
    engine_b_value: Optional[str] = None
    is_resolved:    bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":  self.conflict_id,
            "severity":     self.severity.value,
            "engine_pair":  self.engine_pair,
            "type":         self.conflict_type,
            "description":  self.description,
            "is_resolved":  self.is_resolved,
        }


class ConflictDetector:
    """Detects conflicts between engine contributions in merged data."""

    def detect(
        self,
        merged:       Dict[str, Any],
        portfolio_id: str = "",
    ) -> List[DetectedConflict]:
        conflicts: List[DetectedConflict] = []

        constr = merged.get("construction",    {})
        alloc  = merged.get("allocation",      {})
        optim  = merged.get("optimization",    {})
        risk   = merged.get("risk",            {})
        perf   = merged.get("performance",     {})
        rebal  = merged.get("rebalancing",     {})
        rec    = merged.get("recommendation",  {})

        rb_util  = risk.get("risk_budget_utilization", 0.0)
        within   = risk.get("is_risk_within_budget",   True)
        var_util = risk.get("var_utilization",         0.0)
        action   = rec.get("primary_action",           "no_action")
        at_front = optim.get("is_at_efficient_frontier", False)
        c_qual   = constr.get("construction_quality",  1.0)
        rebal_r  = rebal.get("rebalance_recommended",  False)
        eq_drift = abs(alloc.get("equity_drift",       0.0))
        sharpe   = perf.get("sharpe_ratio",            0.0)

        # Conflict 1: is_risk_within_budget=True yet utilization >95%
        if within and rb_util > 0.95:
            conflicts.append(DetectedConflict(
                conflict_id    = str(uuid.uuid4()),
                portfolio_id   = portfolio_id,
                detected_at    = now_utc(),
                severity       = ConflictSeverity.HIGH,
                engine_pair    = "risk",
                conflict_type  = "internal_inconsistency",
                description    = (
                    f"is_risk_within_budget=True but risk_budget_utilization="
                    f"{rb_util:.1%} (>95%)"
                ),
                engine_a_value = f"within_budget={within}",
                engine_b_value = f"utilization={rb_util:.1%}",
            ))

        # Conflict 2: Aggressive recommendation with near-limit risk budget
        if action == "aggressive_positioning" and rb_util > 0.88:
            conflicts.append(DetectedConflict(
                conflict_id    = str(uuid.uuid4()),
                portfolio_id   = portfolio_id,
                detected_at    = now_utc(),
                severity       = ConflictSeverity.CRITICAL,
                engine_pair    = "risk:recommendation",
                conflict_type  = "direction_conflict",
                description    = (
                    f"Aggressive positioning recommended while risk budget "
                    f"is {rb_util:.1%}"
                ),
                engine_a_value = f"risk_budget={rb_util:.1%}",
                engine_b_value = f"recommendation={action}",
            ))

        # Conflict 3: Rebalancing recommended but equity drift negligible
        if rebal_r and eq_drift < 0.01:
            conflicts.append(DetectedConflict(
                conflict_id    = str(uuid.uuid4()),
                portfolio_id   = portfolio_id,
                detected_at    = now_utc(),
                severity       = ConflictSeverity.MEDIUM,
                engine_pair    = "allocation:rebalancing",
                conflict_type  = "direction_conflict",
                description    = (
                    f"Rebalancing recommended but equity drift is only {eq_drift:.2%}"
                ),
                engine_a_value = f"rebalance_recommended={rebal_r}",
                engine_b_value = f"equity_drift={eq_drift:.2%}",
            ))

        # Conflict 4: Optimization claims efficient frontier with low construction quality
        if at_front and c_qual < 0.40:
            conflicts.append(DetectedConflict(
                conflict_id    = str(uuid.uuid4()),
                portfolio_id   = portfolio_id,
                detected_at    = now_utc(),
                severity       = ConflictSeverity.HIGH,
                engine_pair    = "construction:optimization",
                conflict_type  = "value_mismatch",
                description    = (
                    f"Optimization claims efficient frontier but construction quality "
                    f"is {c_qual:.2f}"
                ),
                engine_a_value = f"construction_quality={c_qual:.2f}",
                engine_b_value = f"at_frontier={at_front}",
            ))

        # Conflict 5: Excellent Sharpe combined with extreme VaR utilization
        if sharpe > 1.5 and var_util > 0.90:
            conflicts.append(DetectedConflict(
                conflict_id    = str(uuid.uuid4()),
                portfolio_id   = portfolio_id,
                detected_at    = now_utc(),
                severity       = ConflictSeverity.MEDIUM,
                engine_pair    = "performance:risk",
                conflict_type  = "value_mismatch",
                description    = (
                    f"Excellent Sharpe {sharpe:.2f} combined with very high VaR "
                    f"utilization {var_util:.1%}"
                ),
                engine_a_value = f"sharpe={sharpe:.2f}",
                engine_b_value = f"var_util={var_util:.1%}",
            ))

        return conflicts
