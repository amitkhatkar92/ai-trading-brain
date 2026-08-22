"""
risk_optimization_engine.py — iios.risk.assessment
====================================================
Risk optimization engine — identifies portfolio improvements to reduce risk.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_CONCENTRATION,
    OptimizationObjective,
    VERSION,
)
from .exceptions import RiskOptimizationError
from .risk_assessment_response import (
    OptimizationRecommendation,
    RiskOptimizationReport,
)


class RiskOptimizationEngine:
    """
    Risk optimization engine.

    Analyses the current portfolio risk profile and generates actionable
    recommendations to achieve the specified optimization objectives.

    All recommendations are analytical — no trades are executed.
    No policy evaluation.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Objective handlers
    # ------------------------------------------------------------------

    def _rec_minimize_concentration(
        self,
        hhi:            float,
        max_weight:     float,
        n_positions:    int,
    ) -> OptimizationRecommendation:
        target_hhi   = max(1.0 / max(n_positions, 1), hhi * 0.7)
        target_max_w = min(max_weight, DEFAULT_MAX_CONCENTRATION)
        improvement  = max(0.0, hhi - target_hhi)
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.MINIMIZE_CONCENTRATION,
            description = (
                f"Reduce top-position weight from {max_weight:.1%} to ≤ "
                f"{target_max_w:.1%}; target HHI {target_hhi:.3f}"
            ),
            current     = hhi,
            target      = target_hhi,
            improvement = improvement,
        )

    def _rec_minimize_portfolio_risk(
        self,
        var_pct:   float,
        risk_score: float,
    ) -> OptimizationRecommendation:
        target_var   = var_pct * 0.8   # 20% VaR reduction target
        improvement  = risk_score * 0.15
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.MINIMIZE_PORTFOLIO_RISK,
            description = (
                f"Reduce portfolio VaR from {var_pct:.1%} to target "
                f"{target_var:.1%} via diversification or hedges"
            ),
            current     = var_pct,
            target      = target_var,
            improvement = improvement,
        )

    def _rec_minimize_tail_risk(
        self,
        es_pct:   float,
        risk_score: float,
    ) -> OptimizationRecommendation:
        target_es   = es_pct * 0.75
        improvement = risk_score * 0.12
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.MINIMIZE_TAIL_RISK,
            description = (
                f"Reduce Expected Shortfall from {es_pct:.1%} to target "
                f"{target_es:.1%} with protective options or stop-losses"
            ),
            current     = es_pct,
            target      = target_es,
            improvement = improvement,
        )

    def _rec_optimize_capital(
        self,
        capital_utilisation: float,
    ) -> OptimizationRecommendation:
        target = min(0.85, capital_utilisation)
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.OPTIMIZE_CAPITAL_ALLOCATION,
            description = (
                f"Reallocate capital from low Sharpe strategies; "
                f"current utilisation {capital_utilisation:.1%}"
            ),
            current     = capital_utilisation,
            target      = target,
            improvement = max(0.0, capital_utilisation - target),
        )

    def _rec_optimize_liquidity(
        self,
        liquidity_score: float,
    ) -> OptimizationRecommendation:
        target = min(1.0, liquidity_score + 0.1)
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.OPTIMIZE_LIQUIDITY,
            description = (
                f"Increase liquidity score from {liquidity_score:.2f} to "
                f"{target:.2f} by reducing illiquid position allocation"
            ),
            current     = liquidity_score,
            target      = target,
            improvement = target - liquidity_score,
        )

    def _rec_improve_risk_adjusted(
        self,
        sharpe: float,
    ) -> OptimizationRecommendation:
        target = sharpe + 0.2
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.IMPROVE_RISK_ADJUSTED_PERFORMANCE,
            description = (
                f"Improve Sharpe ratio from {sharpe:.2f} to target {target:.2f} "
                "by adding high Sharpe strategies and trimming loss-makers"
            ),
            current     = sharpe,
            target      = target,
            improvement = 0.2,
        )

    def _rec_improve_stability(
        self,
        annual_vol: float,
    ) -> OptimizationRecommendation:
        target = annual_vol * 0.85
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.IMPROVE_PORTFOLIO_STABILITY,
            description = (
                f"Reduce annualised volatility from {annual_vol:.1%} to "
                f"{target:.1%} through lower-vol instrument substitution"
            ),
            current     = annual_vol,
            target      = target,
            improvement = annual_vol - target,
        )

    def _rec_optimize_exposure(
        self,
        gross_exposure_pct: float,
    ) -> OptimizationRecommendation:
        target = min(gross_exposure_pct, 1.5)
        return OptimizationRecommendation(
            rec_id      = str(uuid.uuid4()),
            objective   = OptimizationObjective.OPTIMIZE_EXPOSURE,
            description = (
                f"Reduce gross exposure from {gross_exposure_pct:.1%} "
                f"to target {target:.1%}"
            ),
            current     = gross_exposure_pct,
            target      = target,
            improvement = max(0.0, gross_exposure_pct - target),
        )

    # ------------------------------------------------------------------
    # Generate optimization report
    # ------------------------------------------------------------------

    def optimise(
        self,
        assessment_id:       str,
        portfolio_id:        str,
        risk_score:          float,
        objectives:          List[OptimizationObjective],
        *,
        hhi:                 float = 0.0,
        max_weight:          float = 0.0,
        n_positions:         int   = 1,
        var_pct:             float = 0.0,
        es_pct:              float = 0.0,
        capital_utilisation: float = 0.5,
        liquidity_score:     float = 0.5,
        sharpe:              float = 0.0,
        annual_vol:          float = 0.0,
        gross_exposure_pct:  float = 1.0,
    ) -> RiskOptimizationReport:
        """
        Run risk optimization for the given objectives.

        Returns a :class:`~.risk_assessment_response.RiskOptimizationReport`.
        """
        if not objectives:
            raise RiskOptimizationError("At least one optimization objective is required")

        recommendations: List[OptimizationRecommendation] = []

        for obj in objectives:
            if obj == OptimizationObjective.MINIMIZE_CONCENTRATION:
                recommendations.append(self._rec_minimize_concentration(hhi, max_weight, n_positions))
            elif obj == OptimizationObjective.MINIMIZE_PORTFOLIO_RISK:
                recommendations.append(self._rec_minimize_portfolio_risk(var_pct, risk_score))
            elif obj == OptimizationObjective.MINIMIZE_TAIL_RISK:
                recommendations.append(self._rec_minimize_tail_risk(es_pct, risk_score))
            elif obj == OptimizationObjective.OPTIMIZE_CAPITAL_ALLOCATION:
                recommendations.append(self._rec_optimize_capital(capital_utilisation))
            elif obj == OptimizationObjective.OPTIMIZE_LIQUIDITY:
                recommendations.append(self._rec_optimize_liquidity(liquidity_score))
            elif obj == OptimizationObjective.IMPROVE_RISK_ADJUSTED_PERFORMANCE:
                recommendations.append(self._rec_improve_risk_adjusted(sharpe))
            elif obj == OptimizationObjective.IMPROVE_PORTFOLIO_STABILITY:
                recommendations.append(self._rec_improve_stability(annual_vol))
            elif obj == OptimizationObjective.OPTIMIZE_EXPOSURE:
                recommendations.append(self._rec_optimize_exposure(gross_exposure_pct))

        total_improvement = sum(r.improvement for r in recommendations)
        risk_score_after  = max(0.0, risk_score - total_improvement)

        return RiskOptimizationReport.create(
            assessment_id     = assessment_id,
            portfolio_id      = portfolio_id,
            objectives        = objectives,
            recommendations   = recommendations,
            risk_score_before = risk_score,
            risk_score_after  = risk_score_after,
        )
