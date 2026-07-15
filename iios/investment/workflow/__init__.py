"""iios/investment/workflow/__init__.py"""
from __future__ import annotations

from iios.investment.workflow.engine_lifecycle import (
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
from iios.investment.workflow.institutional_investment_workflow import (
    InstitutionalInvestmentWorkflow,
    InstitutionalWorkflowOrchestrator,
    WorkflowResult,
)
from iios.investment.workflow.investment_workflow import (
    InvestmentWorkflow,
    NoOpWorkflow,
)
from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from iios.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from iios.investment.workflow.workflow_executor import WorkflowExecutor
from iios.investment.workflow.workflow_history import WorkflowHistory, WorkflowRunRecord
from iios.investment.workflow.workflow_state import StageRecord, WorkflowState
from iios.investment.workflow.workflow_statistics import (
    WorkflowRunMetric,
    WorkflowStatistics,
    WorkflowStatisticsSnapshot,
)
from iios.investment.workflow.workflow_types import (
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
