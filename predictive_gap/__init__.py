"""predictive_gap — PGA-001 Predictive Gap Analysis Package.

Automatically runs every trading day after market close to analyse:
  - Top 5 Gainers and Top 5 Losers
  - Every executed, approved, and rejected trade
  - Watchlist candidates (scanned but not decided)

For each stock, determines:
  - Was the move PREDICTED? (YES / PARTIALLY / NO)
  - Was the move PREDICTABLE? (PREDICTABLE / PARTIALLY_PREDICTABLE / NOT_PREDICTABLE)
  - Root Cause for misses (13 categories)
  - Learning actions (A–G)

CLI:
    python -m predictive_gap.pga_runner [--date YYYY-MM-DD] [--dry-run]
"""
from .pga_runner import run_pga
from .pga_config import PGAConfig
from .pga_collector import DailyData, StockMove, SignalRecord, DecisionRecord, collect_daily
from .pga_analyzer import StockAnalysis, analyze_universe
from .pga_root_cause import RootCause, analyze_misses
from .pga_learning import LearningAction, plan_actions, execute_actions
from .pga_reporter import write_all_reports

__all__ = [
    "run_pga",
    "PGAConfig",
    "DailyData",
    "StockMove",
    "SignalRecord",
    "DecisionRecord",
    "StockAnalysis",
    "RootCause",
    "LearningAction",
    "collect_daily",
    "analyze_universe",
    "analyze_misses",
    "plan_actions",
    "execute_actions",
    "write_all_reports",
]
