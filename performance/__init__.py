"""
Performance Evaluation Framework
=================================
Answers: "Is the AI brain actually making money?"

Public API::
    from performance import PerformanceEvaluator, PerformanceReport

    evaluator = PerformanceEvaluator(capital=1_000_000)
    evaluator.record_trade("Iron_Condor", "range_market", pnl=2800, r_multiple=1.4, won=True)
    report = evaluator.evaluate()
    evaluator.print_full_report(report)
"""

from .performance_evaluator       import PerformanceEvaluator, PerformanceReport, PerformanceRecord
from .drawdown_analyzer           import DrawdownAnalyzer, DrawdownReport
from .regime_performance_tracker  import RegimePerformanceTracker
from .strategy_attribution        import StrategyAttributionEngine
from .walk_forward_tester         import WalkForwardTester, WalkForwardReport

__all__ = [
    "PerformanceEvaluator", "PerformanceReport", "PerformanceRecord",
    "DrawdownAnalyzer", "DrawdownReport",
    "RegimePerformanceTracker",
    "StrategyAttributionEngine",
    "WalkForwardTester", "WalkForwardReport",
]
