"""
Task Queue — Priority-Based Work Distribution for All 25 Agents
===============================================================
Every agent can post work items (tasks) to any other agent via this
queue.  Tasks are executed in priority order:

    CRITICAL → HIGH → NORMAL → LOW

This enables:
  • The Orchestrator to broadcast "analyse market NOW" to all agents
  • The Risk Manager to stop the Execution Engine with CRITICAL priority
  • Learning Engine to schedule EOD analysis at LOW priority without
    blocking live trading

Threading model
---------------
  Each agent that wants to consume tasks starts a dedicated worker thread
  via  TaskQueue.start_worker(agent_name).  Workers keep running until
  TaskQueue.stop_worker(agent_name) is called, or the queue is shut down.

Quick reference
---------------
    tq = get_task_queue()

    # Submit a task
    task_id = tq.submit(Task(
        agent_name = "RiskManagerAI",
        fn         = lambda: risk_manager.check(),
        priority   = Priority.CRITICAL,
    ))

    # Start a worker for an agent
    tq.start_worker("RiskManagerAI")

    # Cancel a pending task
    tq.cancel(task_id)

    # Graceful shutdown
    tq.shutdown()
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from utils import get_logger

log = get_logger(__name__)


# ── Priority Enum ─────────────────────────────────────────────────────────────

class Priority(IntEnum):
    """Lower integer = higher priority (matches heapq min-heap order)."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3


# ── Task Dataclass ────────────────────────────────────────────────────────────

@dataclass
class Task:
    """
    A unit of work assigned to a specific agent.

    Parameters
    ----------
    agent_name  : Target agent that should execute this task
    fn          : Callable to invoke (no arguments — use a lambda or partial)
    priority    : Scheduling priority (default NORMAL)
    deadline    : Absolute monotonic time by which the task must start
                  (None = no deadline)
    description : Human-readable label for logging / diagnostics
    """
    agent_name  : str
    fn          : Callable[[], Any]
    priority    : Priority               = Priority.NORMAL
    deadline    : Optional[float]        = None     # time.monotonic()
    description : str                    = ""

    # Auto-assigned — do not set manually
    task_id     : str                    = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at  : float                  = field(default_factory=time.monotonic)
    retry_count : int                    = 0
    max_retries : int                    = 2

    @property
    def is_overdue(self) -> bool:
        return self.deadline is not None and time.monotonic() > self.deadline

    def __lt__(self, other: "Task") -> bool:
        # Used by heapq to break ties: earlier creation time wins
        return self.created_at < other.created_at


# ── Internal heap item ────────────────────────────────────────────────────────

# Item stored in the heap: (priority_int, sequence, Task)
# sequence is a monotonically-increasing counter to guarantee stable ordering
# when two tasks share the same priority.
_HeapItem = Tuple[int, int, Task]


# ── Task Queue ────────────────────────────────────────────────────────────────

class TaskQueue:
    """
    Thread-safe, priority-ordered task dispatcher.

    One shared heap stores tasks for ALL agents.
    Each agent runs its own worker thread that pulls only tasks
    addressed to itself.
    """

    MAX_RETRIES    = 2
    WORKER_TIMEOUT = 0.2    # seconds to wait in each polling loop

    def __init__(self):
        self._heap     : List[_HeapItem]      = []
        self._counter              = itertools.count()
        self._lock                 = threading.Lock()
        self._not_empty            = threading.Condition(self._lock)
        self._cancelled : Set[str]            = set()
        self._completed : List[Dict[str, Any]] = []
        self._failed    : List[Dict[str, Any]] = []
        self._workers   : Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event]  = {}
        self._running   = True
        log.info("[TaskQueue] Initialised.")

    # ── Submit ──────────────────────────────────────────────────────────────

    def submit(self, task: Task) -> str:
        """
        Add a task to the queue.  Returns the task_id for tracking.

        If the task has a deadline and is already overdue it is rejected
        immediately.
        """
        if not self._running:
            log.warning("[TaskQueue] Queue is shut down — rejected task %s", task.task_id)
            return task.task_id

        if task.is_overdue:
            log.warning("[TaskQueue] Task %s is already overdue, discarding.", task.task_id)
            return task.task_id

        item: _HeapItem = (int(task.priority), next(self._counter), task)
        with self._not_empty:
            heapq.heappush(self._heap, item)
            self._not_empty.notify_all()

        log.debug("[TaskQueue] Queued task %s → %s (priority=%s)",
                  task.task_id, task.agent_name, task.priority.name)
        return task.task_id

    # ── Cancel ──────────────────────────────────────────────────────────────

    def cancel(self, task_id: str) -> bool:
        """Mark a task as cancelled. If it hasn't started yet it will be skipped."""
        with self._lock:
            if task_id not in self._cancelled:
                self._cancelled.add(task_id)
                log.debug("[TaskQueue] Cancelled task %s", task_id)
                return True
        return False

    # ── Worker ──────────────────────────────────────────────────────────────

    def start_worker(self, agent_name: str) -> threading.Thread:
        """
        Start a background worker thread for the given agent.
        Returns the thread (already started).
        """
        if agent_name in self._workers and self._workers[agent_name].is_alive():
            log.debug("[TaskQueue] Worker for %s already running.", agent_name)
            return self._workers[agent_name]

        stop_flag = threading.Event()
        self._stop_flags[agent_name] = stop_flag
        t = threading.Thread(
            target=self._worker_loop,
            args=(agent_name, stop_flag),
            name=f"TaskWorker-{agent_name}",
            daemon=True,
        )
        self._workers[agent_name] = t
        t.start()
        log.info("[TaskQueue] Worker started for agent: %s", agent_name)
        return t

    def stop_worker(self, agent_name: str):
        """Signal the worker for `agent_name` to stop after its current task."""
        flag = self._stop_flags.get(agent_name)
        if flag:
            flag.set()
            log.info("[TaskQueue] Stop signal sent to worker: %s", agent_name)

    def _worker_loop(self, agent_name: str, stop_flag: threading.Event):
        log.debug("[TaskWorker:%s] Loop started.", agent_name)
        while not stop_flag.is_set() and self._running:
            task = self._pull(agent_name)
            if task is None:
                continue
            self._execute(task)
        log.debug("[TaskWorker:%s] Loop finished.", agent_name)

    def _pull(self, agent_name: str) -> Optional[Task]:
        """
        Block briefly waiting for a task addressed to `agent_name`.
        Returns None if timeout expires without finding a matching task.
        """
        with self._not_empty:
            deadline = time.monotonic() + self.WORKER_TIMEOUT
            while self._running:
                task = self._find_next_for(agent_name)
                if task:
                    return task
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._not_empty.wait(timeout=remaining)
        return None

    def _find_next_for(self, agent_name: str) -> Optional[Task]:
        """
        Scan the heap for the highest-priority non-cancelled task for
        `agent_name`.  Removes and returns it, or None.
        """
        # We need to peek without permanently removing items.
        # Build a small temp list of items we skip over, then put them back.
        skipped: List[_HeapItem] = []
        result: Optional[Task] = None

        while self._heap:
            item = heapq.heappop(self._heap)
            _, _, task = item
            if task.task_id in self._cancelled:
                # Discard cancelled tasks silently
                continue
            if task.is_overdue and task.retry_count == 0:
                log.warning("[TaskQueue] Task %s overdue — skipping.", task.task_id)
                continue
            if task.agent_name == agent_name:
                result = task
                break
            skipped.append(item)

        for s in skipped:
            heapq.heappush(self._heap, s)

        return result

    def _execute(self, task: Task):
        log.debug("[TaskWorker:%s] Executing task %s (%s)",
                  task.agent_name, task.task_id, task.description or "—")
        start = time.monotonic()
        try:
            task.fn()
            elapsed = time.monotonic() - start
            self._completed.append({
                "task_id"   : task.task_id,
                "agent"     : task.agent_name,
                "elapsed_s" : round(elapsed, 4),
                "desc"      : task.description,
            })
            log.debug("[TaskWorker:%s] Task %s done in %.3fs",
                      task.agent_name, task.task_id, elapsed)
        except Exception as exc:
            log.error("[TaskWorker:%s] Task %s FAILED: %s",
                      task.agent_name, task.task_id, exc, exc_info=True)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                log.info("[TaskQueue] Retrying task %s (attempt %d/%d)",
                         task.task_id, task.retry_count, task.max_retries)
                self.submit(task)
            else:
                self._failed.append({
                    "task_id": task.task_id,
                    "agent"  : task.agent_name,
                    "error"  : str(exc),
                    "desc"   : task.description,
                })

    # ── Convenience helpers ──────────────────────────────────────────────────

    def submit_to(self, agent_name: str, fn: Callable[[], Any],
                  priority: Priority = Priority.NORMAL,
                  description: str = "",
                  deadline: Optional[float] = None) -> str:
        """
        Inline helper — create and submit a task in one call.

        Example::
            tq.submit_to("RiskManagerAI", lambda: rm.check(), Priority.CRITICAL)
        """
        task = Task(agent_name=agent_name, fn=fn, priority=priority,
                    description=description, deadline=deadline)
        return self.submit(task)

    def broadcast(self, fn_factory: Callable[[str], Callable[[], Any]],
                  agent_names: List[str],
                  priority: Priority = Priority.NORMAL,
                  description: str = ""):
        """
        Submit a task to multiple agents.

        `fn_factory(agent_name)` should return the callable for each agent,
        allowing per-agent customisation if needed.

        Example::
            tq.broadcast(
                fn_factory=lambda a: lambda: agents[a].on_market_open(),
                agent_names=ALL_AGENTS,
                priority=Priority.HIGH,
                description="market_open",
            )
        """
        ids = []
        for name in agent_names:
            ids.append(self.submit_to(name, fn_factory(name),
                                      priority=priority,
                                      description=description))
        return ids

    # ── Diagnostics ──────────────────────────────────────────────────────────

    def queue_size(self) -> int:
        with self._lock:
            return len(self._heap)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            pending = len(self._heap)
        return {
            "pending"  : pending,
            "cancelled": len(self._cancelled),
            "completed": len(self._completed),
            "failed"   : len(self._failed),
            "workers"  : {a: t.is_alive() for a, t in self._workers.items()},
        }

    def print_stats(self):
        s = self.stats()
        print(f"\n{'='*50}")
        print("  TASK QUEUE DIAGNOSTICS")
        print(f"{'='*50}")
        print(f"  Pending   : {s['pending']}")
        print(f"  Completed : {s['completed']}")
        print(f"  Failed    : {s['failed']}")
        print(f"  Cancelled : {s['cancelled']}")
        print(f"  Workers   :")
        for name, alive in s["workers"].items():
            status = "RUNNING" if alive else "STOPPED"
            print(f"    {name:<35} {status}")
        print(f"{'='*50}\n")

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self, timeout: float = 5.0):
        """Signal all workers to stop and wait for them to finish."""
        log.info("[TaskQueue] Shutting down…")
        self._running = False
        with self._not_empty:
            self._not_empty.notify_all()
        for name, flag in self._stop_flags.items():
            flag.set()
        for name, t in self._workers.items():
            t.join(timeout=timeout)
            if t.is_alive():
                log.warning("[TaskQueue] Worker %s did not stop cleanly.", name)
        log.info("[TaskQueue] Shutdown complete.")


# ── Global Singleton ──────────────────────────────────────────────────────────

_task_queue: Optional[TaskQueue] = None
_tq_lock = threading.Lock()


def get_task_queue() -> TaskQueue:
    """
    Return the process-wide singleton TaskQueue.
    Creates it on first call.

    Usage::
        from communication.task_queue import get_task_queue, Priority
        tq = get_task_queue()
        tq.submit_to("RiskManagerAI", lambda: rm.check(), Priority.CRITICAL)
    """
    global _task_queue
    if _task_queue is None:
        with _tq_lock:
            if _task_queue is None:
                _task_queue = TaskQueue()
    return _task_queue
