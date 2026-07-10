"""backtest_factory.py — Factory for creating all backtesting framework components."""
from __future__ import annotations

from typing import Optional

from iios.integration.research.backtesting.backtest_constants import DEFAULT_MAX_BACKTESTS
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.core.backtest_history import BacktestHistory


class BacktestFactory:
    """Static factory for all framework components."""

    @staticmethod
    def create_registry(max_backtests: int = DEFAULT_MAX_BACKTESTS):
        from iios.integration.research.backtesting.backtest_registry import BacktestRegistry
        return BacktestRegistry(max_backtests)

    @staticmethod
    def create_simulation_engine():
        from iios.integration.research.backtesting.engine.simulation_engine import SimulationEngine
        return SimulationEngine()

    @staticmethod
    def create_market_simulator():
        from iios.integration.research.backtesting.engine.market_simulator import MarketSimulator
        return MarketSimulator()

    @staticmethod
    def create_execution_simulator(config: Optional[BacktestConfiguration] = None):
        from iios.integration.research.backtesting.engine.execution_simulator import ExecutionSimulator
        return ExecutionSimulator(config or BacktestConfiguration())

    @staticmethod
    def create_simulation_clock():
        from iios.integration.research.backtesting.engine.simulation_clock import SimulationClock
        return SimulationClock()

    @staticmethod
    def create_event_scheduler():
        from iios.integration.research.backtesting.engine.event_scheduler import EventScheduler
        return EventScheduler()

    @staticmethod
    def create_performance_engine():
        from iios.integration.research.backtesting.metrics.performance_engine import PerformanceEngine
        return PerformanceEngine()

    @staticmethod
    def create_report_generator():
        from iios.integration.research.backtesting.reporting.report_generator import ReportGenerator
        return ReportGenerator()

    @staticmethod
    def create_validation_engine():
        from iios.integration.research.backtesting.validation.validation_engine import ValidationEngine
        return ValidationEngine()

    @staticmethod
    def create_walk_forward_validator():
        from iios.integration.research.backtesting.validation.walk_forward_validator import WalkForwardValidator
        return WalkForwardValidator()

    @staticmethod
    def create_oos_validator():
        from iios.integration.research.backtesting.validation.out_of_sample_validator import OutOfSampleValidator
        return OutOfSampleValidator()

    @staticmethod
    def create_overfitting_detector():
        from iios.integration.research.backtesting.validation.overfitting_detector import OverfittingDetector
        return OverfittingDetector()

    @staticmethod
    def create_robustness_analyzer():
        from iios.integration.research.backtesting.validation.robustness_analyzer import RobustnessAnalyzer
        return RobustnessAnalyzer()

    @staticmethod
    def create_history(max_entries: int = 100_000):
        return BacktestHistory(max_entries)

    @staticmethod
    def create_configuration(**kwargs) -> BacktestConfiguration:
        return BacktestConfiguration(**kwargs)
