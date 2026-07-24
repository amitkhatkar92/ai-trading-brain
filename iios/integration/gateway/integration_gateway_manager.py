"""
integration_gateway_manager.py — iios.integration.gateway
-----------------------------------------------------------
IntegrationGatewayManager — manages multiple IntegrationGateway instances.

Supports multi-tenant and multi-environment gateway deployments.
Thread-safe.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_GATEWAY_ID,
    DEFAULT_MAX_GATEWAYS,
    GatewayComponentType,
)
from .exceptions import GatewayCapacityError, IntegrationGatewayError
from .integration_gateway import IntegrationGateway
from .integration_gateway_health import IntegrationHealthSummary
from .integration_gateway_statistics import IntegrationStatistics

_log = get_logger(__name__)


class IntegrationGatewayManager:
    """
    Manages a collection of IntegrationGateway instances.

    Provides:
      - create / retrieve / remove gateways
      - bulk lifecycle (initialize_all, start_all, stop_all)
      - aggregated health and statistics across all gateways
      - a thread-safe default gateway accessor
    """

    def __init__(self, max_gateways: int = DEFAULT_MAX_GATEWAYS) -> None:
        self._gateways:    Dict[str, IntegrationGateway] = {}
        self._max_gateways = max_gateways
        self._default_id:  str = DEFAULT_GATEWAY_ID
        self._lock         = threading.Lock()
        _log.info(f"IntegrationGatewayManager created: max_gateways={max_gateways}")

    # ─── gateway lifecycle ────────────────────────────────────────────

    def create_gateway(
        self,
        gateway_id:  str  = DEFAULT_GATEWAY_ID,
        config:      Optional[Dict[str, Any]] = None,
        auto_start:  bool = False,
    ) -> IntegrationGateway:
        """
        Create and register a new gateway.

        If *auto_start* is True the gateway is initialized and started.
        Raises GatewayCapacityError if max_gateways is reached.
        Raises IntegrationGatewayError if gateway_id already exists.
        """
        with self._lock:
            if len(self._gateways) >= self._max_gateways:
                raise GatewayCapacityError(
                    f"Gateway manager capacity ({self._max_gateways}) exceeded"
                )
            if gateway_id in self._gateways:
                raise IntegrationGatewayError(
                    f"Gateway {gateway_id!r} already exists"
                )

        gw = IntegrationGateway(gateway_id=gateway_id)

        # Register externally-injected components if config provides them
        if config:
            components = config.get("components", {})
            for ct_str, comp in components.items():
                try:
                    ct = GatewayComponentType(ct_str)
                    gw.component_registry.register(ct, comp)
                except (ValueError, KeyError):
                    _log.info(f"Manager: unknown component type {ct_str!r} — skipped")

        with self._lock:
            self._gateways[gateway_id] = gw
            if len(self._gateways) == 1:
                self._default_id = gateway_id

        if auto_start:
            gw.start()

        _log.info(f"IntegrationGatewayManager: gateway {gateway_id!r} created")
        return gw

    def get_gateway(self, gateway_id: str) -> Optional[IntegrationGateway]:
        """Return the gateway with *gateway_id*, or None."""
        with self._lock:
            return self._gateways.get(gateway_id)

    def get_or_raise(self, gateway_id: str) -> IntegrationGateway:
        """Return the gateway with *gateway_id* or raise IntegrationGatewayError."""
        with self._lock:
            gw = self._gateways.get(gateway_id)
        if gw is None:
            raise IntegrationGatewayError(f"Gateway {gateway_id!r} not found")
        return gw

    def remove_gateway(self, gateway_id: str) -> bool:
        """Stop and remove the gateway. Returns True if found."""
        with self._lock:
            gw = self._gateways.pop(gateway_id, None)
        if gw is None:
            return False
        try:
            gw.stop()
        except Exception:
            pass
        _log.info(f"IntegrationGatewayManager: gateway {gateway_id!r} removed")
        return True

    # ─── default gateway ──────────────────────────────────────────────

    def default_gateway(self) -> IntegrationGateway:
        """
        Return the default gateway, creating and starting it if necessary.
        """
        with self._lock:
            gw = self._gateways.get(self._default_id)
        if gw is None:
            gw = self.create_gateway(DEFAULT_GATEWAY_ID, auto_start=True)
        return gw

    # ─── bulk operations ──────────────────────────────────────────────

    def initialize_all(self) -> Dict[str, bool]:
        """Initialize all registered gateways. Returns {id: success}."""
        results: Dict[str, bool] = {}
        with self._lock:
            ids = list(self._gateways.keys())
        for gid in ids:
            try:
                self._gateways[gid].initialize()
                results[gid] = True
            except Exception as exc:
                _log.info(f"Manager: initialize failed for {gid!r}: {exc!s}")
                results[gid] = False
        return results

    def start_all(self) -> Dict[str, bool]:
        """Start all registered gateways. Returns {id: success}."""
        results: Dict[str, bool] = {}
        with self._lock:
            ids = list(self._gateways.keys())
        for gid in ids:
            try:
                self._gateways[gid].start()
                results[gid] = True
            except Exception as exc:
                _log.info(f"Manager: start failed for {gid!r}: {exc!s}")
                results[gid] = False
        return results

    def stop_all(self) -> Dict[str, bool]:
        """Stop all registered gateways. Returns {id: success}."""
        results: Dict[str, bool] = {}
        with self._lock:
            ids = list(self._gateways.keys())
        for gid in ids:
            try:
                self._gateways[gid].stop()
                results[gid] = True
            except Exception as exc:
                _log.info(f"Manager: stop failed for {gid!r}: {exc!s}")
                results[gid] = False
        return results

    # ─── aggregated observability ─────────────────────────────────────

    def health_all(self) -> Dict[str, IntegrationHealthSummary]:
        """Return health summaries for all registered gateways."""
        result: Dict[str, IntegrationHealthSummary] = {}
        with self._lock:
            gateways = dict(self._gateways)
        for gid, gw in gateways.items():
            result[gid] = gw.health()
        return result

    def statistics_all(self) -> Dict[str, IntegrationStatistics]:
        """Return statistics for all registered gateways."""
        result: Dict[str, IntegrationStatistics] = {}
        with self._lock:
            gateways = dict(self._gateways)
        for gid, gw in gateways.items():
            result[gid] = gw.statistics()
        return result

    # ─── enumeration ─────────────────────────────────────────────────

    def list_gateways(self) -> List[str]:
        """Return list of all registered gateway IDs."""
        with self._lock:
            return list(self._gateways.keys())

    def exists(self, gateway_id: str) -> bool:
        with self._lock:
            return gateway_id in self._gateways

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._gateways)

    @property
    def max_gateways(self) -> int:
        return self._max_gateways

    def __repr__(self) -> str:
        return (
            f"IntegrationGatewayManager("
            f"count={self.count}, "
            f"max={self._max_gateways})"
        )
