"""iios/execution/gateway/engine/gateway_dispatcher.py
==================================================
GatewayDispatcher — coordinates dispatch of gateway requests to the
Broker Abstraction (M3) and Routing Framework (M4).

Defines the BrokerAbstractionProtocol and RoutingFrameworkProtocol
interfaces that future modules will implement.

When no broker is registered, SimulatedDispatch is used, which
accepts all requests and returns ACCEPTED (paper-trading mode).

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:                     # Python < 3.8 fallback
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from .constants import ACTOR_DISPATCHER, DispatchOutcome, VERSION
from .gateway_request import EngineGatewayRequest


# ── DispatchResult ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DispatchResult:
    """
    Immutable result returned by a broker abstraction after a dispatch call.

    ``accepted`` is True when outcome is ACCEPTED.
    ``external_id`` is the broker's own order / reference identifier.
    """

    accepted:         bool
    outcome:          DispatchOutcome
    external_id:      str
    result_metadata:  Dict[str, Any]
    error_code:       str
    error_message:    str
    dispatched_at:    float
    version:          str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted":        self.accepted,
            "outcome":         self.outcome.value,
            "external_id":     self.external_id,
            "result_metadata": dict(self.result_metadata),
            "error_code":      self.error_code,
            "error_message":   self.error_message,
            "dispatched_at":   self.dispatched_at,
            "version":         self.version,
        }


# ── RouteDecision ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteDecision:
    """
    Immutable routing decision returned by the Routing Framework (M4).

    ``routed`` is True when the framework resolved a valid route.
    ``route_id`` identifies the selected route.
    """

    routed:         bool
    route_id:       str
    route_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routed":         self.routed,
            "route_id":       self.route_id,
            "route_metadata": dict(self.route_metadata),
        }


# ── Protocols ─────────────────────────────────────────────────────────────────

@runtime_checkable
class BrokerAbstractionProtocol(Protocol):
    """
    Protocol that the Broker Abstraction (M3) must implement.

    The engine dispatches requests through this interface.
    Do NOT implement broker-specific logic here.
    """

    @property
    def is_available(self) -> bool:
        """True if the broker abstraction is ready to accept requests."""
        ...

    def dispatch(self, request: EngineGatewayRequest) -> DispatchResult:
        """Dispatch a gateway request to the broker layer."""
        ...

    def cancel(self, request_id: str, reason: str = "") -> bool:
        """Request cancellation of a previously dispatched request."""
        ...


@runtime_checkable
class RoutingFrameworkProtocol(Protocol):
    """
    Protocol that the Routing Framework (M4) must implement.

    The dispatcher queries this before handing off to the broker.
    Do NOT implement routing algorithms here.
    """

    @property
    def is_available(self) -> bool:
        """True if the routing framework is ready to resolve routes."""
        ...

    def route(self, request: EngineGatewayRequest) -> RouteDecision:
        """Resolve the route for a gateway request."""
        ...


# ── SimulatedDispatch ─────────────────────────────────────────────────────────

class SimulatedDispatch:
    """
    Default dispatcher used when no broker abstraction is registered.

    Simulates accept-and-complete behaviour for paper-trading / test mode.
    Returns ACCEPTED for every request.  This is NOT a placeholder — it is
    the intentional default for environments without a live broker.
    """

    @property
    def is_available(self) -> bool:
        return True

    def dispatch(self, request: EngineGatewayRequest) -> DispatchResult:
        return DispatchResult(
            accepted=True,
            outcome=DispatchOutcome.ACCEPTED,
            external_id=f"SIM-{str(uuid.uuid4())[:8].upper()}",
            result_metadata={
                "mode":       "simulated",
                "request_id": request.request_id,
                "symbol":     request.symbol,
                "side":       request.side,
                "quantity":   request.context.quantity,
                "price":      request.context.price,
            },
            error_code="",
            error_message="",
            dispatched_at=time.time(),
        )

    def cancel(self, request_id: str, reason: str = "") -> bool:
        return True     # simulated: always succeeds


class _NullRouter:
    """Default router when no routing framework is registered. Passes through."""

    @property
    def is_available(self) -> bool:
        return True

    def route(self, request: EngineGatewayRequest) -> RouteDecision:
        return RouteDecision(
            routed=True,
            route_id="null-route",
            route_metadata={"mode": "passthrough"},
        )


# ── GatewayDispatcher ─────────────────────────────────────────────────────────

class GatewayDispatcher:
    """
    Coordinates dispatch of gateway requests to Broker Abstraction and
    Routing Framework.

    When no broker is registered, SimulatedDispatch is used.
    When no router is registered, the null passthrough router is used.

    Non-responsibilities
    --------------------
    * No broker-specific logic.
    * No routing algorithms.
    * No exchange connectivity.
    """

    def __init__(
        self,
        broker: Optional[BrokerAbstractionProtocol] = None,
        router: Optional[RoutingFrameworkProtocol]  = None,
    ) -> None:
        self._broker: BrokerAbstractionProtocol = broker or SimulatedDispatch()
        self._router: RoutingFrameworkProtocol  = router or _NullRouter()
        self._dispatch_count = 0
        self._cancel_count   = 0

    # ── Registration ──────────────────────────────────────────────────────────

    def register_broker(self, broker: BrokerAbstractionProtocol) -> None:
        """Replace the active broker abstraction."""
        if not isinstance(broker, BrokerAbstractionProtocol):
            raise TypeError(
                f"broker must implement BrokerAbstractionProtocol, "
                f"got {type(broker).__name__}"
            )
        self._broker = broker

    def register_router(self, router: RoutingFrameworkProtocol) -> None:
        """Replace the active routing framework."""
        if not isinstance(router, RoutingFrameworkProtocol):
            raise TypeError(
                f"router must implement RoutingFrameworkProtocol, "
                f"got {type(router).__name__}"
            )
        self._router = router

    # ── Availability ──────────────────────────────────────────────────────────

    @property
    def has_broker(self) -> bool:
        return not isinstance(self._broker, SimulatedDispatch)

    @property
    def has_router(self) -> bool:
        return not isinstance(self._router, _NullRouter)

    @property
    def broker_available(self) -> bool:
        return self._broker.is_available

    @property
    def router_available(self) -> bool:
        return self._router.is_available

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def dispatch(self, request: EngineGatewayRequest) -> DispatchResult:
        """
        Dispatch a gateway request.

        1. Query routing framework for route decision.
        2. Hand off to broker abstraction for execution.

        Returns ``DispatchResult``.
        """
        # Step 1 — route
        _route = self._router.route(request)

        # Step 2 — dispatch
        result = self._broker.dispatch(request)
        self._dispatch_count += 1
        return result

    def cancel(self, request_id: str, reason: str = "") -> bool:
        """Request cancellation of a previously dispatched request."""
        success = self._broker.cancel(request_id, reason)
        if success:
            self._cancel_count += 1
        return success

    # ── Statistics ────────────────────────────────────────────────────────────

    @property
    def dispatch_count(self) -> int:
        return self._dispatch_count

    @property
    def cancel_count(self) -> int:
        return self._cancel_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_broker":       self.has_broker,
            "has_router":       self.has_router,
            "broker_available": self.broker_available,
            "router_available": self.router_available,
            "dispatch_count":   self._dispatch_count,
            "cancel_count":     self._cancel_count,
        }
