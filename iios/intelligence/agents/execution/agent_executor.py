"""
iios/intelligence/agents/execution/agent_executor.py
====================================================
AgentExecutor — executes agents with timeout enforcement,
metrics recording, and optional supervision integration.

Singleton: get_agent_executor() / reset_agent_executor()
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..agent_constants import AGENT_EXECUTION_TIMEOUT_S, MAX_CONCURRENT_AGENTS
from ..agent_exceptions import AgentTimeoutError, AgentExecutionError
from ..core.base_agent import BaseAgent, AgentRequest, AgentResponse
from ..monitoring.agent_monitor import AgentMonitor, get_agent_monitor

log = logging.getLogger(__name__)

__all__ = [
    "ExecutionSpec",
    "ExecutionResult",
    "AgentExecutor",
    "get_agent_executor",
    "reset_agent_executor",
]


@dataclass
class ExecutionSpec:
    """Describes how a single agent execution should be run."""
    agent:      BaseAgent
    request:    AgentRequest
    timeout_s:  float = AGENT_EXECUTION_TIMEOUT_S
    monitor:    bool  = True


@dataclass
class ExecutionResult:
    """Wraps an AgentResponse with executor-level metadata."""
    response:     AgentResponse
    timed_out:    bool  = False
    retried:      bool  = False
    attempt:      int   = 1

    @property
    def success(self) -> bool:
        return self.response.success

    def to_dict(self) -> dict:
        d = self.response.to_dict()
        d["timed_out"] = self.timed_out
        d["attempt"]   = self.attempt
        return d


class AgentExecutor:
    """
    Executes agents safely with:
      - Configurable per-call timeouts
      - Automatic metric recording
      - Thread-pool-based parallel execution
    """

    def __init__(
        self,
        max_workers: int                    = MAX_CONCURRENT_AGENTS,
        monitor:     Optional[AgentMonitor] = None,
    ) -> None:
        self._max_workers = max_workers
        self._monitor     = monitor or get_agent_monitor()
        self._lock        = threading.RLock()
        self._exec_count  = 0
        self._pool:       Optional[concurrent.futures.ThreadPoolExecutor] = None

    # ── Single execution ──────────────────────────────────────────────────────

    def execute(
        self,
        agent:     BaseAgent,
        request:   AgentRequest,
        timeout_s: float = AGENT_EXECUTION_TIMEOUT_S,
        monitor:   bool  = True,
    ) -> ExecutionResult:
        """
        Execute a single agent with timeout enforcement.
        """
        t0     = time.perf_counter()
        future = concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(
            agent.run, request
        )
        try:
            response = future.result(timeout=timeout_s)
            with self._lock:
                self._exec_count += 1
            if monitor:
                self._monitor.record(response)
            return ExecutionResult(response=response)
        except concurrent.futures.TimeoutError:
            future.cancel()
            agent.cancel()
            ms = (time.perf_counter() - t0) * 1_000
            resp = AgentResponse(
                request_id  = request.request_id,
                agent_id    = agent.agent_id,
                success     = False,
                error       = f"Timed out after {timeout_s:.1f}s",
                duration_ms = ms,
                confidence  = 0.0,
            )
            if monitor:
                self._monitor.record(resp)
            return ExecutionResult(response=resp, timed_out=True)
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1_000
            resp = AgentResponse(
                request_id  = request.request_id,
                agent_id    = agent.agent_id,
                success     = False,
                error       = str(exc),
                duration_ms = ms,
                confidence  = 0.0,
            )
            if monitor:
                self._monitor.record(resp)
            return ExecutionResult(response=resp)

    def execute_many(
        self,
        specs:     list[ExecutionSpec],
        parallel:  bool  = True,
    ) -> list[ExecutionResult]:
        """
        Execute multiple agent specs, optionally in parallel.
        """
        if not parallel or len(specs) == 1:
            return [
                self.execute(s.agent, s.request, s.timeout_s, s.monitor)
                for s in specs
            ]

        results: list[Optional[ExecutionResult]] = [None] * len(specs)

        def _run(i: int, spec: ExecutionSpec) -> None:
            results[i] = self.execute(
                spec.agent, spec.request, spec.timeout_s, spec.monitor
            )

        workers = min(self._max_workers, len(specs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run, i, s) for i, s in enumerate(specs)]
            concurrent.futures.wait(futures)

        return [r for r in results if r is not None]

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "exec_count":  self._exec_count,
                "max_workers": self._max_workers,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_exec_lock = threading.Lock()
_exec_inst: Optional[AgentExecutor] = None


def get_agent_executor() -> AgentExecutor:
    global _exec_inst
    if _exec_inst is None:
        with _exec_lock:
            if _exec_inst is None:
                _exec_inst = AgentExecutor()
    return _exec_inst


def reset_agent_executor() -> None:
    global _exec_inst
    with _exec_lock:
        _exec_inst = None
