"""iios/decision_governance/audit/audit_manager.py

Thread-safe singleton AuditManager.
"""
from __future__ import annotations

import threading

from iios.decision_governance.audit.audit_engine import AuditEngine
from iios.decision_governance.audit.audit_history import AuditHistory
from iios.decision_governance.audit.audit_registry import AuditRegistry, get_audit_registry


class AuditManager:
    """High-level manager; owns the AuditEngine and provides singleton access."""

    def __init__(self, registry: AuditRegistry | None = None) -> None:
        _reg            = registry or get_audit_registry()
        self._history   = AuditHistory()
        self._engine    = AuditEngine(history=self._history, registry=_reg)

    @property
    def engine(self) -> AuditEngine:
        return self._engine

    @property
    def history(self) -> AuditHistory:
        return self._history

    def statistics(self) -> dict:
        return {
            "total_events":    self._history.count(),
            "total_decisions": len(self._history._by_decision),  # noqa: SLF001
        }


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock    = threading.Lock()
_instance:       AuditManager | None = None


def get_audit_manager() -> AuditManager:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = AuditManager()
    return _instance


def reset_audit_manager() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
