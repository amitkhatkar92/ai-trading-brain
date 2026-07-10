"""deployment/rollback_manager.py — Records deployment history and executes rollbacks."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from iios.integration.research.learning.deployment.deployment_registry import DeploymentRecord, DeploymentRegistry
from iios.integration.research.learning.learning_constants import DeploymentStatus
from iios.integration.research.learning.learning_exceptions import DeploymentError


@dataclass
class RollbackRecord:
    """Audit record of a rollback event."""
    rollback_id:    str
    from_version:   str
    to_version:     str
    model_id:       str
    reason:         str
    triggered_at:   float
    triggered_by:   str


class RollbackManager:
    """
    Maintains a per-model deployment history and executes rollback operations.

    A rollback retires the current champion and re-activates the previous one.
    """

    def __init__(self, registry: DeploymentRegistry) -> None:
        self._registry = registry
        self._history: dict[str, deque[DeploymentRecord]] = {}
        self._rollbacks: list[RollbackRecord] = []
        self._lock = threading.RLock()

    def push_champion(self, record: DeploymentRecord) -> None:
        """Record a newly deployed champion so it can be rolled back later."""
        with self._lock:
            dq = self._history.setdefault(record.model_id, deque(maxlen=10))
            dq.append(record)

    def rollback(
        self,
        model_id:     str,
        reason:       str = "",
        triggered_by: str = "system",
    ) -> Optional[DeploymentRecord]:
        """
        Retire the current champion and re-activate the previous one.

        Returns the restored DeploymentRecord, or None if no history exists.
        """
        with self._lock:
            dq = self._history.get(model_id)
            if not dq or len(dq) < 2:
                return None

            # Pop current (latest) champion
            current = dq.pop()
            previous = dq[-1]

        # Retire current champion
        current.retire()

        # Re-activate previous
        previous.status     = DeploymentStatus.CHAMPION
        previous.updated_at = time.time()
        previous.retired_at = None

        import uuid
        rb = RollbackRecord(
            rollback_id  = f"rb_{uuid.uuid4().hex[:10]}",
            from_version = current.model_version,
            to_version   = previous.model_version,
            model_id     = model_id,
            reason       = reason,
            triggered_at = time.time(),
            triggered_by = triggered_by,
        )
        with self._lock:
            self._rollbacks.append(rb)

        return previous

    def rollback_history(self, model_id: Optional[str] = None) -> list[RollbackRecord]:
        with self._lock:
            if model_id is not None:
                return [r for r in self._rollbacks if r.model_id == model_id]
            return list(self._rollbacks)

    def deployment_history(self, model_id: str) -> list[DeploymentRecord]:
        with self._lock:
            dq = self._history.get(model_id)
            return list(dq) if dq else []

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "models_tracked": len(self._history),
                "total_rollbacks": len(self._rollbacks),
            }
