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
from .strategy_resilience_ai import StrategyResilienceAI, ResilienceScore
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

        # Print cycle summary table
        self._reporter.print_cycle_summary(result.scores)

        log.info(
            "  [MSE] %d/%d signals approved by simulation (%.0f%% pass rate)",
            len(result.approved_trades),
            len(signals),
            result.approval_rate * 100,
        )

        return result
