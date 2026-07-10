"""reporting/simulation_report.py — Full simulation report assembly."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.core.paper_account    import PaperAccount
from iios.integration.research.paper_trading.core.paper_order      import PaperOrder
from iios.integration.research.paper_trading.core.paper_session    import PaperSession
from iios.integration.research.paper_trading.core.paper_statistics import PaperStatistics
from iios.integration.research.paper_trading.core.paper_trade      import PaperTrade
from iios.integration.research.paper_trading.reporting.trade_report      import TradeReport
from iios.integration.research.paper_trading.reporting.session_summary   import SessionSummary


class SimulationReport:
    """Builds a full institutional-style simulation report."""

    def __init__(self) -> None:
        self._trade_report   = TradeReport()
        self._session_summary = SessionSummary()

    def build(
        self,
        *,
        session:      PaperSession,
        stats:        PaperStatistics,
        account:      PaperAccount,
        equity_curve: list[tuple[float, float]],
        trade_log:    list[PaperTrade],
        orders:       list[PaperOrder],
        max_equity_points: int = 500,
    ) -> dict[str, Any]:

        summary       = self._session_summary.build(session, stats)
        trade_section = self._trade_report.build(trade_log)

        # Downsample equity curve if needed
        if len(equity_curve) > max_equity_points:
            step  = max(1, len(equity_curve) // max_equity_points)
            curve = equity_curve[::step]
        else:
            curve = equity_curve

        # Monthly returns
        monthly: dict[str, float] = {}
        if len(equity_curve) >= 2:
            for i in range(1, len(equity_curve)):
                ts, val = equity_curve[i]
                _, prev_val = equity_curve[i - 1]
                import datetime
                month_key = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m")
                if month_key not in monthly:
                    monthly[month_key] = 0.0
                if prev_val > 0.0:
                    monthly[month_key] += (val - prev_val) / prev_val

        return {
            "summary":    summary,
            "risk": {
                "volatility":        stats.volatility,
                "sharpe_ratio":      stats.sharpe_ratio,
                "sortino_ratio":     stats.sortino_ratio,
                "calmar_ratio":      stats.calmar_ratio,
                "max_drawdown":      stats.max_drawdown,
                "max_dd_duration":   stats.max_drawdown_duration,
                "value_at_risk_95":  stats.value_at_risk_95,
            },
            "trades":         trade_section,
            "orders": {
                "total":    stats.total_orders,
                "filled":   stats.filled_orders,
                "rejected": stats.rejected_orders,
                "fill_rate": stats.fill_rate,
            },
            "equity_curve":   [{"ts": ts, "equity": v} for ts, v in curve],
            "monthly_returns": monthly,
            "account":        account.to_dict(),
        }
