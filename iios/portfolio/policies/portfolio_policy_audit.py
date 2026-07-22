"""
portfolio_policy_audit.py — iios.portfolio.policies
====================================================
Audit trail for portfolio policy evaluations.

Every PolicyOutcome produces one PolicyAuditEntry.
PortfolioPolicyAuditReport collects all entries for an evaluation run
and provides a fully serialisable audit record.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION, PolicyAction, PolicyType


@dataclass(frozen=True)
class PolicyAuditEntry:
    """
    Immutable audit record for one policy within an evaluation run.

    Fields
    ------
    entry_id :       Unique identifier for this audit entry.
    evaluation_id :  The evaluation run this entry belongs to.
    portfolio_id :   Portfolio being evaluated.
    policy_id :      Policy that produced this entry.
    policy_name :    Human-readable policy name.
    policy_type :    Institutional policy domain.
    action :         The governance outcome this policy returned.
    reason :         Human-readable explanation.
    inputs_summary : Dict of input key→type summaries (not full values).
    conditions_passed : Number of conditions that passed.
    conditions_failed : Number of conditions that failed.
    actor :          Actor that triggered the evaluation.
    recorded_at :    Wall-clock time this entry was recorded.
    framework_version: Framework version string.
    """
    entry_id:           str
    evaluation_id:      str
    portfolio_id:       str
    policy_id:          str
    policy_name:        str
    policy_type:        PolicyType
    action:             PolicyAction
    reason:             str
    inputs_summary:     Dict[str, Any]
    conditions_passed:  int
    conditions_failed:  int
    actor:              str
    recorded_at:        float
    framework_version:  str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":          self.entry_id,
            "evaluation_id":     self.evaluation_id,
            "portfolio_id":      self.portfolio_id,
            "policy_id":         self.policy_id,
            "policy_name":       self.policy_name,
            "policy_type":       self.policy_type.value,
            "action":            self.action.value,
            "reason":            self.reason,
            "inputs_summary":    dict(self.inputs_summary),
            "conditions_passed": self.conditions_passed,
            "conditions_failed": self.conditions_failed,
            "actor":             self.actor,
            "recorded_at":       self.recorded_at,
            "framework_version": self.framework_version,
        }


class PortfolioPolicyAuditReport:
    """
    Audit report for one portfolio policy evaluation run.

    Collects PolicyAuditEntry objects as policies are evaluated and
    produces a final serialisable audit record upon completion.

    Parameters
    ----------
    evaluation_id : Evaluation run identifier.
    portfolio_id :  Portfolio that was evaluated.
    actor :         Actor that requested the evaluation.
    """

    def __init__(
        self,
        evaluation_id: str,
        portfolio_id:  str,
        actor:         str = "",
    ) -> None:
        self._audit_id      = str(uuid.uuid4())
        self._evaluation_id = evaluation_id
        self._portfolio_id  = portfolio_id
        self._actor         = actor
        self._entries: List[PolicyAuditEntry] = []
        self._final_action: Optional[PolicyAction] = None
        self._generated_at: Optional[float]        = None
        self._finalized:    bool                   = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def audit_id(self) -> str:
        return self._audit_id

    @property
    def evaluation_id(self) -> str:
        return self._evaluation_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def final_action(self) -> Optional[PolicyAction]:
        return self._final_action

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_entry(self, entry: PolicyAuditEntry) -> None:
        """Add an audit entry to this report."""
        if self._finalized:
            from .exceptions import PortfolioPolicyAuditError
            raise PortfolioPolicyAuditError(
                "Cannot add entries to a finalized audit report"
            )
        self._entries.append(entry)

    def finalize(self, final_action: PolicyAction) -> None:
        """Mark the report as complete with the resolved final action."""
        self._final_action = final_action
        self._generated_at = time.time()
        self._finalized    = True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":       self._audit_id,
            "evaluation_id":  self._evaluation_id,
            "portfolio_id":   self._portfolio_id,
            "actor":          self._actor,
            "entry_count":    len(self._entries),
            "entries":        [e.to_dict() for e in self._entries],
            "final_action":   self._final_action.value if self._final_action else None,
            "is_finalized":   self._finalized,
            "generated_at":   self._generated_at,
            "framework_version": VERSION,
        }
