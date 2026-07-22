"""
risk_policy_audit.py — iios.risk.policies
===========================================
Audit trail value objects and auditor for the Risk Policy Framework.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, PolicyAction
from .risk_policy_request import RiskPolicyRequest
from .risk_policy_result import RiskPolicyResult


# ---------------------------------------------------------------------------
# Audit report value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskPolicyAuditReport:
    """
    Immutable audit trail for a single policy evaluation run.

    Fields
    ------
    audit_id :                  Unique audit record identifier.
    request_id :                Evaluated request identifier.
    evaluation_id :             Risk workflow evaluation correlation identifier.
    portfolio_id :              Portfolio identifier.
    risk_id :                   Risk assessment identifier.
    policies_loaded :           Number of policies loaded from the registry.
    policies_evaluated :        Number of policies actually evaluated.
    evaluation_details :        Per-policy evaluation detail snapshots.
    conflict_resolution_applied : Whether conflict resolution logic was invoked.
    conflict_strategy_used :    Name of the conflict resolution strategy applied.
    final_action :              Resolved governance outcome.
    final_rationale :           Human-readable explanation of the final action.
    elapsed_s :                 Total evaluation elapsed time in seconds.
    created_at :                Wall-clock time the report was generated.
    framework_version :         Framework version string.
    """
    audit_id:                   str
    request_id:                 str
    evaluation_id:              str
    portfolio_id:               str
    risk_id:                    str
    policies_loaded:            int
    policies_evaluated:         int
    evaluation_details:         Tuple[Dict[str, Any], ...]
    conflict_resolution_applied: bool
    conflict_strategy_used:     str
    final_action:               PolicyAction
    final_rationale:            str
    elapsed_s:                  float
    created_at:                 float                = field(default_factory=time.time)
    framework_version:          str                  = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":                   self.audit_id,
            "request_id":                 self.request_id,
            "evaluation_id":              self.evaluation_id,
            "portfolio_id":               self.portfolio_id,
            "risk_id":                    self.risk_id,
            "policies_loaded":            self.policies_loaded,
            "policies_evaluated":         self.policies_evaluated,
            "conflict_resolution_applied": self.conflict_resolution_applied,
            "conflict_strategy_used":     self.conflict_strategy_used,
            "final_action":               self.final_action.value,
            "final_rationale":            self.final_rationale,
            "elapsed_s":                  self.elapsed_s,
            "created_at":                 self.created_at,
            "framework_version":          self.framework_version,
            "evaluation_details":         list(self.evaluation_details),
        }


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class RiskPolicyAuditor:
    """
    Factory that builds :class:`RiskPolicyAuditReport` objects from raw
    evaluation artefacts.

    No state is maintained between calls — all methods are effectively
    static factories.
    """

    def create_report(
        self,
        request:                    RiskPolicyRequest,
        results:                    List[RiskPolicyResult],
        final_action:               PolicyAction,
        policies_loaded:            int,
        elapsed_s:                  float,
        *,
        conflict_resolution_applied: bool = False,
        conflict_strategy_used:      str  = "",
        final_rationale:             str  = "",
        audit_id:                    Optional[str] = None,
    ) -> RiskPolicyAuditReport:
        """
        Build and return an immutable audit report.
        """
        details: List[Dict[str, Any]] = []
        for r in results:
            details.append({
                "policy_id":            r.policy_id,
                "policy_name":          r.policy_name,
                "policy_type":          r.policy_type.value,
                "priority":             r.priority.value,
                "action":               r.action.value,
                "triggered_rule_id":    r.triggered_rule_id,
                "triggered_rule_name":  r.triggered_rule_name,
                "conditions_met":       list(r.conditions_met),
                "conditions_failed":    list(r.conditions_failed),
                "rationale":            r.rationale,
                "evaluation_elapsed_s": r.evaluation_elapsed_s,
            })

        return RiskPolicyAuditReport(
            audit_id                   = audit_id or str(uuid.uuid4()),
            request_id                 = request.request_id,
            evaluation_id              = request.evaluation_id,
            portfolio_id               = request.portfolio_id,
            risk_id                    = request.risk_id,
            policies_loaded            = policies_loaded,
            policies_evaluated         = len(results),
            evaluation_details         = tuple(details),
            conflict_resolution_applied = conflict_resolution_applied,
            conflict_strategy_used     = conflict_strategy_used,
            final_action               = final_action,
            final_rationale            = final_rationale or f"Final action: {final_action.value}",
            elapsed_s                  = elapsed_s,
        )
