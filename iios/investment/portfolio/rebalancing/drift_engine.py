"""iios/investment/portfolio/rebalancing/drift_engine.py

Drift engine: orchestrates all drift analyses into a unified DriftReport.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.allocation_drift import (
    AllocationDrift, compute_allocation_drift,
)
from iios.investment.portfolio.rebalancing.exposure_drift import (
    ExposureDrift, compute_exposure_drift,
)
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, DriftLevel, TargetPosition,
    aggregate_drift_level, now_utc,
)
from iios.investment.portfolio.rebalancing.risk_drift import (
    RiskDrift, compute_risk_drift,
)


@dataclass(frozen=True)
class DriftReport:
    """Unified drift report combining all drift dimensions."""

    report_id:          str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str             = ""
    created_at:         str             = field(default_factory=now_utc)

    allocation:         Optional[AllocationDrift]  = None
    risk:               Optional[RiskDrift]        = None
    exposure:           Optional[ExposureDrift]    = None

    # Aggregate
    overall_drift_level:DriftLevel      = DriftLevel.NONE
    rebalance_required: bool            = False
    urgency_score:      float           = 0.0   # [0, 1] — higher = more urgent
    primary_driver:     str             = ""    # which dimension drives drift

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "overall_drift_level": self.overall_drift_level.value,
            "rebalance_required":  self.rebalance_required,
            "urgency_score":       round(self.urgency_score, 4),
            "primary_driver":      self.primary_driver,
        }
        if self.allocation:
            d["allocation"] = self.allocation.to_dict()
        if self.risk:
            d["risk"] = self.risk.to_dict()
        return d


class DriftEngine:
    """Orchestrates drift analysis across allocation, risk, and exposure dimensions."""

    def analyze(
        self,
        current:      List[CurrentPosition],
        target:       List[TargetPosition],
        portfolio_id: str = "",
    ) -> DriftReport:
        alloc_drift   = compute_allocation_drift(current, target, portfolio_id)
        risk_drift    = compute_risk_drift(current, target, portfolio_id)
        exposure_drift= compute_exposure_drift(current, target, portfolio_id)

        # Determine overall level (max across dimensions)
        levels = [
            alloc_drift.drift_level,
            risk_drift.drift_level,
            exposure_drift.overall_drift_level,
        ]
        overall = aggregate_drift_level(levels)

        rebalance_required = alloc_drift.rebalance_recommended or risk_drift.requires_rebalance

        urgency = _compute_urgency(overall, alloc_drift)

        primary = _identify_primary_driver(alloc_drift, risk_drift, exposure_drift)

        return DriftReport(
            portfolio_id       = portfolio_id,
            allocation         = alloc_drift,
            risk               = risk_drift,
            exposure           = exposure_drift,
            overall_drift_level= overall,
            rebalance_required = rebalance_required,
            urgency_score      = round(urgency, 4),
            primary_driver     = primary,
        )


def _compute_urgency(level: DriftLevel, alloc: AllocationDrift) -> float:
    """Compute urgency score [0, 1] from drift level and number of drifted positions."""
    level_scores = {
        DriftLevel.NONE:       0.0,
        DriftLevel.MINOR:      0.2,
        DriftLevel.MODERATE:   0.5,
        DriftLevel.SIGNIFICANT:0.75,
        DriftLevel.CRITICAL:   1.0,
    }
    base = level_scores.get(level, 0.0)
    # Scale up slightly if many positions require rebalancing
    n_factor = min(1.0, alloc.n_requires_rebalance / max(alloc.n_positions_current, 1))
    return min(1.0, base * 0.8 + n_factor * 0.2)


def _identify_primary_driver(
    alloc:    AllocationDrift,
    risk:     RiskDrift,
    exposure: ExposureDrift,
) -> str:
    drivers = [
        ("allocation", alloc.max_abs_drift),
        ("sector",     exposure.max_sector_drift),
        ("risk",       risk.abs_risk_drift * 0.5),  # normalize
        ("country",    exposure.max_country_drift),
    ]
    if not drivers:
        return "none"
    return max(drivers, key=lambda x: x[1])[0]
