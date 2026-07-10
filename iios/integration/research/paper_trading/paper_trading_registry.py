"""paper_trading_registry.py — Thread-safe registry of PaperSession entities."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    SessionStatus,
    DEFAULT_MAX_SESSIONS,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    SessionAlreadyExistsError,
    SessionCapacityError,
    SessionNotFoundError,
)
from iios.integration.research.paper_trading.core.paper_session import PaperSession


class PaperTradingRegistry:
    """
    Central in-memory store for all PaperSession entities.

    Thread-safe via a single RLock.  Intended as a singleton managed by
    PaperTradingEngine.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        self._store:   dict[str, PaperSession] = {}
        self._max      = max_sessions
        self._lock     = threading.RLock()
        self._total_registered = 0

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, session: PaperSession) -> None:
        with self._lock:
            if session.session_id in self._store:
                raise SessionAlreadyExistsError(
                    f"Session {session.session_id!r} already exists"
                )
            if len(self._store) >= self._max:
                raise SessionCapacityError(
                    f"Registry capacity ({self._max}) reached"
                )
            self._store[session.session_id] = session
            self._total_registered += 1

    def get(self, session_id: str) -> PaperSession:
        with self._lock:
            if session_id not in self._store:
                raise SessionNotFoundError(f"Session {session_id!r} not found")
            return self._store[session_id]

    def update(self, session: PaperSession) -> None:
        with self._lock:
            if session.session_id not in self._store:
                raise SessionNotFoundError(f"Session {session.session_id!r} not found")
            self._store[session.session_id] = session

    def remove(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._store:
                raise SessionNotFoundError(f"Session {session_id!r} not found")
            del self._store[session_id]

    def has(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_sessions(self) -> list[PaperSession]:
        with self._lock:
            return list(self._store.values())

    def find_by_status(self, status: SessionStatus) -> list[PaperSession]:
        with self._lock:
            return [s for s in self._store.values() if s.status == status]

    def find_by_account(self, account_id: str) -> list[PaperSession]:
        with self._lock:
            return [s for s in self._store.values() if s.account_id == account_id]

    def find_by_strategy(self, strategy_id: str) -> list[PaperSession]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.strategy_id == strategy_id
            ]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for s in self._store.values():
                by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
            return {
                "total":            len(self._store),
                "total_registered": self._total_registered,
                "capacity":         self._max,
                "by_status":        by_status,
            }
