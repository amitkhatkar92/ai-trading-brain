"""
Market Simulation Engine
=========================
Pre-execution simulation layer that stress-tests trade signals
against hypothetical market scenarios before they reach the
Debate / Decision system.

Sub-modules
-----------
scenario_generator     → defines 9 standard + Monte Carlo scenarios
market_simulator       → applies scenarios to MarketSnapshot
stress_test_engine     → per-(signal, scenario) outcome computation
strategy_resilience_ai → survival rate, stability, Monte Carlo scoring
simulation_report      → formatted log output
simulation_engine      → top-level orchestrator (use this in MasterOrchestrator)

Quick usage
-----------
from market_simulation import SimulationEngine, SimulationResult

engine = SimulationEngine()
result: SimulationResult = engine.run(signals, snapshot)
approved = result.approved_trades
"""

from .scenario_generator    import Scenario, ScenarioGenerator
from .market_simulator      import MarketSimulator, SimulatedSnapshot
from .stress_test_engine    import StressTestEngine, ScenarioTestResult, TradeOutcome
from .strategy_resilience_ai import StrategyResilienceAI, ResilienceScore
from .simulation_report     import SimulationReporter
from .simulation_engine     import SimulationEngine, SimulationResult

__all__ = [
    # Core engine
    "SimulationEngine",
    "SimulationResult",
    # Sub-components (available for direct use / testing)
    "ScenarioGenerator",
    "Scenario",
    "MarketSimulator",
    "SimulatedSnapshot",
    "StressTestEngine",
    "ScenarioTestResult",
    "TradeOutcome",
    "StrategyResilienceAI",
    "ResilienceScore",
    "SimulationReporter",
]
