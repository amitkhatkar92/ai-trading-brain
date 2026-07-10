"""iios/execution/monitoring/monitoring_exceptions.py"""
from __future__ import annotations


# ── Base ──────────────────────────────────────────────────────────────────────

class MonitoringEngineError(Exception):
    """EM-000 — root for all monitoring engine errors."""
    error_code: str = "EM-000"

    def __init__(self, message: str = "", code: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.code    = code or self.__class__.error_code


# ── Execution tracking ────────────────────────────────────────────────────────

class ExecutionTrackingError(MonitoringEngineError):
    """EM-010 — execution tracking errors."""
    error_code = "EM-010"


class ExecutionRecordNotFoundError(ExecutionTrackingError):
    """EM-011 — no record for the given execution_id."""
    error_code = "EM-011"


class ExecutionRecordAlreadyExistsError(ExecutionTrackingError):
    """EM-012 — duplicate execution_id."""
    error_code = "EM-012"


class ExecutionTrackerOverflowError(ExecutionTrackingError):
    """EM-013 — tracker capacity exceeded."""
    error_code = "EM-013"


# ── Reconciliation ────────────────────────────────────────────────────────────

class ReconciliationError(MonitoringEngineError):
    """EM-020 — reconciliation errors."""
    error_code = "EM-020"


class ReconciliationFailedError(ReconciliationError):
    """EM-021 — reconciliation run failed."""
    error_code = "EM-021"


class ReconciliationNotFoundError(ReconciliationError):
    """EM-022 — no reconciliation result for given ID."""
    error_code = "EM-022"


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditError(MonitoringEngineError):
    """EM-030 — audit framework errors."""
    error_code = "EM-030"


class AuditEventNotFoundError(AuditError):
    """EM-031 — no audit event for given ID."""
    error_code = "EM-031"


class AuditStorageOverflowError(AuditError):
    """EM-032 — audit history capacity exceeded."""
    error_code = "EM-032"


class AuditTamperingDetectedError(AuditError):
    """EM-033 — audit record hash does not match stored hash."""
    error_code = "EM-033"


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertError(MonitoringEngineError):
    """EM-040 — alert framework errors."""
    error_code = "EM-040"


class AlertRuleNotFoundError(AlertError):
    """EM-041 — no rule registered with given name."""
    error_code = "EM-041"


class AlertStorageOverflowError(AlertError):
    """EM-042 — alert store capacity exceeded."""
    error_code = "EM-042"


# ── Registry / Manager ────────────────────────────────────────────────────────

class MonitoringRegistryError(MonitoringEngineError):
    """EM-050 — monitoring registry errors."""
    error_code = "EM-050"


class MonitoringEngineNotInitializedError(MonitoringEngineError):
    """EM-060 — engine used before initialisation."""
    error_code = "EM-060"


class MonitoringEngineAlreadyRunningError(MonitoringEngineError):
    """EM-061 — engine already started."""
    error_code = "EM-061"
