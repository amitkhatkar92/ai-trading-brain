"""
First-Month Monitoring Module
=============================
Tracks KPIs against first-month goals:
  • Signal Accuracy:    ≥ 40% win rate
  • Execution Slippage: < 0.15% per trade
  • Drawdown:          < 5% of capital
  • System Uptime:     100% (no crashes)

Usage:
    from monitoring.first_month_tracker import FirstMonthTracker
    
    tracker = FirstMonthTracker(initial_capital=1_000_000)
    tracker.update()
    print(tracker.get_daily_report())
    
    # Or use the report generator:
    from monitoring.generate_monitoring_report import generate_report, print_monitoring_summary
    report = generate_report()
    print_monitoring_summary(report)
"""

from .first_month_tracker import FirstMonthTracker
from .generate_monitoring_report import generate_report, print_monitoring_summary

__all__ = [
    "FirstMonthTracker",
    "generate_report",
    "print_monitoring_summary",
]
