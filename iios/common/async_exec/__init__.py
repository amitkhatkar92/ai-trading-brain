"""iios/common/async_exec/__init__.py
Public API for the IIOS Unified Async Execution Framework.

Note: This package is named ``async_exec`` because ``async`` is a reserved
keyword in Python and cannot be used as a package name.

Quick-start::

    # 1. Classify a callable:
    from iios.common.async_exec import classify, WorkloadType
    result = classify(my_fn)               # → ClassificationResult

    # 2. Run from sync code (most current IIOS engines):
    from iios.common.async_exec import get_execution_manager
    mgr    = get_execution_manager()
    result = mgr.execute_sync(blocking_feed_call, symbol, timeout_sec=10.0)

    # 3. Run from async code:
    result = await mgr.execute(my_coro, timeout_sec=30.0)

    # 4. Enforce timeouts:
    from iios.common.async_exec import apply_timeout, TimeoutPolicy
    policy = TimeoutPolicy(engine_timeout_sec=15.0)
    result = await apply_timeout(coro, policy.engine_timeout_sec)

    # 5. Cancellation:
    from iios.common.async_exec import CancellationToken
    token = CancellationToken()
    # from another thread:
    token.cancel("shutdown requested")

    # 6. Migration roadmap:
    from iios.common.async_exec import PLATFORM_ASYNC_PROFILES
"""

from iios.common.async_exec.execution_classifier import (
    ClassificationResult,
    ExecutionClassifier,
    WorkloadType,
    classify,
    classify_as,
)

from iios.common.async_exec.timeout_policy import (
    TimeoutPolicy,
    apply_timeout,
    with_engine_timeout,
    with_pipeline_timeout,
    with_stage_timeout,
    with_workflow_timeout,
    timeout_scope,
)

from iios.common.async_exec.cancellation import (
    CancellationToken,
    CancellationScope,
    LinkedCancellationToken,
    create_token,
)

from iios.common.async_exec.async_executor import (
    AsyncExecutor,
    ExecutorConfig,
)

from iios.common.async_exec.async_execution_manager import (
    AsyncExecutionManager,
    ExecutionManagerConfig,
    ExecutionMetricsSnapshot,
    TaskRecord,
    get_execution_manager,
    reset_execution_manager,
)

from iios.common.async_exec.migration_analysis import (
    AsyncMethodProfile,
    EngineAsyncProfile,
    PLATFORM_ASYNC_PROFILES,
    all_async_methods,
    engines_by_complexity,
    engines_needing_standardization,
    get_profile,
    methods_needing_standardization,
)


__all__ = [
    # Execution classifier
    "ClassificationResult",
    "ExecutionClassifier",
    "WorkloadType",
    "classify",
    "classify_as",
    # Timeout policy
    "TimeoutPolicy",
    "apply_timeout",
    "with_engine_timeout",
    "with_pipeline_timeout",
    "with_stage_timeout",
    "with_workflow_timeout",
    "timeout_scope",
    # Cancellation
    "CancellationToken",
    "CancellationScope",
    "LinkedCancellationToken",
    "create_token",
    # Async executor
    "AsyncExecutor",
    "ExecutorConfig",
    # Execution manager
    "AsyncExecutionManager",
    "ExecutionManagerConfig",
    "ExecutionMetricsSnapshot",
    "TaskRecord",
    "get_execution_manager",
    "reset_execution_manager",
    # Migration analysis
    "AsyncMethodProfile",
    "EngineAsyncProfile",
    "PLATFORM_ASYNC_PROFILES",
    "all_async_methods",
    "engines_by_complexity",
    "engines_needing_standardization",
    "get_profile",
    "methods_needing_standardization",
]
