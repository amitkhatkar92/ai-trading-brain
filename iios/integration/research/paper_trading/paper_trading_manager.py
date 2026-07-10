"""paper_trading_manager.py — High-level coordinator for paper trading sessions."""
from __future__ import annotations

import logging
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_RISK_FREE_RATE,
    SessionStatus,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    SessionNotFoundError,
    SessionStateError,
)
from iios.integration.research.paper_trading.paper_trading_registry  import PaperTradingRegistry
from iios.integration.research.paper_trading.accounts.account_manager import AccountManager
from iios.integration.research.paper_trading.core.paper_session       import PaperSession
from iios.integration.research.paper_trading.core.paper_history       import PaperHistory, PaperHistoryEntry
from iios.integration.research.paper_trading.market.market_simulator  import PriceBar
from iios.integration.research.paper_trading.simulation.simulation_engine import (
    PaperSessionResult,
    PaperTradingStrategy,
    SimulationEngine,
)

_log = logging.getLogger(__name__)


class PaperTradingManager:
    """
    Manages the full lifecycle of paper trading sessions.

    Responsibilities:
    - Create and register sessions
    - Delegate simulation runs to SimulationEngine
    - Store session results
    - Expose query / compare APIs
    """

    def __init__(
        self,
        registry:         PaperTradingRegistry,
        account_manager:  AccountManager,
        sim_engine:       SimulationEngine,
        history:          PaperHistory,
    ) -> None:
        self._registry   = registry
        self._accounts   = account_manager
        self._sim_engine = sim_engine
        self._history    = history
        self._results:   dict[str, PaperSessionResult] = {}

    # ── Session creation ──────────────────────────────────────────────────────

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
        # Validate account exists
        self._accounts.get_account(account_id)  # raises AccountNotFoundError if missing
        session = PaperSession.create(
            account_id    = account_id,
            strategy_id   = strategy_id,
            strategy_name = strategy_name,
            session_id    = session_id,
            tags          = tags,
            metadata      = metadata,
        )
        self._registry.register(session)
        self._history.append(PaperHistoryEntry.create(
            entity_type = "session",
            entity_id   = session.session_id,
            event_type  = "created",
            data        = {"account_id": account_id, "strategy_id": strategy_id},
        ))
        _log.debug("[PaperTradingManager] session created: %s", session.session_id)
        return session

    # ── Session execution ─────────────────────────────────────────────────────

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
        session = self._registry.get(session_id)
        account = self._accounts.get_account(session.account_id)

        self._history.append(PaperHistoryEntry.create(
            entity_type = "session",
            entity_id   = session_id,
            event_type  = "started",
        ))

        result = await self._sim_engine.run(
            session_id        = session_id,
            account           = account,
            config            = config or {},
            strategy          = strategy,
            bars_data         = bars_data,
            risk_free_rate    = risk_free_rate,
            benchmark_returns = benchmark_returns,
        )

        # Persist result and update registry
        self._results[session_id] = result
        self._registry.update(result.session)
        self._accounts.update_account(result.account)

        self._history.append(PaperHistoryEntry.create(
            entity_type = "session",
            entity_id   = session_id,
            event_type  = "completed",
            data        = {
                "total_trades": result.stats.total_trades,
                "total_return": result.stats.total_return,
                "sharpe_ratio": result.stats.sharpe_ratio,
            },
        ))
        _log.info(
            "[PaperTradingManager] session completed: %s  trades=%d  return=%.2f%%",
            session_id,
            result.stats.total_trades,
            result.stats.total_return * 100,
        )
        return result

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> PaperSession:
        return self._registry.get(session_id)

    def get_result(self, session_id: str) -> Optional[PaperSessionResult]:
        return self._results.get(session_id)

    def list_sessions(
        self,
        *,
        status:     Optional[SessionStatus] = None,
        account_id: Optional[str]           = None,
    ) -> list[PaperSession]:
        sessions = self._registry.all_sessions()
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        if account_id is not None:
            sessions = [s for s in sessions if s.account_id == account_id]
        return sessions

    def cancel_session(self, session_id: str) -> None:
        session = self._registry.get(session_id)
        if session.is_terminal():
            raise SessionStateError(
                f"Session {session_id!r} is already terminal (status={session.status.value})"
            )
        session.status = SessionStatus.CANCELLED
        self._registry.update(session)

    def compare_sessions(self, session_ids: list[str]) -> dict[str, Any]:
        results = []
        for sid in session_ids:
            r = self._results.get(sid)
            if r is not None:
                results.append({
                    "session_id":    sid,
                    "sharpe_ratio":  r.stats.sharpe_ratio,
                    "total_return":  r.stats.total_return,
                    "max_drawdown":  r.stats.max_drawdown,
                    "win_rate":      r.stats.win_rate,
                    "total_trades":  r.stats.total_trades,
                })
        ranked = sorted(results, key=lambda s: s.get("sharpe_ratio", float("-inf")), reverse=True)
        return {"total": len(ranked), "ranked": ranked}

    def stats(self) -> dict[str, Any]:
        return {
            "sessions": self._registry.stats(),
            "accounts": self._accounts.stats(),
            "results":  len(self._results),
            "history":  self._history.count(),
        }
