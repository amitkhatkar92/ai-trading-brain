"""iios/common/async_exec/timeout_policy.py
Configurable timeout policies for the IIOS async execution framework.

Provides:
  • ``TimeoutPolicy``   — frozen config with per-scope timeouts
  • ``with_stage_timeout``     — async context manager / wrapper
  • ``with_workflow_timeout``  — async context manager / wrapper
  • ``with_engine_timeout``    — async context manager / wrapper
  • ``with_pipeline_timeout``  — async context manager / wrapper
  • ``apply_timeout``          — generic timeout wrapper

All timeout functions raise ``iios.common.errors.exceptions.TimeoutError``
(not the Python builtin) with full context on expiry.

Usage::

    from iios.common.async_exec.timeout_policy import TimeoutPolicy, apply_timeout

    policy = TimeoutPolicy(stage_timeout_sec=5.0, workflow_timeout_sec=120.0)

    result = await apply_timeout(
        my_coroutine(),
        timeout_sec = policy.stage_timeout_sec,
        operation   = "data_fetch",
    )
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, TypeVar

from iios.common.errors.exceptions import TimeoutError as IIOSTimeoutError


T = TypeVar("T")

# ── TimeoutPolicy ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimeoutPolicy:
    """
    Immutable per-scope timeout configuration.

    All values are in seconds.  Use ``None`` to disable a specific scope.

    Defaults are intentionally conservative for production safety.
    """

    stage_timeout_sec:    Optional[float] = 30.0
    workflow_timeout_sec: Optional[float] = 300.0
    engine_timeout_sec:   Optional[float] = 60.0
    pipeline_timeout_sec: Optional[float] = 120.0

    # Soft warning threshold — log a warning at this fraction of timeout.
    # 0.8 means warn when 80% of the timeout has elapsed.
    soft_threshold: float = 0.8

    @classmethod
    def strict(cls) -> "TimeoutPolicy":
        """Short timeouts for latency-sensitive paths."""
        return cls(
            stage_timeout_sec    = 5.0,
            workflow_timeout_sec = 60.0,
            engine_timeout_sec   = 15.0,
            pipeline_timeout_sec = 45.0,
        )

    @classmethod
    def relaxed(cls) -> "TimeoutPolicy":
        """Generous timeouts for batch/overnight jobs."""
        return cls(
            stage_timeout_sec    = 120.0,
            workflow_timeout_sec = 1800.0,
            engine_timeout_sec   = 300.0,
            pipeline_timeout_sec = 600.0,
        )

    @classmethod
    def unlimited(cls) -> "TimeoutPolicy":
        """No timeout limits — use only in test or debug contexts."""
        return cls(
            stage_timeout_sec    = None,
            workflow_timeout_sec = None,
            engine_timeout_sec   = None,
            pipeline_timeout_sec = None,
        )


# ── Core timeout wrapper ──────────────────────────────────────────────────────

async def apply_timeout(
    awaitable:   Awaitable[T],
    timeout_sec: Optional[float],
    *,
    operation:   str = "",
    engine_id:   str = "",
) -> T:
    """
    Await *awaitable* subject to *timeout_sec*.

    Raises ``IIOSTimeoutError`` (not ``asyncio.TimeoutError``) on expiry
    so callers can catch it as part of the IIOS exception hierarchy.

    :param awaitable:   The coroutine or awaitable to execute.
    :param timeout_sec: Seconds until timeout.  ``None`` disables the timeout.
    :param operation:   Human-readable operation name for the error message.
    :param engine_id:   Engine that owns the operation.
    """
    if timeout_sec is None:
        return await awaitable
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_sec)
    except asyncio.TimeoutError:
        raise IIOSTimeoutError(
            f"Operation timed out after {timeout_sec:.1f}s: {operation or 'unknown'}",
            operation   = operation,
            timeout_sec = timeout_sec,
            context     = {"engine_id": engine_id} if engine_id else {},
        )


# ── Scope-specific helpers ────────────────────────────────────────────────────

async def with_stage_timeout(
    awaitable: Awaitable[T],
    policy:    TimeoutPolicy,
    *,
    stage:     str = "",
    engine_id: str = "",
) -> T:
    """Apply the stage timeout from *policy* to *awaitable*."""
    return await apply_timeout(
        awaitable,
        policy.stage_timeout_sec,
        operation = f"stage:{stage}" if stage else "stage",
        engine_id = engine_id,
    )


async def with_workflow_timeout(
    awaitable:   Awaitable[T],
    policy:      TimeoutPolicy,
    *,
    workflow_id: str = "",
    engine_id:   str = "",
) -> T:
    """Apply the workflow timeout from *policy* to *awaitable*."""
    return await apply_timeout(
        awaitable,
        policy.workflow_timeout_sec,
        operation = f"workflow:{workflow_id}" if workflow_id else "workflow",
        engine_id = engine_id,
    )


async def with_engine_timeout(
    awaitable: Awaitable[T],
    policy:    TimeoutPolicy,
    *,
    engine_id: str = "",
) -> T:
    """Apply the engine timeout from *policy* to *awaitable*."""
    return await apply_timeout(
        awaitable,
        policy.engine_timeout_sec,
        operation = f"engine:{engine_id}" if engine_id else "engine",
        engine_id = engine_id,
    )


async def with_pipeline_timeout(
    awaitable: Awaitable[T],
    policy:    TimeoutPolicy,
    *,
    pipeline:  str = "",
    engine_id: str = "",
) -> T:
    """Apply the pipeline timeout from *policy* to *awaitable*."""
    return await apply_timeout(
        awaitable,
        policy.pipeline_timeout_sec,
        operation = f"pipeline:{pipeline}" if pipeline else "pipeline",
        engine_id = engine_id,
    )


# ── Timeout scope context manager ─────────────────────────────────────────────

@asynccontextmanager
async def timeout_scope(
    timeout_sec: Optional[float],
    *,
    operation:   str = "",
    engine_id:   str = "",
) -> AsyncGenerator[None, None]:
    """
    Async context manager that enforces a timeout on the entire block.

    Usage::

        async with timeout_scope(30.0, operation="fetch_quotes"):
            data = await feed.get_multiple_quotes(symbols)
            processed = process(data)   # sync CPU work — safe
    """
    if timeout_sec is None:
        yield
        return

    deadline_task = asyncio.current_task()
    try:
        async with asyncio.timeout(timeout_sec):
            yield
    except TimeoutError:
        raise IIOSTimeoutError(
            f"Timeout scope exceeded {timeout_sec:.1f}s: {operation or 'unknown'}",
            operation   = operation,
            timeout_sec = timeout_sec,
            context     = {"engine_id": engine_id} if engine_id else {},
        )
    except asyncio.TimeoutError:
        raise IIOSTimeoutError(
            f"Timeout scope exceeded {timeout_sec:.1f}s: {operation or 'unknown'}",
            operation   = operation,
            timeout_sec = timeout_sec,
            context     = {"engine_id": engine_id} if engine_id else {},
        )
