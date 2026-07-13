"""iios/investment/strategy/lifecycle/__init__.py
Institutional Strategy Lifecycle & Execution Engine.

Public API — import from this package, not from individual modules.
"""
# ── Pre-existing (strategy state-machine lifecycle) ───────────────────────────
from iios.investment.strategy.lifecycle.lifecycle_history import (
    LifecycleHistory,
    LifecycleHistoryEntry,
)
from iios.investment.strategy.lifecycle.lifecycle_manager import LifecycleManager

# ── Runtime ───────────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.runtime_context import RuntimeContext
from iios.investment.strategy.lifecycle.runtime_state import (
    RuntimeState,
    RuntimeStateSnapshot,
    validate_runtime_transition,
)
from iios.investment.strategy.lifecycle.runtime_statistics import (
    CycleSample,
    RuntimeStatistics,
)
from iios.investment.strategy.lifecycle.runtime_manager import (
    RuntimeManager,
    RuntimeManagerError,
)

# ── Scheduler ─────────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.execution_queue import (
    ExecutionQueue,
    ExecutionRequest,
    QueueFullError,
    SchedulePriority,
)
from iios.investment.strategy.lifecycle.priority_scheduler import PriorityScheduler
from iios.investment.strategy.lifecycle.schedule_registry import (
    ScheduleEntry,
    ScheduleRegistry,
    ScheduleType,
)
from iios.investment.strategy.lifecycle.strategy_scheduler import StrategyScheduler

# ── Dependency ────────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
    DependencyNode,
)
from iios.investment.strategy.lifecycle.dependency_validator import (
    DependencyValidationResult,
    DependencyValidator,
)
from iios.investment.strategy.lifecycle.dependency_registry import (
    DependencyDeclaration,
    DependencyRegistry,
    DependencyType,
)
from iios.investment.strategy.lifecycle.dependency_engine import (
    DependencyEngine,
    DependencyResolutionError,
)

# ── Execution monitoring ──────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionStatus,
    ExecutionTracker,
)
from iios.investment.strategy.lifecycle.performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
)
from iios.investment.strategy.lifecycle.execution_monitor import (
    EngineHealthReport,
    ExecutionMonitor,
    HealthStatus,
    StrategyHealth,
)

# ── Recovery ──────────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.checkpoint_manager import (
    Checkpoint,
    CheckpointManager,
)
from iios.investment.strategy.lifecycle.failure_handler import (
    CircuitState,
    FailureHandler,
    FailurePolicy,
    FailureRecord,
    StrategyCircuit,
)
from iios.investment.strategy.lifecycle.restart_manager import (
    RestartManager,
    RestartPolicy,
    RestartRecord,
)
from iios.investment.strategy.lifecycle.recovery_engine import (
    RecoveryDecision,
    RecoveryEngine,
)

# ── Resources ─────────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.resource_limits import (
    ResourceLimits,
    ResourceProfile,
)
from iios.investment.strategy.lifecycle.resource_statistics import (
    ResourceSnapshot,
    ResourceStatistics,
)
from iios.investment.strategy.lifecycle.resource_allocator import (
    AllocationError,
    AllocationTicket,
    ResourceAllocator,
)
from iios.investment.strategy.lifecycle.resource_manager import ResourceManager

# ── Main engine ───────────────────────────────────────────────────────────────
from iios.investment.strategy.lifecycle.strategy_lifecycle_engine import (
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
