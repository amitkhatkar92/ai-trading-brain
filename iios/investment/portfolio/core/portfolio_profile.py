"""iios/investment/portfolio/core/portfolio_profile.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot


@dataclass
class PortfolioProfile:
    """
    Extended record wrapping Portfolio with tracking metadata.
    Maintained by PortfolioManager for each registered portfolio.
    """

    profile_id:      str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str                    = ""
    portfolio:       Portfolio              = field(default_factory=Portfolio)
    latest_snapshot: PortfolioSnapshot | None = None

    # NAV tracking for drawdown computation
    peak_nav:        float                  = 0.0
    inception_nav:   float                  = 0.0

    # Linkages
    strategy_ids:    list[str]              = field(default_factory=list)
    account_id:      str                    = ""
    manager_id:      str                    = ""

    metadata:        dict[str, Any]         = field(default_factory=dict)
    created_at:      float                  = field(default_factory=time.time)
    updated_at:      float                  = field(default_factory=time.time)

    def update_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        self.latest_snapshot = snapshot
        nav = snapshot.total_nav
        if nav > self.peak_nav:
            self.peak_nav = nav
        if self.inception_nav == 0.0 and nav > 0:
            self.inception_nav = nav
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id":       self.profile_id,
            "portfolio_id":     self.portfolio_id,
            "has_snapshot":     self.latest_snapshot is not None,
            "peak_nav":         self.peak_nav,
            "inception_nav":    self.inception_nav,
            "strategy_ids":     self.strategy_ids,
            "account_id":       self.account_id,
            "manager_id":       self.manager_id,
            "metadata":         self.metadata,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
        }
