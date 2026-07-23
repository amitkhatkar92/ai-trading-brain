"""
constants.py — iios.supervisor.governance
------------------------------------------
Shared enumerations, constants, and lookup tables for the
Autonomous Governance Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet, List

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------

AUTONOMOUS_GOVERNANCE_SYSTEM_ID:   str = "iios:supervisor:autonomous_governance"
REASONING_SYSTEM_ID:               str = "iios:supervisor:autonomous_governance:reasoning"
COORDINATION_SYSTEM_ID:            str = "iios:supervisor:autonomous_governance:coordination"
DETECTION_SYSTEM_ID:               str = "iios:supervisor:autonomous_governance:detection"
MANAGER_SYSTEM_ID:                 str = "iios:supervisor:autonomous_governance:manager"
REGISTRY_SYSTEM_ID:                str = "iios:supervisor:autonomous_governance:registry"
FACTORY_SYSTEM_ID:                 str = "iios:supervisor:autonomous_governance:factory"

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

ACTOR_GOVERNANCE_ENGINE: str = "autonomous_governance_engine"
ACTOR_MANAGER:           str = "autonomous_governance_manager"
ACTOR_REASONING:         str = "enterprise_reasoning"
ACTOR_DETECTION:         str = "anomaly_detection"
ACTOR_OPERATOR:          str = "operator"
ACTOR_SYSTEM:            str = "system"
ACTOR_ENTERPRISE:        str = "enterprise"

# ---------------------------------------------------------------------------
# Capacity defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_SESSIONS:        int   = 10_000
DEFAULT_MAX_HISTORY:         int   = 1_000
DEFAULT_ASSESSMENT_TIMEOUT_S: float = 60.0
DEFAULT_MAX_ANOMALIES:       int   = 500
DEFAULT_MAX_INCIDENTS:       int   = 200
DEFAULT_MAX_RECOMMENDATIONS: int   = 100

# ---------------------------------------------------------------------------
# Health score thresholds
# ---------------------------------------------------------------------------

HEALTH_OPTIMAL_THRESHOLD:   float = 0.90
HEALTH_NORMAL_THRESHOLD:    float = 0.70
HEALTH_DEGRADED_THRESHOLD:  float = 0.50
HEALTH_CRITICAL_THRESHOLD:  float = 0.30

# ---------------------------------------------------------------------------
# Anomaly detection thresholds
# ---------------------------------------------------------------------------

ANOMALY_RISK_HIGH:          float = 0.80
ANOMALY_RISK_MEDIUM:        float = 0.60
ANOMALY_MISSING_SNAPSHOT_SCORE: float = 0.70

# ---------------------------------------------------------------------------
# Governance scoring
# ---------------------------------------------------------------------------

GOVERNANCE_COMPLIANCE_PASS:  float = 0.80
GOVERNANCE_STABILITY_PASS:   float = 0.70

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SupervisionDomain(str, Enum):
    """Platform subsystem domains that autonomous governance supervises."""
    EXECUTION_INTELLIGENCE  = "execution_intelligence"
    EXECUTION_RECOVERY      = "execution_recovery"
    EXECUTION_ANALYTICS     = "execution_analytics"
    DECISION_INTELLIGENCE   = "decision_intelligence"
    PORTFOLIO_INTELLIGENCE  = "portfolio_intelligence"
    RISK_INTELLIGENCE       = "risk_intelligence"
    MARKET_INTELLIGENCE     = "market_intelligence"
    PLATFORM_INFRASTRUCTURE = "platform_infrastructure"
    ENTERPRISE              = "enterprise"


class GovernanceCapability(str, Enum):
    """Capabilities provided by the autonomous governance framework."""
    ENTERPRISE_REASONING        = "enterprise_reasoning"
    CROSS_SUBSYSTEM_COORDINATION = "cross_subsystem_coordination"
    DEPENDENCY_ANALYSIS         = "dependency_analysis"
    PLATFORM_HEALTH_ASSESSMENT  = "platform_health_assessment"
    ANOMALY_DETECTION           = "anomaly_detection"
    ROOT_CAUSE_ANALYSIS         = "root_cause_analysis"
    INCIDENT_CORRELATION        = "incident_correlation"
    OPERATIONAL_INTELLIGENCE    = "operational_intelligence"
    SELF_HEALING_RECOMMENDATIONS = "self_healing_recommendations"
    GOVERNANCE_RECOMMENDATIONS  = "governance_recommendations"
    ENTERPRISE_STATE_ASSESSMENT = "enterprise_state_assessment"
    AUTONOMOUS_SUPERVISION      = "autonomous_supervision"


class AnomalySeverity(str, Enum):
    """Severity classification for detected anomalies."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class IncidentSeverity(str, Enum):
    """Severity classification for correlated incidents."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class RecommendationPriority(IntEnum):
    """Governance recommendation priority — lower = more urgent."""
    CRITICAL      = 1
    HIGH          = 2
    MEDIUM        = 3
    LOW           = 4
    INFORMATIONAL = 5


class SubsystemStatus(str, Enum):
    """Operational status of a supervised subsystem."""
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    IMPAIRED = "impaired"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


class EnterpriseState(str, Enum):
    """Overall enterprise operational state."""
    OPTIMAL   = "optimal"
    NORMAL    = "normal"
    DEGRADED  = "degraded"
    CRITICAL  = "critical"
    EMERGENCY = "emergency"
    UNKNOWN   = "unknown"


class GovernanceDecision(str, Enum):
    """Autonomous governance decision for the current supervision cycle."""
    CONTINUE    = "continue"
    DEFER       = "defer"
    ESCALATE    = "escalate"
    HALT        = "halt"
    INVESTIGATE = "investigate"


class SelfHealingActionType(str, Enum):
    """Type of self-healing action that can be recommended."""
    RESTART              = "restart"
    THROTTLE             = "throttle"
    ISOLATE              = "isolate"
    FAILOVER             = "failover"
    ALERT                = "alert"
    MONITOR              = "monitor"
    SCALE                = "scale"
    REBALANCE            = "rebalance"
    DEGRADE_GRACEFULLY   = "degrade_gracefully"
    NO_ACTION            = "no_action"


class RootCauseCategory(str, Enum):
    """Category of root cause for an identified incident."""
    INFRASTRUCTURE = "infrastructure"
    SOFTWARE       = "software"
    CONFIGURATION  = "configuration"
    DATA           = "data"
    EXTERNAL       = "external"
    HUMAN          = "human"
    UNKNOWN        = "unknown"


class DependencyType(str, Enum):
    """Strength / criticality of a subsystem dependency."""
    HARD       = "hard"
    SOFT       = "soft"
    OPTIONAL   = "optional"
    MONITORING = "monitoring"


class ReasoningMode(str, Enum):
    """Enterprise reasoning mode."""
    ANALYTICAL   = "analytical"
    HEURISTIC    = "heuristic"
    PROBABILISTIC = "probabilistic"
    RULE_BASED   = "rule_based"
    COMPOSITE    = "composite"


class SupervisionStrategyType(str, Enum):
    """Supervision intensity strategy."""
    INTENSIVE = "intensive"
    ELEVATED  = "elevated"
    STANDARD  = "standard"
    REDUCED   = "reduced"
    EMERGENCY = "emergency"


class AutonomousGovernanceEventType(str, Enum):
    """Events fired by the autonomous governance framework."""
    GOVERNANCE_STARTED             = "governance_started"
    SNAPSHOTS_COLLECTED            = "snapshots_collected"
    DEPENDENCY_GRAPH_BUILT         = "dependency_graph_built"
    ANOMALY_DETECTED               = "anomaly_detected"
    INCIDENT_CORRELATED            = "incident_correlated"
    ROOT_CAUSE_IDENTIFIED          = "root_cause_identified"
    RECOMMENDATIONS_GENERATED      = "recommendations_generated"
    SELF_HEALING_GENERATED         = "self_healing_generated"
    ENTERPRISE_ASSESSMENT_COMPLETED = "enterprise_assessment_completed"
    GOVERNANCE_PUBLISHED           = "governance_published"
    GOVERNANCE_ENGINE_STARTED      = "governance_engine_started"
    GOVERNANCE_ENGINE_STOPPED      = "governance_engine_stopped"


class AutonomousGovernanceValidationCode(str, Enum):
    """Validation check codes for autonomous governance."""
    REQUEST_COMPLETENESS    = "request_completeness"
    CONTEXT_CONSISTENCY     = "context_consistency"
    SNAPSHOT_CONSISTENCY    = "snapshot_consistency"
    DEPENDENCY_CONSISTENCY  = "dependency_consistency"
    REASONING_INTEGRITY     = "reasoning_integrity"
    OUTPUT_COMPLETENESS     = "output_completeness"

# ---------------------------------------------------------------------------
# Static subsystem dependency graph
# ---------------------------------------------------------------------------

# Maps each domain to the list of domains it depends on (hard dependencies).
PLATFORM_DEPENDENCIES: Dict[str, List[str]] = {
    SupervisionDomain.EXECUTION_INTELLIGENCE.value:  [
        SupervisionDomain.DECISION_INTELLIGENCE.value,
        SupervisionDomain.PORTFOLIO_INTELLIGENCE.value,
        SupervisionDomain.RISK_INTELLIGENCE.value,
    ],
    SupervisionDomain.EXECUTION_RECOVERY.value: [
        SupervisionDomain.EXECUTION_INTELLIGENCE.value,
    ],
    SupervisionDomain.EXECUTION_ANALYTICS.value: [
        SupervisionDomain.EXECUTION_INTELLIGENCE.value,
        SupervisionDomain.EXECUTION_RECOVERY.value,
    ],
    SupervisionDomain.DECISION_INTELLIGENCE.value: [
        SupervisionDomain.MARKET_INTELLIGENCE.value,
        SupervisionDomain.RISK_INTELLIGENCE.value,
    ],
    SupervisionDomain.PORTFOLIO_INTELLIGENCE.value: [
        SupervisionDomain.RISK_INTELLIGENCE.value,
        SupervisionDomain.MARKET_INTELLIGENCE.value,
    ],
    SupervisionDomain.RISK_INTELLIGENCE.value: [
        SupervisionDomain.MARKET_INTELLIGENCE.value,
    ],
    SupervisionDomain.MARKET_INTELLIGENCE.value: [
        SupervisionDomain.PLATFORM_INFRASTRUCTURE.value,
    ],
    SupervisionDomain.PLATFORM_INFRASTRUCTURE.value: [],
    SupervisionDomain.ENTERPRISE.value: [
        SupervisionDomain.EXECUTION_INTELLIGENCE.value,
        SupervisionDomain.DECISION_INTELLIGENCE.value,
        SupervisionDomain.PORTFOLIO_INTELLIGENCE.value,
        SupervisionDomain.RISK_INTELLIGENCE.value,
        SupervisionDomain.MARKET_INTELLIGENCE.value,
    ],
}

# Maps supervision domain to its canonical snapshot key in the context inputs.
DOMAIN_SNAPSHOT_KEY: Dict[str, str] = {
    SupervisionDomain.EXECUTION_INTELLIGENCE.value:  "execution_snapshot",
    SupervisionDomain.EXECUTION_RECOVERY.value:      "execution_recovery_snapshot",
    SupervisionDomain.EXECUTION_ANALYTICS.value:     "execution_analytics_snapshot",
    SupervisionDomain.DECISION_INTELLIGENCE.value:   "decision_snapshot",
    SupervisionDomain.PORTFOLIO_INTELLIGENCE.value:  "portfolio_snapshot",
    SupervisionDomain.RISK_INTELLIGENCE.value:       "risk_snapshot",
    SupervisionDomain.MARKET_INTELLIGENCE.value:     "market_snapshot",
    SupervisionDomain.PLATFORM_INFRASTRUCTURE.value: "infrastructure_metrics",
    SupervisionDomain.ENTERPRISE.value:              "supervisor_snapshot",
}

# Severity ordering for conflict resolution (higher = more severe).
ANOMALY_SEVERITY_ORDER: Dict[str, int] = {
    AnomalySeverity.INFO.value:     0,
    AnomalySeverity.LOW.value:      1,
    AnomalySeverity.MEDIUM.value:   2,
    AnomalySeverity.HIGH.value:     3,
    AnomalySeverity.CRITICAL.value: 4,
}

INCIDENT_SEVERITY_ORDER: Dict[str, int] = {
    IncidentSeverity.INFO.value:     0,
    IncidentSeverity.LOW.value:      1,
    IncidentSeverity.MEDIUM.value:   2,
    IncidentSeverity.HIGH.value:     3,
    IncidentSeverity.CRITICAL.value: 4,
}
