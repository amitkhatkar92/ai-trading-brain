"""enterprise_ai_platform/investment/workflow/__init__.py"""
from __future__ import annotations

from enterprise_ai_platform.investment.workflow.engine_lifecycle import (
    EngineState,
    LifecycleAwareMixin,
    LifecycleController,
    LifecycleError,
    LifecycleEvent,
    LifecycleEventType,
    LifecycleStatus,
    InvalidTransitionError,
    EngineAlreadyRunningError,
    EngineNotRunningError,
    EngineShutdownError,
)
from enterprise_ai_platform.investment.workflow.institutional_investment_workflow import (
    InstitutionalInvestmentWorkflow,
    InstitutionalWorkflowOrchestrator,
    WorkflowResult,
)
from enterprise_ai_platform.investment.workflow.investment_workflow import (
    InvestmentWorkflow,
    NoOpWorkflow,
)
from enterprise_ai_platform.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from enterprise_ai_platform.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from enterprise_ai_platform.investment.workflow.workflow_executor import WorkflowExecutor
from enterprise_ai_platform.investment.workflow.workflow_history import WorkflowHistory, WorkflowRunRecord
from enterprise_ai_platform.investment.workflow.workflow_state import StageRecord, WorkflowState
from enterprise_ai_platform.investment.workflow.workflow_statistics import (
    WorkflowRunMetric,
    WorkflowStatistics,
    WorkflowStatisticsSnapshot,
)
from enterprise_ai_platform.investment.workflow.workflow_types import (
    PIPELINE_STAGES,
    TERMINAL_STAGES,
    WORKFLOW_VERSION,
    PipelineEventType,
    StageStatus,
    WorkflowStage,
)

__all__ = [
    # Lifecycle framework
    "EngineState",
    "LifecycleAwareMixin",
    "LifecycleController",
    "LifecycleError",
    "LifecycleEvent",
    "LifecycleEventType",
    "LifecycleStatus",
    "InvalidTransitionError",
    "EngineAlreadyRunningError",
    "EngineNotRunningError",
    "EngineShutdownError",
    # Core abstract base
    "InvestmentWorkflow",
    "NoOpWorkflow",
    "WorkflowExecutor",
    # Concrete pipeline
    "InstitutionalInvestmentWorkflow",
    "InstitutionalWorkflowOrchestrator",
    "WorkflowResult",
    # Configuration + engines
    "WorkflowParameters",
    "WorkflowEngines",
    # Types
    "WorkflowStage",
    "StageStatus",
    "PipelineEventType",
    "PIPELINE_STAGES",
    "TERMINAL_STAGES",
    "WORKFLOW_VERSION",
    # State
    "WorkflowState",
    "StageRecord",
    # Events
    "WorkflowEvent",
    "WorkflowEventPublisher",
    # History
    "WorkflowRunRecord",
    "WorkflowHistory",
    # Statistics
    "WorkflowRunMetric",
    "WorkflowStatistics",
    "WorkflowStatisticsSnapshot",
]
