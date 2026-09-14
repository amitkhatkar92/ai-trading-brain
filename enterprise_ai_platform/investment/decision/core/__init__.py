"""enterprise_ai_platform/investment/decision/core/__init__.py
Public surface of the Institutional Decision Framework Core.
"""
from enterprise_ai_platform.investment.decision.core.decision_constants import (
    VALID_TRANSITIONS,
    ActionType,
    ApprovalStatus,
    ConfidenceLevel,
    DecisionEventType,
    DecisionFrameworkStatus,
    DecisionPriority,
    DecisionStatus,
    DecisionType,
    EnvironmentProfile,
    RecommendationType,
    RiskReviewStatus,
    DEFAULT_APPROVAL_THRESHOLD,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_RISK_THRESHOLD,
    DEFAULT_EVIDENCE_TIMEOUT_SECS,
    MAX_DECISION_AGE_SECS,
)
from enterprise_ai_platform.investment.decision.core.decision_types import (
    DecisionTypeDescriptor,
    DECISION_TYPE_DESCRIPTORS,
    get_descriptor,
)
from enterprise_ai_platform.investment.decision.core.recommendation_types import (
    RecommendationDescriptor,
    RECOMMENDATION_DESCRIPTORS,
    get_recommendation_descriptor,
)
from enterprise_ai_platform.investment.decision.core.action_types import (
    ActionDescriptor,
    ACTION_DESCRIPTORS,
    get_action_descriptor,
)
from enterprise_ai_platform.investment.decision.core.decision_context import (
    DecisionContext,
    make_context,
)
from enterprise_ai_platform.investment.decision.core.decision_metadata import (
    AuditEntry,
    DecisionMetadata,
)
from enterprise_ai_platform.investment.decision.core.decision_configuration import (
    DecisionConfiguration,
    DEVELOPMENT_CONFIG,
    PAPER_CONFIG,
    LIVE_CONFIG,
    BACKTEST_CONFIG,
)
from enterprise_ai_platform.investment.decision.core.decision_state import (
    DecisionState,
    InvalidTransitionError,
)
from enterprise_ai_platform.investment.decision.core.base_decision import BaseDecision
from enterprise_ai_platform.investment.decision.core.decision_events import (
    DecisionEvent,
    EventDispatcher,
    EventHistory,
    make_event,
)
from enterprise_ai_platform.investment.decision.core.decision_lifecycle import (
    DecisionLifecycle,
    PhaseRecord,
)
from enterprise_ai_platform.investment.decision.core.decision_session import DecisionSession
from enterprise_ai_platform.investment.decision.core.decision_history import (
    DecisionHistory,
    DecisionRecord,
)
from enterprise_ai_platform.investment.decision.core.decision_catalog import (
    CatalogEntry,
    DecisionCatalog,
)
from enterprise_ai_platform.investment.decision.core.decision_registry import (
    DecisionRegistry,
    DuplicateDecisionTypeError,
    UnknownDecisionTypeError,
)
from enterprise_ai_platform.investment.decision.core.decision_factory import DecisionFactory
from enterprise_ai_platform.investment.decision.core.decision_loader import DecisionLoader
from enterprise_ai_platform.investment.decision.core.parameter_validation import (
    ParameterRule,
    ParameterValidator,
    ValidationResult,
)
from enterprise_ai_platform.investment.decision.core.parameter_registry import (
    ParameterDescriptor,
    ParameterRegistry,
)
from enterprise_ai_platform.investment.decision.core.configuration_version import (
    ConfigSnapshot,
    ConfigurationVersion,
)
from enterprise_ai_platform.investment.decision.core.configuration_engine import ConfigurationEngine
from enterprise_ai_platform.investment.decision.core.decision_framework import DecisionFramework

__all__ = [
    # Constants
    "VALID_TRANSITIONS", "ActionType", "ApprovalStatus", "ConfidenceLevel",
    "DecisionEventType", "DecisionFrameworkStatus", "DecisionPriority",
    "DecisionStatus", "DecisionType", "EnvironmentProfile", "RecommendationType",
    "RiskReviewStatus",
    "DEFAULT_APPROVAL_THRESHOLD", "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_RISK_THRESHOLD", "DEFAULT_EVIDENCE_TIMEOUT_SECS", "MAX_DECISION_AGE_SECS",
    # Types
    "DecisionTypeDescriptor", "DECISION_TYPE_DESCRIPTORS", "get_descriptor",
    "RecommendationDescriptor", "RECOMMENDATION_DESCRIPTORS", "get_recommendation_descriptor",
    "ActionDescriptor", "ACTION_DESCRIPTORS", "get_action_descriptor",
    # Context / Metadata / Config / State
    "DecisionContext", "make_context",
    "AuditEntry", "DecisionMetadata",
    "DecisionConfiguration", "DEVELOPMENT_CONFIG", "PAPER_CONFIG", "LIVE_CONFIG", "BACKTEST_CONFIG",
    "DecisionState", "InvalidTransitionError",
    # Base
    "BaseDecision",
    # Events
    "DecisionEvent", "EventDispatcher", "EventHistory", "make_event",
    # Lifecycle
    "DecisionLifecycle", "PhaseRecord",
    "DecisionSession", "DecisionHistory", "DecisionRecord",
    # Registry
    "CatalogEntry", "DecisionCatalog",
    "DecisionRegistry", "DuplicateDecisionTypeError", "UnknownDecisionTypeError",
    "DecisionFactory", "DecisionLoader",
    # Configuration
    "ParameterRule", "ParameterValidator", "ValidationResult",
    "ParameterDescriptor", "ParameterRegistry",
    "ConfigSnapshot", "ConfigurationVersion",
    "ConfigurationEngine",
    # Framework
    "DecisionFramework",
]
