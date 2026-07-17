"""iios/execution/risk/rules/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Risk Rules Framework.

Error codes: ERR-000 through ERR-009

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class ExecutionRuleError(IIOSError):
    """ERR-000 — Base exception for the Execution Risk Rules Framework."""
    error_code = "ERR-000"

    def __init__(self, message: str = "Execution risk rule error") -> None:
        super().__init__(f"[{self.error_code}] {message}")


class RuleRegistrationError(ExecutionRuleError):
    """ERR-001 — Raised when a rule cannot be registered."""
    error_code = "ERR-001"

    def __init__(self, message: str, *, rule_id: str = "") -> None:
        self.rule_id = rule_id
        super().__init__(message)


class DuplicateRuleError(ExecutionRuleError):
    """ERR-002 — Raised when a rule with the same ID already exists."""
    error_code = "ERR-002"

    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Rule '{rule_id}' is already registered")


class RuleNotFoundError(ExecutionRuleError):
    """ERR-003 — Raised when a rule cannot be located in the registry."""
    error_code = "ERR-003"

    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Rule '{rule_id}' not found in registry")


class RuleValidationError(ExecutionRuleError):
    """ERR-004 — Raised when a rule fails structural validation."""
    error_code = "ERR-004"

    def __init__(self, message: str, *, rule_id: str = "") -> None:
        self.rule_id = rule_id
        super().__init__(message)


class RuleExecutionError(ExecutionRuleError):
    """ERR-005 — Raised when a rule encounters an unexpected error during evaluation."""
    error_code = "ERR-005"

    def __init__(self, message: str, *, rule_id: str = "") -> None:
        self.rule_id = rule_id
        super().__init__(message)


class RuleTimeoutError(ExecutionRuleError):
    """ERR-006 — Raised when a rule evaluation exceeds its timeout."""
    error_code = "ERR-006"

    def __init__(self, rule_id: str, timeout_ms: float) -> None:
        self.rule_id     = rule_id
        self.timeout_ms  = timeout_ms
        super().__init__(
            f"Rule '{rule_id}' exceeded execution timeout of {timeout_ms:.1f} ms"
        )


class RuleFrameworkError(ExecutionRuleError):
    """ERR-007 — Raised for internal framework errors not covered by other types."""
    error_code = "ERR-007"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RuleNotRunningError(ExecutionRuleError):
    """ERR-008 — Raised when a registry or manager operation is called before start."""
    error_code = "ERR-008"

    def __init__(self) -> None:
        super().__init__(
            "Execution Risk Rules Framework is not running — call start() first"
        )


class CircularDependencyError(ExecutionRuleError):
    """ERR-009 — Raised when a circular rule dependency is detected."""
    error_code = "ERR-009"

    def __init__(self, message: str) -> None:
        super().__init__(message)
