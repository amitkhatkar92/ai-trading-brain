"""iios/investment/portfolio/portfolio_intelligence_engine.py
Top-level facade for the Portfolio & Risk Intelligence Engine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    PORTFOLIO_ENGINE_SYSTEM_ID,
    PORTFOLIO_ENGINE_VERSION,
    PortfolioObjective,
    PortfolioType,
)
from iios.investment.portfolio.portfolio_exceptions import (
    PortfolioEngineAlreadyRunningError,
    PortfolioEngineNotInitializedError,
)
from iios.investment.portfolio.portfolio_manager import (
    PortfolioManager,
    get_portfolio_manager,
    reset_portfolio_manager,
)
from iios.investment.portfolio.portfolio_registry import (
    PortfolioRegistry,
    get_portfolio_registry,
    reset_portfolio_registry,
)
from iios.investment.portfolio.core.portfolio_intelligence import PortfolioIntelligence
from iios.investment.portfolio.core.portfolio_profile import PortfolioProfile
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot
from iios.investment.portfolio.core.position import Position


class PortfolioIntelligenceEngine:
    """
    Top-level facade for the Portfolio & Risk Intelligence Engine.
    Provides the public API consumed by higher IIOS layers.
    """

    VERSION   = PORTFOLIO_ENGINE_VERSION
    SYSTEM_ID = PORTFOLIO_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.RLock          = threading.RLock()
        self._running:  bool                     = False
        self._manager:  PortfolioManager | None  = None
        self._registry: PortfolioRegistry | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  PortfolioManager  | None = None,
        registry: PortfolioRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise PortfolioEngineAlreadyRunningError()
            self._registry = registry or get_portfolio_registry()
            self._manager  = manager  or get_portfolio_manager()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running  = False
            self._manager  = None
            self._registry = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── portfolio management ─────────────────────────────────────────────────

    def create_portfolio(
        self,
        name:           str              = "",
        portfolio_type: PortfolioType    = PortfolioType.EQUITY,
        objective:      PortfolioObjective = PortfolioObjective.GROWTH,
        cash:           float            = 0.0,
        **kwargs: Any,
    ) -> PortfolioProfile:
        self._require_running()
        return self._manager.create_portfolio(
            name=name, portfolio_type=portfolio_type,
            objective=objective, cash=cash, **kwargs,
        )

    def add_position(self, portfolio_id: str, position: Position) -> None:
        self._require_running()
        self._manager.add_position(portfolio_id, position)

    def remove_position(self, portfolio_id: str, position_id: str) -> None:
        self._require_running()
        self._manager.remove_position(portfolio_id, position_id)

    def update_position_price(
        self, portfolio_id: str, position_id: str, price: float
    ) -> Position:
        self._require_running()
        return self._manager.update_position_price(portfolio_id, position_id, price)

    def update_cash(self, portfolio_id: str, amount: float) -> None:
        self._require_running()
        self._manager.update_cash(portfolio_id, amount)

    # ── intelligence API ─────────────────────────────────────────────────────

    def analyze(self, portfolio_id: str, **kwargs: Any) -> PortfolioIntelligence:
        self._require_running()
        return self._manager.analyze(portfolio_id, **kwargs)

    async def analyze_async(self, portfolio_id: str, **kwargs: Any) -> PortfolioIntelligence:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.analyze(portfolio_id, **kwargs)
        )

    def get_latest(self, portfolio_id: str) -> PortfolioIntelligence:
        self._require_running()
        return self._manager.get_latest(portfolio_id)

    def get_profile(self, portfolio_id: str) -> PortfolioProfile:
        self._require_running()
        return self._manager.get_profile(portfolio_id)

    def summary(self, portfolio_id: str) -> PortfolioSnapshot:
        self._require_running()
        return self._manager.summary(portfolio_id)

    def recent(self, n: int = 10) -> list[PortfolioIntelligence]:
        self._require_running()
        return self._manager.recent(n)

    def health(self) -> dict[str, Any]:
        return {
            "status":    "running" if self._running else "stopped",
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
        }

    def stats(self) -> dict[str, Any]:
        self._require_running()
        return self._manager.statistics()

    # ── internal ─────────────────────────────────────────────────────────────

    def _require_running(self) -> None:
        if not self._running or self._manager is None:
            raise PortfolioEngineNotInitializedError(
                "PortfolioIntelligenceEngine is not initialized. Call initialize() first."
            )


# ── module-level singleton ────────────────────────────────────────────────────

_engine_lock:     threading.Lock                       = threading.Lock()
_engine_instance: PortfolioIntelligenceEngine | None   = None


def get_portfolio_engine() -> PortfolioIntelligenceEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = PortfolioIntelligenceEngine()
        return _engine_instance


def reset_portfolio_engine() -> None:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None:
            _engine_instance.shutdown()
        _engine_instance = None
