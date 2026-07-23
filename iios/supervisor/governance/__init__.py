"""
__init__.py — iios.supervisor.governance
-----------------------------------------
Public surface for the Autonomous Governance Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from .constants import (
    # System identifiers
    AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
    REASONING_SYSTEM_ID,
    COORDINATION_SYSTEM_ID,
    DETECTION_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    # Capacity defaults
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_ASSESSMENT_TIMEOUT_S,
    DEFAULT_MAX_ANOMALIES,
    DEFAULT_MAX_INCIDENTS,
    DEFAULT_MAX_RECOMMENDATIONS,
    # Health thresholds
    HEALTH_OPTIMAL_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    HEALTH_DEGRADED_THRESHOLD,
    HEALTH_CRITICAL_THRESHOLD,
    # Platform topology
    PLATFORM_DEPENDENCIES,
    DOMAIN_SNAPSHOT_KEY,
    ANOMALY_SEVERITY_ORDER,
    INCIDENT_SEVERITY_ORDER,
    # Enumerations
    SupervisionDomain,
    GovernanceCapability,
    AnomalySeverity,
    IncidentSeverity,
    RecommendationPriority,
    SubsystemStatus,
    EnterpriseState,
    GovernanceDecision,
    SelfHealingActionType,
    RootCauseCategory,
    DependencyType,
    ReasoningMode,
    SupervisionStrategyType,
    AutonomousGovernanceEventType,
    AutonomousGovernanceValidationCode,
)

from .exceptions import (
    AutonomousGovernanceError,
    AutonomousGovernanceEngineNotRunningError,
    AutonomousGovernanceSessionError,
    AutonomousGovernanceContextError,
    AutonomousGovernanceValidationError,
    AutonomousGovernanceAssessmentError,
    AutonomousGovernanceReasoningError,
    AutonomousGovernanceRegistryError,
    AutonomousGovernanceCapacityError,
    AutonomousGovernancePublicationError,
)

from .autonomous_governance_context import AutonomousGovernanceContext

from .autonomous_governance_request import AutonomousGovernanceRequest

from .autonomous_governance_response import (
    GovernanceAnomaly,
    AnomalyReport,
    GovernanceIncident,
    IncidentReport,
    RootCause,
    RootCauseReport,
    SubsystemDependency,
    DependencyReport,
    SubsystemHealth,
    PlatformHealthReport,
    GovernanceRecommendation,
    GovernanceRecommendations,
    SelfHealingActionItem,
    SelfHealingPlan,
    EnterpriseStateReport,
    EnterpriseGovernanceReport,
    AutonomousGovernanceSummary,
)

from .autonomous_governance_events import (
    AutonomousGovernanceEvent,
    make_governance_started_event,
    make_snapshots_collected_event,
    make_dependency_graph_built_event,
    make_anomaly_detected_event,
    make_incident_correlated_event,
    make_root_cause_identified_event,
    make_recommendations_generated_event,
    make_self_healing_generated_event,
    make_enterprise_assessment_completed_event,
    make_governance_published_event,
    make_governance_engine_started_event,
    make_governance_engine_stopped_event,
)

from .autonomous_governance_validator import (
    GovernanceValidationCheckResult,
    AutonomousGovernanceValidationResult,
    AutonomousGovernanceValidator,
)

from .autonomous_governance_statistics import AutonomousGovernanceStatistics
from .autonomous_governance_history import AutonomousGovernanceHistory
from .autonomous_governance_registry import AutonomousGovernanceRegistry
from .autonomous_governance_factory import AutonomousGovernanceFactory

from .platform_health_engine import PlatformHealthEngine
from .dependency_analysis_engine import DependencyAnalysisEngine
from .anomaly_detection_engine import AnomalyDetectionEngine
from .incident_analysis_engine import IncidentAnalysisEngine
from .root_cause_analysis_engine import RootCauseAnalysisEngine
from .enterprise_state_engine import EnterpriseStateEngine
from .governance_score_engine import GovernanceScoreEngine
from .self_healing_engine import SelfHealingEngine
from .recommendation_engine import RecommendationEngine
from .governance_decision_engine import GovernanceDecisionEngine
from .enterprise_reasoning_engine import EnterpriseReasoningEngine
from .supervision_strategy_engine import SupervisionStrategyEngine
from .subsystem_coordination_engine import SubsystemCoordinationEngine
from .agent_orchestration_engine import AgentOrchestrationEngine

from .autonomous_governance_manager import AutonomousGovernanceManager
from .autonomous_governance_engine import AutonomousGovernanceEngine


__all__ = [
    # --- system identifiers ---
    "AUTONOMOUS_GOVERNANCE_SYSTEM_ID",
    "REASONING_SYSTEM_ID",
    "COORDINATION_SYSTEM_ID",
    "DETECTION_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    # --- defaults ---
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_ASSESSMENT_TIMEOUT_S",
    "DEFAULT_MAX_ANOMALIES",
    "DEFAULT_MAX_INCIDENTS",
    "DEFAULT_MAX_RECOMMENDATIONS",
    # --- thresholds ---
    "HEALTH_OPTIMAL_THRESHOLD",
    "HEALTH_NORMAL_THRESHOLD",
    "HEALTH_DEGRADED_THRESHOLD",
    "HEALTH_CRITICAL_THRESHOLD",
    # --- topology ---
    "PLATFORM_DEPENDENCIES",
    "DOMAIN_SNAPSHOT_KEY",
    "ANOMALY_SEVERITY_ORDER",
    "INCIDENT_SEVERITY_ORDER",
    # --- enumerations ---
    "SupervisionDomain",
    "GovernanceCapability",
    "AnomalySeverity",
    "IncidentSeverity",
    "RecommendationPriority",
    "SubsystemStatus",
    "EnterpriseState",
    "GovernanceDecision",
    "SelfHealingActionType",
    "RootCauseCategory",
    "DependencyType",
    "ReasoningMode",
    "SupervisionStrategyType",
    "AutonomousGovernanceEventType",
    "AutonomousGovernanceValidationCode",
    # --- exceptions ---
    "AutonomousGovernanceError",
    "AutonomousGovernanceEngineNotRunningError",
    "AutonomousGovernanceSessionError",
    "AutonomousGovernanceContextError",
    "AutonomousGovernanceValidationError",
    "AutonomousGovernanceAssessmentError",
    "AutonomousGovernanceReasoningError",
    "AutonomousGovernanceRegistryError",
    "AutonomousGovernanceCapacityError",
    "AutonomousGovernancePublicationError",
    # --- context ---
    "AutonomousGovernanceContext",
    # --- request ---
    "AutonomousGovernanceRequest",
    # --- response types ---
    "GovernanceAnomaly",
    "AnomalyReport",
    "GovernanceIncident",
    "IncidentReport",
    "RootCause",
    "RootCauseReport",
    "SubsystemDependency",
    "DependencyReport",
    "SubsystemHealth",
    "PlatformHealthReport",
    "GovernanceRecommendation",
    "GovernanceRecommendations",
    "SelfHealingActionItem",
    "SelfHealingPlan",
    "EnterpriseStateReport",
    "EnterpriseGovernanceReport",
    "AutonomousGovernanceSummary",
    # --- events ---
    "AutonomousGovernanceEvent",
    "make_governance_started_event",
    "make_snapshots_collected_event",
    "make_dependency_graph_built_event",
    "make_anomaly_detected_event",
    "make_incident_correlated_event",
    "make_root_cause_identified_event",
    "make_recommendations_generated_event",
    "make_self_healing_generated_event",
    "make_enterprise_assessment_completed_event",
    "make_governance_published_event",
    "make_governance_engine_started_event",
    "make_governance_engine_stopped_event",
    # --- validation ---
    "GovernanceValidationCheckResult",
    "AutonomousGovernanceValidationResult",
    "AutonomousGovernanceValidator",
    # --- statistics ---
    "AutonomousGovernanceStatistics",
    # --- history ---
    "AutonomousGovernanceHistory",
    # --- registry ---
    "AutonomousGovernanceRegistry",
    # --- factory ---
    "AutonomousGovernanceFactory",
    # --- engines ---
    "PlatformHealthEngine",
    "DependencyAnalysisEngine",
    "AnomalyDetectionEngine",
    "IncidentAnalysisEngine",
    "RootCauseAnalysisEngine",
    "EnterpriseStateEngine",
    "GovernanceScoreEngine",
    "SelfHealingEngine",
    "RecommendationEngine",
    "GovernanceDecisionEngine",
    "EnterpriseReasoningEngine",
    "SupervisionStrategyEngine",
    "SubsystemCoordinationEngine",
    "AgentOrchestrationEngine",
    # --- orchestration ---
    "AutonomousGovernanceManager",
    # --- engine ---
    "AutonomousGovernanceEngine",
]
