"""
risk_mitigation_engine.py — iios.risk.assessment
==================================================
Risk mitigation recommendation engine.

Analyses identified risk drivers and produces actionable mitigation
recommendations ranked by priority and estimated impact.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import MITIGATION_TRIGGERS, VERSION
from .exceptions import RiskMitigationError
from .risk_assessment_response import MitigationAction, MitigationPlan


class RiskMitigationEngine:
    """
    Risk mitigation planning engine.

    Pattern-based recommendation system: maps risk drivers identified
    during assessment to concrete mitigation actions.

    No policy evaluation.  No trade execution.
    """

    VERSION: str = VERSION

    # Thresholds that trigger mitigation recommendations
    _VAR_THRESHOLD:     float = 0.05   # VaR > 5% of portfolio
    _ES_THRESHOLD:      float = 0.08   # ES > 8%
    _DRAWDOWN_THRESHOLD: float = 0.15  # Drawdown > 15%
    _HHI_THRESHOLD:     float = 0.25   # HHI > 0.25 (≈ less than 4 effective positions)
    _CONCENTRATION_THRESHOLD: float = 0.30  # Single position > 30%
    _VOL_THRESHOLD:     float = 0.30   # Annualised vol > 30%
    _STRESS_THRESHOLD:  float = 0.20   # Stress loss > 20%
    _LIMIT_THRESHOLD:   float = 0.90   # Limit utilisation > 90%

    # ------------------------------------------------------------------
    # Identify risk drivers
    # ------------------------------------------------------------------

    def identify_drivers(
        self,
        var_pct:             float = 0.0,
        es_pct:              float = 0.0,
        max_drawdown:        float = 0.0,
        hhi:                 float = 0.0,
        top_position_weight: float = 0.0,
        annual_volatility:   float = 0.0,
        worst_stress_pct:    float = 0.0,
        max_limit_util:      float = 0.0,
    ) -> List[str]:
        """
        Identify active risk drivers based on current metrics.

        Returns a list of driver keys from
        :data:`~.constants.MITIGATION_TRIGGERS`.
        """
        drivers = []
        if top_position_weight > self._CONCENTRATION_THRESHOLD:
            drivers.append("concentration_high")
        elif hhi > self._HHI_THRESHOLD:
            drivers.append("concentration_high")
        if var_pct > self._VAR_THRESHOLD:
            drivers.append("var_high")
        if es_pct > self._ES_THRESHOLD:
            drivers.append("es_high")
        if max_drawdown > self._DRAWDOWN_THRESHOLD:
            drivers.append("drawdown_high")
        if max_limit_util >= self._LIMIT_THRESHOLD:
            drivers.append("limit_breach")
        if annual_volatility > self._VOL_THRESHOLD:
            drivers.append("volatility_high")
        if worst_stress_pct > self._STRESS_THRESHOLD:
            drivers.append("stress_loss_high")
        return drivers

    # ------------------------------------------------------------------
    # Build action for a driver
    # ------------------------------------------------------------------

    def _build_action(
        self,
        driver:       str,
        current_risk: float,
    ) -> MitigationAction:
        description   = MITIGATION_TRIGGERS.get(driver, f"Investigate risk driver: {driver}")
        priority      = "high" if driver in ("limit_breach", "es_high", "var_high") else "medium"
        # Estimated impact: high-priority actions score 10pts, medium 5pts
        impact_score  = 10.0 if priority == "high" else 5.0
        return MitigationAction(
            action_id    = str(uuid.uuid4()),
            trigger      = driver,
            description  = description,
            priority     = priority,
            impact_score = impact_score,
        )

    # ------------------------------------------------------------------
    # Generate mitigation plan
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        assessment_id: str,
        portfolio_id:  str,
        risk_score:    float,
        drivers:       Optional[List[str]] = None,
        var_pct:             float = 0.0,
        es_pct:              float = 0.0,
        max_drawdown:        float = 0.0,
        hhi:                 float = 0.0,
        top_position_weight: float = 0.0,
        annual_volatility:   float = 0.0,
        worst_stress_pct:    float = 0.0,
        max_limit_util:      float = 0.0,
    ) -> MitigationPlan:
        """
        Generate a complete :class:`~.risk_assessment_response.MitigationPlan`.

        If ``drivers`` is ``None``, they are automatically identified from
        the provided metric arguments.
        """
        if drivers is None:
            drivers = self.identify_drivers(
                var_pct             = var_pct,
                es_pct              = es_pct,
                max_drawdown        = max_drawdown,
                hhi                 = hhi,
                top_position_weight = top_position_weight,
                annual_volatility   = annual_volatility,
                worst_stress_pct    = worst_stress_pct,
                max_limit_util      = max_limit_util,
            )

        actions = [self._build_action(d, risk_score) for d in drivers]

        return MitigationPlan.create(
            assessment_id     = assessment_id,
            portfolio_id      = portfolio_id,
            actions           = actions,
            risk_score_before = risk_score,
        )
