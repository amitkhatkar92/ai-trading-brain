"""
risk_stress_testing_engine.py — iios.risk.assessment
======================================================
Stress testing engine — applies deterministic shocks to portfolio value.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .constants import STRESS_SHOCK_PARAMS, StressScenario, VERSION
from .exceptions import RiskStressTestError
from .risk_assessment_response import StressScenarioResult, StressTestReport


class RiskStressTestingEngine:
    """
    Stress testing engine.

    Applies pre-defined or custom shock parameters to a portfolio value
    to compute stressed losses.  All computations are deterministic.

    No policy evaluation, no trade execution.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Single scenario
    # ------------------------------------------------------------------

    def run_scenario(
        self,
        scenario:        StressScenario,
        portfolio_value: float,
        custom_shock:    Optional[float] = None,
    ) -> StressScenarioResult:
        """
        Apply a stress scenario to the portfolio.

        Parameters
        ----------
        scenario :
            Pre-defined stress scenario.
        portfolio_value :
            Current portfolio market value.
        custom_shock :
            Override equity shock for :attr:`~.constants.StressScenario.CUSTOM`.

        Returns
        -------
        StressScenarioResult
        """
        if portfolio_value <= 0:
            raise RiskStressTestError(
                f"Portfolio value must be positive, got {portfolio_value}",
                scenario=scenario.value,
            )

        params = dict(STRESS_SHOCK_PARAMS.get(scenario, {}))

        if scenario == StressScenario.CUSTOM and custom_shock is not None:
            params["equity_shock"] = custom_shock

        equity_shock = params.get("equity_shock", 0.0)
        stressed_value = portfolio_value * (1.0 + equity_shock)
        stressed_loss  = portfolio_value - stressed_value
        pct            = stressed_loss / portfolio_value if portfolio_value > 0 else 0.0

        return StressScenarioResult(
            scenario          = scenario,
            stressed_loss     = max(0.0, stressed_loss),
            stressed_loss_pct = max(0.0, pct),
            stressed_value    = stressed_value,
            shock_params      = {k: float(v) for k, v in params.items()},
        )

    # ------------------------------------------------------------------
    # All pre-defined scenarios
    # ------------------------------------------------------------------

    def run_all_scenarios(
        self,
        portfolio_value: float,
    ) -> List[StressScenarioResult]:
        """Run all pre-defined stress scenarios and return results."""
        results = []
        for scenario in StressScenario:
            try:
                result = self.run_scenario(scenario, portfolio_value)
                results.append(result)
            except RiskStressTestError:
                pass
        return results

    # ------------------------------------------------------------------
    # Selected scenarios
    # ------------------------------------------------------------------

    def run_selected_scenarios(
        self,
        portfolio_value: float,
        scenarios:       List[StressScenario],
    ) -> List[StressScenarioResult]:
        """Run the specified subset of stress scenarios."""
        return [self.run_scenario(s, portfolio_value) for s in scenarios]

    # ------------------------------------------------------------------
    # Full report builder
    # ------------------------------------------------------------------

    def build_stress_test_report(
        self,
        assessment_id:   str,
        portfolio_id:    str,
        portfolio_value: float,
        scenarios:       Optional[List[StressScenario]] = None,
    ) -> StressTestReport:
        """Build a complete :class:`~.risk_assessment_response.StressTestReport`."""
        if scenarios:
            results = self.run_selected_scenarios(portfolio_value, scenarios)
        else:
            results = self.run_all_scenarios(portfolio_value)

        return StressTestReport.create(
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            portfolio_value = portfolio_value,
            scenarios       = results,
        )
