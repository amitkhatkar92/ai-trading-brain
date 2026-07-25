"""
workflow_history.py — iios.workflow.orchestration
--------------------------------------------------
WorkflowHistory — bounded, thread-safe history of
WorkflowExecutionResult objects.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_HISTORY, WorkflowStatus
from .workflow_runtime import WorkflowExecutionResult


class WorkflowHistory:
    """
    Bounded, thread-safe execution result history.

    Oldest entries are evicted automatically when capacity is exceeded.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max     = max_entries
        self._results: deque[WorkflowExecutionResult]      = deque(maxlen=max_entries)
        self._by_id:   Dict[str, WorkflowExecutionResult]  = {}
        self._by_wf:   Dict[str, List[str]]                = {}
        self._lock     = threading.Lock()

    def record(self, result: WorkflowExecutionResult) -> None:
        with self._lock:
            if len(self._results) == self._max and self._results:
                oldest = self._results[0]
                self._by_id.pop(oldest.result_id, None)
            self._results.append(result)
            self._by_id[result.result_id] = result
            self._by_wf.setdefault(result.workflow_id, []).append(result.result_id)

    def get(self, result_id: str) -> Optional[WorkflowExecutionResult]:
        with self._lock:
            return self._by_id.get(result_id)

    def recent(self, n: int = 20) -> List[WorkflowExecutionResult]:
        with self._lock:
            items = list(self._results)
        return list(reversed(items[-n:]))

    def by_workflow(self, workflow_id: str) -> List[WorkflowExecutionResult]:
        with self._lock:
            ids  = list(self._by_wf.get(workflow_id, []))
            return [self._by_id[rid] for rid in ids if rid in self._by_id]

    def successes(self, n: int = 20) -> List[WorkflowExecutionResult]:
        return [r for r in self.recent(n) if r.is_success]

    def failures(self, n: int = 20) -> List[WorkflowExecutionResult]:
        return [r for r in self.recent(n) if r.is_failure]

    def count(self) -> int:
        with self._lock:
            return len(self._results)

    def clear(self) -> int:
        with self._lock:
            n = len(self._results)
            self._results.clear()
            self._by_id.clear()
            self._by_wf.clear()
        return n
