"""
decision_engine_worker.py — iios.decision.engine
==================================================
Background worker thread for asynchronous decision processing.

Workers pull requests from the :class:`DecisionScheduler` queue and forward
them to :class:`DecisionManager` for processing.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .decision_manager   import DecisionManager
from .decision_response  import DecisionResponse
from .decision_scheduler import DecisionScheduler

_log = get_logger(__name__)

_POLL_INTERVAL_S: float = 0.05   # 50 ms idle poll


class DecisionEngineWorker:
    """
    Daemon thread that drains the scheduler queue.

    Parameters
    ----------
    worker_id :   Human-readable identifier (for logging).
    scheduler :   Shared :class:`DecisionScheduler`.
    manager :     Shared :class:`DecisionManager`.
    on_complete : Callback invoked on successful pipeline completion.
    on_fail :     Callback invoked on pipeline failure.
    """

    def __init__(
        self,
        worker_id:   str,
        scheduler:   DecisionScheduler,
        manager:     DecisionManager,
        on_complete: Optional[Callable[[DecisionResponse], None]] = None,
        on_fail:     Optional[Callable[[DecisionResponse], None]] = None,
    ) -> None:
        self._worker_id   = worker_id
        self._scheduler   = scheduler
        self._manager     = manager
        self._on_complete = on_complete
        self._on_fail     = on_fail
        self._stop_event  = threading.Event()
        self._thread:     Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target  = self._run,
            name    = f"de-worker-{self._worker_id}",
            daemon  = True,
        )
        self._thread.start()
        _log.debug(f"DecisionEngineWorker {self._worker_id}: started")

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the worker to stop and wait for the thread to join."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        _log.debug(f"DecisionEngineWorker {self._worker_id}: stopped")

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop_event.is_set():
            request = self._scheduler.next()
            if request is None:
                time.sleep(_POLL_INTERVAL_S)
                continue
            try:
                response = self._manager.process(request)
                if response.is_success and self._on_complete:
                    self._on_complete(response)
                elif response.is_failed and self._on_fail:
                    self._on_fail(response)
            except Exception as exc:
                _log.warning(
                    f"DecisionEngineWorker {self._worker_id}: "
                    f"unhandled error processing {request.request_id!r}: {exc}"
                )
