"""paper_trading_engine.py — Singleton facade for the Paper Trading & Market Simulation Framework."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    PAPER_TRADING_ENGINE_VERSION,
    DEFAULT_RISK_FREE_RATE,
    PaperEngineStatus,
    SessionStatus,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    EngineAlreadyRunningError,
    EngineInitializationError,
    EngineNotRunningError,
)
from iios.integration.research.paper_trading.paper_trading_factory   import PaperTradingFactory
from iios.integration.research.paper_trading.paper_trading_manager   import PaperTradingManager
from iios.integration.research.paper_trading.core.paper_account      import PaperAccount
from iios.integration.research.paper_trading.core.paper_session      import PaperSession
from iios.integration.research.paper_trading.market.market_simulator import PriceBar
from iios.integration.research.paper_trading.simulation.simulation_engine import (
    PaperSessionResult,
    PaperTradingStrategy,
)

_log = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Singleton facade for the Paper Trading & Market Simulation Framework.

    Provides a single, stable API that hides all internal complexity.

    Usage::

        engine = get_paper_trading_engine(auto_start=True)
        account = engine.create_account("My Strategy Account", initial_capital=500_000)
        session = engine.create_session(account.account_id, strategy_id="strat_1")
        result  = await engine.run_session(session.session_id, my_strategy, bars_data)
    """

    def __init__(self) -> None:
        self._status:   PaperEngineStatus          = PaperEngineStatus.STOPPED
        self._started_at: Optional[float]          = None
        self._manager:  Optional[PaperTradingManager] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._status == PaperEngineStatus.RUNNING:
            raise EngineAlreadyRunningError("PaperTradingEngine is already running")
        self._status = PaperEngineStatus.INITIALIZING
        try:
            self._manager = PaperTradingManager(
                registry        = PaperTradingFactory.create_registry(),
                account_manager = PaperTradingFactory.create_account_manager(),
                sim_engine      = PaperTradingFactory.create_simulation_engine(),
                history         = PaperTradingFactory.create_history(),
            )
            self._status     = PaperEngineStatus.RUNNING
            self._started_at = time.time()
            _log.info(
                "[PaperTradingEngine] started  version=%s",
                PAPER_TRADING_ENGINE_VERSION,
            )
        except Exception as exc:
            self._status = PaperEngineStatus.ERROR
            raise EngineInitializationError(f"Init failed: {exc}") from exc

    async def stop(self) -> None:
        self._status  = PaperEngineStatus.STOPPED
        self._manager = None
        _log.info("[PaperTradingEngine] stopped")

    def is_running(self) -> bool:
        return self._status == PaperEngineStatus.RUNNING

    def status(self) -> PaperEngineStatus:
        return self._status

    def uptime_sec(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    # ── Account management ────────────────────────────────────────────────────

    def create_account(
        self,
        name:            str,
        initial_capital: float = 1_000_000.0,
        *,
        account_id:      Optional[str] = None,
        leverage:        float          = 1.0,
    ) -> PaperAccount:
        self._assert_running()
        return self._manager._accounts.create_account(  # type: ignore[union-attr]
            name            = name,
            initial_capital = initial_capital,
            account_id      = account_id,
            leverage        = leverage,
        )

    def get_account(self, account_id: str) -> PaperAccount:
        self._assert_running()
        return self._manager._accounts.get_account(account_id)  # type: ignore[union-attr]

    # ── Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        account_id:    str,
        strategy_id:   Optional[str] = None,
        strategy_name: Optional[str] = None,
        *,
        session_id:    Optional[str] = None,
        tags:          Optional[list] = None,
        metadata:      Optional[dict] = None,
    ) -> PaperSession:
        self._assert_running()
        return self._manager.create_session(  # type: ignore[union-attr]
            account_id    = account_id,
            strategy_id   = strategy_id,
            strategy_name = strategy_name,
            session_id    = session_id,
            tags          = tags,
            metadata      = metadata,
        )

    async def run_session(
        self,
        session_id:        str,
        strategy:          PaperTradingStrategy,
        bars_data:         dict[str, list[PriceBar]],
        config:            Optional[dict]         = None,
        *,
        risk_free_rate:    float                  = DEFAULT_RISK_FREE_RATE,
        benchmark_returns: Optional[list[float]] = None,
    ) -> PaperSessionResult:
        self._assert_running()
        return await self._manager.run_session(  # type: ignore[union-attr]
            session_id        = session_id,
            strategy          = strategy,
            bars_data         = bars_data,
            config            = config,
            risk_free_rate    = risk_free_rate,
            benchmark_returns = benchmark_returns,
        )

    def get_session(self, session_id: str) -> PaperSession:
        self._assert_running()
        return self._manager.get_session(session_id)  # type: ignore[union-attr]

    def get_result(self, session_id: str) -> Optional[PaperSessionResult]:
        self._assert_running()
        return self._manager.get_result(session_id)  # type: ignore[union-attr]

    def cancel_session(self, session_id: str) -> None:
        self._assert_running()
        self._manager.cancel_session(session_id)  # type: ignore[union-attr]

    def list_sessions(
        self,
        *,
        status:     Optional[SessionStatus] = None,
        account_id: Optional[str]           = None,
    ) -> list[PaperSession]:
        self._assert_running()
        return self._manager.list_sessions(  # type: ignore[union-attr]
            status=status, account_id=account_id
        )

    def compare_sessions(self, session_ids: list[str]) -> dict[str, Any]:
        self._assert_running()
        return self._manager.compare_sessions(session_ids)  # type: ignore[union-attr]

    def stats(self) -> dict[str, Any]:
        self._assert_running()
        return {
            "version": PAPER_TRADING_ENGINE_VERSION,
            "uptime_sec": self.uptime_sec(),
            "status": self._status.value,
            **self._manager.stats(),  # type: ignore[union-attr]
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self._status != PaperEngineStatus.RUNNING:
            raise EngineNotRunningError(
                f"PaperTradingEngine is not running (status={self._status.value})"
            )


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[PaperTradingEngine] = None
_lock = threading.Lock()


def get_paper_trading_engine(*, auto_start: bool = False) -> PaperTradingEngine:
    """
    Return the global PaperTradingEngine singleton.

    If *auto_start* is True and the engine is not yet running, it is started
    synchronously using ``asyncio.run()``.
    """
    global _instance
    with _lock:
        if _instance is None:
            _instance = PaperTradingEngine()
    if auto_start and not _instance.is_running():
        import asyncio
        asyncio.run(_instance.start())
    return _instance


def reset_paper_trading_engine() -> None:
    """Reset the singleton (for testing only)."""
    global _instance
    with _lock:
        _instance = None
