"""
Market Simulation Engine — Simulation Engine (Main Orchestrator)
=================================================================
The top-level class that coordinates all MSE sub-modules.

Architecture
------------
  StressTestEngine  →  StrategyResilienceAI  →  SimulationReporter
       ↑                       ↑
  ScenarioGenerator       MarketSimulator

Public API
----------
  engine = SimulationEngine()
  result = engine.run(approved_signals, snapshot)

  result.approved_trades  → List[TradeSignal] that passed simulation
  result.rejected_trades  → List[TradeSignal] that failed simulation
  result.scores           → ResilienceScore per signal (all signals)

The orchestrator wires this between Risk Control (Layer 5) and the
Debate / Decision system (Layer 6–7).

Flow in master_orchestrator.run_full_cycle():
  approved_signals  ← _run_risk_control(cre_signals, snapshot)
  sim_result        ← simulation_engine.run(approved_signals, snapshot)   ← NEW
  for signal in sim_result.approved_trades:
      _run_debate_and_decide(signal, snapshot)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from models import TradeSignal, MarketSnapshot
from utils import get_logger

from .scenario_generator   import ScenarioGenerator, Scenario
from .market_simulator     import MarketSimulator
from .stress_test_engine   import StressTestEngine
from .strategy_resilience_ai import (
    StrategyResilienceAI, ResilienceScore,
    THRESHOLD_STABILITY, THRESHOLD_MC_PROFIT_PROB,
)
from .simulation_report    import SimulationReporter

log = get_logger(__name__)


@dataclass
class SimulationResult:
    """
    Container returned by SimulationEngine.run().

    Attributes
    ----------
    approved_trades  : signals that passed ALL simulation checks
    rejected_trades  : signals blocked by simulation
    scores           : ResilienceScore for every evaluated signal
    total_evaluated  : total signals submitted for simulation
    """
    approved_trades: List[TradeSignal]     = field(default_factory=list)
    rejected_trades: List[TradeSignal]     = field(default_factory=list)
    scores:          List[ResilienceScore] = field(default_factory=list)
    total_evaluated: int                   = 0

    @property
    def approval_rate(self) -> float:
        if self.total_evaluated == 0:
            return 0.0
        return len(self.approved_trades) / self.total_evaluated


class SimulationEngine:
    """
    Market Simulation Engine — quant-grade pre-execution validation.

    Runs each risk-approved trade signal through:
      1. 9 standard market scenarios (deterministic stress test)
      2. 1,000-run Monte Carlo simulation (VIX-calibrated)
      3. Resilience scoring and acceptance-threshold decisions

    Only signals that survive simulation are forwarded to the
    Debate / Decision layer.

    Usage
    -----
    sim = SimulationEngine()
    result = sim.run(signals, snapshot)
    """

    def __init__(self, mc_runs: int = 1_000):
        self._scenario_gen   = ScenarioGenerator()
        self._simulator      = MarketSimulator()
        self._stress_engine  = StressTestEngine()
        self._resilience_ai  = StrategyResilienceAI(mc_runs=mc_runs)
        self._reporter       = SimulationReporter()
        log.info(
            "[SimulationEngine] Initialised. MC runs=%d | Scenarios=%d",
            mc_runs,
            len(self._scenario_gen.get_standard_scenarios()),
        )

    # ──────────────────────────────────────────────────────────────────
    # PRIMARY METHOD
    # ──────────────────────────────────────────────────────────────────

    def run(
        self,
        signals:  List[TradeSignal],
        snapshot: MarketSnapshot,
    ) -> SimulationResult:
        """
        Run the full simulation pipeline for every signal.

        Parameters
        ----------
        signals  : risk-approved TradeSignals from the Risk Control layer
        snapshot : current MarketSnapshot providing regime + VIX context

        Returns
        -------
        SimulationResult containing approved/rejected lists and scores
        """
        log.info("── Market Simulation Engine ──")
        log.info("  [MSE] %d signal(s) submitted for simulation", len(signals))

        if not signals:
            log.info("  [MSE] No signals to simulate.")
            return SimulationResult(total_evaluated=0)

        # Get deterministic scenarios once for this cycle
        scenarios = self._scenario_gen.get_standard_scenarios()
        vix        = snapshot.vix if snapshot.vix else 16.0
        regime     = snapshot.regime.value if snapshot.regime else "range_market"

        result = SimulationResult(total_evaluated=len(signals))

        for signal in signals:
            # Apply each scenario to a simulated snapshot (used for context)
            # The stress engine itself re-applies price impact internally
            sim_snap = self._simulator.apply(snapshot, scenarios[0])  # reference snap

            # Run all scenario stress tests
            scenario_results = self._stress_engine.test_signal(
                signal, scenarios, sim_snap
            )

            # Compute resilience score + Monte Carlo
            score = self._resilience_ai.evaluate(
                signal,
                scenario_results,
                vix=vix,
                regime=regime,
            )
            result.scores.append(score)

            # Print per-signal detailed report
            self._reporter.print_signal_report(score)

            # Route to approved/rejected
            if score.approved:
                result.approved_trades.append(signal)
            else:
                result.rejected_trades.append(signal)
                log.info(
                    "[SimulationDecision] symbol=%s strategy=%s "
                    "confidence=%.2f rr_ratio=%.2f "
                    "mc_score=%.3f stability_score=%.3f "
                    "required_threshold=%.2f rejection_reason=%s",
                    signal.symbol,
                    getattr(signal, "strategy_name", ""),
                    getattr(signal, "confidence", 0.0),
                    getattr(signal, "risk_reward_ratio", 0.0),
                    score.monte_carlo_profit_prob,
                    score.stability_score,
                    THRESHOLD_STABILITY,
                    score.rejection_reason,
                )
                # Legacy tag retained for backward grep compatibility
                log.info(
                    "[SimulationReject] symbol=%s mc_probability=%.0f%% "
                    "simulation_score=%.3f required_mc=%.0f%% required_stability=%.2f "
                    "survival_rate=%.0f%% worst_loss_r=%.2f stability=%.2f "
                    "top_failure_reason=%s",
                    signal.symbol,
                    score.monte_carlo_profit_prob * 100,
                    score.stability_score,
                    THRESHOLD_MC_PROFIT_PROB * 100,
                    THRESHOLD_STABILITY,
                    score.survival_rate * 100,
                    score.worst_loss_r,
                    score.stability_score,
                    score.rejection_reason,
                )

        # ── [SimulationReject] aggregate ──────────────────────────────────────
        if result.rejected_trades:
            from collections import Counter as _Counter
            _reasons = _Counter(
                s.rejection_reason for s in result.scores if not s.approved
            )
            _mc_probs = [
                s.monte_carlo_profit_prob for s in result.scores if not s.approved
            ]
            _stab_vals = [
                s.stability_score for s in result.scores if not s.approved
            ]
            import statistics as _stats
            log.info(
                "[SimulationReject] AGGREGATE rejected=%d avg_mc_probability=%.0f%% "
                "avg_stability=%.2f reject_reason_counts=%s",
                len(result.rejected_trades),
                (_stats.mean(_mc_probs) * 100) if _mc_probs else 0.0,
                _stats.mean(_stab_vals) if _stab_vals else 0.0,
                dict(_reasons.most_common()),
            )

        # ── [SimulationSummary] + [SimulationVerdict] ─────────────────────────
        try:
            from collections import Counter as _SCtr
            import statistics as _sstats
            _all_mc  = [s.monte_carlo_profit_prob for s in result.scores]
            _all_stab= [s.stability_score for s in result.scores]
            _rej_reasons = _SCtr(
                s.rejection_reason for s in result.scores if not s.approved
            )
            _dom_reason = _rej_reasons.most_common(1)[0][0] if _rej_reasons else "NONE"
            _avg_mc   = (_sstats.mean(_all_mc)   * 100) if _all_mc else 0.0
            _avg_stab = _sstats.mean(_all_stab)   if _all_stab else 0.0
            log.info(
                "[SimulationSummary] signals_in=%d signals_out=%d "
                "avg_mc_score=%.0f%% avg_stability=%.3f "
                "threshold_stability=%.2f threshold_mc=%.0f%% "
                "dominant_rejection_reason=%s",
                result.total_evaluated, len(result.approved_trades),
                _avg_mc, _avg_stab,
                THRESHOLD_STABILITY, THRESHOLD_MC_PROFIT_PROB * 100,
                _dom_reason,
            )
            # Verdict logic
            if result.total_evaluated == 0:
                _sim_verdict = "NO_SIGNALS"
            elif len(result.rejected_trades) == 0:
                _sim_verdict = "SIMULATION_HEALTHY"
            elif len(result.approved_trades) == 0:
                _sim_verdict = "SIMULATION_TOO_RESTRICTIVE"
            elif len(result.rejected_trades) > len(result.approved_trades):
                _sim_verdict = "SIMULATION_TOO_RESTRICTIVE"
            else:
                _sim_verdict = "SIMULATION_HEALTHY"
            log.info(
                "[SimulationVerdict] verdict=%s approved=%d rejected=%d "
                "pass_rate=%.0f%% threshold_stability=%.2f threshold_mc=%.0f%%",
                _sim_verdict,
                len(result.approved_trades), len(result.rejected_trades),
                result.approval_rate * 100,
                THRESHOLD_STABILITY, THRESHOLD_MC_PROFIT_PROB * 100,
            )
        except Exception as _sv_exc:
            log.debug("[SimulationSummary] skipped: %s", _sv_exc)

        # Print cycle summary table
        self._reporter.print_cycle_summary(result.scores)

        log.info(
            "  [MSE] %d/%d signals approved by simulation (%.0f%% pass rate)",
            len(result.approved_trades),
            len(signals),
            result.approval_rate * 100,
        )

        return result
