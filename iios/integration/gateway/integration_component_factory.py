"""
integration_component_factory.py — iios.integration.gateway
-------------------------------------------------------------
IntegrationComponentFactory — creates and returns ready-to-use instances
of the 5 integrated subsystem components.

The factory is the ONLY place in the gateway package that imports from
lifecycle, engine, policies, services, and snapshot.  All other gateway
modules reference components through the IntegrationComponentRegistry.

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import GatewayComponentType

_log = get_logger(__name__)


class IntegrationComponentFactory:
    """
    Creates default instances of the 5 subsystem components.

    Each method returns a fresh, initialized component instance.
    The gateway calls these during ``initialize()`` if components have
    not been injected by the caller.
    """

    # ─── individual component creators ────────────────────────────────

    @staticmethod
    def create_lifecycle() -> Any:
        """Create and return an IntegrationLifecycle instance."""
        from iios.integration.lifecycle import IntegrationLifecycle
        lc = IntegrationLifecycle()
        _log.info("IntegrationComponentFactory: lifecycle created")
        return lc

    @staticmethod
    def create_engine() -> Any:
        """Create and return an IntegrationEngine instance."""
        from iios.integration.engine import IntegrationEngine
        engine = IntegrationEngine()
        engine.initialize()
        _log.info("IntegrationComponentFactory: engine created + initialized")
        return engine

    @staticmethod
    def create_policy_engine() -> Any:
        """Create and return an IntegrationPolicyEngine instance."""
        from iios.integration.policies import IntegrationPolicyEngine
        pe = IntegrationPolicyEngine()
        pe.start()
        _log.info("IntegrationComponentFactory: policy engine created + started")
        return pe

    @staticmethod
    def create_connector_engine() -> Any:
        """Create and return a ConnectorEngine instance."""
        from iios.integration.services import ConnectorEngine
        ce = ConnectorEngine()
        _log.info("IntegrationComponentFactory: connector engine created")
        return ce

    @staticmethod
    def create_snapshot_registry() -> Any:
        """Create and return an IntegrationSnapshotRegistry instance."""
        from iios.integration.snapshot import IntegrationSnapshotRegistry
        sr = IntegrationSnapshotRegistry()
        _log.info("IntegrationComponentFactory: snapshot registry created")
        return sr

    # ─── bulk creation ────────────────────────────────────────────────

    @classmethod
    def create_all(cls) -> Dict[GatewayComponentType, Any]:
        """
        Create all 5 components and return them keyed by GatewayComponentType.
        """
        return {
            GatewayComponentType.LIFECYCLE: cls.create_lifecycle(),
            GatewayComponentType.ENGINE:    cls.create_engine(),
            GatewayComponentType.POLICIES:  cls.create_policy_engine(),
            GatewayComponentType.SERVICES:  cls.create_connector_engine(),
            GatewayComponentType.SNAPSHOT:  cls.create_snapshot_registry(),
        }
