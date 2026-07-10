"""reporting/trade_report.py — Per-trade report builder."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.core.paper_trade import PaperTrade


class TradeReport:
    """Builds a structured trade report from a list of PaperTrade objects."""

    def build(
        self,
        trade_log:  list[PaperTrade],
        max_trades: int = 1_000,
    ) -> dict[str, Any]:
        total   = len(trade_log)
        visible = trade_log[-max_trades:]

        by_symbol: dict[str, dict] = {}
        for t in trade_log:
            if t.symbol not in by_symbol:
                by_symbol[t.symbol] = {"count": 0, "total_pnl": 0.0, "wins": 0}
            entry = by_symbol[t.symbol]
            entry["count"]     += 1
            entry["total_pnl"] += t.net_pnl
            if t.is_winner():
                entry["wins"] += 1

        return {
            "total_trades":  total,
            "shown_trades":  len(visible),
            "trades":        [t.to_dict() for t in visible],
            "by_symbol":     by_symbol,
        }
