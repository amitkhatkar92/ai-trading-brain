"""iios/execution/oms/order_manager/order_manager_validation.py
==================================================
OrderManagerValidator — stateless validation for managed order
registration, state transitions, and parent-child integrity.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from iios.execution.oms.order_manager.constants import (
    ManagerOrderState,
    ManagerValidationCode,
    VALID_MANAGER_TRANSITIONS,
)
from iios.execution.oms.order_manager.order_manager_context import ManagedOrder
from iios.execution.oms.order_manager.order_manager_request import CreateOrderRequest
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:oms:order_manager:validator")


@dataclass(frozen=True)
class ManagerValidationResult:
    """Outcome of a validation pass."""

    passed:   bool
    errors:   tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, *, warnings: tuple[str, ...] = ()) -> "ManagerValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "ManagerValidationResult":
        return cls(passed=False, errors=errors)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class OrderManagerValidator:
    """
    Stateless validator for Order Manager operations.
    Thread-safe (no mutable state).
    """

    # ── Registration ──────────────────────────────────────────────────────────

    def validate_registration(
        self,
        request:         CreateOrderRequest,
        existing_ids:    frozenset[str],
    ) -> ManagerValidationResult:
        """Validate a CreateOrderRequest before registration."""
        errors: list[str] = []
        warnings: list[str] = []

        if not request.order_id:
            errors.append(
                f"[{ManagerValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        elif request.order_id in existing_ids:
            errors.append(
                f"[{ManagerValidationCode.DUPLICATE_ORDER_ID.value}] "
                f"order_id '{request.order_id}' is already registered"
            )

        # Parent validation
        if request.parent_order_id:
            if request.parent_order_id not in existing_ids:
                errors.append(
                    f"[{ManagerValidationCode.PARENT_NOT_FOUND.value}] "
                    f"parent_order_id '{request.parent_order_id}' not found"
                )
            if request.parent_order_id == request.order_id:
                errors.append(
                    f"[{ManagerValidationCode.CIRCULAR_PARENT.value}] "
                    "order_id cannot be its own parent"
                )

        if errors:
            return ManagerValidationResult.fail(*errors)
        return ManagerValidationResult.ok(warnings=tuple(warnings))

    # ── State transition ──────────────────────────────────────────────────────

    def validate_transition(
        self,
        order_id:  str,
        current:   ManagerOrderState,
        target:    ManagerOrderState,
    ) -> ManagerValidationResult:
        """Validate an OMS state transition."""
        valid_targets = VALID_MANAGER_TRANSITIONS.get(current, frozenset())
        if target not in valid_targets:
            return ManagerValidationResult.fail(
                f"[{ManagerValidationCode.INVALID_MANAGER_STATE.value}] "
                f"Invalid OMS transition for '{order_id}': "
                f"{current.value} → {target.value}. "
                f"Allowed: {[s.value for s in sorted(valid_targets, key=lambda x: x.value)]}"
            )
        return ManagerValidationResult.ok()

    # ── Parent-child integrity ────────────────────────────────────────────────

    def validate_parent_child(
        self,
        parent:  ManagedOrder,
        child_id: str,
    ) -> ManagerValidationResult:
        """Validate that a child can be attached to a parent."""
        if parent.is_terminal:
            return ManagerValidationResult.fail(
                f"[{ManagerValidationCode.INVALID_PARENT_ID.value}] "
                f"Cannot attach child to terminal parent '{parent.order_id}'"
            )
        if child_id in parent.child_order_ids:
            return ManagerValidationResult.fail(
                f"[{ManagerValidationCode.DUPLICATE_ORDER_ID.value}] "
                f"child '{child_id}' already attached to parent '{parent.order_id}'"
            )
        return ManagerValidationResult.ok()

    # ── Managed order ─────────────────────────────────────────────────────────

    def validate_managed_order(
        self,
        managed: ManagedOrder,
    ) -> ManagerValidationResult:
        """Validate a fully assembled ManagedOrder."""
        errors: list[str] = []
        if not managed.order_id:
            errors.append(
                f"[{ManagerValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if errors:
            return ManagerValidationResult.fail(*errors)
        return ManagerValidationResult.ok()
