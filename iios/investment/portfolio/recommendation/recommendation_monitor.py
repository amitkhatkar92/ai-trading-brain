"""iios/investment/portfolio/recommendation/recommendation_monitor.py

Monitors active recommendations for staleness and condition changes.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.recommendation.recommendation_expiration import (
    hours_remaining, is_expired,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    RecommendationPriority, now_utc,
)


@dataclass(frozen=True)
class RecommendationMonitorReport:
    """Snapshot of active recommendation health across portfolios."""

    report_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:         str   = field(default_factory=now_utc)
    n_portfolios_checked: int   = 0
    n_active:             int   = 0
    n_expiring_soon:      int   = 0   # expiry within 2h
    n_expired:            int   = 0
    n_requires_approval:  int   = 0
    oldest_hours:         float = 0.0
    is_healthy:           bool  = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_portfolios_checked": self.n_portfolios_checked,
            "n_active":             self.n_active,
            "n_expiring_soon":      self.n_expiring_soon,
            "n_expired":            self.n_expired,
            "n_requires_approval":  self.n_requires_approval,
            "is_healthy":           self.is_healthy,
        }


class RecommendationMonitor:
    """
    Monitors the health of currently active recommendations.
    Does NOT modify recommendations — read-only analysis.
    """

    EXPIRING_SOON_HOURS = 2.0

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def check(self, active_recs_by_portfolio: Dict[str, List[Any]]) -> RecommendationMonitorReport:
        """
        Analyse a snapshot of active recommendations.

        Parameters
        ----------
        active_recs_by_portfolio : dict mapping portfolio_id → list of active recommendations
        """
        n_portfolios = len(active_recs_by_portfolio)
        n_active = 0
        n_expiring = 0
        n_expired = 0
        n_approval = 0
        max_age_hours = 0.0

        for pid, recs in active_recs_by_portfolio.items():
            for rec in recs:
                n_active += 1
                if is_expired(rec):
                    n_expired += 1
                else:
                    hr = hours_remaining(rec)
                    if 0 < hr <= self.EXPIRING_SOON_HOURS:
                        n_expiring += 1
                    age = self._age_hours(rec)
                    if age > max_age_hours:
                        max_age_hours = age
                if getattr(rec, "requires_approval", False):
                    n_approval += 1

        is_healthy = n_expired == 0 and n_approval == 0

        return RecommendationMonitorReport(
            n_portfolios_checked = n_portfolios,
            n_active             = n_active,
            n_expiring_soon      = n_expiring,
            n_expired            = n_expired,
            n_requires_approval  = n_approval,
            oldest_hours         = round(max_age_hours, 2),
            is_healthy           = is_healthy,
        )

    @staticmethod
    def _age_hours(rec: Any) -> float:
        """Return the age of the recommendation in hours."""
        from datetime import datetime, timezone
        created_at = getattr(rec, "created_at", None)
        if not created_at:
            return 0.0
        try:
            created = datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - created).total_seconds() / 3600.0
        except (ValueError, TypeError):
            return 0.0
