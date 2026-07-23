"""
risk_component_factory.py — iios.risk.integration
===================================================
Factory for creating default Risk Intelligence subsystem components.

Creates and wires together M1-M5 subsystem components for injection
into the RiskComponentRegistry.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

from .constants import (
    COMPONENT_ASSESSMENT,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICIES,
    COMPONENT_SNAPSHOT,
    ComponentStatus,
    VERSION,
)
from .risk_component_registry import RiskComponentRegistry

_log = get_logger(__name__)


class RiskComponentFactory:
    """
    Factory that creates default M1-M5 subsystem component instances
    and populates a :class:`~.risk_component_registry.RiskComponentRegistry`.

    Each subsystem is imported lazily so that missing optional dependencies
    do not crash the factory at import time.

    Usage::

        factory  = RiskComponentFactory()
        registry = factory.create_default_registry()
    """

    def __init__(self, environment: str = "production") -> None:
        self._environment = environment

    def create_default_registry(self) -> RiskComponentRegistry:
        """
        Build a fully populated registry with one default instance of each
        M1-M5 subsystem component.

        Components that fail to instantiate are registered as UNAVAILABLE
        so the integration engine degrades gracefully.
        """
        registry = RiskComponentRegistry()
        self._register_lifecycle(registry)
        self._register_engine(registry)
        self._register_policies(registry)
        self._register_assessment(registry)
        self._register_snapshot(registry)
        return registry

    # ------------------------------------------------------------------
    # Component creation helpers
    # ------------------------------------------------------------------

    def _register_lifecycle(self, registry: RiskComponentRegistry) -> None:
        try:
            from iios.risk.lifecycle import RiskLifecycle
            component = RiskLifecycle()
            registry.register(COMPONENT_LIFECYCLE, component,
                               status=ComponentStatus.AVAILABLE)
            _log.debug("RiskComponentFactory: registered risk_lifecycle")
        except Exception as exc:
            _log.warning(f"RiskComponentFactory: risk_lifecycle unavailable — {exc}")
            registry.register(COMPONENT_LIFECYCLE, None,
                               status=ComponentStatus.UNAVAILABLE)

    def _register_engine(self, registry: RiskComponentRegistry) -> None:
        try:
            from iios.risk.engine import RiskEngine
            component = RiskEngine()
            registry.register(COMPONENT_ENGINE, component,
                               status=ComponentStatus.AVAILABLE)
            _log.debug("RiskComponentFactory: registered risk_engine")
        except Exception as exc:
            _log.warning(f"RiskComponentFactory: risk_engine unavailable — {exc}")
            registry.register(COMPONENT_ENGINE, None,
                               status=ComponentStatus.UNAVAILABLE)

    def _register_policies(self, registry: RiskComponentRegistry) -> None:
        try:
            from iios.risk.policies import RiskPolicyEngine
            component = RiskPolicyEngine()
            registry.register(COMPONENT_POLICIES, component,
                               status=ComponentStatus.AVAILABLE)
            _log.debug("RiskComponentFactory: registered risk_policies")
        except Exception as exc:
            _log.warning(f"RiskComponentFactory: risk_policies unavailable — {exc}")
            registry.register(COMPONENT_POLICIES, None,
                               status=ComponentStatus.UNAVAILABLE)

    def _register_assessment(self, registry: RiskComponentRegistry) -> None:
        try:
            from iios.risk.assessment import RiskAssessmentEngine
            component = RiskAssessmentEngine()
            registry.register(COMPONENT_ASSESSMENT, component,
                               status=ComponentStatus.AVAILABLE)
            _log.debug("RiskComponentFactory: registered risk_assessment")
        except Exception as exc:
            _log.warning(f"RiskComponentFactory: risk_assessment unavailable — {exc}")
            registry.register(COMPONENT_ASSESSMENT, None,
                               status=ComponentStatus.UNAVAILABLE)

    def _register_snapshot(self, registry: RiskComponentRegistry) -> None:
        try:
            from iios.risk.snapshot import RiskSnapshotFactory
            component = RiskSnapshotFactory(environment=self._environment)
            registry.register(COMPONENT_SNAPSHOT, component,
                               status=ComponentStatus.AVAILABLE)
            _log.debug("RiskComponentFactory: registered risk_snapshot")
        except Exception as exc:
            _log.warning(f"RiskComponentFactory: risk_snapshot unavailable — {exc}")
            registry.register(COMPONENT_SNAPSHOT, None,
                               status=ComponentStatus.UNAVAILABLE)

    def component_versions(self) -> Dict[str, str]:
        """Return a best-effort dict of component → version strings."""
        versions: Dict[str, str] = {}
        for mod, key in [
            ("iios.risk.lifecycle.constants",   COMPONENT_LIFECYCLE),
            ("iios.risk.engine.constants",      COMPONENT_ENGINE),
            ("iios.risk.policies.constants",    COMPONENT_POLICIES),
            ("iios.risk.assessment.constants",  COMPONENT_ASSESSMENT),
            ("iios.risk.snapshot.constants",    COMPONENT_SNAPSHOT),
        ]:
            try:
                import importlib
                m = importlib.import_module(mod)
                versions[key] = getattr(m, "VERSION", VERSION)
            except Exception:
                versions[key] = "unknown"
        return versions
