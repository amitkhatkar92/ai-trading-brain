"""
iios/bootstrap/shutdown_manager.py
=====================================
Orchestrates an ordered, graceful shutdown of all IIOS components.

Components are registered with a shutdown priority (lower = shut down first).
Within the same priority, components are shut down in reverse registration
order (LIFO). Each component gets a configurable timeout; if it exceeds
the timeout, its shutdown is abandoned and the next component proceeds.

Architecture Reference: IIOS-BSS-001 §5 Shutdown Sequence
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .startup_state import ShutdownError
from .system_state import get_system_state

__all__ = [
    "ShutdownManager",
    "ShutdownComponent",
    "ShutdownReport",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Component descriptor
# ---------------------------------------------------------------------------


@dataclass
class ShutdownComponent:
    """A component that must be shut down during system teardown."""

    name: str
    handler: Callable[[], None]         # Zero-argument shutdown callable
    priority: int = 50                  # Lower = shut down first (0-100)
    timeout_seconds: float = 10.0
    critical: bool = False              # If True, failure raises ShutdownError
    instance: Optional[Any] = None      # Reference to the component (informational)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class ShutdownReport:
    """Summary of the shutdown sequence."""

    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None
    components_ok: list[str] = field(default_factory=list)
    components_timeout: list[str] = field(default_factory=list)
    components_failed: list[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        end = self.completed_at or time.monotonic()
        return (end - self.started_at) * 1000.0

    @property
    def clean(self) -> bool:
        return len(self.components_timeout) == 0 and len(self.components_failed) == 0


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class ShutdownManager:
    """Manages graceful shutdown of all registered IIOS components.

    Shutdown order:
      1. Components sorted by ``priority`` ascending (lower = first)
      2. Within same priority: LIFO (last registered = first to shut down)

    Typical usage::

        mgr = ShutdownManager()
        mgr.register("order_manager", order_manager.shutdown, priority=10)
        mgr.register("feed_manager", feed_mgr.close, priority=20)
        mgr.register("telegram_bot", bot.stop, priority=30)
        mgr.register("database", db.close, priority=90)
        report = mgr.run()
    """

    # Standard shutdown priorities
    PRIORITY_TRADING    = 10    # Stop order routing first
    PRIORITY_MONITORING = 20    # Stop monitoring agents
    PRIORITY_FEEDS      = 30    # Close market data feeds
    PRIORITY_BOTS       = 40    # Stop notification bots
    PRIORITY_SERVICES   = 50    # General services
    PRIORITY_SCHEDULER  = 60    # Task scheduler
    PRIORITY_DATABASE   = 90    # Database last (flush pending writes)
    PRIORITY_LOGGING    = 99    # Logging very last

    def __init__(self) -> None:
        self._components: list[ShutdownComponent] = []
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        handler: Callable[[], None],
        priority: int = 50,
        timeout_seconds: float = 10.0,
        critical: bool = False,
        instance: Optional[Any] = None,
    ) -> None:
        """Register a component for shutdown."""
        with self._lock:
            component = ShutdownComponent(
                name=name,
                handler=handler,
                priority=priority,
                timeout_seconds=timeout_seconds,
                critical=critical,
                instance=instance,
            )
            self._components.append(component)
            logger.debug("ShutdownManager: registered %r (priority=%d)", name, priority)

    def register_component(self, component: ShutdownComponent) -> None:
        """Register a pre-built ``ShutdownComponent``."""
        with self._lock:
            self._components.append(component)

    # ─────────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> ShutdownReport:
        """Execute the full shutdown sequence. Returns a report."""
        report = ShutdownReport()
        ordered = self._build_order()

        logger.info(
            "ShutdownManager: shutting down %d components", len(ordered)
        )

        for component in ordered:
            self._shutdown_component(component, report)

        report.completed_at = time.monotonic()
        level = "CLEAN" if report.clean else "WITH ISSUES"
        logger.info(
            "ShutdownManager: %s in %.1f ms (ok=%d, timeout=%d, failed=%d)",
            level,
            report.duration_ms,
            len(report.components_ok),
            len(report.components_timeout),
            len(report.components_failed),
        )
        return report

    def run_component(self, name: str) -> bool:
        """Shut down a single registered component by name. Returns True if ok."""
        with self._lock:
            matches = [c for c in self._components if c.name == name]
        if not matches:
            logger.warning("ShutdownManager: no component named %r", name)
            return False
        report = ShutdownReport()
        self._shutdown_component(matches[0], report)
        return name in report.components_ok

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_order(self) -> list[ShutdownComponent]:
        """Sort components: ascending priority, then LIFO within priority."""
        with self._lock:
            components = list(self._components)
        # Stable sort by priority; reversed within each priority group via enumerate
        indexed = list(enumerate(components))
        indexed.sort(key=lambda t: (t[1].priority, -t[0]))
        return [c for _, c in indexed]

    def _shutdown_component(
        self, component: ShutdownComponent, report: ShutdownReport
    ) -> None:
        logger.info(
            "Shutting down: %s (priority=%d, timeout=%.1fs)",
            component.name, component.priority, component.timeout_seconds,
        )
        t0 = time.monotonic()
        result_holder: dict[str, Any] = {"error": None, "done": False}

        def _run() -> None:
            try:
                component.handler()
                result_holder["done"] = True
            except Exception as exc:  # noqa: BLE001
                result_holder["error"] = exc

        thread = threading.Thread(target=_run, name=f"shutdown-{component.name}", daemon=True)
        thread.start()
        thread.join(timeout=component.timeout_seconds)

        elapsed = (time.monotonic() - t0) * 1000.0

        if thread.is_alive():
            # Timeout
            logger.warning(
                "Shutdown timeout: %s exceeded %.1f s (%.0f ms elapsed)",
                component.name, component.timeout_seconds, elapsed,
            )
            report.components_timeout.append(component.name)
            if component.critical:
                raise ShutdownError(
                    f"Critical component {component.name!r} timed out during shutdown"
                )
        elif result_holder["error"] is not None:
            error = result_holder["error"]
            logger.error(
                "Shutdown error: %s — %s (%.0f ms)", component.name, error, elapsed
            )
            report.components_failed.append(component.name)
            if component.critical:
                raise ShutdownError(
                    f"Critical component {component.name!r} raised during shutdown: {error}"
                )
        else:
            logger.debug("Shutdown ok: %s (%.0f ms)", component.name, elapsed)
            report.components_ok.append(component.name)
