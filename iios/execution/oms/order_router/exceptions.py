"""iios/execution/oms/order_router/exceptions.py
==================================================
Exception hierarchy for the IIOS Order Router.

Error Codes
-----------
OR-000  OrderRouterError           — base
OR-001  RoutingRequestError        — invalid request
OR-002  RoutingRejectedError       — no viable route found
OR-003  NoCandidatesError          — zero candidates after evaluation
OR-004  RouterCapacityError        — history / registry full
OR-005  RouterNotRunning           — router not started
OR-006  RoutingValidationError     — validation failure
OR-007  RoutingPolicyError         — policy evaluation failure
OR-008  RoutingStrategyError       — strategy evaluation failure
OR-009  RoutingExpiredError        — request TTL exceeded
OR-010  DuplicateRoutingError      — duplicate routing request

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class OrderRouterError(IIOSError):
    """Base for all Order Router errors."""
    DEFAULT_CODE = "OR-000"


class RoutingRequestError(OrderRouterError):
    """Invalid routing request."""
    DEFAULT_CODE = "OR-001"


class RoutingRejectedError(OrderRouterError):
    """No viable routing target found."""
    DEFAULT_CODE = "OR-002"

    def __init__(
        self,
        order_id: str,
        reason:   str = "",
        *,
        code:           str = "OR-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Routing rejected for order '{order_id}': {reason}",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id
        self.reason   = reason


class NoCandidatesError(OrderRouterError):
    """Zero routing candidates after evaluation."""
    DEFAULT_CODE = "OR-003"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OR-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"No routing candidates for order '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class RouterCapacityError(OrderRouterError):
    """Router history or registry at capacity."""
    DEFAULT_CODE = "OR-004"


class RouterNotRunning(OrderRouterError):
    """Router was not started before use."""
    DEFAULT_CODE = "OR-005"


class RoutingValidationError(OrderRouterError):
    """Routing validation failed."""
    DEFAULT_CODE = "OR-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "OR-006",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class RoutingPolicyError(OrderRouterError):
    """Policy evaluation failure."""
    DEFAULT_CODE = "OR-007"


class RoutingStrategyError(OrderRouterError):
    """Strategy evaluation failure."""
    DEFAULT_CODE = "OR-008"


class RoutingExpiredError(OrderRouterError):
    """Routing request TTL exceeded."""
    DEFAULT_CODE = "OR-009"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OR-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Routing request for '{order_id}' has expired",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id


class DuplicateRoutingError(OrderRouterError):
    """Duplicate routing request for the same order."""
    DEFAULT_CODE = "OR-010"

    def __init__(
        self,
        order_id: str,
        *,
        code:           str = "OR-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Routing request already exists for order '{order_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.order_id = order_id
