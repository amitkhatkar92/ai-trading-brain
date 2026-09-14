"""enterprise_ai_platform/investment/strategy/lifecycle/__init__.py
Institutional Strategy Lifecycle & Execution Engine.

Public API — import from this package, not from individual modules.
"""
# ── Pre-existing (strategy state-machine lifecycle) ───────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.lifecycle_history import (
    LifecycleHistory,
    LifecycleHistoryEntry,
)
from enterprise_ai_platform.investment.strategy.lifecycle.lifecycle_manager import LifecycleManager

# ── Runtime ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.runtime_context import RuntimeContext
from enterprise_ai_platform.investment.strategy.lifecycle.runtime_state import (
    RuntimeState,
    RuntimeStateSnapshot,
    validate_runtime_transition,
)
from enterprise_ai_platform.investment.strategy.lifecycle.runtime_statistics import (
    CycleSample,
    RuntimeStatistics,
)
from enterprise_ai_platform.investment.strategy.lifecycle.runtime_manager import (
    RuntimeManager,
    RuntimeManagerError,
)

# ── Scheduler ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.execution_queue import (
    ExecutionQueue,
    ExecutionRequest,
    QueueFullError,
    SchedulePriority,
)
from enterprise_ai_platform.investment.strategy.lifecycle.priority_scheduler import PriorityScheduler
from enterprise_ai_platform.investment.strategy.lifecycle.schedule_registry import (
    ScheduleEntry,
    ScheduleRegistry,
    ScheduleType,
)
from enterprise_ai_platform.investment.strategy.lifecycle.strategy_scheduler import StrategyScheduler

# ── Dependency ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
    DependencyNode,
)
from enterprise_ai_platform.investment.strategy.lifecycle.dependency_validator import (
    DependencyValidationResult,
    DependencyValidator,
)
from enterprise_ai_platform.investment.strategy.lifecycle.dependency_registry import (
    DependencyDeclaration,
    DependencyRegistry,
    DependencyType,
)
from enterprise_ai_platform.investment.strategy.lifecycle.dependency_engine import (
    DependencyEngine,
    DependencyResolutionError,
)

# ── Execution monitoring ──────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionStatus,
    ExecutionTracker,
)
from enterprise_ai_platform.investment.strategy.lifecycle.performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
)
from enterprise_ai_platform.investment.strategy.lifecycle.execution_monitor import (
    EngineHealthReport,
    ExecutionMonitor,
    HealthStatus,
    StrategyHealth,
)

# ── Recovery ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.checkpoint_manager import (
    Checkpoint,
    CheckpointManager,
)
from enterprise_ai_platform.investment.strategy.lifecycle.failure_handler import (
    CircuitState,
    FailureHandler,
    FailurePolicy,
    FailureRecord,
    StrategyCircuit,
)
from enterprise_ai_platform.investment.strategy.lifecycle.restart_manager import (
    RestartManager,
    RestartPolicy,
    RestartRecord,
)
from enterprise_ai_platform.investment.strategy.lifecycle.recovery_engine import (
    RecoveryDecision,
    RecoveryEngine,
)

# ── Resources ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.resource_limits import (
    ResourceLimits,
    ResourceProfile,
)
from enterprise_ai_platform.investment.strategy.lifecycle.resource_statistics import (
    ResourceSnapshot,
    ResourceStatistics,
)
from enterprise_ai_platform.investment.strategy.lifecycle.resource_allocator import (
    AllocationError,
    AllocationTicket,
    ResourceAllocator,
)
from enterprise_ai_platform.investment.strategy.lifecycle.resource_manager import ResourceManager

# ── Main engine ───────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.strategy.lifecycle.strategy_lifecycle_engine import (
    EngineNotRunningError,
    LifecycleEngineError,
    StrategyLifecycleEngine,
    StrategyNotRegisteredError,
)

__all__ = [
    # Pre-existing
    "LifecycleHistory",
    "LifecycleHistoryEntry",
    "LifecycleManager",
    # Runtime
    "RuntimeContext",
    "RuntimeState",
    "RuntimeStateSnapshot",
    "validate_runtime_transition",
    "CycleSample",
    "RuntimeStatistics",
    "RuntimeManager",
    "RuntimeManagerError",
    # Scheduler
    "ExecutionQueue",
    "ExecutionRequest",
    "QueueFullError",
    "SchedulePriority",
    "PriorityScheduler",
    "ScheduleEntry",
    "ScheduleRegistry",
    "ScheduleType",
    "StrategyScheduler",
    # Dependency
    "CyclicDependencyError",
    "DependencyGraph",
    "DependencyNode",
    "DependencyValidationResult",
    "DependencyValidator",
    "DependencyDeclaration",
    "DependencyRegistry",
    "DependencyType",
    "DependencyEngine",
    "DependencyResolutionError",
    # Monitoring
    "ExecutionRecord",
    "ExecutionStatus",
    "ExecutionTracker",
    "PerformanceMetrics",
    "PerformanceTracker",
    "EngineHealthReport",
    "ExecutionMonitor",
    "HealthStatus",
    "StrategyHealth",
    # Recovery
    "Checkpoint",
    "CheckpointManager",
    "CircuitState",
    "FailureHandler",
    "FailurePolicy",
    "FailureRecord",
    "StrategyCircuit",
    "RestartManager",
    "RestartPolicy",
    "RestartRecord",
    "RecoveryDecision",
    "RecoveryEngine",
    # Resources
    "ResourceLimits",
    "ResourceProfile",
    "ResourceSnapshot",
    "ResourceStatistics",
    "AllocationError",
    "AllocationTicket",
    "ResourceAllocator",
    "ResourceManager",
    # Main engine
    "EngineNotRunningError",
    "LifecycleEngineError",
    "StrategyLifecycleEngine",
    "StrategyNotRegisteredError",
]
