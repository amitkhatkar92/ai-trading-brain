"""iios/common/async_exec/migration_analysis.py
Static migration analysis of async patterns across all IIOS platform engines.

This is executable data (not a markdown file) that records the current async
surface of each engine and provides a programmatic migration roadmap.

Query the analysis::

    from iios.common.async_exec.migration_analysis import (
        PLATFORM_ASYNC_PROFILES,
        engines_by_complexity,
        engines_needing_standardization,
        get_profile,
    )

    for engine_id, profile in engines_needing_standardization():
        print(f"{engine_id}: {profile.recommended_action}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterator, List, Tuple

from iios.common.async_exec.execution_classifier import WorkloadType


# ── Async method descriptor ───────────────────────────────────────────────────

@dataclass(frozen=True)
class AsyncMethodProfile:
    """
    Profile of a single async method within an engine.

    Attributes
    ----------
    name:
        Method name (e.g. ``"async_update"``).
    current_pattern:
        How the method is currently implemented.
        One of: ``"coroutine"``, ``"run_in_executor"``, ``"asyncio.run"``,
        ``"daemon_thread_loop"``, ``"taskgroup"``.
    workload:
        Classified workload type.
    standardize_to:
        Recommended standardization action.
        One of: ``"keep_native_async"``, ``"use_async_executor"``,
        ``"use_execute_sync"``, ``"no_change"``.
    notes:
        Contextual notes for the engineer performing the migration.
    """
    name:            str
    current_pattern: str
    workload:        WorkloadType
    standardize_to:  str
    notes:           str = ""


# ── Engine async profile ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class EngineAsyncProfile:
    """
    Complete async profile for one IIOS engine.

    Attributes
    ----------
    engine_id:
        Canonical IIOS engine identifier (e.g. ``"iios:market:intelligence:integration"``).
    file_path:
        Workspace-relative path to the engine's main Python file.
    has_native_async:
        True if the engine exposes at least one ``async def`` public method.
    has_own_executor:
        True if the engine creates its own ``ThreadPoolExecutor`` or ``ProcessPoolExecutor``.
    has_daemon_loop:
        True if the engine spins a persistent event loop in a daemon thread.
    methods:
        Profiles of all relevant async / executor-delegated methods.
    workload_classification:
        Dominant workload type for this engine.
    recommended_action:
        High-level migration recommendation.
        One of: ``"standardize_with_async_executor"``, ``"use_execute_sync"``,
        ``"no_change"``, ``"keep_native_async"``.
    migration_complexity:
        Estimated effort level: ``"none"``, ``"low"``, ``"medium"``, ``"high"``.
    rationale:
        Why the action is recommended.
    """
    engine_id:               str
    file_path:               str
    has_native_async:        bool
    has_own_executor:        bool
    has_daemon_loop:         bool
    methods:                 List[AsyncMethodProfile]
    workload_classification: WorkloadType
    recommended_action:      str
    migration_complexity:    str
    rationale:               str


# ── Platform profiles ─────────────────────────────────────────────────────────

PLATFORM_ASYNC_PROFILES: Dict[str, EngineAsyncProfile] = {

    # ── C1: Market Intelligence ──────────────────────────────────────────────
    "iios:market:intelligence:integration": EngineAsyncProfile(
        engine_id               = "iios:market:intelligence:integration",
        file_path               = "iios/investment/market/integration/market_intelligence_integration_engine.py",
        has_native_async        = True,
        has_own_executor        = True,
        has_daemon_loop         = False,
        methods                 = [
            AsyncMethodProfile(
                name            = "async_update",
                current_pattern = "run_in_executor",
                workload        = WorkloadType.IO_BOUND,
                standardize_to  = "use_async_executor",
                notes           = (
                    "Creates a new ThreadPoolExecutor(max_workers=1) on each call. "
                    "Replace with AsyncExecutor.run_in_thread() to reuse the managed pool."
                ),
            ),
        ],
        workload_classification = WorkloadType.IO_BOUND,
        recommended_action      = "standardize_with_async_executor",
        migration_complexity    = "low",
        rationale               = (
            "Engine has one async method that creates its own executor per call. "
            "Switch to AsyncExecutionManager.execute() to reuse the shared thread pool "
            "and gain automatic metrics and timeout enforcement."
        ),
    ),

    # ── C2: Company Intelligence ─────────────────────────────────────────────
    "iios:company:intelligence:integration": EngineAsyncProfile(
        engine_id               = "iios:company:intelligence:integration",
        file_path               = "iios/investment/company/integration/company_intelligence_integration_engine.py",
        has_native_async        = False,
        has_own_executor        = False,
        has_daemon_loop         = False,
        methods                 = [],
        workload_classification = WorkloadType.SYNC_WRAPPER,
        recommended_action      = "no_change",
        migration_complexity    = "none",
        rationale               = (
            "Fully synchronous engine. No async patterns present. "
            "Current design is correct for a data-transformation stage."
        ),
    ),

    # ── C3: Strategy Intelligence ────────────────────────────────────────────
    "iios:strategy:intelligence:integration": EngineAsyncProfile(
        engine_id               = "iios:strategy:intelligence:integration",
        file_path               = "iios/investment/strategy/integration/strategy_intelligence_integration_engine.py",
        has_native_async        = True,
        has_own_executor        = True,
        has_daemon_loop         = True,
        methods                 = [
            AsyncMethodProfile(
                name            = "submit_update",
                current_pattern = "coroutine",
                workload        = WorkloadType.IO_BOUND,
                standardize_to  = "keep_native_async",
                notes           = "Native coroutine in daemon-managed event loop — correct design.",
            ),
            AsyncMethodProfile(
                name            = "get_snapshot",
                current_pattern = "coroutine",
                workload        = WorkloadType.IO_BOUND,
                standardize_to  = "keep_native_async",
                notes           = "Native coroutine. Sync wrapper uses asyncio.run() — risk of loop conflict.",
            ),
            AsyncMethodProfile(
                name            = "get_snapshot_batch",
                current_pattern = "coroutine",
                workload        = WorkloadType.IO_BOUND,
                standardize_to  = "keep_native_async",
                notes           = "Uses asyncio.gather() correctly for parallelism.",
            ),
            AsyncMethodProfile(
                name            = "get_snapshot_sync",
                current_pattern = "asyncio.run",
                workload        = WorkloadType.SYNC_WRAPPER,
                standardize_to  = "use_execute_sync",
                notes           = (
                    "Calls asyncio.run(get_snapshot()). "
                    "Replace with AsyncExecutionManager.execute_sync() to prevent "
                    "RuntimeError if called from within a running event loop."
                ),
            ),
            AsyncMethodProfile(
                name            = "submit_update_sync",
                current_pattern = "asyncio.run",
                workload        = WorkloadType.SYNC_WRAPPER,
                standardize_to  = "use_execute_sync",
                notes           = "Same asyncio.run() risk as get_snapshot_sync.",
            ),
            AsyncMethodProfile(
                name            = "_build_and_cache",
                current_pattern = "coroutine",
                workload        = WorkloadType.MIXED,
                standardize_to  = "keep_native_async",
                notes           = "Internal async helper — no changes needed.",
            ),
        ],
        workload_classification = WorkloadType.MIXED,
        recommended_action      = "standardize_with_async_executor",
        migration_complexity    = "medium",
        rationale               = (
            "Most complex async surface in the platform. The daemon-thread event loop "
            "pattern is intentional and correct for maintaining persistent async state. "
            "The sync wrappers that call asyncio.run() should be replaced with "
            "AsyncExecutionManager.execute_sync() to guard against 'cannot run nested "
            "event loop' errors. The native async public API should remain unchanged."
        ),
    ),

    # ── C4: Decision Intelligence ────────────────────────────────────────────
    "iios:decision:intelligence:integration": EngineAsyncProfile(
        engine_id               = "iios:decision:intelligence:integration",
        file_path               = "iios/investment/decision/integration/decision_intelligence_integration_engine.py",
        has_native_async        = True,
        has_own_executor        = False,
        has_daemon_loop         = False,
        methods                 = [
            AsyncMethodProfile(
                name            = "integrate",
                current_pattern = "run_in_executor",
                workload        = WorkloadType.CPU_BOUND,
                standardize_to  = "use_async_executor",
                notes           = (
                    "Uses asyncio.TaskGroup for parallel sub-tasks and delegates "
                    "CPU-bound scoring to run_in_executor(None) — correct pattern. "
                    "Replace run_in_executor(None) with AsyncExecutor.run_in_thread() "
                    "to use the managed pool instead of the default loop executor."
                ),
            ),
        ],
        workload_classification = WorkloadType.CPU_BOUND,
        recommended_action      = "standardize_with_async_executor",
        migration_complexity    = "low",
        rationale               = (
            "Engine correctly uses asyncio.TaskGroup for concurrency. The run_in_executor "
            "call should use the managed AsyncExecutor rather than the loop's default executor "
            "for consistent pool sizing and metrics visibility."
        ),
    ),

    # ── C5: Portfolio Intelligence ───────────────────────────────────────────
    "iios:portfolio:intelligence:integration": EngineAsyncProfile(
        engine_id               = "iios:portfolio:intelligence:integration",
        file_path               = "iios/investment/portfolio/integration/portfolio_intelligence_integration_engine.py",
        has_native_async        = False,
        has_own_executor        = False,
        has_daemon_loop         = False,
        methods                 = [],
        workload_classification = WorkloadType.SYNC_WRAPPER,
        recommended_action      = "no_change",
        migration_complexity    = "none",
        rationale               = (
            "Fully synchronous. Portfolio allocation computation is CPU-bound and "
            "designed to run inline. No async surface needed."
        ),
    ),

    # ── Workflow Orchestrator ────────────────────────────────────────────────
    "iios:workflow:institutional": EngineAsyncProfile(
        engine_id               = "iios:workflow:institutional",
        file_path               = "iios/investment/workflow/institutional_investment_workflow.py",
        has_native_async        = False,
        has_own_executor        = False,
        has_daemon_loop         = False,
        methods                 = [],
        workload_classification = WorkloadType.SYNC_WRAPPER,
        recommended_action      = "no_change",
        migration_complexity    = "none",
        rationale               = (
            "Synchronous orchestrator that coordinates all engines in sequence. "
            "The sync design is intentional — it enforces execution order and makes "
            "the workflow deterministic. No async needed at the orchestration layer."
        ),
    ),

    # ── Shared: HealthMonitor ────────────────────────────────────────────────
    "iios:shared:health_monitor": EngineAsyncProfile(
        engine_id               = "iios:shared:health_monitor",
        file_path               = "iios/investment/shared/health_monitor.py",
        has_native_async        = True,
        has_own_executor        = False,
        has_daemon_loop         = False,
        methods                 = [
            AsyncMethodProfile(
                name            = "start",
                current_pattern = "coroutine",
                workload        = WorkloadType.NATIVE_ASYNC,
                standardize_to  = "keep_native_async",
                notes           = "Pure async class designed to run inside an event loop — correct.",
            ),
            AsyncMethodProfile(
                name            = "stop",
                current_pattern = "coroutine",
                workload        = WorkloadType.NATIVE_ASYNC,
                standardize_to  = "keep_native_async",
                notes           = "Clean async teardown with CancelledError handling.",
            ),
            AsyncMethodProfile(
                name            = "_run_loop",
                current_pattern = "coroutine",
                workload        = WorkloadType.NATIVE_ASYNC,
                standardize_to  = "keep_native_async",
                notes           = "Polling loop using asyncio.sleep — correct pattern.",
            ),
            AsyncMethodProfile(
                name            = "_tick",
                current_pattern = "coroutine",
                workload        = WorkloadType.IO_BOUND,
                standardize_to  = "keep_native_async",
                notes           = (
                    "Performs periodic health checks. Consider wrapping blocking "
                    "health-check calls with AsyncExecutor.run_in_thread() if they "
                    "do filesystem or network I/O."
                ),
            ),
        ],
        workload_classification = WorkloadType.NATIVE_ASYNC,
        recommended_action      = "keep_native_async",
        migration_complexity    = "none",
        rationale               = (
            "Correctly designed pure-async class. Lives inside the daemon thread "
            "event loop managed by the hosting engine. No changes needed — "
            "this is the reference implementation for IIOS async components."
        ),
    ),
}


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_profile(engine_id: str) -> EngineAsyncProfile:
    """Return the profile for *engine_id*, raising ``KeyError`` if not found."""
    return PLATFORM_ASYNC_PROFILES[engine_id]


def engines_needing_standardization() -> Iterator[Tuple[str, EngineAsyncProfile]]:
    """
    Yield (engine_id, profile) for engines that need work.

    Excludes ``"no_change"`` and ``"keep_native_async"`` engines.
    """
    for eid, profile in PLATFORM_ASYNC_PROFILES.items():
        if profile.recommended_action not in ("no_change", "keep_native_async"):
            yield eid, profile


def engines_by_complexity(complexity: str) -> Iterator[Tuple[str, EngineAsyncProfile]]:
    """
    Yield (engine_id, profile) filtered by *complexity*.

    :param complexity: One of ``"none"``, ``"low"``, ``"medium"``, ``"high"``.
    """
    for eid, profile in PLATFORM_ASYNC_PROFILES.items():
        if profile.migration_complexity == complexity:
            yield eid, profile


def all_async_methods() -> Iterator[Tuple[str, AsyncMethodProfile]]:
    """
    Yield (engine_id, method_profile) for every method across all engines.
    """
    for eid, profile in PLATFORM_ASYNC_PROFILES.items():
        for method in profile.methods:
            yield eid, method


def methods_needing_standardization() -> Iterator[Tuple[str, AsyncMethodProfile]]:
    """
    Yield (engine_id, method_profile) for methods that should be updated.

    Excludes ``"keep_native_async"`` and ``"no_change"`` methods.
    """
    for eid, method in all_async_methods():
        if method.standardize_to not in ("keep_native_async", "no_change"):
            yield eid, method
