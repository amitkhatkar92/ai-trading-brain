"""reporting/portfolio_report.py — Portfolio-level report builder."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.paper_trading.core.paper_account   import PaperAccount
from iios.integration.research.paper_trading.core.paper_portfolio import PaperPortfolio


class PortfolioReport:
    """Builds a structured portfolio snapshot report."""

    def build(
        self,
        portfolio:         PaperPortfolio,
        account:           PaperAccount,
        benchmark_returns: Optional[list[float]] = None,
    ) -> dict[str, Any]:
        mv    = portfolio.total_market_value()
        equity = account.equity(mv)

        return {
            "account_id":         account.account_id,
            "portfolio_id":       portfolio.portfolio_id,
            "cash":               account.cash,
            "market_value":       mv,
            "total_equity":       equity,
            "unrealized_pnl":     portfolio.total_unrealized_pnl(),
            "realized_pnl":       portfolio.total_realized_pnl(),
            "total_return_pct":   account.total_return_pct(mv),
            "position_count":     portfolio.position_count(),
            "positions":          [p.to_dict() for p in portfolio.positions.values()],
            "has_benchmark":      benchmark_returns is not None,
            "equity_curve_len":   len(portfolio.equity_curve),
        }
