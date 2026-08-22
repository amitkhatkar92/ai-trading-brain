"""
tests/unit/bootstrap/test_startup_manager.py
==============================================
Unit tests for StartupManager — execution order, dependency checks,
retry logic, and progress callbacks.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from iios.bootstrap.startup_context import StartupContext
from iios.bootstrap.startup_manager import StartupManager, StartupManagerConfig
from iios.bootstrap.startup_state import (
    BootstrapError,
    BootstrapStage,
    StageStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_stage(
    number: int,
    handler: object = None,
    deps: list[int] | None = None,
    optional: bool = False,
    can_retry: bool = False,
    max_retries: int = 1,
) -> BootstrapStage:
    if handler is None:
        handler = lambda ctx: None  # noqa: E731
    return BootstrapStage(
        number=number,
        name=f"stage_{number}",
        description="",
        handler=handler,
        dependencies=deps or [],
        optional=optional,
        can_retry=can_retry,
        max_retries=max_retries,
        timeout_seconds=5.0,
    )


def make_context() -> StartupContext:
    return StartupContext(total_stages=10)


# ---------------------------------------------------------------------------
# Execution order
# ---------------------------------------------------------------------------


class TestExecutionOrder:
    def test_runs_stages_in_number_order(self) -> None:
        order: list[int] = []
        stages = [
            make_stage(3, handler=lambda ctx: order.append(3)),
            make_stage(1, handler=lambda ctx: order.append(1)),
            make_stage(2, handler=lambda ctx: order.append(2)),
        ]
        manager = StartupManager(make_context(), stages)
        manager.run()
        assert order == [1, 2, 3]

    def test_all_stages_recorded_in_context(self) -> None:
        ctx = make_context()
        stages = [make_stage(i) for i in range(1, 4)]
        StartupManager(ctx, stages).run()
        assert len(ctx.stage_results) == 3
        for i, result in enumerate(ctx.stage_results, start=1):
            assert result.stage_number == i
            assert result.status == StageStatus.COMPLETED


# ---------------------------------------------------------------------------
# Dependency validation
# ---------------------------------------------------------------------------


class TestDependencyValidation:
    def test_stage_skipped_if_dependency_failed(self) -> None:
        ctx = make_context()
        always_fail = lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))  # noqa: E731

        stages = [
            make_stage(1, handler=lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))),
            make_stage(2, deps=[1]),
        ]
        config = StartupManagerConfig(abort_on_critical_failure=False)
        manager = StartupManager(ctx, stages, config=config)
        manager.run()

        r1 = ctx.get_stage_result(1)
        r2 = ctx.get_stage_result(2)
        assert r1 is not None and r1.status == StageStatus.FAILED
        assert r2 is not None and r2.status == StageStatus.SKIPPED

    def test_stage_runs_when_dependency_succeeds(self) -> None:
        ctx = make_context()
        ran: list[int] = []
        stages = [
            make_stage(1, handler=lambda ctx: ran.append(1)),
            make_stage(2, deps=[1], handler=lambda ctx: ran.append(2)),
        ]
        StartupManager(ctx, stages).run()
        assert ran == [1, 2]

    def test_optional_stage_skipped_silently(self) -> None:
        ctx = make_context()
        stages = [
            make_stage(1, handler=lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))),
            make_stage(2, deps=[1], optional=True),
        ]
        config = StartupManagerConfig(abort_on_critical_failure=False)
        manager = StartupManager(ctx, stages, config=config)
        manager.run()
        r2 = ctx.get_stage_result(2)
        assert r2 is not None and r2.status == StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    def test_stage_retries_on_failure_then_succeeds(self) -> None:
        attempts: list[int] = []

        def flaky(ctx: StartupContext) -> None:
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("transient error")

        ctx = make_context()
        stages = [make_stage(1, handler=flaky, can_retry=True, max_retries=3)]
        config = StartupManagerConfig(retry_base_delay_seconds=0.0)
        manager = StartupManager(ctx, stages, config=config)
        manager.run()
        assert len(attempts) == 2
        assert ctx.get_stage_result(1).status == StageStatus.COMPLETED

    def test_stage_fails_after_all_retries(self) -> None:
        def always_fail(ctx: StartupContext) -> None:
            raise RuntimeError("always fails")

        ctx = make_context()
        stages = [make_stage(1, handler=always_fail, can_retry=True, max_retries=3)]
        config = StartupManagerConfig(
            abort_on_critical_failure=False,
            retry_base_delay_seconds=0.0,
        )
        manager = StartupManager(ctx, stages, config=config)
        manager.run()
        r = ctx.get_stage_result(1)
        assert r is not None
        assert r.status == StageStatus.FAILED
        assert r.attempt == 3

    def test_no_retry_when_can_retry_false(self) -> None:
        attempts: list[int] = []

        def handler(ctx: StartupContext) -> None:
            attempts.append(1)
            raise RuntimeError("fail")

        ctx = make_context()
        stages = [make_stage(1, handler=handler, can_retry=False, max_retries=1)]
        config = StartupManagerConfig(abort_on_critical_failure=False)
        manager = StartupManager(ctx, stages, config=config)
        manager.run()
        assert len(attempts) == 1


# ---------------------------------------------------------------------------
# Abort on critical failure
# ---------------------------------------------------------------------------


class TestAbortBehaviour:
    def test_raises_bootstrap_error_on_critical_failure(self) -> None:
        def fail(ctx: StartupContext) -> None:
            raise RuntimeError("critical!")

        ctx = make_context()
        stages = [make_stage(1, handler=fail)]
        config = StartupManagerConfig(
            abort_on_critical_failure=True,
            retry_base_delay_seconds=0.0,
        )
        manager = StartupManager(ctx, stages, config=config)
        with pytest.raises(BootstrapError, match="stage_1"):
            manager.run()

    def test_does_not_raise_when_abort_disabled(self) -> None:
        def fail(ctx: StartupContext) -> None:
            raise RuntimeError("non-critical")

        ctx = make_context()
        stages = [make_stage(1, handler=fail)]
        config = StartupManagerConfig(
            abort_on_critical_failure=False,
            retry_base_delay_seconds=0.0,
        )
        manager = StartupManager(ctx, stages, config=config)
        manager.run()  # Should not raise
        r = ctx.get_stage_result(1)
        assert r.status == StageStatus.FAILED


# ---------------------------------------------------------------------------
# Progress callbacks
# ---------------------------------------------------------------------------


class TestProgressCallbacks:
    def test_callback_called_for_each_stage(self) -> None:
        calls: list[tuple] = []

        def cb(stage_number: int, name: str, status: StageStatus, elapsed_ms: float) -> None:
            calls.append((stage_number, status))

        ctx = make_context()
        stages = [make_stage(i) for i in range(1, 4)]
        manager = StartupManager(ctx, stages)
        manager.add_progress_callback(cb)
        manager.run()
        assert len(calls) == 3
        assert all(status == StageStatus.COMPLETED for _, status in calls)

    def test_callback_called_on_failure(self) -> None:
        statuses: list[StageStatus] = []

        def cb(n: int, name: str, status: StageStatus, ms: float) -> None:
            statuses.append(status)

        def fail(ctx: StartupContext) -> None:
            raise RuntimeError("fail")

        ctx = make_context()
        stages = [make_stage(1, handler=fail)]
        config = StartupManagerConfig(abort_on_critical_failure=False, retry_base_delay_seconds=0.0)
        manager = StartupManager(ctx, stages, config=config)
        manager.add_progress_callback(cb)
        manager.run()
        assert StageStatus.FAILED in statuses

    def test_broken_callback_does_not_abort(self) -> None:
        def broken_cb(*args: object) -> None:
            raise RuntimeError("callback broken")

        ctx = make_context()
        stages = [make_stage(1)]
        manager = StartupManager(ctx, stages)
        manager.add_progress_callback(broken_cb)
        manager.run()  # Should complete despite bad callback
        assert ctx.get_stage_result(1).status == StageStatus.COMPLETED


# ---------------------------------------------------------------------------
# run_stage (targeted)
# ---------------------------------------------------------------------------


class TestRunSingleStage:
    def test_run_stage_by_number(self) -> None:
        ran: list[int] = []
        ctx = make_context()
        stages = [make_stage(5, handler=lambda ctx: ran.append(5))]
        manager = StartupManager(ctx, stages)
        result = manager.run_stage(5)
        assert result.status == StageStatus.COMPLETED
        assert 5 in ran

    def test_run_stage_unknown_raises(self) -> None:
        ctx = make_context()
        manager = StartupManager(ctx, [make_stage(1)])
        with pytest.raises(ValueError, match="99"):
            manager.run_stage(99)
