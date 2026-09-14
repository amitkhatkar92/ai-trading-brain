"""enterprise_ai_platform/investment/__init__.py — Investment Intelligence Engine Core"""
from __future__ import annotations

# ── constants ─────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_constants import (
    AnalysisStatus,
    AssetClass,
    IntelligenceType,
    InvestmentObjective,
    RiskProfile,
    SessionStatus,
    TimeHorizon,
    WorkflowStatus,
    INVESTMENT_ENGINE_VERSION,
    INVESTMENT_ENGINE_SYSTEM_ID,
)

# ── exceptions ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_exceptions import (
    InvestmentEngineError,
    InvestmentError,
    InvestmentNotFoundError,
    InvestmentAlreadyExistsError,
    InvestmentFailedError,
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowAlreadyExistsError,
    WorkflowExecutionError,
    WorkflowCancelledError,
    RegistryError,
    RegistryItemNotFoundError,
    RegistryItemAlreadyExistsError,
    RegistryOverflowError,
    AnalysisError,
    AnalysisFailedError,
    AnalysisTimeoutError,
    AnalysisInvalidError,
    EngineLifecycleError,
    EngineNotInitializedError,
    EngineAlreadyRunningError,
    SessionError,
    SessionNotFoundError,
    SessionExpiredError,
    AssetClassError,
    AssetClassNotSupportedError,
    AssetClassInvalidError,
    DomainEngineError,
    DomainEngineNotFoundError,
    DomainEngineAlreadyRegisteredError,
    RequestValidationError,
)

# ── context ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_context import (
    InvestmentContextState,
    get_investment_context,
    reset_investment_context,
    investment_session,
    inv_stage_scope,
)

# ── models ────────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.models.investment_request import InvestmentRequest
from enterprise_ai_platform.investment.models.investment_context_model import InvestmentContext
from enterprise_ai_platform.investment.models.investment_analysis import InvestmentAnalysis
from enterprise_ai_platform.investment.models.investment_result import InvestmentResult
from enterprise_ai_platform.investment.models.investment_session import InvestmentSession
from enterprise_ai_platform.investment.models.investment_metadata import InvestmentMetadata
from enterprise_ai_platform.investment.models.investment_statistics import InvestmentStatistics
from enterprise_ai_platform.investment.models.investment_history import InvestmentHistory

# ── workflow ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.workflow.investment_workflow import InvestmentWorkflow, NoOpWorkflow
from enterprise_ai_platform.investment.workflow.workflow_executor import WorkflowExecutor

# ── registry ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_registry import (
    InvestmentRegistry,
    get_investment_registry,
    reset_investment_registry,
)

# ── manager ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_manager import (
    InvestmentManager,
    get_investment_manager,
    reset_investment_manager,
)

# ── services ──────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.services.investment_service import InvestmentService

# ── monitoring ────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.monitoring.investment_metrics import InvestmentMetrics
from enterprise_ai_platform.investment.monitoring.investment_monitor import InvestmentMonitor

# ── factory ───────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_factory import InvestmentFactory

# ── engine ────────────────────────────────────────────────────────────────────
from enterprise_ai_platform.investment.investment_engine import (
    InvestmentIntelligenceEngine,
    get_investment_engine,
    reset_investment_engine,
)

__version__ = INVESTMENT_ENGINE_VERSION

__all__ = [
    # constants
    "AnalysisStatus", "AssetClass", "IntelligenceType", "InvestmentObjective",
    "RiskProfile", "SessionStatus", "TimeHorizon", "WorkflowStatus",
    "INVESTMENT_ENGINE_VERSION", "INVESTMENT_ENGINE_SYSTEM_ID",
    # exceptions
    "InvestmentEngineError", "InvestmentError",
    "InvestmentNotFoundError", "InvestmentAlreadyExistsError", "InvestmentFailedError",
    "WorkflowError", "WorkflowNotFoundError", "WorkflowAlreadyExistsError",
    "WorkflowExecutionError", "WorkflowCancelledError",
    "RegistryError", "RegistryItemNotFoundError", "RegistryItemAlreadyExistsError",
    "RegistryOverflowError",
    "AnalysisError", "AnalysisFailedError", "AnalysisTimeoutError", "AnalysisInvalidError",
    "EngineLifecycleError", "EngineNotInitializedError", "EngineAlreadyRunningError",
    "SessionError", "SessionNotFoundError", "SessionExpiredError",
    "AssetClassError", "AssetClassNotSupportedError", "AssetClassInvalidError",
    "DomainEngineError", "DomainEngineNotFoundError", "DomainEngineAlreadyRegisteredError",
    "RequestValidationError",
    # context
    "InvestmentContextState", "get_investment_context", "reset_investment_context",
    "investment_session", "inv_stage_scope",
    # models
    "InvestmentRequest", "InvestmentContext", "InvestmentAnalysis",
    "InvestmentResult", "InvestmentSession", "InvestmentMetadata",
    "InvestmentStatistics", "InvestmentHistory",
    # workflow
    "InvestmentWorkflow", "NoOpWorkflow", "WorkflowExecutor",
    # registry
    "InvestmentRegistry", "get_investment_registry", "reset_investment_registry",
    # manager
    "InvestmentManager", "get_investment_manager", "reset_investment_manager",
    # services
    "InvestmentService",
    # monitoring
    "InvestmentMetrics", "InvestmentMonitor",
    # factory
    "InvestmentFactory",
    # engine
    "InvestmentIntelligenceEngine", "get_investment_engine", "reset_investment_engine",
]
