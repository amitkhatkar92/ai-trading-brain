"""
iios/execution/analytics/snapshot/analytics_snapshot_history.py
================================================================
AnalyticsSnapshotHistory — bounded per-dimension version history.

Tracks historical snapshots grouped by:
  - analytics_session_id
  - execution_session_id
  - portfolio_id
  - strategy_id
  - workflow_id

Also provides a global ordered timeline of all snapshots.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import collections
import threading
from typing import Any, Deque, Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY
from .execution_analytics_snapshot import ExecutionAnalyticsSnapshot


class AnalyticsSnapshotHistory:
    """
    Bounded version history for ExecutionAnalyticsSnapshot objects.

    Thread-safe.
    """

    def __init__(self, maxlen: int = DEFAULT_MAX_HISTORY) -> None:
        self._maxlen  = maxlen
        self._lock    = threading.Lock()

        # Global timeline
        self._timeline: Deque[ExecutionAnalyticsSnapshot] = (
            collections.deque(maxlen=maxlen)
        )

        # Per-key indices (snapshot_id → list kept for version history)
        self._by_session:   Dict[str, Deque[ExecutionAnalyticsSnapshot]] = {}
        self._by_exec:      Dict[str, Deque[ExecutionAnalyticsSnapshot]] = {}
        self._by_portfolio: Dict[str, Deque[ExecutionAnalyticsSnapshot]] = {}
        self._by_strategy:  Dict[str, Deque[ExecutionAnalyticsSnapshot]] = {}
        self._by_workflow:  Dict[str, Deque[ExecutionAnalyticsSnapshot]] = {}

    def _deque(self) -> Deque[ExecutionAnalyticsSnapshot]:
        return collections.deque(maxlen=self._maxlen)

    # ── Add ───────────────────────────────────────────────────────────────────

    def add(self, snapshot: ExecutionAnalyticsSnapshot) -> None:
        with self._lock:
            self._timeline.append(snapshot)
            sid = snapshot.analytics_session_id
            if sid not in self._by_session:
                self._by_session[sid] = self._deque()
            self._by_session[sid].append(snapshot)

            eid = snapshot.execution_session_id
            if eid not in self._by_exec:
                self._by_exec[eid] = self._deque()
            self._by_exec[eid].append(snapshot)

            pid = snapshot.portfolio_id
            if pid and pid not in self._by_portfolio:
                self._by_portfolio[pid] = self._deque()
            if pid:
                self._by_portfolio[pid].append(snapshot)

            strat = snapshot.strategy_id
            if strat and strat not in self._by_strategy:
                self._by_strategy[strat] = self._deque()
            if strat:
                self._by_strategy[strat].append(snapshot)

            wf = snapshot.workflow_id
            if wf and wf not in self._by_workflow:
                self._by_workflow[wf] = self._deque()
            if wf:
                self._by_workflow[wf].append(snapshot)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def recent(self, n: int = 10) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            items = list(self._timeline)
        return items[-n:] if n > 0 else items

    def by_session(self, session_id: str) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            deq = self._by_session.get(session_id)
            return list(deq) if deq else []

    def by_execution_session(self, exec_id: str) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            deq = self._by_exec.get(exec_id)
            return list(deq) if deq else []

    def by_portfolio(self, portfolio_id: str) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            deq = self._by_portfolio.get(portfolio_id)
            return list(deq) if deq else []

    def by_strategy(self, strategy_id: str) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            deq = self._by_strategy.get(strategy_id)
            return list(deq) if deq else []

    def by_workflow(self, workflow_id: str) -> List[ExecutionAnalyticsSnapshot]:
        with self._lock:
            deq = self._by_workflow.get(workflow_id)
            return list(deq) if deq else []

    def latest_for_session(
        self, session_id: str
    ) -> Optional[ExecutionAnalyticsSnapshot]:
        items = self.by_session(session_id)
        return items[-1] if items else None

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._timeline)

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._by_session)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._timeline.clear()
            self._by_session.clear()
            self._by_exec.clear()
            self._by_portfolio.clear()
            self._by_strategy.clear()
            self._by_workflow.clear()
