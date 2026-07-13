"""iios/investment/strategy/lifecycle/strategy_lifecycle_engine.py
Institutional Strategy Lifecycle & Execution Engine.

The Strategy Runtime Manager — every IIOS strategy executes ONLY through
this engine.

Responsibilities:
  Orchestration   — registers, loads, initialises, and runs strategies
  Scheduling      — time-based / periodic / event-driven / priority dispatch
  Dependencies    — enforces ordering constraints each cycle
  Execution       — dispatches to thread pool with resource admission control
  Monitoring      — tracks execution latency, failures, and health
  Recovery        — retries, checkpoints, circuit-breakers, auto-restarts
  APIs            — exposes runtime state, metrics, history, health

This engine does NOT:
  • Generate buy / sell signals
  • Evaluate market or company conditions
  • Execute or route orders
  • Contain any trading logic

Architecture guarantees:
  • Thread-safe throughout — no caller synchronisation required
  • Hot-reload capable — register new strategies without restarting
  • Plugin-based — accepts any callable(RuntimeContext) → Any
  • Distributed-ready — each method is side-effect isolated and stateless
    at the call-site; internal state is injectable / replaceable
  • Scales to thousands of concurrent strategy instances without
    architectural modification (add workers, increase limits)
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from iios.investment.strategy.lifecycle.dependency_engine import (
    DependencyDeclaration,
    DependencyEngine,
)
from iios.investment.strategy.lifecycle.dependency_registry import DependencyType
from iios.investment.strategy.lifecycle.dependency_validator import (
    DependencyValidationResult,
)
from iios.investment.strategy.lifecycle.execution_monitor import (
    EngineHealthReport,
    ExecutionMonitor,
    StrategyHealth,
)
from iios.investment.strategy.lifecycle.execution_queue import SchedulePriority
from iios.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionStatus,
)
from iios.investment.strategy.lifecycle.failure_handler import FailurePolicy
from iios.investment.strategy.lifecycle.recovery_engine import (
    RecoveryDecision,
    RecoveryEngine,
)
from iios.investment.strategy.lifecycle.resource_limits import ResourceLimits
from iios.investment.strategy.lifecycle.resource_manager import ResourceManager
from iios.investment.strategy.lifecycle.restart_manager import RestartPolicy
from iios.investment.strategy.lifecycle.runtime_context import RuntimeContext
from iios.investment.strategy.lifecycle.runtime_manager import RuntimeManager
from iios.investment.strategy.lifecycle.runtime_state import (
    RuntimeState,
    RuntimeStateSnapshot,
)
from iios.investment.strategy.lifecycle.runtime_statistics import CycleSample
from iios.investment.strategy.lifecycle.schedule_registry import (
    ScheduleEntry,
    ScheduleType,
)
from iios.investment.strategy.lifecycle.strategy_scheduler import StrategyScheduler

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────


class LifecycleEngineError(Exception):
    """Base exception for the StrategyLifecycleEngine."""


class StrategyNotRegisteredError(LifecycleEngineError):
    """Raised when referencing a strategy_id that is not registered."""


class EngineNotRunningError(LifecycleEngineError):
    """Raised when submitting work to an engine that is not in RUNNING state."""


# ── Internal registration record ─────────────────────────────────────────────


class _StrategyRecord:
    """
    Internal registry entry — one per registered strategy.

    Holds the callable and its policies.  Intentionally separate from
    InstitutionalBaseStrategy so the engine can wrap any callable,
    including lambdas, plain functions, or adapter objects.
    """

    __slots__ = (
        "strategy_id", "name", "execute_fn", "registered_at",
        "failure_policy", "restart_policy", "tags",
    )

    def __init__(
        self,
        strategy_id: str,
        name: str,
        execute_fn: Callable[[RuntimeContext], Any],
        failure_policy: Optional[FailurePolicy],
        restart_policy: RestartPolicy,
        tags: List[str],
    ) -> None:
        self.strategy_id = strategy_id
        self.name = name
        self.execute_fn = execute_fn
        self.registered_at: datetime = datetime.now(timezone.utc)
        self.failure_policy = failure_policy
        self.restart_policy = restart_policy
        self.tags = tags


# ── Main engine ───────────────────────────────────────────────────────────────


class StrategyLifecycleEngine:
    """
    Central runtime manager for all IIOS institutional strategies.

    Quick-start:
        engine = StrategyLifecycleEngine()
        engine.start()

        def my_strategy(ctx: RuntimeContext) -> None: ...

        engine.register("alpha-001", "AlphaStrategy", execute_fn=my_strategy)
        engine.schedule_periodic("alpha-001", interval_seconds=60)
        # … runs automatically …

        engine.shutdown()

    Direct execution:
        engine.submit("alpha-001", context)
        results = engine.run_cycle(context)   # all strategies in dep order
    """

    def __init__(
        self,
        resource_limits: Optional[ResourceLimits] = None,
        max_workers: int = 64,
        max_queue_depth: int = 10_000,
        default_failure_policy: Optional[FailurePolicy] = None,
        p95_latency_warn_ms: float = 5_000.0,
        failure_rate_warn: float = 0.10,
    ) -> None:
        self._limits = resource_limits or ResourceLimits.standard()
        self._lock = threading.RLock()

        # ── Subsystems ────────────────────────────────────────────────────────
        self._runtime = RuntimeManager()
        self._resource_manager = ResourceManager(limits=self._limits)
        self._dep_engine = DependencyEngine()
        self._monitor = ExecutionMonitor(
            p95_latency_warn_ms=p95_latency_warn_ms,
            failure_rate_warn=failure_rate_warn,
        )
        self._recovery = RecoveryEngine(
            default_failure_policy=default_failure_policy,
            max_restarts_per_strategy=self._limits.max_restarts_per_strategy,
            restart_fn=self._on_restart_triggered,
        )

        # Shared thread pool — used by both the scheduler and direct submissions
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="iios-engine",
        )

        # Strategy registry: id → _StrategyRecord
        self._strategies: Dict[str, _StrategyRecord] = {}

        # Scheduler — delegates actual execution to _execute_request
        self._scheduler = StrategyScheduler(
            executor_fn=self._execute_request,
            max_concurrent=self._limits.max_concurrent_strategies or max_workers,
            max_queue_depth=max_queue_depth,
            thread_pool=self._pool,
        )

        self._runtime.add_state_listener(self._on_runtime_state_change)

        logger.info(
            "StrategyLifecycleEngine created (max_workers=%d, queue=%d)",
            max_workers, max_queue_depth,
        )

    # ── Engine lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the engine. Must be called before submitting strategies."""
        self._runtime.start()
        self._scheduler.start()
        logger.info("StrategyLifecycleEngine STARTED")

    def shutdown(self, drain: bool = True) -> None:
        """
        Gracefully shut down the engine.

        Args:
            drain: When True, wait for in-flight strategies to complete.
        """
        logger.info("StrategyLifecycleEngine SHUTDOWN (drain=%s)", drain)
        self._scheduler.stop(wait=drain)
        self._runtime.stop(drain=drain)
        self._pool.shutdown(wait=drain, cancel_futures=not drain)
        logger.info("StrategyLifecycleEngine SHUTDOWN complete")

    def pause(self) -> None:
        """Suspend scheduling. In-flight executions complete normally."""
        self._scheduler.pause()
        self._runtime.pause()

    def resume(self) -> None:
        """Resume scheduling from paused state."""
        self._runtime.resume()
        self._scheduler.resume()

    # ── Strategy registration ─────────────────────────────────────────────────

    def register(
        self,
        strategy_id: str,
        name: str,
        execute_fn: Callable[[RuntimeContext], Any],
        failure_policy: Optional[FailurePolicy] = None,
        restart_policy: RestartPolicy = RestartPolicy.NEVER,
        tags: Optional[List[str]] = None,
        replace: bool = False,
    ) -> None:
        """
        Register a strategy with the engine.

        Args:
            strategy_id:     Unique string identifier.
            name:            Human-readable display name.
            execute_fn:      Callable(RuntimeContext) → Any  (pure orchestration).
            failure_policy:  Override per-strategy retry / circuit-breaker policy.
            restart_policy:  When to auto-restart after completion / failure.
            tags:            Optional classification labels.
            replace:         If True, silently replaces an existing registration.
        """
        with self._lock:
            if strategy_id in self._strategies and not replace:
                raise LifecycleEngineError(
                    f"Strategy {strategy_id!r} already registered — "
                    f"use replace=True to overwrite."
                )
            self._strategies[strategy_id] = _StrategyRecord(
                strategy_id=strategy_id,
                name=name,
                execute_fn=execute_fn,
                failure_policy=failure_policy,
                restart_policy=restart_policy,
                tags=tags or [],
            )

        self._recovery.configure_strategy(
            strategy_id,
            failure_policy=failure_policy,
            restart_policy=restart_policy,
        )
        logger.debug("Registered strategy %s (%s)", strategy_id, name)

    def unregister(self, strategy_id: str) -> bool:
        """
        Remove a strategy from the engine.

        Returns True if the strategy was found and removed.
        """
        with self._lock:
            if strategy_id not in self._strategies:
                return False
            del self._strategies[strategy_id]

        self._scheduler.unschedule(strategy_id)
        self._dep_engine.remove_strategy(strategy_id)
        self._recovery.reset_strategy(strategy_id)
        logger.debug("Unregistered strategy %s", strategy_id)
        return True

    def registered_ids(self) -> List[str]:
        """Return all currently registered strategy IDs."""
        with self._lock:
            return list(self._strategies.keys())

    # ── Scheduling API ────────────────────────────────────────────────────────

    def schedule_periodic(
        self,
        strategy_id: str,
        interval_seconds: float,
        priority: SchedulePriority = SchedulePriority.NORMAL,
    ) -> None:
        """Run strategy every ``interval_seconds`` seconds."""
        self._ensure_registered(strategy_id)
        self._scheduler.schedule(ScheduleEntry(
            strategy_id=strategy_id,
            schedule_type=ScheduleType.PERIODIC,
            interval_seconds=interval_seconds,
            priority=int(priority),
        ))

    def schedule_time_based(
        self,
        strategy_id: str,
        trigger_times: List[str],
        priority: SchedulePriority = SchedulePriority.NORMAL,
    ) -> None:
        """Run strategy at specific UTC times in "HH:MM" format."""
        self._ensure_registered(strategy_id)
        self._scheduler.schedule(ScheduleEntry(
            strategy_id=strategy_id,
            schedule_type=ScheduleType.TIME_BASED,
            trigger_times=trigger_times,
            priority=int(priority),
        ))

    def schedule_event(
        self,
        strategy_id: str,
        event_name: str,
        priority: SchedulePriority = SchedulePriority.NORMAL,
    ) -> None:
        """Run strategy whenever fire_event(event_name) is called."""
        self._ensure_registered(strategy_id)
        self._scheduler.schedule(ScheduleEntry(
            strategy_id=strategy_id,
            schedule_type=ScheduleType.EVENT,
            trigger_event=event_name,
            priority=int(priority),
        ))

    def schedule_conditional(
        self,
        strategy_id: str,
        condition_fn: Callable[[], bool],
        priority: SchedulePriority = SchedulePriority.NORMAL,
    ) -> None:
        """Run strategy on each scheduler tick where condition_fn() is True."""
        self._ensure_registered(strategy_id)
        self._scheduler.schedule(ScheduleEntry(
            strategy_id=strategy_id,
            schedule_type=ScheduleType.CONDITIONAL,
            condition_fn=condition_fn,
            priority=int(priority),
        ))

    def unschedule(self, strategy_id: str) -> None:
        """Remove all scheduling for a strategy."""
        self._scheduler.unschedule(strategy_id)

    # ── Dependency API ────────────────────────────────────────────────────────

    def declare_dependency(
        self,
        strategy_id: str,
        depends_on: str,
        required: bool = True,
    ) -> None:
        """
        Declare that strategy_id must execute after depends_on each cycle.

        Raises CyclicDependencyError if this creates a cycle.
        """
        self._ensure_registered(strategy_id)
        from iios.investment.strategy.lifecycle.dependency_graph import (
            CyclicDependencyError,
        )
        self._dep_engine.declare(DependencyDeclaration(
            strategy_id=strategy_id,
            depends_on=depends_on,
            dependency_type=DependencyType.STRATEGY,
            required=required,
        ))

    def validate_dependencies(self) -> DependencyValidationResult:
        """Validate the current dependency graph."""
        with self._lock:
            registered = set(self._strategies.keys())
        return self._dep_engine.validate(registered)

    # ── Execution API ─────────────────────────────────────────────────────────

    def submit(
        self,
        strategy_id: str,
        context: Optional[RuntimeContext] = None,
        priority: SchedulePriority = SchedulePriority.NORMAL,
    ) -> Future:
        """
        Submit a strategy for immediate execution.

        Returns a Future that resolves when execution completes.
        Raises EngineNotRunningError when the engine is not RUNNING.
        """
        if not self._runtime.is_running:
            raise EngineNotRunningError(
                f"Engine is {self._runtime.state.value} — cannot accept submissions"
            )
        self._ensure_registered(strategy_id)
        ctx = context or self._runtime.make_context()
        return self._pool.submit(self._execute_strategy, strategy_id, ctx)

    def run_cycle(
        self,
        context: Optional[RuntimeContext] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Execute all (or a subset of) registered strategies in dependency order.

        Strategies sharing no dependencies within a batch run in parallel.

        Returns:
            dict mapping strategy_id → result string:
              "success" | "failed:<ErrorType>" | "skipped_circuit_open"
        """
        ctx = context or self._runtime.make_context()
        cycle_start = time.monotonic()

        with self._lock:
            candidates: Set[str] = (
                set(strategy_ids) if strategy_ids else set(self._strategies.keys())
            )

        self._dep_engine.reset_cycle()
        results: Dict[str, str] = {}

        # Build execution batches: dep-declared strategies get ordered batches;
        # strategies with no deps are collected into a single leading batch.
        batches = self._dep_engine.parallel_batches()
        dep_ids: Set[str] = {sid for batch in batches for sid in batch}
        no_dep = sorted(candidates - dep_ids)
        if no_dep:
            batches = [no_dep] + batches

        for batch in batches:
            batch_targets = [sid for sid in batch if sid in candidates]
            if not batch_targets:
                continue

            futures: Dict[str, Future] = {}
            for sid in batch_targets:
                if self._recovery.is_circuit_open(sid):
                    results[sid] = "skipped_circuit_open"
                    continue
                futures[sid] = self._pool.submit(self._execute_strategy, sid, ctx)

            for sid, future in futures.items():
                try:
                    future.result()
                    results[sid] = "success"
                    self._dep_engine.mark_completed(sid)
                except Exception as exc:
                    results[sid] = f"failed:{type(exc).__name__}"

        elapsed_ms = (time.monotonic() - cycle_start) * 1_000
        success_n = sum(1 for v in results.values() if v == "success")
        failure_n = len(results) - success_n
        self._runtime.statistics.record(CycleSample(
            cycle_id=ctx.cycle_id,
            strategy_count=len(results),
            duration_ms=elapsed_ms,
            success_count=success_n,
            failure_count=failure_n,
        ))

        return results

    def fire_event(
        self,
        event_name: str,
        context: Optional[RuntimeContext] = None,
    ) -> int:
        """
        Fire a named event, triggering all subscribed strategies.

        Returns the number of strategies dispatched.
        """
        ctx = context or self._runtime.make_context()
        return self._scheduler.fire_event(event_name, ctx)

    # ── Checkpointing API ─────────────────────────────────────────────────────

    def save_checkpoint(
        self,
        strategy_id: str,
        state_snapshot: Dict[str, Any],
        cycle_id: str = "",
        label: str = "",
    ) -> Any:
        """Save a state checkpoint for a strategy."""
        return self._recovery.save_checkpoint(
            strategy_id, state_snapshot, cycle_id, label
        )

    def load_checkpoint(self, strategy_id: str) -> Optional[Any]:
        """Load the most recent checkpoint for a strategy, or None."""
        return self._recovery.load_latest_checkpoint(strategy_id)

    # ── Observability API ─────────────────────────────────────────────────────

    def runtime_snapshot(self) -> RuntimeStateSnapshot:
        """Point-in-time view of engine state and cycle statistics."""
        snap = self._runtime.snapshot()
        snap.active_strategies = self._resource_manager.active_count
        snap.queued_strategies = self._scheduler.queue_depth
        return snap

    def health_report(self) -> EngineHealthReport:
        """Overall engine and per-strategy health summary."""
        return self._monitor.engine_health_report()

    def strategy_health(self, strategy_id: str) -> StrategyHealth:
        """Health assessment for one specific strategy."""
        return self._monitor.assess_strategy(strategy_id)

    def execution_history(
        self,
        strategy_id: Optional[str] = None,
        last_n: int = 50,
    ) -> List[ExecutionRecord]:
        """Recent execution records (all strategies or one specific strategy)."""
        if strategy_id:
            return self._monitor.tracker.get_for_strategy(strategy_id, last_n)
        return self._monitor.tracker.get_recent(last_n)

    def performance_metrics(self, strategy_id: Optional[str] = None) -> Any:
        """Execution performance metrics (global or per-strategy)."""
        return self._monitor.performance.compute(strategy_id=strategy_id)

    def recovery_status(self, strategy_id: str) -> dict:
        """Recovery status summary for a strategy."""
        return {
            "strategy_id": strategy_id,
            "circuit_state": self._recovery.circuit_state(strategy_id).value,
            "restart_count": self._recovery.restart_count(strategy_id),
            "recent_failures": len(self._recovery.failure_history(strategy_id)),
            "has_checkpoint": (
                self._recovery.load_latest_checkpoint(strategy_id) is not None
            ),
        }

    def queue_depth(self) -> int:
        return self._scheduler.queue_depth

    def in_flight_count(self) -> int:
        return self._scheduler.in_flight_count

    def in_flight_ids(self) -> List[str]:
        return self._scheduler.in_flight_ids

    def resource_snapshot(self) -> Any:
        return self._resource_manager.snapshot()

    # ── Engine properties ─────────────────────────────────────────────────────

    @property
    def state(self) -> RuntimeState:
        return self._runtime.state

    @property
    def is_running(self) -> bool:
        return self._runtime.is_running

    @property
    def resource_manager(self) -> ResourceManager:
        return self._resource_manager

    @property
    def dependency_engine(self) -> DependencyEngine:
        return self._dep_engine

    @property
    def scheduler(self) -> StrategyScheduler:
        return self._scheduler

    @property
    def monitor(self) -> ExecutionMonitor:
        return self._monitor

    @property
    def recovery(self) -> RecoveryEngine:
        return self._recovery

    # ── Internal execution pipeline ───────────────────────────────────────────

    def _execute_strategy(
        self,
        strategy_id: str,
        ctx: RuntimeContext,
    ) -> None:
        """
        Core execution path — always invoked on a pool thread.

        1. Acquire resource ticket (admission control)
        2. Loop: run execute_fn, handle failures with inline retry + backoff
        3. Re-raise on final failure (enables run_cycle to record "failed:")
        4. Release resource ticket (always, via finally)
        """
        with self._lock:
            record = self._strategies.get(strategy_id)
        if record is None:
            logger.warning("_execute_strategy: %s not found — skipped", strategy_id)
            return

        # Admission control
        try:
            ticket = self._resource_manager.allocator.request(strategy_id)
        except Exception as alloc_exc:  # noqa: BLE001
            logger.warning(
                "Resource allocation denied for %s: %s", strategy_id, alloc_exc
            )
            return

        attempt = 0
        last_exc: Optional[Exception] = None

        try:
            while True:
                exec_record = self._monitor.start_record(
                    strategy_id, cycle_id=ctx.cycle_id
                )
                try:
                    record.execute_fn(ctx)
                    exec_record.complete(ExecutionStatus.SUCCESS)
                    self._recovery.handle_success(strategy_id)
                    last_exc = None
                    break  # success — exit retry loop

                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    error_type = type(exc).__name__
                    error_msg = str(exc)
                    logger.error(
                        "Strategy %s failed (attempt=%d): %s: %s",
                        strategy_id, attempt, error_type, error_msg,
                    )
                    exec_record.complete(
                        ExecutionStatus.FAILED,
                        error_type=error_type,
                        error_message=error_msg,
                    )
                    decision = self._recovery.handle_failure(
                        strategy_id=strategy_id,
                        error_type=error_type,
                        error_message=error_msg,
                        attempt=attempt,
                    )
                    if decision.should_retry:
                        attempt += 1
                        logger.info(
                            "Retrying strategy %s in %.1fs (attempt %d)",
                            strategy_id, decision.retry_delay_s, attempt,
                        )
                        time.sleep(decision.retry_delay_s)
                        continue  # next iteration = retry
                    break  # no more retries

        finally:
            self._resource_manager.allocator.release(ticket)

        # Propagate to run_cycle (which catches it for result tracking)
        if last_exc is not None:
            raise last_exc

    def _execute_request(self, request: Any) -> None:
        """Adapter: PriorityScheduler calls this for queue-sourced requests."""
        strategy_id = request.strategy_id
        ctx = request.context_ref or self._runtime.make_context()
        try:
            self._execute_strategy(strategy_id, ctx)
        except Exception:  # noqa: BLE001
            # Scheduler path: exception already logged; swallow here
            pass

    def _on_runtime_state_change(
        self, from_state: RuntimeState, to_state: RuntimeState
    ) -> None:
        logger.info(
            "Engine runtime: %s → %s", from_state.value, to_state.value
        )

    def _on_restart_triggered(self, strategy_id: str) -> None:
        """Callback from RestartManager when a strategy should auto-restart."""
        if self._runtime.is_running:
            ctx = self._runtime.make_context()
            self._pool.submit(self._execute_request_wrapper, strategy_id, ctx)

    def _execute_request_wrapper(self, strategy_id: str, ctx: RuntimeContext) -> None:
        """Fire-and-forget wrapper used by restart and scheduler paths."""
        try:
            self._execute_strategy(strategy_id, ctx)
        except Exception:  # noqa: BLE001
            pass

    def _ensure_registered(self, strategy_id: str) -> None:
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotRegisteredError(
                    f"Strategy {strategy_id!r} is not registered with the engine"
                )
