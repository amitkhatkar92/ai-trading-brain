"""reporting/session_summary.py — Compact session summary builder."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.core.paper_session    import PaperSession
from iios.integration.research.paper_trading.core.paper_statistics import PaperStatistics


class SessionSummary:
    """Builds a concise summary dict for a completed paper trading session."""

    def build(
        self,
        session: PaperSession,
        stats:   PaperStatistics,
    ) -> dict[str, Any]:
        return {
            "session_id":         session.session_id,
            "account_id":         session.account_id,
            "strategy_id":        session.strategy_id,
            "strategy_name":      session.strategy_name,
            "status":             session.status.value,
            "elapsed_sec":        session.elapsed_sec(),
            "bar_count":          stats.bar_count,
            "total_trades":       stats.total_trades,
            "win_rate":           stats.win_rate,
            "total_return":       stats.total_return,
            "annualized_return":  stats.annualized_return,
            "sharpe_ratio":       stats.sharpe_ratio,
            "max_drawdown":       stats.max_drawdown,
            "initial_capital":    stats.initial_capital,
            "final_equity":       stats.final_equity,
            "total_commission":   stats.total_commission,
            "total_slippage":     stats.total_slippage,
            "started_at":         session.started_at,
            "ended_at":           session.ended_at,
        }
