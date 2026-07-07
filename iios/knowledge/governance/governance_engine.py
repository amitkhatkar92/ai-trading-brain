"""
iios/knowledge/governance/governance_engine.py
===============================================
GovernanceEngine — manages the approval workflow for knowledge records.

Callers submit records for approval; the engine creates GovernanceRecord
objects, evaluates policies, and transitions records through the
PENDING → APPROVED / REJECTED lifecycle.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Optional

from ..knowledge_constants import KnowledgeStatus
from ..models.knowledge_record import KnowledgeRecord
from .governance_constants import (
    ApprovalStatus,
    GovernanceAction,
    SYSTEM_GOVERNANCE_ACTOR,
)
from .governance_exceptions import (
    ApprovalAlreadyExistsError,
    ApprovalError,
    ApprovalNotFoundError,
)
from .models.governance_record import GovernanceRecord

__all__ = ["GovernanceEngine", "get_governance_engine", "reset_governance_engine"]

_LOG = logging.getLogger("iios.knowledge.governance.engine")
_lock = threading.Lock()
_engine: Optional["GovernanceEngine"] = None


class GovernanceEngine:
    """Thread-safe workflow engine for knowledge approval."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # gov_id → GovernanceRecord
        self._records: dict[str, GovernanceRecord] = {}
        # knowledge_id → [gov_id, ...] (insertion order)
        self._by_knowledge: dict[str, list[str]] = defaultdict(list)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_raise(self, gov_id: str) -> GovernanceRecord:
        gr = self._records.get(gov_id)
        if gr is None:
            raise ApprovalNotFoundError(
                f"Governance record '{gov_id}' not found.", code="GE-101"
            )
        return gr

    # ── Submission ────────────────────────────────────────────────────────────

    def submit(
        self,
        knowledge_id:     str,
        submitted_by:     str   = SYSTEM_GOVERNANCE_ACTOR,
        kqi:              float = 0.0,
        violations_count: int   = 0,
        notes:            str   = "",
    ) -> GovernanceRecord:
        """Open a new governance review for *knowledge_id*."""
        with self._lock:
            gr = GovernanceRecord(
                knowledge_id       = knowledge_id,
                status             = ApprovalStatus.PENDING,
                submitted_by       = submitted_by,
                kqi_at_submission  = kqi,
                violations_count   = violations_count,
                notes              = notes,
            )
            self._records[gr.gov_id] = gr
            self._by_knowledge[knowledge_id].append(gr.gov_id)

        _LOG.info(
            "GovernanceEngine: submitted '%s' (gov_id=%s, kqi=%.2f)",
            knowledge_id[:16], gr.gov_id[:8], kqi,
        )
        return gr

    # ── Decisions ─────────────────────────────────────────────────────────────

    def approve(
        self,
        gov_id:      str,
        approved_by: str = SYSTEM_GOVERNANCE_ACTOR,
        reason:      str = "",
    ) -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            if not gr.is_pending:
                raise ApprovalError(
                    f"Governance record '{gov_id}' is not pending "
                    f"(status: {gr.status.value}).",
                    code="GE-100",
                )
            gr.approve(approved_by, reason)
        _LOG.info("Approved: '%s' by '%s'", gr.knowledge_id[:16], approved_by)
        return gr

    def auto_approve(
        self,
        gov_id: str,
        reason: str = "Auto-approved by policy",
    ) -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            if not gr.is_pending:
                raise ApprovalError(
                    f"Cannot auto-approve '{gov_id}' (status: {gr.status.value}).",
                    code="GE-100",
                )
            gr.auto_approve(reason)
        return gr

    def reject(
        self,
        gov_id:      str,
        rejected_by: str = SYSTEM_GOVERNANCE_ACTOR,
        reason:      str = "",
    ) -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            if not gr.is_pending:
                raise ApprovalError(
                    f"Governance record '{gov_id}' is not pending "
                    f"(status: {gr.status.value}).",
                    code="GE-100",
                )
            gr.reject(rejected_by, reason)
        _LOG.info("Rejected: '%s' by '%s'", gr.knowledge_id[:16], rejected_by)
        return gr

    def revoke(
        self,
        gov_id:     str,
        revoked_by: str = SYSTEM_GOVERNANCE_ACTOR,
        reason:     str = "",
    ) -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            gr.revoke(revoked_by, reason)
        return gr

    def set_under_review(self, gov_id: str, reviewer: str) -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            gr.set_under_review(reviewer)
        return gr

    def escalate(self, gov_id: str, reason: str = "") -> GovernanceRecord:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            gr.escalate(reason)
        return gr

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, gov_id: str) -> GovernanceRecord:
        with self._lock:
            return self._get_or_raise(gov_id)

    def get_latest(self, knowledge_id: str) -> Optional[GovernanceRecord]:
        with self._lock:
            ids = self._by_knowledge.get(knowledge_id, [])
            if not ids:
                return None
            return self._records.get(ids[-1])

    def get_all(self, knowledge_id: str) -> list[GovernanceRecord]:
        with self._lock:
            return [
                self._records[gid]
                for gid in self._by_knowledge.get(knowledge_id, [])
                if gid in self._records
            ]

    def get_pending(self) -> list[GovernanceRecord]:
        with self._lock:
            return [gr for gr in self._records.values() if gr.is_pending]

    def get_approved(self, knowledge_id: str) -> Optional[GovernanceRecord]:
        """Return the most recent approved record for *knowledge_id*."""
        for gr in reversed(self.get_all(knowledge_id)):
            if gr.is_approved:
                return gr
        return None

    def is_approved(self, knowledge_id: str) -> bool:
        return self.get_approved(knowledge_id) is not None

    def record_count(self) -> int:
        with self._lock:
            return len(self._records)

    # ── Policy IDs attachment ─────────────────────────────────────────────────

    def attach_policies(self, gov_id: str, policy_ids: list[str]) -> None:
        with self._lock:
            gr = self._get_or_raise(gov_id)
            gr.policy_ids_applied = policy_ids

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for gr in self._records.values():
                k = gr.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total_records":   len(self._records),
                "pending":         len(self.get_pending()),
                "unique_items":    len(self._by_knowledge),
                "by_status":       by_status,
            }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_governance_engine() -> GovernanceEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = GovernanceEngine()
    return _engine


def reset_governance_engine() -> None:
    global _engine
    with _lock:
        _engine = None
