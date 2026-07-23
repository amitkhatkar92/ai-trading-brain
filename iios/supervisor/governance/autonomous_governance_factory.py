"""
autonomous_governance_factory.py — iios.supervisor.governance
--------------------------------------------------------------
Factory for creating governance objects and common test scenarios.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    AnomalySeverity,
    GovernanceDecision,
    IncidentSeverity,
    RecommendationPriority,
    RootCauseCategory,
    SelfHealingActionType,
    SupervisionDomain,
)
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_request import AutonomousGovernanceRequest
from .autonomous_governance_response import (
    AnomalyReport,
    AutonomousGovernanceSummary,
    DependencyReport,
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
    GovernanceAnomaly,
    GovernanceIncident,
    GovernanceRecommendation,
    GovernanceRecommendations,
    IncidentReport,
    PlatformHealthReport,
    RootCause,
    RootCauseReport,
    SelfHealingActionItem,
    SelfHealingPlan,
    SubsystemHealth,
)
from .constants import EnterpriseState, SubsystemStatus


class AutonomousGovernanceFactory:
    """
    Factory for constructing governance value objects.

    Provides both low-level builders and high-level domain convenience
    methods for common governance scenarios.
    """

    # ------------------------------------------------------------------
    # Core builders
    # ------------------------------------------------------------------

    def create_context(
        self,
        supervision_id: str,
        subsystem_id:   str = "",
        **snapshot_kwargs,
    ) -> AutonomousGovernanceContext:
        return AutonomousGovernanceContext.create(supervision_id, subsystem_id, **snapshot_kwargs)

    def create_request(
        self,
        supervision_id: str,
        subsystem_id:   str = "",
        workflow_type:  str = "enterprise_health_review",
        *,
        domains:  Optional[List[SupervisionDomain]] = None,
        inputs:   Optional[Dict[str, Any]]           = None,
        metadata: Optional[Dict[str, Any]]           = None,
    ) -> AutonomousGovernanceRequest:
        return AutonomousGovernanceRequest.create(
            supervision_id = supervision_id,
            subsystem_id   = subsystem_id,
            workflow_type  = workflow_type,
            domains        = domains,
            inputs         = inputs,
            metadata       = metadata,
        )

    def create_anomaly(
        self,
        subsystem_id:   str,
        field_path:     str,
        observed_value: Any,
        severity:       AnomalySeverity = AnomalySeverity.MEDIUM,
        *,
        description: str = "",
    ) -> GovernanceAnomaly:
        return GovernanceAnomaly.create(
            subsystem_id   = subsystem_id,
            field_path     = field_path,
            observed_value = observed_value,
            severity       = severity,
            description    = description,
        )

    def create_recommendation(
        self,
        subsystem_id: str,
        title:        str,
        priority:     RecommendationPriority = RecommendationPriority.MEDIUM,
        *,
        description:     str = "",
        action:          str = "",
        expected_impact: str = "",
    ) -> GovernanceRecommendation:
        return GovernanceRecommendation.create(
            subsystem_id    = subsystem_id,
            title           = title,
            priority        = priority,
            description     = description,
            action          = action,
            expected_impact = expected_impact,
        )

    # ------------------------------------------------------------------
    # Domain convenience methods
    # ------------------------------------------------------------------

    def create_healthy_platform_request(
        self,
        supervision_id: str = "",
    ) -> AutonomousGovernanceRequest:
        """Create a request representing a fully healthy platform."""
        sid = supervision_id or str(uuid.uuid4())
        inputs = {
            "platform_health":              {"overall": 0.95, "score": 0.95},
            "risk_snapshot":                {"var": 0.02, "health_score": 0.95},
            "market_snapshot":              {"status": "active", "health_score": 0.95},
            "execution_snapshot":           {"fill_rate": 0.98, "health_score": 0.95},
            "execution_recovery_snapshot":  {"health_score": 0.95},
            "execution_analytics_snapshot": {"health_score": 0.95},
            "decision_snapshot":            {"health_score": 0.95},
            "portfolio_snapshot":           {"health_score": 0.95},
            "infrastructure_metrics":       {"cpu_usage": 0.30, "memory_usage": 0.40},
            "supervisor_snapshot":          {"health_score": 0.95},
            "governance_policy_response":   {"final_action": "approve"},
        }
        return self.create_request(sid, inputs=inputs)

    def create_emergency_request(
        self,
        supervision_id: str = "",
    ) -> AutonomousGovernanceRequest:
        """Create a request representing an emergency platform state."""
        sid = supervision_id or str(uuid.uuid4())
        inputs = {
            "platform_health": {"overall": 0.15, "score": 0.15},
            "risk_snapshot":   {"var": 0.95, "health_score": 0.10},
            "market_snapshot": {"status": "halt", "health_score": 0.0},
            "execution_snapshot": {"fill_rate": 0.05, "health_score": 0.10},
            "governance_policy_response": {"final_action": "emergency_stop"},
        }
        return self.create_request(sid, inputs=inputs)

    def create_degraded_request(
        self,
        supervision_id: str = "",
    ) -> AutonomousGovernanceRequest:
        """Create a request representing a degraded platform state."""
        sid = supervision_id or str(uuid.uuid4())
        inputs = {
            "platform_health": {"overall": 0.60, "score": 0.60},
            "risk_snapshot":   {"var": 0.70, "health_score": 0.55},
            "market_snapshot": {"status": "active", "stress_score": 0.85},
            "governance_policy_response": {"final_action": "approve_with_conditions"},
        }
        return self.create_request(sid, inputs=inputs)

    def create_compliance_request(
        self,
        supervision_id: str = "",
    ) -> AutonomousGovernanceRequest:
        """Create a request where governance policy requires escalation."""
        sid = supervision_id or str(uuid.uuid4())
        inputs = {
            "platform_health": {"overall": 0.75},
            "governance_policy_response": {"final_action": "require_human_approval"},
        }
        return self.create_request(sid, inputs=inputs)
