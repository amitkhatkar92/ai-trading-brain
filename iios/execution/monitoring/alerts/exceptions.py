"""iios/execution/monitoring/alerts/exceptions.py
==================================================
Exception hierarchy for the Execution Alert Framework.

Error code prefix: AF

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class AlertFrameworkError(IIOSError):
    """Base exception for all alert framework errors.  AF-000."""

    error_code = "AF-000"

    def __init__(self, message: str = "Alert framework error.") -> None:
        super().__init__(message)


class AlertEngineNotRunningError(AlertFrameworkError):
    """Alert engine is not running.  AF-001."""

    error_code = "AF-001"

    def __init__(self) -> None:
        super().__init__(
            "Alert engine is not running. "
            "Call start() before performing alert operations."
        )


class AlertNotFoundError(AlertFrameworkError):
    """No alert with the given ID exists.  AF-002."""

    error_code = "AF-002"

    def __init__(self, alert_id: str) -> None:
        super().__init__(f"Alert '{alert_id}' not found.")
        self.alert_id = alert_id


class AlertRuleNotFoundError(AlertFrameworkError):
    """No rule with the given ID exists.  AF-003."""

    error_code = "AF-003"

    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Alert rule '{rule_id}' not found.")
        self.rule_id = rule_id


class AlertRuleEvaluationError(AlertFrameworkError):
    """A rule evaluation failed.  AF-004."""

    error_code = "AF-004"

    def __init__(self, rule_id: str = "", reason: str = "") -> None:
        msg = f"Alert rule '{rule_id}' evaluation failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg + ".")
        self.rule_id = rule_id
        self.reason  = reason


class AlertRegistryCapacityError(AlertFrameworkError):
    """Registry is at capacity.  AF-005."""

    error_code = "AF-005"

    def __init__(self, max_count: int) -> None:
        super().__init__(
            f"Alert registry capacity reached ({max_count}). "
            "Resolve or expire active alerts."
        )
        self.max_count = max_count


class AlertValidationError(AlertFrameworkError):
    """Alert validation failed.  AF-006."""

    error_code = "AF-006"

    def __init__(
        self,
        message: str  = "Alert validation failed.",
        errors:  tuple = (),
    ) -> None:
        super().__init__(message)
        self.errors = errors


class AlertTransitionError(AlertFrameworkError):
    """Invalid alert status transition.  AF-007."""

    error_code = "AF-007"

    def __init__(
        self,
        alert_id:    str,
        from_status: str,
        to_status:   str,
    ) -> None:
        super().__init__(
            f"Invalid alert transition for '{alert_id}': "
            f"'{from_status}' → '{to_status}'"
        )
        self.alert_id    = alert_id
        self.from_status = from_status
        self.to_status   = to_status


class AlertSnapshotError(AlertFrameworkError):
    """Alert snapshot creation failed.  AF-008."""

    error_code = "AF-008"

    def __init__(self, reason: str = "") -> None:
        msg = "Alert snapshot creation failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg + ".")
        self.reason = reason


class DuplicateAlertRuleError(AlertFrameworkError):
    """A rule with the same ID already exists.  AF-009."""

    error_code = "AF-009"

    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Alert rule '{rule_id}' already registered.")
        self.rule_id = rule_id
