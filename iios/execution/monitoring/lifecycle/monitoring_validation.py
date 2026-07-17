"""iios/execution/monitoring/lifecycle/monitoring_validation.py
==================================================
MonitoringValidator — stateless validator for monitoring sessions,
contexts, and transitions.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VALID_TRANSITIONS, MonitoringState


@dataclass
class ValidationResult:
    """Result from a validation operation."""

    is_valid:  bool
    errors:    List[str] = field(default_factory=list)
    warnings:  List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   self.errors,
            "warnings": self.warnings,
        }


class MonitoringValidator:
    """Stateless validator.  Create once and reuse."""

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(self, context) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not context.execution_session_id:
            result.add_error("execution_session_id is required.")
        if not context.portfolio_id:
            result.add_error("portfolio_id is required.")
        if context.monitoring_version < 1:
            result.add_error("monitoring_version must be >= 1.")
        return result

    # ── Session validation ────────────────────────────────────────────────────

    def validate_session(self, session) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not session.session_id:
            result.add_error("session_id is required.")
        if not session.execution_session_id:
            result.add_error("execution_session_id is required.")
        if not session.portfolio_id:
            result.add_error("portfolio_id is required.")
        if session.monitoring_version < 1:
            result.add_error("monitoring_version must be >= 1.")
        if session.state not in MonitoringState.__members__.values():
            result.add_error(f"Unknown state: {session.state!r}.")
        return result

    # ── Transition validation ─────────────────────────────────────────────────

    def validate_transition(
        self,
        from_state: MonitoringState,
        to_state:   MonitoringState,
    ) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        allowed = VALID_TRANSITIONS.get(from_state, frozenset())
        if to_state not in allowed:
            result.add_error(
                f"Transition {from_state.value} → {to_state.value} is not allowed. "
                f"Allowed: {[s.value for s in allowed]}."
            )
        return result

    # ── Metadata validation ───────────────────────────────────────────────────

    def validate_metadata(self, metadata) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        if not metadata.session_id:
            result.add_error("metadata.session_id is required.")
        if not metadata.source_system:
            result.add_error("metadata.source_system is required.")
        if not metadata.created_by:
            result.add_error("metadata.created_by is required.")
        if not metadata.environment:
            result.add_error("metadata.environment is required.")
        return result
