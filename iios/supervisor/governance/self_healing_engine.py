"""
self_healing_engine.py — iios.supervisor.governance
----------------------------------------------------
Self-healing plan generation engine.

Maps root causes to concrete self-healing actions.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .constants import (
    RecommendationPriority,
    RootCauseCategory,
    SelfHealingActionType,
)
from .autonomous_governance_response import (
    IncidentReport,
    RootCause,
    RootCauseReport,
    SelfHealingActionItem,
    SelfHealingPlan,
)

# Maps root cause category to the most appropriate self-healing action.
_RC_TO_ACTION = {
    RootCauseCategory.INFRASTRUCTURE: SelfHealingActionType.RESTART,
    RootCauseCategory.SOFTWARE:       SelfHealingActionType.RESTART,
    RootCauseCategory.CONFIGURATION:  SelfHealingActionType.ALERT,
    RootCauseCategory.DATA:           SelfHealingActionType.REBALANCE,
    RootCauseCategory.EXTERNAL:       SelfHealingActionType.MONITOR,
    RootCauseCategory.HUMAN:          SelfHealingActionType.ALERT,
    RootCauseCategory.UNKNOWN:        SelfHealingActionType.MONITOR,
}


class SelfHealingEngine:
    """
    Stateless self-healing plan generation engine.

    One SelfHealingActionItem is generated per incident root cause.
    """

    def plan(
        self,
        incident_report:   IncidentReport,
        root_cause_report: RootCauseReport,
    ) -> SelfHealingPlan:
        """
        Generate a self-healing plan for all incidents.

        Parameters
        ----------
        incident_report : IncidentReport
        root_cause_report : RootCauseReport

        Returns
        -------
        SelfHealingPlan
        """
        actions: List[SelfHealingActionItem] = []
        rc_by_incident = {r.incident_id: r for r in root_cause_report.root_causes}

        for incident in incident_report.incidents:
            root_cause = rc_by_incident.get(incident.incident_id)
            if not root_cause:
                continue
            action = self._build_action(incident.affected_subsystems, root_cause)
            actions.append(action)

        # Sort by priority (CRITICAL first).
        actions.sort(key=lambda a: a.priority.value)
        return SelfHealingPlan.create(tuple(actions))

    # ------------------------------------------------------------------

    def _build_action(
        self,
        affected_subsystems: tuple,
        root_cause:          RootCause,
    ) -> SelfHealingActionItem:
        action_type = _RC_TO_ACTION.get(root_cause.category, SelfHealingActionType.MONITOR)
        priority    = self._priority(root_cause)
        subsystem   = affected_subsystems[0] if affected_subsystems else "platform"

        is_automated      = action_type in (
            SelfHealingActionType.MONITOR,
            SelfHealingActionType.ALERT,
        )
        requires_approval = not is_automated

        description = (
            f"[{action_type.value.upper()}] {root_cause.description}"
            f" (confidence={root_cause.confidence:.0%})"
        )
        expected_outcome = self._expected_outcome(action_type)

        return SelfHealingActionItem.create(
            subsystem_id      = subsystem,
            action_type       = action_type,
            priority          = priority,
            description       = description,
            expected_outcome  = expected_outcome,
            is_automated      = is_automated,
            requires_approval = requires_approval,
        )

    @staticmethod
    def _priority(root_cause: RootCause) -> RecommendationPriority:
        if root_cause.confidence >= 0.8:
            return RecommendationPriority.HIGH
        if root_cause.confidence >= 0.5:
            return RecommendationPriority.MEDIUM
        return RecommendationPriority.LOW

    @staticmethod
    def _expected_outcome(action_type: SelfHealingActionType) -> str:
        outcomes = {
            SelfHealingActionType.RESTART:            "Subsystem restores normal operation",
            SelfHealingActionType.THROTTLE:           "Load reduced to safe levels",
            SelfHealingActionType.ISOLATE:            "Faulty subsystem isolated from platform",
            SelfHealingActionType.FAILOVER:           "Failover to standby completes successfully",
            SelfHealingActionType.ALERT:              "Operations team alerted for manual investigation",
            SelfHealingActionType.MONITOR:            "Anomaly monitored; no immediate action required",
            SelfHealingActionType.SCALE:              "Additional resources allocated",
            SelfHealingActionType.REBALANCE:          "Data or load rebalanced across subsystems",
            SelfHealingActionType.DEGRADE_GRACEFULLY: "Non-critical functions suspended gracefully",
            SelfHealingActionType.NO_ACTION:          "No action required",
        }
        return outcomes.get(action_type, "Outcome unknown")
