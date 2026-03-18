"""
Validation Engine
=================
Institutional-grade multi-stage strategy validation pipeline.

Stages:
  1. IS / OOS Backtest         — BacktestEngine
  2. Walk-Forward Analysis     — WalkForwardAnalyzer
  3. Cross-Market Validation   — CrossMarketValidator
  4. Monte Carlo Simulation    — MonteCarloSimulator
  5. Parameter Sensitivity     — ParameterSensitivityAnalyzer
  6. Regime Robustness         — RegimeRobustnessTester

Usage::
    from validation_engine import ValidationEngine

    engine = ValidationEngine()
    report = engine.validate("MyStrategy", pnl_series, capital=1_000_000)
    report.print_report()
"""

from __future__ import annotations
import time
from typing import Optional

from utils import get_logger

from .backtest_engine        import BacktestEngine, BacktestResult
from .walkforward_test       import WalkForwardAnalyzer, WalkForwardResult
from .cross_market_test      import CrossMarketValidator, CrossMarketResult
from .monte_carlo_simulator  import MonteCarloSimulator, MonteCarloResult
from .parameter_sensitivity  import ParameterSensitivityAnalyzer, SensitivityResult, ParamGrid
from .regime_robustness_test import RegimeRobustnessTester, RegimeRobustnessResult
from .validation_report      import ValidationReport, ValidationReportBuilder

log = get_logger(__name__)

# Minimum trade history before we validate
MIN_TRADES_REQUIRED = 30


class ValidationEngine:
    """
    Orchestrates the full 6-stage validation pipeline.

    The pipeline runs sequentially and can stop early if a critical stage
    fails catastrophically (optional via `stop_on_critical_fail`).

    Usage::
        from validation_engine import ValidationEngine

        engine = ValidationEngine()
        report = engine.validate("ORB_Strategy", pnl_series, capital)
        report.print_report()
    """

    # Agents exposed for system agent count
    AGENTS = [
        "ValidationEngine",
        "BacktestEngine",
        "WalkForwardAnalyzer",
        "CrossMarketValidator",
        "MonteCarloSimulator",
        "ParameterSensitivityAnalyzer",
        "RegimeRobustnessTester",
        "ValidationReportBuilder",
    ]

    def __init__(self,
                 stop_on_critical_fail: bool = True,
                 n_mc_runs: int = 5_000) -> None:
        self._stop_on_crit = stop_on_critical_fail

        self._backtest    = BacktestEngine()
        self._walkforward = WalkForwardAnalyzer()
        self._cross_mkt   = CrossMarketValidator()
        self._monte_carlo = MonteCarloSimulator(n_runs=n_mc_runs)
        self._sensitivity = ParameterSensitivityAnalyzer()
        self._regime      = RegimeRobustnessTester()
        self._builder     = ValidationReportBuilder()

        log.info("[ValidationEngine] Initialised. %d validation stages ready. "
                 "Stop-on-crit: %s  MC runs: %d",
                 6, stop_on_critical_fail, n_mc_runs)

    # ── Public API ────────────────────────────────────────────────────────
    def validate(
        self,
        strategy_name:  str,
        pnl_series:     list[float],
        capital:        float = 1_000_000,
        param_grids:    Optional[list[ParamGrid]] = None,
        print_report:   bool  = True,
    ) -> ValidationReport:
        """
        Run the full 6-stage validation pipeline.

        Parameters
        ----------
        strategy_name : Human-readable strategy label
        pnl_series    : List of per-trade P&L values (₹)
        capital       : Total deployed capital (₹)
        param_grids   : Optional list of ParamGrid for sensitivity analysis
        print_report  : Whether to print the final report to stdout

        Returns
        -------
        ValidationReport with overall_score, verdict, and all stage results.
        """
        n = len(pnl_series)
        if n < MIN_TRADES_REQUIRED:
            log.warning("[ValidationEngine] '%s' has only %d trades — "
                        "minimum %d required.  Skipping validation.",
                        strategy_name, n, MIN_TRADES_REQUIRED)
            return self._builder.build(strategy_name)   # all stages None → REJECTED

        log.info("[ValidationEngine] ══ Starting validation: '%s' "
                 "(%d trades, capital ₹%.0f) ══",
                 strategy_name, n, capital)
        t0 = time.perf_counter()

        # ─ Stage 1: IS/OOS Backtest ─────────────────────────────────────
        bt: Optional[BacktestResult] = None
        try:
            bt = self._backtest.run(strategy_name, pnl_series, capital)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 1 BacktestEngine failed: %s", exc)

        # Stop early if backtest is a hard fail (catastrophic losses)
        if (self._stop_on_crit and bt is not None
                and bt.overfitting_flag == "FAIL"
                and bt.oos_stats.return_pct < -20):
            log.warning("[ValidationEngine] Critical failure in Stage 1 — "
                        "stopping pipeline early.")
            report = self._builder.build(strategy_name, backtest=bt)
            if print_report:
                report.print_report()
            return report

        # ─ Stage 2: Walk-Forward ─────────────────────────────────────────
        wf: Optional[WalkForwardResult] = None
        try:
            wf = self._walkforward.run(strategy_name, pnl_series, capital)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 2 WalkForwardAnalyzer failed: %s", exc)

        # ─ Stage 3: Cross-Market ─────────────────────────────────────────
        cm: Optional[CrossMarketResult] = None
        try:
            cm = self._cross_mkt.run(strategy_name, pnl_series, capital)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 3 CrossMarketValidator failed: %s", exc)

        # ─ Stage 4: Monte Carlo ──────────────────────────────────────────
        mc: Optional[MonteCarloResult] = None
        try:
            mc = self._monte_carlo.run(strategy_name, pnl_series, capital)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 4 MonteCarloSimulator failed: %s", exc)

        # ─ Stage 5: Parameter Sensitivity ───────────────────────────────
        ps: Optional[SensitivityResult] = None
        try:
            ps = self._sensitivity.run(
                strategy_name, pnl_series, capital, param_grids)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 5 ParameterSensitivity failed: %s", exc)

        # ─ Stage 6: Regime Robustness ────────────────────────────────────
        rr: Optional[RegimeRobustnessResult] = None
        try:
            rr = self._regime.run(strategy_name, pnl_series, capital)
        except Exception as exc:
            log.error("[ValidationEngine] Stage 6 RegimeRobustness failed: %s", exc)

        # ─ Build & print report ──────────────────────────────────────────
        report = self._builder.build(
            strategy_name, bt, wf, cm, mc, ps, rr)

        elapsed = (time.perf_counter() - t0) * 1000
        log.info("[ValidationEngine] Validation complete in %.0fms  "
                 "→ Score: %.1f/100  Verdict: %s",
                 elapsed, report.overall_score, report.verdict)

        if print_report:
            report.print_report()
        return report


__all__ = [
    "ValidationEngine",
    "ValidationReport",
    "BacktestResult",
    "WalkForwardResult",
    "CrossMarketResult",
    "MonteCarloResult",
    "SensitivityResult",
    "RegimeRobustnessResult",
    "ParamGrid",
]
