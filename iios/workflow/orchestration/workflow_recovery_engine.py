"""
workflow_recovery_engine.py — iios.workflow.orchestration
----------------------------------------------------------
WorkflowRecoveryEngine — restores a failed or interrupted workflow
execution from its most-recent checkpoint.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .constants import WorkflowStatus
from .exceptions import WorkflowRecoveryError
from .workflow_checkpoint_manager import WorkflowCheckpoint, WorkflowCheckpointManager
from .workflow_context_manager import WorkflowContextManager
from .workflow_runtime import WorkflowRuntime

_log = get_logger(__name__)


class WorkflowRecoveryEngine:
    """
    Restores workflow execution state from the most-recent checkpoint.

    After restore, the WorkflowExecutor re-runs only the steps that
    have not yet completed (based on the restored step_statuses).

    Thread-safe — stateless.
    """

    def __init__(self, checkpoint_manager: Optional[WorkflowCheckpointManager] = None) -> None:
        self._checkpoint_manager = checkpoint_manager or WorkflowCheckpointManager()

    def recover(
        self,
        runtime:  WorkflowRuntime,
        ctx_mgr:  WorkflowContextManager,
    ) -> Optional[WorkflowCheckpoint]:
        """
        Attempt to recover a runtime from its latest checkpoint.

        Returns the applied checkpoint, or None if no checkpoint exists.

        Raises WorkflowRecoveryError if restore fails.
        """
        checkpoint = self._checkpoint_manager.get_latest(runtime.runtime_id)
        if checkpoint is None:
            _log.info(
                f"Recovery: no checkpoint for runtime={runtime.runtime_id!r} "
                f"— starting fresh"
            )
            return None

        _log.info(
            f"Recovery: restoring runtime={runtime.runtime_id!r} "
            f"from checkpoint={checkpoint.checkpoint_id!r}"
        )

        try:
            runtime.set_status(WorkflowStatus.RECOVERING)
            self._checkpoint_manager.restore(checkpoint, runtime)
            ctx_mgr.restore(checkpoint.context_snapshot)
        except Exception as exc:
            raise WorkflowRecoveryError(
                f"Failed to restore checkpoint {checkpoint.checkpoint_id!r}: {exc}"
            ) from exc

        return checkpoint

    def can_recover(self, runtime_id: str) -> bool:
        """Return True if a checkpoint exists for this runtime."""
        return self._checkpoint_manager.get_latest(runtime_id) is not None

    def checkpoint_count(self, runtime_id: str) -> int:
        return self._checkpoint_manager.checkpoint_count(runtime_id)
