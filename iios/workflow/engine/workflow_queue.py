"""
workflow_queue.py — iios.workflow.engine
-----------------------------------------
WorkflowQueue — bounded, thread-safe, priority-ordered queue for
pending workflow execution requests.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import heapq
import threading
from typing import Dict, List, Optional, Set

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_QUEUE_SIZE
from .exceptions import WorkflowQueueCapacityError
from .workflow_priority import PriorityWorkflowItem

_log = get_logger(__name__)


class WorkflowQueue:
    """
    Thread-safe, bounded, priority-ordered queue.

    Lower priority integers = higher urgency (min-heap).
    Items with identical priority are dequeued in insertion order (FIFO).
    """

    def __init__(self, max_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self._max       = max_size
        self._heap:     List[PriorityWorkflowItem]      = []
        self._index:    Dict[str, PriorityWorkflowItem] = {}  # item_id → item
        self._cancelled: Set[str]                       = set()  # cancelled item_ids
        self._lock      = threading.Lock()

    # ----------------------------------------------------------------
    # Enqueue
    # ----------------------------------------------------------------

    def enqueue(self, item: PriorityWorkflowItem) -> PriorityWorkflowItem:
        """
        Add a pre-created PriorityWorkflowItem to the queue.

        Raises:
            WorkflowQueueCapacityError if queue is full.
        """
        with self._lock:
            active = len(self._heap) - len(self._cancelled)
            if active >= self._max:
                raise WorkflowQueueCapacityError(limit=self._max)
            heapq.heappush(self._heap, item)
            self._index[item.item_id] = item
        _log.debug(
            f"Queue: enqueued item={item.item_id!r} "
            f"priority={item.priority} request={item.request.request_id!r}"
        )
        return item

    # ----------------------------------------------------------------
    # Dequeue
    # ----------------------------------------------------------------

    def dequeue(self) -> Optional[PriorityWorkflowItem]:
        """
        Remove and return the highest-priority non-cancelled item.

        Returns None if queue is empty.
        """
        with self._lock:
            while self._heap:
                item = heapq.heappop(self._heap)
                self._index.pop(item.item_id, None)
                if item.item_id not in self._cancelled:
                    return item
                self._cancelled.discard(item.item_id)
        return None

    # ----------------------------------------------------------------
    # Cancel
    # ----------------------------------------------------------------

    def cancel(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self._index:
                self._cancelled.add(item_id)
                return True
        return False

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def size(self) -> int:
        """Approximate count of non-cancelled items."""
        with self._lock:
            return max(0, len(self._heap) - len(self._cancelled))

    def is_empty(self) -> bool:
        return self.size() == 0

    def peek(self) -> Optional[PriorityWorkflowItem]:
        """Return the top item without removing it (may be stale)."""
        with self._lock:
            return self._heap[0] if self._heap else None

    def clear(self) -> int:
        """Clear all items. Returns the count cleared."""
        with self._lock:
            n = len(self._heap)
            self._heap.clear()
            self._index.clear()
            self._cancelled.clear()
            self._seq = 0
        return n

    @property
    def max_size(self) -> int:
        return self._max
