"""
risk_scenario_engine.py — iios.risk.assessment
================================================
Forward scenario analysis engine.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import statistics
from typing import List, Optional

from .constants import (
    SCENARIO_PROBABILITIES,
    SCENARIO_RETURN_MULTIPLIERS,
    ScenarioType,
    VERSION,
)
from .exceptions import RiskScenarioError
from .risk_assessment_response import ScenarioAnalysisReport, ScenarioOutcome


class RiskScenarioEngine:
    """
    Forward scenario analysis engine.

    Generates best-case, expected-case, worst-case, and black-swan
    scenario projections based on the portfolio's historical return
    statistics.  All computations are deterministic.

    No policy evaluation, no trade execution.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Single scenario projection
    # ------------------------------------------------------------------

    def project_scenario(
        self,
        scenario_type:   ScenarioType,
        portfolio_value: float,
        expected_return: float,
        volatility:      float,
        horizon_days:    int   = 1,
        custom_multiplier: Optional[float] = None,
    ) -> ScenarioOutcome:
        """
        Project portfolio outcome under a given scenario.

        Parameters
        ----------
        scenario_type :
            The scenario to project.
        portfolio_value :
            Current portfolio market value.
        expected_return :
            Daily expected return (fraction).
        volatility :
            Daily return volatility (fraction).
        horizon_days :
            Number of trading days in the projection horizon.
        custom_multiplier :
            Override return multiplier for CUSTOM / MULTI_FACTOR scenarios.

        Returns
        -------
        ScenarioOutcome
        """
        if portfolio_value <= 0:
            raise RiskScenarioError(
                f"Portfolio value must be positive, got {portfolio_value}",
                scenario_type=scenario_type.value,
            )

        multiplier  = (
            custom_multiplier
            if custom_multiplier is not None
            else SCENARIO_RETURN_MULTIPLIERS[scenario_type]
        )
        probability = SCENARIO_PROBABILITIES.get(scenario_type, 0.0)

        # Scale horizon (compound expected return, scale vol by sqrt(t))
        horizon_return = expected_return * horizon_days
        horizon_vol    = volatility * (horizon_days ** 0.5)

        projected_return_pct = horizon_return + multiplier * horizon_vol
        projected_return     = portfolio_value * projected_return_pct
        projected_value      = portfolio_value + projected_return
        risk_contribution    = abs(projected_return_pct) * (1.0 - probability)

        return ScenarioOutcome(
            scenario_type        = scenario_type,
            probability          = probability,
            projected_value      = projected_value,
            projected_return     = projected_return,
            projected_return_pct = projected_return_pct,
            risk_contribution    = risk_contribution,
        )

    # ------------------------------------------------------------------
    # All scenarios
    # ------------------------------------------------------------------

    def run_all_scenarios(
        self,
        portfolio_value: float,
        returns:         List[float],
        horizon_days:    int = 1,
    ) -> List[ScenarioOutcome]:
        """
        Run all standard scenario types.

        Uses historical mean and volatility to parameterise projections.
        Returns 0-outcome list when fewer than 2 returns are provided.
        """
        if len(returns) < 2:
            return []
        exp_return = statistics.mean(returns)
        vol        = statistics.stdev(returns)

        outcomes = []
        for stype in [
            ScenarioType.BEST_CASE,
            ScenarioType.EXPECTED_CASE,
            ScenarioType.WORST_CASE,
            ScenarioType.BLACK_SWAN,
        ]:
            outcome = self.project_scenario(
                stype, portfolio_value, exp_return, vol, horizon_days
            )
            outcomes.append(outcome)
        return outcomes

    # ------------------------------------------------------------------
    # Full report builder
    # ------------------------------------------------------------------

    def build_scenario_report(
        self,
        assessment_id:   str,
        portfolio_id:    str,
        portfolio_value: float,
        returns:         List[float],
        horizon_days:    int = 1,
    ) -> ScenarioAnalysisReport:
        """Build a complete :class:`~.risk_assessment_response.ScenarioAnalysisReport`."""
        if portfolio_value <= 0:
            raise RiskScenarioError(
                f"Portfolio value must be positive, got {portfolio_value}",
                scenario_type="all",
            )
        exp_return = statistics.mean(returns) if len(returns) >= 1 else 0.0
        outcomes   = self.run_all_scenarios(portfolio_value, returns, horizon_days)

        return ScenarioAnalysisReport.create(
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            portfolio_value = portfolio_value,
            expected_return = portfolio_value * exp_return,
            outcomes        = outcomes,
        )
