"""enterprise_ai_platform/execution/oms/order_queue/__init__.py
==================================================
Public API for the IIOS Order Queue.

C6 Execution Intelligence — Phase 2, Module 4
"""
from enterprise_ai_platform.execution.oms.order_queue.constants import (
    QUEUE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    ACTOR_QUEUE,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_TTL_SEC,
    DEFAULT_RETRY_DELAY_SEC,
    DEFAULT_MAX_RETRIES,
    ACTIVE_ENTRY_STATES,
    TERMINAL_ENTRY_STATES,
    DISPATCHABLE_STATES,
    VALID_ENTRY_TRANSITIONS,
    ExecutionMode,
    QueueEntryState,
    QueueEventType,
    QueuePolicyType,
    QueuePriorityLevel,
    QueueValidationCode,
)
from enterprise_ai_platform.execution.oms.order_queue.exceptions import (
    QueueError,
    QueueEntryError,
    DuplicateQueueEntryError,
    QueueEntryNotFoundError,
    QueueCapacityError,
    QueueNotRunning,
    QueueValidationError,
    QueuePolicyError,
    QueueSchedulerError,
    QueueEntryExpiredError,
    QueueEntryStateError,
)
from enterprise_ai_platform.execution.oms.order_queue.queue_entry import QueueEntry
from enterprise_ai_platform.execution.oms.order_queue.queue_priority import (
    priority_sort_key,
    compare_priority,
    highest_priority,
    lowest_priority,
)
from enterprise_ai_platform.execution.oms.order_queue.queue_context import QueueContext
from enterprise_ai_platform.execution.oms.order_queue.queue_policy import (
    QueuePolicy,
    get_policy,
    make_fifo_policy,
    make_priority_policy,
    make_scheduled_policy,
    make_delayed_policy,
    make_recovery_policy,
    make_replay_policy,
    make_paper_trading_policy,
    make_backtest_policy,
)
from enterprise_ai_platform.execution.oms.order_queue.queue_scheduler import QueueScheduler
from enterprise_ai_platform.execution.oms.order_queue.queue_dispatch_plan import QueueDispatchPlan
from enterprise_ai_platform.execution.oms.order_queue.queue_snapshot import QueueSnapshot
from enterprise_ai_platform.execution.oms.order_queue.queue_events import (
    QueueEvent,
    make_order_queued,
    make_queue_updated,
    make_priority_changed,
    make_order_dispatched,
    make_retry_scheduled,
    make_queue_suspended,
    make_queue_resumed,
    make_queue_cleared,
)
from enterprise_ai_platform.execution.oms.order_queue.queue_statistics import QueueStatistics
from enterprise_ai_platform.execution.oms.order_queue.queue_history import QueueHistory
from enterprise_ai_platform.execution.oms.order_queue.queue_validation import QueueValidator
from enterprise_ai_platform.execution.oms.order_queue.queue_registry import QueueRegistry
from enterprise_ai_platform.execution.oms.order_queue.queue_factory import QueueFactory
from enterprise_ai_platform.execution.oms.order_queue.order_queue import OrderQueue

__all__ = [
    # System IDs
    "QUEUE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    "ACTOR_QUEUE",
    # Defaults
    "DEFAULT_MAX_QUEUE_SIZE",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_TTL_SEC",
    "DEFAULT_RETRY_DELAY_SEC",
    "DEFAULT_MAX_RETRIES",
    # State sets
    "ACTIVE_ENTRY_STATES",
    "TERMINAL_ENTRY_STATES",
    "DISPATCHABLE_STATES",
    "VALID_ENTRY_TRANSITIONS",
    # Enumerations
    "ExecutionMode",
    "QueueEntryState",
    "QueueEventType",
    "QueuePolicyType",
    "QueuePriorityLevel",
    "QueueValidationCode",
    # Exceptions
    "QueueError",
    "QueueEntryError",
    "DuplicateQueueEntryError",
    "QueueEntryNotFoundError",
    "QueueCapacityError",
    "QueueNotRunning",
    "QueueValidationError",
    "QueuePolicyError",
    "QueueSchedulerError",
    "QueueEntryExpiredError",
    "QueueEntryStateError",
    # Data models
    "QueueEntry",
    "QueueContext",
    "QueueDispatchPlan",
    "QueueSnapshot",
    # Priority helpers
    "priority_sort_key",
    "compare_priority",
    "highest_priority",
    "lowest_priority",
    # Policies
    "QueuePolicy",
    "get_policy",
    "make_fifo_policy",
    "make_priority_policy",
    "make_scheduled_policy",
    "make_delayed_policy",
    "make_recovery_policy",
    "make_replay_policy",
    "make_paper_trading_policy",
    "make_backtest_policy",
    # Scheduler
    "QueueScheduler",
    # Events
    "QueueEvent",
    "make_order_queued",
    "make_queue_updated",
    "make_priority_changed",
    "make_order_dispatched",
    "make_retry_scheduled",
    "make_queue_suspended",
    "make_queue_resumed",
    "make_queue_cleared",
    # Infrastructure
    "QueueStatistics",
    "QueueHistory",
    "QueueValidator",
    "QueueRegistry",
    "QueueFactory",
    # Primary facade
    "OrderQueue",
]
