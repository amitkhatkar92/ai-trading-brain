"""
workflow_context_manager.py — iios.workflow.orchestration
----------------------------------------------------------
WorkflowContextManager — thread-safe context store for a single
workflow execution.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


class WorkflowContextManager:
    """
    Thread-safe context store for a single workflow execution.

    Each workflow execution gets its own context manager.  Steps read
    inputs from the context and write outputs back to it.  The context
    evolves as the workflow progresses.
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(initial_data or {})
        self._lock = threading.RLock()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    # ── Write ─────────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def merge(self, data: Dict[str, Any]) -> None:
        """Merge a dict of values into the context (additive, no delete)."""
        with self._lock:
            self._data.update(data)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
        return False

    # ── Step I/O mapping ──────────────────────────────────────────────────────

    def resolve_inputs(self, input_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Resolve step inputs from context using a mapping.

        mapping: {context_key → step_input_key}
        Returns: {step_input_key → value_from_context}
        """
        with self._lock:
            return {
                step_key: self._data.get(ctx_key)
                for ctx_key, step_key in input_mapping.items()
            }

    def apply_outputs(self, outputs: Dict[str, Any], output_mapping: Dict[str, str]) -> None:
        """
        Write step outputs back to context using a mapping.

        outputs: {step_output_key → value}
        mapping: {step_output_key → context_key}
        """
        with self._lock:
            for step_key, ctx_key in output_mapping.items():
                if step_key in outputs:
                    self._data[ctx_key] = outputs[step_key]

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def restore(self, snapshot: Dict[str, Any]) -> None:
        with self._lock:
            self._data = dict(snapshot)

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
