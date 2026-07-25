"""
workflow_resource_manager.py — iios.workflow.orchestration
-----------------------------------------------------------
WorkflowResourceManager — tracks and limits concurrent workflow
execution resources (execution slots).

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowResourceError

_log = get_logger(__name__)


class WorkflowResourceManager:
    """
    Semaphore-based resource manager for concurrent workflow slots.

    Prevents the system from running more simultaneous workflows than
    the configured limit, ensuring predictable resource consumption.

    Thread-safe.
    """

    def __init__(self, max_concurrent: int = 32) -> None:
        if max_concurrent < 1:
            raise WorkflowResourceError(
                f"max_concurrent must be >= 1, got {max_concurrent}"
            )
        self._max        = max_concurrent
        self._semaphore  = threading.Semaphore(max_concurrent)
        self._lock       = threading.Lock()
        self._in_use     = 0

    def acquire(self, blocking: bool = True, timeout: float = 30.0) -> bool:
        """
        Acquire an execution slot.

        Returns True if acquired, False if not available (non-blocking)
        or timed out.

        Raises WorkflowResourceError if timeout is exceeded (blocking mode).
        """
        acquired = self._semaphore.acquire(
            blocking=blocking,
            timeout=timeout if blocking else None,
        )
        if acquired:
            with self._lock:
                self._in_use += 1
            _log.debug(
                f"ResourceManager: acquired slot "
                f"({self._in_use}/{self._max} in use)"
            )
        else:
            if blocking:
                raise WorkflowResourceError(
                    f"Resource timeout: no execution slot available within "
                    f"{timeout:.1f}s (max_concurrent={self._max})"
                )
        return acquired

    def release(self) -> None:
        """Release an execution slot."""
        self._semaphore.release()
        with self._lock:
            self._in_use = max(0, self._in_use - 1)
        _log.debug(
            f"ResourceManager: released slot "
            f"({self._in_use}/{self._max} in use)"
        )

    def available(self) -> int:
        with self._lock:
            return max(0, self._max - self._in_use)

    def in_use(self) -> int:
        with self._lock:
            return self._in_use

    @property
    def max_concurrent(self) -> int:
        return self._max

    def health(self) -> Dict[str, Any]:
        return {
            "max_concurrent": self._max,
            "in_use":         self.in_use(),
            "available":      self.available(),
        }
