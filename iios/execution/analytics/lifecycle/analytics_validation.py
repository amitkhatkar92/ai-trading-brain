"""
iios/execution/analytics/lifecycle/analytics_validation.py
==========================================================
AnalyticsValidationResult and AnalyticsValidator — validation for
analytics sessions and contexts.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .analytics_context import AnalyticsContext
    from .analytics_session import AnalyticsSession


@dataclass
class AnalyticsValidationResult:
    """Mutable accumulator of analytics validation findings."""

    is_valid: bool      = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "AnalyticsValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class AnalyticsValidator:
    """Validates analytics contexts and sessions."""

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(
        self, context: Optional["AnalyticsContext"]
    ) -> AnalyticsValidationResult:
        r = AnalyticsValidationResult()
        if context is None:
            r.add_error("context must not be None")
            return r
        if not getattr(context, "execution_session_id", ""):
            r.add_error("execution_session_id is required")
        if not getattr(context, "analytics_scope", None):
            r.add_error("analytics_scope is required")
        if not getattr(context, "analytics_mode", None):
            r.add_error("analytics_mode is required")
        if not getattr(context, "analytics_trigger", None):
            r.add_error("analytics_trigger is required")
        return r

    # ── Session validation ────────────────────────────────────────────────────

    def validate_session(
        self, session: Optional["AnalyticsSession"]
    ) -> AnalyticsValidationResult:
        r = AnalyticsValidationResult()
        if session is None:
            r.add_error("session must not be None")
            return r
        if not getattr(session, "session_id", ""):
            r.add_error("session_id is required")
        if not getattr(session, "execution_session_id", ""):
            r.add_error("execution_session_id is required")
        if not getattr(session, "analytics_scope", None):
            r.add_error("analytics_scope is required")
        return r

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_lifecycle_consistency(
        self, session: Optional["AnalyticsSession"]
    ) -> AnalyticsValidationResult:
        r = AnalyticsValidationResult()
        if session is None:
            r.add_error("session must not be None")
            return r
        # start_time must be set if in ACTIVE or COMPLETED
        from .constants import AnalyticsState
        if session.state in (AnalyticsState.ACTIVE, AnalyticsState.COMPLETED):
            if session.start_time is None:
                r.add_warning("session in ACTIVE/COMPLETED state but start_time is None")
        # end_time must be set if COMPLETED
        if session.state == AnalyticsState.COMPLETED:
            if session.end_time is None:
                r.add_warning("session COMPLETED but end_time is None")
        # failure_reason should be set if FAILED
        if session.state == AnalyticsState.FAILED:
            if not session.failure_reason:
                r.add_warning("session FAILED but failure_reason is empty")
        return r
