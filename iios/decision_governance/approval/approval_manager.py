"""iios/decision_governance/approval/approval_manager.py

Thread-safe singleton manager for approval results.
"""
from __future__ import annotations

import threading
from typing import ClassVar

from iios.decision_governance.governance_exceptions import (
    ApprovalNotFoundError,
)
from iios.decision_governance.approval.approval_result import ApprovalResult


class ApprovalManager:
    """Stores and retrieves ApprovalResults."""

    def __init__(self) -> None:
        self._lock:    threading.RLock            = threading.RLock()
        self._results: dict[str, ApprovalResult]  = {}

    def store(self, result: ApprovalResult) -> None:
        with self._lock:
            self._results[result.result_id] = result

    def get(self, result_id: str) -> ApprovalResult:
        with self._lock:
            r = self._results.get(result_id)
        if r is None:
            raise ApprovalNotFoundError(result_id)
        return r

    def by_decision(self, decision_id: str) -> list[ApprovalResult]:
        with self._lock:
            return [r for r in self._results.values() if r.decision_id == decision_id]

    def pending(self) -> list[ApprovalResult]:
        from iios.decision_governance.governance_constants import ApprovalStatus  # noqa: PLC0415
        with self._lock:
            return [
                r for r in self._results.values()
                if r.status == ApprovalStatus.ESCALATED
            ]

    def recent(self, n: int = 10) -> list[ApprovalResult]:
        with self._lock:
            results = sorted(self._results.values(), key=lambda r: r.created_at, reverse=True)
        return results[:n]

    def statistics(self) -> dict:
        from iios.decision_governance.governance_constants import ApprovalStatus  # noqa: PLC0415
        with self._lock:
            total     = len(self._results)
            approved  = sum(1 for r in self._results.values() if r.approved)
            rejected  = sum(1 for r in self._results.values() if not r.approved and r.status == ApprovalStatus.REJECTED)
            escalated = sum(1 for r in self._results.values() if r.status == ApprovalStatus.ESCALATED)
        return {
            "total":     total,
            "approved":  approved,
            "rejected":  rejected,
            "escalated": escalated,
        }


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock = threading.Lock()
_instance:       ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = ApprovalManager()
    return _instance


def reset_approval_manager() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
