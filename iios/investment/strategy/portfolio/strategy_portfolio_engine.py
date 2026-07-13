"""iios/investment/strategy/portfolio/strategy_portfolio_engine.py
StrategyPortfolioEngine — authoritative strategy portfolio management engine.

Responsibilities:
  • Construct portfolios of strategies (NOT portfolios of securities)
  • Optimise, rebalance, monitor, and score strategy portfolios
  • Consume evaluation and opportunity intelligence; never generate it
  • Never produce Buy/Sell/Hold signals

Public API:
  create_portfolio()        → StrategyPortfolio
  optimize_portfolio()      → OptimizationResult
  rebalance_portfolio()     → RebalanceResult
  get_portfolio()           → Optional[StrategyPortfolio]
  list_portfolios()         → List[StrategyPortfolio]
  archive_portfolio()       → bool
  portfolio_health()        → PortfolioHealth
  portfolio_score()         → PortfolioScore
  diversification_report()  → DiversificationReport
  rebalance_history()       → List[RebalanceRecord]
  compare_portfolios()      → Dict[str, PortfolioScore]
  take_snapshot()           → PortfolioSnapshot
  snapshot_history()        → List[PortfolioSnapshot]
  stats()                   → Dict[str, Any]
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.portfolio_registry import PortfolioRegistry
from iios.investment.strategy.portfolio.portfolio_history import PortfolioHistory
from iios.investment.strategy.portfolio.portfolio_snapshot import PortfolioSnapshot
from iios.investment.strategy.portfolio.portfolio_constructor import (
    PortfolioConstructor, PortfolioConstructionError
)
from iios.investment.strategy.portfolio.portfolio_optimizer import PortfolioOptimizer
from iios.investment.strategy.portfolio.optimization_engine import OptimizationResult
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.strategy_allocation import AllocationMethod
from iios.investment.strategy.portfolio.portfolio_lifecycle import PortfolioLifecycle
from iios.investment.strategy.portfolio.portfolio_events import (
    PortfolioEventBus, PortfolioEventType
)
from iios.investment.strategy.portfolio.portfolio_monitor import PortfolioMonitor, PortfolioAlert
from iios.investment.strategy.portfolio.diversification_engine import (
    DiversificationEngine, DiversificationReport
)
from iios.investment.strategy.portfolio.rebalancing_engine import (
    RebalancingEngine, RebalanceResult
)
from iios.investment.strategy.portfolio.rebalance_history import RebalanceRecord
from iios.investment.strategy.portfolio.rebalance_policy import (
    RebalancePolicy, DEFAULT_POLICY
)
from iios.investment.strategy.portfolio.portfolio_score import (
    PortfolioScore, PortfolioScoreCalculator
)
from iios.investment.strategy.portfolio.portfolio_health import PortfolioHealth


class StrategyPortfolioEngine:
    """
    Central facade for all portfolio management operations.
    Thread-safe.  All mutations route through this engine.
    """

    def __init__(
        self,
        event_bus:   Optional[PortfolioEventBus] = None,
    ) -> None:
        self._registry   = PortfolioRegistry()
        self._history    = PortfolioHistory()
        self._lifecycle  = PortfolioLifecycle(event_bus=event_bus or PortfolioEventBus())
        self._monitor    = PortfolioMonitor(self._registry, self._lifecycle.event_bus)
        self._constructor = PortfolioConstructor()
        self._optimizer  = PortfolioOptimizer()
        self._div_engine = DiversificationEngine()
        self._rebalancer = RebalancingEngine(lifecycle=self._lifecycle)
        self._scorer     = PortfolioScoreCalculator()
        self._lock       = threading.RLock()

        # Strategy map: sid → PortfolioStrategy (caller-maintained)
        self._strategy_store: Dict[str, PortfolioStrategy] = {}
        self._meta_lock = threading.Lock()

    # ── strategy registration ─────────────────────────────────────────────────

    def register_strategy(self, strategy: PortfolioStrategy) -> None:
        """Register / update a PortfolioStrategy for use in portfolio construction."""
        with self._meta_lock:
            self._strategy_store[strategy.strategy_id] = strategy

    def unregister_strategy(self, strategy_id: str) -> None:
        with self._meta_lock:
            self._strategy_store.pop(strategy_id, None)

    def get_registered_strategies(self) -> List[PortfolioStrategy]:
        with self._meta_lock:
            return list(self._strategy_store.values())

    # ── portfolio construction ────────────────────────────────────────────────

    def create_portfolio(
        self,
        strategies:     List[PortfolioStrategy],
        portfolio_type: PortfolioType = PortfolioType.COMPOSITE_WEIGHT,
        constraints:    ConstructionConstraints = DEFAULT_CONSTRAINTS,
        portfolio_name: str = "",
        total_capital:  float = 0.0,
        portfolio_id:   Optional[str] = None,
        metadata:       Optional[Dict[str, Any]] = None,
        auto_optimize:  bool = True,
    ) -> StrategyPortfolio:
        """
        Build a StrategyPortfolio and register it.
        Raises PortfolioConstructionError if eligibility constraints fail.
        """
        portfolio = self._constructor.build(
            strategies=strategies,
            portfolio_type=portfolio_type,
            constraints=constraints,
            portfolio_name=portfolio_name,
            total_capital=total_capital,
            portfolio_id=portfolio_id,
            metadata=metadata,
        )
        self._registry.register(portfolio)
        self._history.capture(portfolio)

        if auto_optimize:
            self._optimizer.optimize(portfolio, constraints)
            self._history.capture(portfolio)

        return portfolio

    # ── optimization ──────────────────────────────────────────────────────────

    def optimize_portfolio(
        self,
        portfolio_id: str,
        constraints:  ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> Optional[OptimizationResult]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        result = self._optimizer.optimize(portfolio, constraints)
        self._history.capture(portfolio)
        return result

    # ── rebalancing ───────────────────────────────────────────────────────────

    def rebalance_portfolio(
        self,
        portfolio_id: str,
        strategies:   Optional[List[PortfolioStrategy]] = None,
        policy:       RebalancePolicy = DEFAULT_POLICY,
        constraints:  ConstructionConstraints = DEFAULT_CONSTRAINTS,
        force:        bool = False,
    ) -> Optional[RebalanceResult]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        strats = strategies or self._resolve_strategies(portfolio)
        result = self._rebalancer.rebalance(portfolio, strats, policy, constraints, force)
        if result.rebalanced:
            self._history.capture(portfolio)
        return result

    def _resolve_strategies(self, portfolio: StrategyPortfolio) -> List[PortfolioStrategy]:
        """Resolve active allocation IDs to registered PortfolioStrategy objects."""
        with self._meta_lock:
            return [
                self._strategy_store[a.strategy_id]
                for a in portfolio.active_allocations()
                if a.strategy_id in self._strategy_store
            ]

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def approve_portfolio(self, portfolio_id: str, reason: str = "") -> bool:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return False
        return self._lifecycle.approve(portfolio, reason)

    def activate_portfolio(self, portfolio_id: str, reason: str = "") -> bool:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return False
        return self._lifecycle.activate(portfolio, reason)

    def pause_portfolio(self, portfolio_id: str, reason: str = "") -> bool:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return False
        return self._lifecycle.pause(portfolio, reason)

    def archive_portfolio(self, portfolio_id: str, reason: str = "") -> bool:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return False
        return self._lifecycle.archive(portfolio, reason)

    # ── queries ───────────────────────────────────────────────────────────────

    def get_portfolio(self, portfolio_id: str) -> Optional[StrategyPortfolio]:
        return self._registry.get(portfolio_id)

    def list_portfolios(
        self, state: Optional[PortfolioState] = None
    ) -> List[StrategyPortfolio]:
        if state is not None:
            return self._registry.by_state(state)
        return self._registry.all()

    # ── intelligence ──────────────────────────────────────────────────────────

    def portfolio_health(
        self,
        portfolio_id:      str,
        strategy_conf_map: Optional[Dict[str, float]] = None,
        constraints:       ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> Optional[PortfolioHealth]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        conf_map = strategy_conf_map or {
            sid: s.confidence_score
            for sid, s in self._strategy_store.items()
        }
        return PortfolioHealth.assess(portfolio, conf_map, constraints)

    def portfolio_score(
        self,
        portfolio_id:      str,
        strategies:        Optional[List[PortfolioStrategy]] = None,
        strategy_conf_map: Optional[Dict[str, float]] = None,
        constraints:       ConstructionConstraints = DEFAULT_CONSTRAINTS,
    ) -> Optional[PortfolioScore]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        strats = strategies or self.get_registered_strategies()
        return self._scorer.score(portfolio, strats, strategy_conf_map, constraints)

    def diversification_report(
        self,
        portfolio_id: str,
        strategies:   Optional[List[PortfolioStrategy]] = None,
    ) -> Optional[DiversificationReport]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        strats = strategies or self.get_registered_strategies()
        return self._div_engine.analyse(portfolio, strats)

    def compare_portfolios(
        self,
        portfolio_ids: List[str],
        strategies:    Optional[List[PortfolioStrategy]] = None,
    ) -> Dict[str, PortfolioScore]:
        strats = strategies or self.get_registered_strategies()
        results = {}
        for pid in portfolio_ids:
            score = self.portfolio_score(pid, strats)
            if score:
                results[pid] = score
        return results

    # ── history ───────────────────────────────────────────────────────────────

    def take_snapshot(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        portfolio = self._registry.get(portfolio_id)
        if portfolio is None:
            return None
        return self._history.capture(portfolio)

    def snapshot_history(
        self, portfolio_id: str, n: int = 20
    ) -> List[PortfolioSnapshot]:
        return self._history.history(portfolio_id, n)

    def rebalance_history(
        self, portfolio_id: str, n: int = 20
    ) -> List[RebalanceRecord]:
        return self._rebalancer._history.history(portfolio_id, n)

    # ── monitoring ────────────────────────────────────────────────────────────

    def run_health_check(self) -> List[PortfolioAlert]:
        return self._monitor.run_health_check()

    def alert_history(
        self, portfolio_id: Optional[str] = None, n: int = 50
    ) -> List[PortfolioAlert]:
        return self._monitor.alert_history(portfolio_id, n)

    # ── stats ────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        total = self._registry.count()
        all_p = self._registry.all()
        by_state: Dict[str, int] = {}
        for p in all_p:
            by_state[p.state.value] = by_state.get(p.state.value, 0) + 1

        return {
            "total_portfolios":  total,
            "by_state":          by_state,
            "registered_strategies": len(self._strategy_store),
            "timestamp":         datetime.now(timezone.utc).isoformat(),
        }
