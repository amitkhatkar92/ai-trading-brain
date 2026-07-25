"""
workflow_policy_audit.py — iios.workflow.policies
--------------------------------------------------
WorkflowPolicyAuditRecord + WorkflowPolicyAudit — governance audit trail.

Every governance evaluation is captured as an immutable audit record.
Records are stored in a bounded, thread-safe deque.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_HISTORY, GovernanceDecision, PolicyAction
from .exceptions import WorkflowPolicyAuditError
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_response import WorkflowPolicyResponse
from .workflow_policy_result import WorkflowPolicyResult

_log = get_logger(__name__)


@dataclass(frozen=True)
class WorkflowPolicyAuditRecord:
    """Immutable audit record for a single governance evaluation."""
    audit_id:          str
    request_id:        str
    workflow_id:       str
    decision:          GovernanceDecision
    winning_action:    PolicyAction
    policies_evaluated: int
    policy_results:    tuple                  # Tuple[WorkflowPolicyResult, ...]
    conditions_applied: List[str]
    reasoning:         str
    audit_timestamp:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":          self.audit_id,
            "request_id":        self.request_id,
            "workflow_id":       self.workflow_id,
            "decision":          self.decision.value,
            "winning_action":    self.winning_action.value,
            "policies_evaluated": self.policies_evaluated,
            "reasoning":         self.reasoning,
            "audit_timestamp":   self.audit_timestamp,
        }


class WorkflowPolicyAudit:
    """
    Thread-safe, bounded audit log for governance evaluations.

    Oldest records are evicted automatically when capacity is exceeded.
    """

    def __init__(self, max_records: int = DEFAULT_MAX_HISTORY) -> None:
        self._max     = max_records
        self._records: deque[WorkflowPolicyAuditRecord]           = deque(maxlen=max_records)
        self._by_id:  Dict[str, WorkflowPolicyAuditRecord]        = {}
        self._by_wf:  Dict[str, List[str]]                        = {}  # workflow_id → [audit_id]
        self._lock    = threading.Lock()

    # ----------------------------------------------------------------
    # Recording
    # ----------------------------------------------------------------

    def record(
        self,
        request:  WorkflowPolicyRequest,
        response: WorkflowPolicyResponse,
    ) -> WorkflowPolicyAuditRecord:
        """Create and store an audit record from a request/response pair."""
        audit_id = f"wpa-{uuid.uuid4().hex[:12]}"
        rec = WorkflowPolicyAuditRecord(
            audit_id           = audit_id,
            request_id         = request.request_id,
            workflow_id        = request.workflow_id,
            decision           = response.decision,
            winning_action     = response.winning_action,
            policies_evaluated = response.policies_evaluated,
            policy_results     = response.policy_results,
            conditions_applied = list(response.conditions_applied),
            reasoning          = response.reasoning,
            audit_timestamp    = datetime.now(tz=timezone.utc).isoformat(),
        )
        with self._lock:
            # Evict oldest from by_id if deque is full
            if len(self._records) == self._max and self._records:
                oldest = self._records[0]
                self._by_id.pop(oldest.audit_id, None)
            self._records.append(rec)
            self._by_id[audit_id] = rec
            self._by_wf.setdefault(request.workflow_id, []).append(audit_id)

        _log.debug(
            f"Audit: recorded audit_id={audit_id!r} "
            f"decision={response.decision.value!r}"
        )
        return rec

    # ----------------------------------------------------------------
    # Retrieval
    # ----------------------------------------------------------------

    def get(self, audit_id: str) -> WorkflowPolicyAuditRecord:
        """Return a record by audit_id.  Raises WorkflowPolicyAuditError if missing."""
        with self._lock:
            rec = self._by_id.get(audit_id)
        if rec is None:
            raise WorkflowPolicyAuditError(f"Audit record not found: {audit_id!r}")
        return rec

    def recent(self, n: int = 20) -> List[WorkflowPolicyAuditRecord]:
        """Return the N most-recent audit records (newest first)."""
        with self._lock:
            records = list(self._records)
        return list(reversed(records[-n:]))

    def by_workflow(self, workflow_id: str) -> List[WorkflowPolicyAuditRecord]:
        """Return all audit records for a given workflow_id."""
        with self._lock:
            ids   = list(self._by_wf.get(workflow_id, []))
            recs  = [self._by_id[aid] for aid in ids if aid in self._by_id]
        return recs

    def audit_count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> int:
        """Clear all records.  Returns count cleared."""
        with self._lock:
            n = len(self._records)
            self._records.clear()
            self._by_id.clear()
            self._by_wf.clear()
        return n
