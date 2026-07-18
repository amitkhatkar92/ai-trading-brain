"""iios/execution/monitoring/integration/monitoring_component_factory.py
==================================================
ComponentFactory — creates and assembles the sub-component instances
used by the integration engine.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ComponentType,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    FACTORY_SYSTEM_ID,
    VERSION,
)

_log = get_logger(__name__)


class ComponentFactory(LifecycleAwareMixin):
    """
    Factory that instantiates the three core sub-components.

    Sub-components created:
    - MonitoringLifecycle  (M1)
    - MetricsEngine        (M3)
    - AlertManager         (M4)

    Each sub-component is created fresh; the factory does NOT start them —
    that is the responsibility of the integration engine.
    """

    def _on_start(self) -> None:
        _log.info("ComponentFactory started.", system_id=FACTORY_SYSTEM_ID, version=VERSION)

    def _on_stop(self) -> None:
        _log.info("ComponentFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    # ── Component creation ────────────────────────────────────────────────────

    def create_lifecycle(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ):  # -> MonitoringLifecycle
        """Create a new MonitoringLifecycle instance (M1)."""
        from iios.execution.monitoring.lifecycle import MonitoringLifecycle
        _log.info(
            "Creating MonitoringLifecycle.",
            component_type=ComponentType.LIFECYCLE.value,
        )
        return MonitoringLifecycle(
            max_sessions=max_sessions,
            max_history=max_history,
        )

    def create_metrics_engine(
        self,
        max_points_per_series: int = 10_000,
        max_snapshots:         int = 50_000,
        max_history:           int = DEFAULT_MAX_HISTORY,
    ):  # -> MetricsEngine
        """Create a new MetricsEngine instance (M3)."""
        from iios.execution.monitoring.metrics import MetricsEngine
        _log.info(
            "Creating MetricsEngine.",
            component_type=ComponentType.METRICS_ENGINE.value,
        )
        return MetricsEngine(
            max_points_per_series=max_points_per_series,
            max_snapshots=max_snapshots,
            max_history=max_history,
        )

    def create_alert_manager(
        self,
        max_alerts:         int   = 10_000,
        max_history:        int   = DEFAULT_MAX_HISTORY,
        escalation_age_sec: float = 300.0,
    ):  # -> AlertManager
        """Create a new AlertManager instance (M4)."""
        from iios.execution.monitoring.alerts import AlertManager
        _log.info(
            "Creating AlertManager.",
            component_type=ComponentType.ALERT_MANAGER.value,
        )
        return AlertManager(
            max_alerts=max_alerts,
            max_history=max_history,
            escalation_age_sec=escalation_age_sec,
        )
