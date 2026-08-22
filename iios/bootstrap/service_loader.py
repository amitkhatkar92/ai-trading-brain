"""
iios/bootstrap/service_loader.py
===================================
Loads and registers IIOS infrastructure services during bootstrap.

For each declared service, ``ServiceLoader`` attempts to acquire the
singleton instance via the canonical factory function (never by direct
instantiation). Failures are recorded and optionally rethrown.

The four protected singletons are handled specially:
  - get_performance_tracker()    learning_system.strategy_performance_tracker
  - get_regime_strategy_map()    meta_learning.regime_strategy_map
  - get_telegram_bot()           notifications.telegram_bot
  - get_feed_manager()           data_feeds.data_feed_manager

Architecture Reference: IIOS-BSS-001 Stages 21-25 (Infrastructure Registration)
Foundation: IIOS-FCR-001 (CERTIFIED)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

__all__ = [
    "ServiceLoader",
    "ServiceSpec",
    "ServiceTier",
    "ServiceRegistry",
    "ServiceReport",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service tiers
# ---------------------------------------------------------------------------


class ServiceTier(Enum):
    CORE        = "core"        # Must load; failure aborts startup
    STANDARD    = "standard"    # Should load; failure = degraded mode
    OPTIONAL    = "optional"    # Nice to have; failure = feature unavailable


# ---------------------------------------------------------------------------
# Service specification
# ---------------------------------------------------------------------------


@dataclass
class ServiceSpec:
    """Descriptor for a single IIOS service."""

    name: str                           # Logical service name (key in registry)
    factory_module: str                 # Module path for the factory function
    factory_function: str               # Name of the factory function
    tier: ServiceTier = ServiceTier.STANDARD
    description: str = ""
    condition_env: str = ""             # Optional env var that gates loading (e.g. "IIOS_ENABLE_TELEGRAM")
    condition_value: str = "true"       # Expected value to load (default: "true")


# Declared services — all loaded via factory functions, never direct instantiation
_SERVICE_SPECS: list[ServiceSpec] = [
    ServiceSpec(
        name="feed_manager",
        factory_module="data_feeds.data_feed_manager",
        factory_function="get_feed_manager",
        tier=ServiceTier.CORE,
        description="Primary/fallback market data feed (Dhan → yfinance)",
    ),
    ServiceSpec(
        name="performance_tracker",
        factory_module="learning_system.strategy_performance_tracker",
        factory_function="get_performance_tracker",
        tier=ServiceTier.STANDARD,
        description="Strategy win-rate tracker and auto-disable watchdog",
    ),
    ServiceSpec(
        name="regime_strategy_map",
        factory_module="meta_learning.regime_strategy_map",
        factory_function="get_regime_strategy_map",
        tier=ServiceTier.STANDARD,
        description="Regime → strategy weight learning map (MetaLearning Layer 3)",
    ),
    ServiceSpec(
        name="telegram_bot",
        factory_module="notifications.telegram_bot",
        factory_function="get_telegram_bot",
        tier=ServiceTier.OPTIONAL,
        description="Telegram operator bot (13 IIOS commands)",
        condition_env="IIOS_ENABLE_TELEGRAM",
        condition_value="true",
    ),
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ServiceRegistry:
    """Holds named service instances acquired during bootstrap."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._loaded_at: dict[str, float] = {}

    def register(self, name: str, instance: Any) -> None:
        if name in self._services:
            logger.warning("ServiceRegistry: overwriting existing service %r", name)
        self._services[name] = instance
        self._loaded_at[name] = time.monotonic()
        logger.debug("Service registered: %s (%s)", name, type(instance).__name__)

    def get(self, name: str, default: Any = None) -> Any:
        return self._services.get(name, default)

    def has(self, name: str) -> bool:
        return name in self._services

    def names(self) -> list[str]:
        return list(self._services.keys())

    def all(self) -> dict[str, Any]:
        return dict(self._services)


# ---------------------------------------------------------------------------
# Load result
# ---------------------------------------------------------------------------


@dataclass
class _ServiceLoadResult:
    spec: ServiceSpec
    instance: Optional[Any] = None
    load_time_ms: float = 0.0
    error: Optional[Exception] = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def succeeded(self) -> bool:
        return self.instance is not None or self.skipped


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class ServiceReport:
    """Summary of service loading during bootstrap."""

    results: list[_ServiceLoadResult] = field(default_factory=list)
    registry: ServiceRegistry = field(default_factory=ServiceRegistry)

    @property
    def loaded(self) -> list[str]:
        return [r.spec.name for r in self.results if r.instance is not None]

    @property
    def skipped(self) -> list[str]:
        return [r.spec.name for r in self.results if r.skipped]

    @property
    def failed(self) -> list[str]:
        return [r.spec.name for r in self.results if r.error is not None]

    @property
    def passed(self) -> bool:
        """True if all CORE services loaded successfully."""
        for r in self.results:
            if r.spec.tier == ServiceTier.CORE and r.error is not None:
                return False
        return True

    def summary(self) -> str:
        return (
            f"loaded={len(self.loaded)}, skipped={len(self.skipped)}, "
            f"failed={len(self.failed)}"
        )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class ServiceLoader:
    """Loads IIOS services via their canonical factory functions.

    Services are looked up by their ``factory_module.factory_function``
    path using importlib. This preserves singleton guarantees — the factory
    functions (``get_feed_manager``, etc.) are the only authorised entry
    points.
    """

    def __init__(
        self,
        env_vars: Optional[dict[str, Any]] = None,
        extra_specs: Optional[list[ServiceSpec]] = None,
    ) -> None:
        self._env: dict[str, Any] = env_vars or {}
        self._specs = list(_SERVICE_SPECS)
        if extra_specs:
            self._specs.extend(extra_specs)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def load_all(self) -> ServiceReport:
        """Load all declared services and return a report."""
        report = ServiceReport()

        for spec in self._specs:
            result = self._load_service(spec)
            report.results.append(result)

            if result.instance is not None:
                report.registry.register(spec.name, result.instance)
            elif result.skipped:
                logger.debug("Service skipped: %s (%s)", spec.name, result.skip_reason)
            else:
                if spec.tier == ServiceTier.CORE:
                    logger.error(
                        "CORE service load FAILED: %s — %s", spec.name, result.error
                    )
                else:
                    logger.warning(
                        "Service load failed (non-critical): %s — %s",
                        spec.name,
                        result.error,
                    )

        logger.info("ServiceLoader: %s", report.summary())
        return report

    def load_service(self, name: str) -> Optional[Any]:
        """Load a single service by logical name. Returns instance or None."""
        for spec in self._specs:
            if spec.name == name:
                result = self._load_service(spec)
                return result.instance
        logger.warning("ServiceLoader: no spec found for service %r", name)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _load_service(self, spec: ServiceSpec) -> _ServiceLoadResult:
        result = _ServiceLoadResult(spec=spec)

        # Condition gate
        if spec.condition_env:
            env_val = str(self._env.get(spec.condition_env, "")).lower()
            expected = spec.condition_value.lower()
            if env_val != expected:
                result.skipped = True
                result.skip_reason = (
                    f"{spec.condition_env}={env_val!r} (expected {expected!r})"
                )
                return result

        t0 = time.monotonic()
        try:
            import importlib  # noqa: PLC0415
            module = importlib.import_module(spec.factory_module)
            factory: Callable[[], Any] = getattr(module, spec.factory_function)
            instance = factory()
            result.instance = instance
            result.load_time_ms = (time.monotonic() - t0) * 1000.0
            logger.debug(
                "Service loaded: %s via %s.%s (%.1f ms)",
                spec.name,
                spec.factory_module,
                spec.factory_function,
                result.load_time_ms,
            )
        except ImportError as exc:
            result.error = exc
            result.load_time_ms = (time.monotonic() - t0) * 1000.0
            logger.debug(
                "Service %r factory module not available: %s.%s — %s",
                spec.name, spec.factory_module, spec.factory_function, exc,
            )
        except Exception as exc:  # noqa: BLE001
            result.error = exc
            result.load_time_ms = (time.monotonic() - t0) * 1000.0

        return result
