"""
integration_gateway_router.py — iios.integration.gateway
----------------------------------------------------------
IntegrationGatewayRouter — determines which subsystem components
must participate for a given gateway request.

Stateless; call ``route(request)`` to get a ``GatewayRouteDecision``.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .constants import (
    GatewayComponentType,
    GatewayOperationType,
    OPERATION_REQUIRED_COMPONENTS,
)
from .integration_gateway_request import IntegrationGatewayRequest


@dataclass(frozen=True)
class GatewayRouteDecision:
    """
    Routing decision for a single gateway request.

    Flags indicate which subsystem components must be invoked.
    Additional routing metadata (e.g. connector type, protocol hint)
    can be carried in ``routing_metadata``.
    """

    request_id:         str
    requires_lifecycle: bool
    requires_engine:    bool
    requires_governance: bool
    requires_services:  bool
    requires_snapshot:  bool
    routing_metadata:   Dict[str, str]

    @property
    def required_components(self) -> List[GatewayComponentType]:
        """Return the list of components that must be invoked."""
        comp = []
        if self.requires_lifecycle:
            comp.append(GatewayComponentType.LIFECYCLE)
        if self.requires_engine:
            comp.append(GatewayComponentType.ENGINE)
        if self.requires_governance:
            comp.append(GatewayComponentType.POLICIES)
        if self.requires_services:
            comp.append(GatewayComponentType.SERVICES)
        if self.requires_snapshot:
            comp.append(GatewayComponentType.SNAPSHOT)
        return comp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":          self.request_id,
            "requires_lifecycle":  self.requires_lifecycle,
            "requires_engine":     self.requires_engine,
            "requires_governance": self.requires_governance,
            "requires_services":   self.requires_services,
            "requires_snapshot":   self.requires_snapshot,
            "routing_metadata":    dict(self.routing_metadata),
        }


class IntegrationGatewayRouter:
    """
    Stateless router that maps gateway operations to component invocation
    decisions.

    Rules:
      SUBMIT     → lifecycle + engine + governance + services + snapshot
      CONNECT    → lifecycle + engine + services
      DISCONNECT → lifecycle + services
      VALIDATE   → no components (validation-only)
      QUERY      → no components (registry lookup)
      HEALTH     → no components (health monitor only)
      STATUS     → no components (status tracker only)
      SNAPSHOT   → snapshot
    """

    def route(self, request: IntegrationGatewayRequest) -> GatewayRouteDecision:
        """Return routing decision for *request*."""
        required = OPERATION_REQUIRED_COMPONENTS.get(request.operation, [])

        # Derive routing metadata hints from request payload
        meta: Dict[str, str] = {}
        if request.connector_config:
            meta["connector_hint"] = str(
                request.connector_config.get("type", "generic")
            )
        if request.protocol_config:
            meta["protocol_hint"] = str(
                request.protocol_config.get("type", "http")
            )
        if request.endpoint_config:
            meta["endpoint_hint"] = str(
                request.endpoint_config.get("url", "")
            )
        meta["operation"] = request.operation.value

        return GatewayRouteDecision(
            request_id          = request.request_id,
            requires_lifecycle  = GatewayComponentType.LIFECYCLE  in required,
            requires_engine     = GatewayComponentType.ENGINE     in required,
            requires_governance = GatewayComponentType.POLICIES   in required,
            requires_services   = GatewayComponentType.SERVICES   in required,
            requires_snapshot   = GatewayComponentType.SNAPSHOT   in required,
            routing_metadata    = meta,
        )
