"""
decision_policy_audit.py — iios.decision.policies
===================================================
Audit trail for policy evaluations.

  PolicyAuditEntry    — record for a single evaluated policy
  PolicyAuditReport   — full audit of one evaluation request
  build_audit_report  — factory function

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Tuple

from .constants import VERSION, PolicyAction
from .decision_policy_result import SinglePolicyResult


@dataclass(frozen=True)
class PolicyAuditEntry:
    """
    Immutable audit record for a single evaluated policy.

    Parameters
    ----------
    entry_id :         Unique entry identifier.
    policy_id :        ID of the evaluated policy.
    policy_name :      Human-readable policy name.
    action :           Action the policy produced.
    reason :           Rationale for the action.
    rules_evaluated :  Total number of rules evaluated.
    rules_triggered :  Number of rules that triggered.
    evaluation_time_s: Wall-clock time taken.
    recorded_at :      When this entry was recorded.
    """

    entry_id:          str
    policy_id:         str
    policy_name:       str
    action:            PolicyAction
    reason:            str
    rules_evaluated:   int
    rules_triggered:   int
    evaluation_time_s: float
    recorded_at:       datetime

    def to_dict(self) -> dict:
        return {
            "entry_id":          self.entry_id,
            "policy_id":         self.policy_id,
            "policy_name":       self.policy_name,
            "action":            self.action.value,
            "reason":            self.reason,
            "rules_evaluated":   self.rules_evaluated,
            "rules_triggered":   self.rules_triggered,
            "evaluation_time_s": self.evaluation_time_s,
            "recorded_at":       self.recorded_at.isoformat(),
        }


@dataclass(frozen=True)
class PolicyAuditReport:
    """
    Full audit report for one policy evaluation request.

    Parameters
    ----------
    report_id :                    Unique report identifier.
    request_id :                   ID of the originating evaluation request.
    decision_id :                  ID of the decision being evaluated.
    final_action :                 Resolved final action.
    entries :                      One entry per evaluated policy.
    total_policies :               Total number of policies that were evaluated.
    conflict_resolution_applied :  Whether conflict resolution was needed.
    generated_at :                 When the report was generated.
    framework_version :            Framework version string.
    """

    report_id:                    str
    request_id:                   str
    decision_id:                  str
    final_action:                 PolicyAction
    entries:                      Tuple[PolicyAuditEntry, ...]
    total_policies:               int
    conflict_resolution_applied:  bool
    generated_at:                 datetime
    framework_version:            str = VERSION

    def to_dict(self) -> dict:
        return {
            "report_id":                   self.report_id,
            "request_id":                  self.request_id,
            "decision_id":                 self.decision_id,
            "final_action":                self.final_action.value,
            "entries":                     [e.to_dict() for e in self.entries],
            "total_policies":              self.total_policies,
            "conflict_resolution_applied": self.conflict_resolution_applied,
            "generated_at":                self.generated_at.isoformat(),
            "framework_version":           self.framework_version,
        }


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def build_audit_report(
    request_id:          str,
    decision_id:         str,
    results:             List[SinglePolicyResult],
    final_action:        PolicyAction,
    *,
    conflict_applied:    bool = False,
) -> PolicyAuditReport:
    """
    Build a :class:`PolicyAuditReport` from the evaluation results.

    Parameters
    ----------
    request_id :       Originating request ID.
    decision_id :      Decision ID.
    results :          Evaluated policy results.
    final_action :     Resolved final action.
    conflict_applied : Whether conflict resolution changed the outcome.
    """
    now = datetime.now(timezone.utc)

    entries: List[PolicyAuditEntry] = []
    for r in results:
        triggered_count = sum(1 for rr in r.rule_results if rr.triggered)
        entries.append(
            PolicyAuditEntry(
                entry_id          = str(uuid.uuid4()),
                policy_id         = r.policy_id,
                policy_name       = r.policy_name,
                action            = r.action,
                reason            = r.reason,
                rules_evaluated   = len(r.rule_results),
                rules_triggered   = triggered_count,
                evaluation_time_s = r.evaluation_time_s,
                recorded_at       = now,
            )
        )

    return PolicyAuditReport(
        report_id                   = str(uuid.uuid4()),
        request_id                  = request_id,
        decision_id                 = decision_id,
        final_action                = final_action,
        entries                     = tuple(entries),
        total_policies              = len(results),
        conflict_resolution_applied = conflict_applied,
        generated_at                = now,
    )
