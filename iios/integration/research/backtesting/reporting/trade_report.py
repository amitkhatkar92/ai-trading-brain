"""reporting/trade_report.py — Structured trade log report."""
from __future__ import annotations

from typing import Any

from iios.integration.research.backtesting.metrics.trade_statistics import trades_by_symbol


class TradeReport:
    """
    Builds a trade-log section for the full backtest report.
    """

    def build(
        self,
        trade_log: list[dict[str, Any]],
        *,
        max_trades: int = 10_000,
    ) -> dict[str, Any]:
        total   = len(trade_log)
        trimmed = trade_log[-max_trades:] if total > max_trades else trade_log

        by_symbol = trades_by_symbol(trade_log)
        symbol_summary = {
            sym: {
                "count":      len(trades),
                "net_pnl":    sum(t.get("net_pnl", 0.0) for t in trades),
                "win_rate":   sum(1 for t in trades if t.get("net_pnl", 0) > 0) / len(trades),
            }
            for sym, trades in by_symbol.items()
        }

        return {
            "total_trades":   total,
            "trades":         trimmed,
            "by_symbol":      symbol_summary,
        }
