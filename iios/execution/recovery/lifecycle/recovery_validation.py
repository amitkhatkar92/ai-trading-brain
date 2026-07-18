"""iios/execution/recovery/lifecycle/recovery_validation.py
==================================================
RecoveryValidator — stateless validator for recovery contexts and
sessions.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import RecoveryState, VALID_TRANSITIONS
from .exceptions import RecoveryInvalidTransitionError


@dataclass
class RecoveryValidationResult:
    """
    Mutable validation result accumulator.

    Fields
    ------
    is_valid:  True until the first error is added.
    errors:    List of error messages.
    warnings:  List of non-blocking warning messages.
    """

    is_valid:  bool      = True
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
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class RecoveryValidator:
    """
    Stateless validator for recovery lifecycle objects.

    All methods return a ``RecoveryValidationResult`` and never raise.
    """

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(self, context: Any) -> RecoveryValidationResult:
        """Validate a RecoveryContext."""
        result = RecoveryValidationResult()

        if not getattr(context, "execution_session_id", ""):
            result.add_error("context.execution_session_id must not be empty")

        if not getattr(context, "subsystem_id", ""):
            result.add_error("context.subsystem_id must not be empty")

        recovery_reason = getattr(context, "recovery_reason", "")
        if not recovery_reason:
            result.add_warning("context.recovery_reason is empty — add context for audit trail")

        recovery_trigger = getattr(context, "recovery_trigger", None)
        if recovery_trigger is None:
            result.add_error("context.recovery_trigger must be set")

        version = getattr(context, "recovery_version", 0)
        if version < 1:
            result.add_error("context.recovery_version must be >= 1")

        return result

    # ── Session validation ────────────────────────────────────────────────────

    def validate_session(self, session: Any) -> RecoveryValidationResult:
        """Validate a RecoverySession for internal consistency."""
        result = RecoveryValidationResult()

        if not getattr(session, "session_id", ""):
            result.add_error("session.session_id must not be empty")

        if not getattr(session, "execution_session_id", ""):
            result.add_error("session.execution_session_id must not be empty")

        if not getattr(session, "subsystem_id", ""):
            result.add_error("session.subsystem_id must not be empty")

        state = getattr(session, "state", None)
        if state is None:
            result.add_error("session.state must not be None")

        # Timestamp consistency
        created_at = getattr(session, "created_at", None)
        updated_at = getattr(session, "updated_at", None)
        if created_at and updated_at and updated_at < created_at:
            result.add_error("session.updated_at must be >= session.created_at")

        # History integrity
        transitions = getattr(session, "transitions", [])
        if len(transitions) > 0:
            from .recovery_transition import RecoveryTransition
            for i, t in enumerate(transitions):
                if not isinstance(t, RecoveryTransition):
                    result.add_error(f"transitions[{i}] is not a RecoveryTransition")
                    break

        return result

    # ── Transition validation ─────────────────────────────────────────────────

    def validate_transition(
        self, from_state: RecoveryState, to_state: RecoveryState
    ) -> RecoveryValidationResult:
        """Validate a single state-machine hop."""
        result = RecoveryValidationResult()

        allowed = VALID_TRANSITIONS.get(from_state, frozenset())
        if to_state not in allowed:
            result.add_error(
                f"Transition from '{from_state.value}' to '{to_state.value}' is not allowed. "
                f"Valid targets: {[s.value for s in sorted(allowed, key=lambda s: s.value)]}"
            )

        return result

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_history_integrity(
        self, transitions: List[Any]
    ) -> RecoveryValidationResult:
        """
        Verify that the sequence of transitions is self-consistent.

        Checks that each consecutive pair forms a valid state machine edge.
        """
        result = RecoveryValidationResult()

        for i in range(1, len(transitions)):
            prev = transitions[i - 1]
            curr = transitions[i]
            if prev.to_state != curr.from_state:
                result.add_error(
                    f"History gap at index {i}: "
                    f"transitions[{i-1}].to_state={prev.to_state.value!r} != "
                    f"transitions[{i}].from_state={curr.from_state.value!r}"
                )

        return result
