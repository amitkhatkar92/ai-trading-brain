"""analytics/paper_analytics.py — Post-session analytics for the Paper Trading Framework."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_RISK_FREE_RATE,
    PaperOrderStatus,
)
from iios.integration.research.paper_trading.core.paper_account    import PaperAccount
from iios.integration.research.paper_trading.core.paper_statistics import PaperStatistics
from iios.integration.research.paper_trading.core.paper_trade      import PaperTrade
from iios.integration.research.paper_trading.core.paper_order      import PaperOrder
from iios.integration.research.paper_trading.execution.fill_simulator import FillResult


class PaperAnalytics:
    """
    Computes analytics from completed paper trading session data.

    All methods are stateless and can be called with raw data.
    """

    # ── Statistics ────────────────────────────────────────────────────────────

    def compute_statistics(
        self,
        *,
        initial_capital:   float,
        equity_curve:      list[tuple[float, float]],
        trades:            list[PaperTrade],
        orders:            list[PaperOrder],
        risk_free_rate:    float                  = DEFAULT_RISK_FREE_RATE,
        benchmark_returns: list[float] | None     = None,
    ) -> PaperStatistics:
        """Compute aggregate session statistics."""
        return PaperStatistics.compute(
            initial_capital   = initial_capital,
            equity_curve      = equity_curve,
            trade_dicts       = [t.to_dict() for t in trades],
            order_dicts       = [o.to_dict() for o in orders],
            risk_free_rate    = risk_free_rate,
            benchmark_returns = benchmark_returns,
        )

    # ── Execution quality ─────────────────────────────────────────────────────

    def execution_quality(
        self,
        fills:  list[FillResult],
        orders: list[PaperOrder],
    ) -> dict[str, Any]:
        """Analyse execution quality: fill rate, average slippage, etc."""
        if not orders:
            return {"fill_rate": 0.0, "avg_slippage": 0.0, "avg_commission": 0.0}

        filled   = [o for o in orders if o.status == PaperOrderStatus.FILLED]
        rejected = [o for o in orders if o.status == PaperOrderStatus.REJECTED]
        fill_rate = len(filled) / len(orders)

        total_slippage    = sum(f.slippage   for f in fills)
        total_commission  = sum(f.commission for f in fills)
        total_notional    = sum(f.fill_price * f.quantity for f in fills)

        avg_slip_pct  = total_slippage   / total_notional if total_notional else 0.0
        avg_comm_pct  = total_commission / total_notional if total_notional else 0.0

        return {
            "total_orders":    len(orders),
            "filled_orders":   len(filled),
            "rejected_orders": len(rejected),
            "fill_rate":       fill_rate,
            "total_fills":     len(fills),
            "total_notional":  total_notional,
            "total_slippage":  total_slippage,
            "total_commission": total_commission,
            "avg_slippage_pct":  avg_slip_pct,
            "avg_commission_pct": avg_comm_pct,
        }

    # ── Order statistics ──────────────────────────────────────────────────────

    def order_statistics(self, orders: list[PaperOrder]) -> dict[str, Any]:
        if not orders:
            return {}
        by_type:   dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_symbol: dict[str, int] = {}
        by_side:   dict[str, int] = {}
        for o in orders:
            by_type[o.order_type.value]   = by_type.get(o.order_type.value, 0)   + 1
            by_status[o.status.value]     = by_status.get(o.status.value, 0)     + 1
            by_symbol[o.symbol]           = by_symbol.get(o.symbol, 0)           + 1
            by_side[o.side.value]         = by_side.get(o.side.value, 0)         + 1
        return {
            "total_orders": len(orders),
            "by_type":      by_type,
            "by_status":    by_status,
            "by_symbol":    by_symbol,
            "by_side":      by_side,
        }

    # ── Session comparison ────────────────────────────────────────────────────

    def compare_sessions(self, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Rank multiple session result dicts by Sharpe ratio.

        Each element in *sessions* must have a ``"sharpe_ratio"`` key.
        """
        if not sessions:
            return {"ranked": []}
        ranked = sorted(sessions, key=lambda s: s.get("sharpe_ratio", float("-inf")), reverse=True)
        for rank, s in enumerate(ranked, 1):
            s["rank"] = rank
        return {"total": len(ranked), "ranked": ranked}
