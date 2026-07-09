"""iios/investment/__init__.py — Investment Intelligence Engine Core"""
from __future__ import annotations

# ── constants ─────────────────────────────────────────────────────────────────
from iios.investment.investment_constants import (
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
from iios.investment.investment_exceptions import (
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
from iios.investment.investment_context import (
    InvestmentContextState,
    get_investment_context,
    reset_investment_context,
    investment_session,
    inv_stage_scope,
)

# ── models ────────────────────────────────────────────────────────────────────
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_result import InvestmentResult
from iios.investment.models.investment_session import InvestmentSession
from iios.investment.models.investment_metadata import InvestmentMetadata
from iios.investment.models.investment_statistics import InvestmentStatistics
from iios.investment.models.investment_history import InvestmentHistory

# ── workflow ──────────────────────────────────────────────────────────────────
from iios.investment.workflow.investment_workflow import InvestmentWorkflow, NoOpWorkflow
from iios.investment.workflow.workflow_executor import WorkflowExecutor

# ── registry ──────────────────────────────────────────────────────────────────
from iios.investment.investment_registry import (
    InvestmentRegistry,
    get_investment_registry,
    reset_investment_registry,
)

# ── manager ───────────────────────────────────────────────────────────────────
from iios.investment.investment_manager import (
    InvestmentManager,
    get_investment_manager,
    reset_investment_manager,
)

# ── services ──────────────────────────────────────────────────────────────────
from iios.investment.services.investment_service import InvestmentService

# ── monitoring ────────────────────────────────────────────────────────────────
from iios.investment.monitoring.investment_metrics import InvestmentMetrics
from iios.investment.monitoring.investment_monitor import InvestmentMonitor

# ── factory ───────────────────────────────────────────────────────────────────
from iios.investment.investment_factory import InvestmentFactory

# ── engine ────────────────────────────────────────────────────────────────────
from iios.investment.investment_engine import (
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
