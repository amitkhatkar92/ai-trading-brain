"""
ai_governance_policy_audit.py — iios.supervisor.policies
----------------------------------------------------------
Audit trail generation for the AI Governance Policy Framework.

Exports
-------
GovernanceAuditEntry       — single per-policy audit record
GovernanceAuditReport      — complete evaluation audit report
AIGovernancePolicyAuditGenerator — generates reports from evaluation artefacts

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    AIGovernancePolicyAction,
    AIGovernancePolicyType,
    STOP_ACTIONS,
    HUMAN_REVIEW_ACTIONS,
    PolicyPriority,
)
from .ai_governance_policy_request import AIGovernancePolicyRequest
from .ai_governance_policy_result import AIGovernancePolicyResult
from .ai_governance_policy_response import AIGovernancePolicyResponse


# ---------------------------------------------------------------------------
# GovernanceAuditEntry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceAuditEntry:
    """
    Immutable audit record for a single policy evaluation outcome.

    Fields
    ------
    entry_id :            Unique identifier.
    supervision_id :      Parent supervision run identifier.
    policy_id :           Evaluated policy identifier.
    policy_name :         Human-readable policy name.
    policy_type :         Governance domain.
    priority :            Policy enforcement priority.
    action :              Governance action prescribed.
    rationale :           Human-readable explanation.
    triggered_rule_id :   Rule that fired (empty = default action).
    conditions_met :      Condition IDs that evaluated True.
    conditions_failed :   Condition IDs that evaluated False.
    evaluation_elapsed_s: Per-policy evaluation duration.
    recorded_at :         Wall-clock record creation time.
    framework_version :   Framework version string.
    """
    entry_id:             str
    supervision_id:       str
    policy_id:            str
    policy_name:          str
    policy_type:          AIGovernancePolicyType
    priority:             PolicyPriority
    action:               AIGovernancePolicyAction
    rationale:            str
    triggered_rule_id:    str             = ""
    conditions_met:       Tuple[str, ...] = field(default_factory=tuple)
    conditions_failed:    Tuple[str, ...] = field(default_factory=tuple)
    evaluation_elapsed_s: float           = 0.0
    recorded_at:          float           = field(default_factory=time.time)
    framework_version:    str             = VERSION

    @classmethod
    def from_result(
        cls,
        result:        AIGovernancePolicyResult,
        supervision_id: str = "",
    ) -> "GovernanceAuditEntry":
        return cls(
            entry_id             = str(uuid.uuid4()),
            supervision_id       = supervision_id,
            policy_id            = result.policy_id,
            policy_name          = result.policy_name,
            policy_type          = result.policy_type,
            priority             = result.priority,
            action               = result.action,
            rationale            = result.rationale,
            triggered_rule_id    = result.triggered_rule_id,
            conditions_met       = result.conditions_met,
            conditions_failed    = result.conditions_failed,
            evaluation_elapsed_s = result.evaluation_elapsed_s,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":             self.entry_id,
            "supervision_id":       self.supervision_id,
            "policy_id":            self.policy_id,
            "policy_name":          self.policy_name,
            "policy_type":          self.policy_type.value,
            "priority":             self.priority.value,
            "action":               self.action.value,
            "rationale":            self.rationale,
            "triggered_rule_id":    self.triggered_rule_id,
            "conditions_met":       list(self.conditions_met),
            "conditions_failed":    list(self.conditions_failed),
            "evaluation_elapsed_s": self.evaluation_elapsed_s,
            "recorded_at":          self.recorded_at,
            "framework_version":    self.framework_version,
        }


# ---------------------------------------------------------------------------
# GovernanceAuditReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceAuditReport:
    """
    Complete immutable audit report for a single governance evaluation.

    Fields
    ------
    report_id :                   Unique identifier.
    request_id :                  Original evaluation request identifier.
    supervision_id :              Supervision run identifier.
    subsystem_id :                Requesting subsystem.
    workflow_type :               Workflow being governed.
    final_action :                Resolved governance outcome.
    entries :                     Per-policy audit entries.
    total_policies_evaluated :    Policies that ran.
    total_policies_loaded :       Policies loaded before type filtering.
    approved_count :              Count of APPROVE outcomes.
    rejected_count :              Count of REJECT outcomes.
    blocked_count :               Count of BLOCK outcomes.
    emergency_stop_triggered :    True when any result is an emergency stop.
    human_approval_requested :    True when any result requires human review.
    conflict_resolution_applied : True when conflict resolution was needed.
    dominant_policy_id :          Policy determining the final action.
    dominant_policy_name :        Human-readable dominant policy name.
    evaluation_elapsed_s :        Total evaluation duration in seconds.
    is_success :                  True when evaluation completed without error.
    error_message :               Non-empty when evaluation failed.
    generated_at :                Wall-clock report generation time.
    framework_version :           Framework version string.
    """
    report_id:                   str
    request_id:                  str
    supervision_id:              str
    subsystem_id:                str
    workflow_type:               str
    final_action:                AIGovernancePolicyAction
    entries:                     Tuple[GovernanceAuditEntry, ...]
    total_policies_evaluated:    int
    total_policies_loaded:       int
    approved_count:              int
    rejected_count:              int
    blocked_count:               int
    emergency_stop_triggered:    bool
    human_approval_requested:    bool
    conflict_resolution_applied: bool
    dominant_policy_id:          str
    dominant_policy_name:        str
    evaluation_elapsed_s:        float
    is_success:                  bool
    error_message:               str   = ""
    generated_at:                float = field(default_factory=time.time)
    framework_version:           str   = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":                   self.report_id,
            "request_id":                  self.request_id,
            "supervision_id":              self.supervision_id,
            "subsystem_id":                self.subsystem_id,
            "workflow_type":               self.workflow_type,
            "final_action":                self.final_action.value,
            "total_policies_evaluated":    self.total_policies_evaluated,
            "total_policies_loaded":       self.total_policies_loaded,
            "approved_count":              self.approved_count,
            "rejected_count":              self.rejected_count,
            "blocked_count":               self.blocked_count,
            "emergency_stop_triggered":    self.emergency_stop_triggered,
            "human_approval_requested":    self.human_approval_requested,
            "conflict_resolution_applied": self.conflict_resolution_applied,
            "dominant_policy_id":          self.dominant_policy_id,
            "dominant_policy_name":        self.dominant_policy_name,
            "evaluation_elapsed_s":        self.evaluation_elapsed_s,
            "is_success":                  self.is_success,
            "error_message":               self.error_message,
            "generated_at":                self.generated_at,
            "framework_version":           self.framework_version,
            "entry_count":                 len(self.entries),
        }


# ---------------------------------------------------------------------------
# AIGovernancePolicyAuditGenerator
# ---------------------------------------------------------------------------

class AIGovernancePolicyAuditGenerator:
    """
    Generates :class:`GovernanceAuditReport` objects from evaluation artefacts.
    """

    def generate(
        self,
        request:              AIGovernancePolicyRequest,
        results:              List[AIGovernancePolicyResult],
        response:             AIGovernancePolicyResponse,
        *,
        total_policies_loaded: int = 0,
        dominant_policy_id:    str = "",
        dominant_policy_name:  str = "",
        conflict_resolution_applied: bool = False,
    ) -> GovernanceAuditReport:
        entries = tuple(
            GovernanceAuditEntry.from_result(r, request.supervision_id)
            for r in results
        )
        approved_count = sum(1 for r in results if r.is_permissive)
        rejected_count = sum(
            1 for r in results
            if r.action == AIGovernancePolicyAction.REJECT
        )
        blocked_count = sum(
            1 for r in results
            if r.action == AIGovernancePolicyAction.BLOCK
        )
        emergency_stop = any(r.is_emergency_stop for r in results)
        human_approval = any(r.requires_human_approval for r in results)

        return GovernanceAuditReport(
            report_id                   = str(uuid.uuid4()),
            request_id                  = request.request_id,
            supervision_id              = request.supervision_id,
            subsystem_id                = request.subsystem_id,
            workflow_type               = request.workflow_type,
            final_action                = response.final_action,
            entries                     = entries,
            total_policies_evaluated    = len(results),
            total_policies_loaded       = total_policies_loaded or len(results),
            approved_count              = approved_count,
            rejected_count              = rejected_count,
            blocked_count               = blocked_count,
            emergency_stop_triggered    = emergency_stop,
            human_approval_requested    = human_approval,
            conflict_resolution_applied = conflict_resolution_applied,
            dominant_policy_id          = dominant_policy_id,
            dominant_policy_name        = dominant_policy_name,
            evaluation_elapsed_s        = response.evaluation_elapsed_s,
            is_success                  = response.is_success,
            error_message               = response.error_message,
        )
