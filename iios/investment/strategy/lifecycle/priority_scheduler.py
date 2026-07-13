"""iios/investment/strategy/lifecycle/priority_scheduler.py
Priority-aware concurrent strategy dispatcher.

Pulls from an ExecutionQueue in priority order and dispatches work to a
thread pool, respecting the max_concurrent slot limit and preventing
duplicate in-flight execution for the same strategy_id.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from iios.investment.strategy.lifecycle.execution_queue import (
    ExecutionQueue,
    ExecutionRequest,
    SchedulePriority,
)

logger = logging.getLogger(__name__)


class PriorityScheduler:
    """
    Drives concurrent strategy execution from a priority queue.

    - Dequeues in priority order (CRITICAL → HIGH → NORMAL → LOW → BACKGROUND).
    - Enforces a max_concurrent ceiling on simultaneous executions.
    - Tracks in-flight strategy IDs; a strategy already running is skipped
      to avoid duplicate concurrent execution of the same ID.
    - After each strategy completes, calls tick() to dispatch the next waiting
      request, keeping the concurrency slots fully utilised.
    """

    def __init__(
        self,
        queue: ExecutionQueue,
        executor_fn: Callable[[ExecutionRequest], None],
        max_concurrent: int = 32,
        thread_pool: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self._queue = queue
        self._executor_fn = executor_fn
        self._max_concurrent = max(1, max_concurrent)
        self._pool = thread_pool or ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="iios-sched",
        )
        self._lock = threading.RLock()
        self._in_flight: Dict[str, Future] = {}   # strategy_id → Future
        self._paused = False

    # ── Control ────────────────────────────────────────────────────────────────

    def pause(self) -> None:
        """Suspend dispatch. In-flight work continues to completion."""
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Resume dispatch and immediately attempt to fill empty slots."""
        with self._lock:
            self._paused = False
        self.tick()

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the underlying thread pool."""
        self._pool.shutdown(wait=wait)

    # ── Scheduling ─────────────────────────────────────────────────────────────

    def submit(
        self,
        strategy_id: str,
        context: object,
        priority: SchedulePriority = SchedulePriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        deadline: object = None,
    ) -> Optional[ExecutionRequest]:
        """
        Enqueue a strategy execution request.

        Returns the request if accepted, or None if the strategy is already
        in-flight (duplicate guard).
        """
        with self._lock:
            if strategy_id in self._in_flight:
                logger.debug(
                    "Strategy %s already in-flight — submission skipped", strategy_id
                )
                return None

        req = ExecutionRequest(
            priority=int(priority),
            strategy_id=strategy_id,
            context_ref=context,
            dependencies=dependencies or [],
            deadline=deadline,
        )
        self._queue.enqueue(req)
        return req

    def tick(self) -> int:
        """
        Dispatch as many queued requests as possible within the concurrency limit.

        Should be called:
        - After enqueuing new requests
        - After a strategy completes (to fill the freed slot)
        - Periodically by the scheduler background loop

        Returns the number of strategies dispatched in this tick.
        """
        dispatched = 0
        while True:
            with self._lock:
                if self._paused:
                    break
                available = self._max_concurrent - len(self._in_flight)
                if available <= 0:
                    break
                req = self._queue.dequeue()
                if req is None:
                    break
                if req.strategy_id in self._in_flight:
                    # Rare race: enqueued twice before either was dispatched
                    continue
                future = self._pool.submit(self._run, req)
                self._in_flight[req.strategy_id] = future
            dispatched += 1
        return dispatched

    # ── Observability ──────────────────────────────────────────────────────────

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    @property
    def in_flight_ids(self) -> List[str]:
        with self._lock:
            return list(self._in_flight.keys())

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self, req: ExecutionRequest) -> None:
        """Thread-pool target: execute one request and free the slot."""
        try:
            self._executor_fn(req)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Strategy %s raised during scheduled execution", req.strategy_id
            )
        finally:
            with self._lock:
                self._in_flight.pop(req.strategy_id, None)
            # Fill the now-free slot
            self.tick()
