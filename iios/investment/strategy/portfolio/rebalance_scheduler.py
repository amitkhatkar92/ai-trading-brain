"""iios/investment/strategy/portfolio/rebalance_scheduler.py
RebalanceScheduler — evaluates whether a portfolio is due for rebalancing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.strategy_portfolio import StrategyPortfolio
from iios.investment.strategy.portfolio.rebalance_policy import RebalancePolicy, RebalanceTrigger
from iios.investment.strategy.portfolio.rebalance_history import RebalanceHistory


@dataclass(frozen=True)
class RebalanceDecision:
    portfolio_id: str
    is_due:       bool
    triggers:     List[str]   # which triggers fired
    reason:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "is_due":       self.is_due,
            "triggers":     self.triggers,
            "reason":       self.reason,
        }


class RebalanceScheduler:
    """
    Evaluates rebalancing eligibility for a portfolio based on its policy.
    Does NOT execute rebalancing — that is done by RebalancingEngine.
    """

    def __init__(self, history: Optional[RebalanceHistory] = None) -> None:
        self._history = history or RebalanceHistory()

    def is_due(
        self,
        portfolio:    StrategyPortfolio,
        policy:       RebalancePolicy,
        current_time: Optional[datetime] = None,
    ) -> RebalanceDecision:
        now     = current_time or datetime.now(timezone.utc)
        pid     = portfolio.portfolio_id
        fired:  List[str] = []

        # Cooldown check
        latest = self._history.latest(pid)
        if latest is not None:
            elapsed_days = (now - latest.created_at).total_seconds() / 86_400
            if elapsed_days < policy.cooldown_days:
                return RebalanceDecision(
                    portfolio_id=pid,
                    is_due=False,
                    triggers=[],
                    reason=f"Cooldown active: {elapsed_days:.1f}d < {policy.cooldown_days}d",
                )

        # Time-based trigger
        if policy.enable_time_trigger:
            last_rb = portfolio.last_rebalanced or portfolio.created_at
            days_since = (now - last_rb).total_seconds() / 86_400
            if days_since >= policy.time_based_days:
                fired.append(RebalanceTrigger.TIME_BASED.value)

        # Threshold (drift) trigger
        if policy.enable_drift_trigger:
            if portfolio.max_drift >= policy.drift_threshold:
                fired.append(RebalanceTrigger.THRESHOLD_BASED.value)

        # Performance trigger
        if policy.enable_performance_trigger:
            for alloc in portfolio.active_allocations():
                if alloc.evaluation_score < policy.min_strategy_eval_score:
                    fired.append(RebalanceTrigger.PERFORMANCE_BASED.value)
                    break

        is_due = len(fired) > 0
        reason = f"Triggers fired: {fired}" if is_due else "No rebalance triggers active"
        return RebalanceDecision(
            portfolio_id=pid,
            is_due=is_due,
            triggers=fired,
            reason=reason,
        )
