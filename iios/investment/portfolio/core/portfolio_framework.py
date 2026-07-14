"""iios/investment/portfolio/core/portfolio_framework.py

Institutional Portfolio Framework — main runtime orchestrator.

PortfolioFramework is the single entry-point for:
  • registering portfolio classes
  • creating, starting, monitoring, and archiving portfolio instances
  • dispatching and consuming framework events
  • publishing health and statistics

Every portfolio in IIOS must be managed through this framework.
No portfolio instance exists outside the framework lifecycle.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Type, TYPE_CHECKING

from iios.investment.portfolio.core.event_dispatcher import EventDispatcher
from iios.investment.portfolio.core.event_history import EventHistory
from iios.investment.portfolio.core.framework_context import (
    IntegrationRefs,
    PortfolioRuntimeContext,
)
from iios.investment.portfolio.core.portfolio_catalog import PortfolioCatalog
from iios.investment.portfolio.core.portfolio_events import (
    EventPriority,
    FrameworkStartedEvent,
    FrameworkStoppedEvent,
    PortfolioArchivedEvent,
    PortfolioEvent,
    PortfolioEventType,
    PortfolioFailedEvent,
    PortfolioInitializedEvent,
    PortfolioRegisteredEvent,
)
from iios.investment.portfolio.core.portfolio_factory import PortfolioFactory, FactoryResult
from iios.investment.portfolio.core.portfolio_lifecycle import PortfolioLifecycle
from iios.investment.portfolio.core.portfolio_loader import PortfolioLoader
from iios.investment.portfolio.core.portfolio_metadata import PortfolioMetadata
from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassEntry,
    PortfolioClassRegistry,
)
from iios.investment.portfolio.core.portfolio_session import SessionManager
from iios.investment.portfolio.core.portfolio_types import (
    FrameworkStatus,
    PortfolioCapability,
    PortfolioDomain,
    PortfolioLifecycleState,
)

if TYPE_CHECKING:
    from iios.investment.portfolio.core.base_portfolio import BasePortfolio

log = logging.getLogger(__name__)

_FRAMEWORK_VERSION = "1.0.0"


@dataclass(frozen=True)
class FrameworkStatistics:
    """Point-in-time statistics for the running framework."""

    framework_version:    str   = _FRAMEWORK_VERSION
    status:               str   = FrameworkStatus.STOPPED.value
    registered_classes:   int   = 0
    active_portfolios:    int   = 0
    total_portfolios:     int   = 0
    archived_portfolios:  int   = 0
    failed_portfolios:    int   = 0
    events_dispatched:    int   = 0
    uptime_seconds:       float = 0.0
    started_at:           Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_version":   self.framework_version,
            "status":              self.status,
            "registered_classes":  self.registered_classes,
            "active_portfolios":   self.active_portfolios,
            "total_portfolios":    self.total_portfolios,
            "archived_portfolios": self.archived_portfolios,
            "failed_portfolios":   self.failed_portfolios,
            "events_dispatched":   self.events_dispatched,
            "uptime_seconds":      self.uptime_seconds,
            "started_at":          self.started_at,
        }


class PortfolioFramework:
    """
    Institutional Portfolio Framework runtime.

    ─── Singleton usage ────────────────────────────────────────────────
    One framework instance per process is the recommended pattern.
    Use get_instance() for a module-level singleton.
    Alternatively, construct directly for testing.

    ─── Lifecycle ──────────────────────────────────────────────────────
        framework = PortfolioFramework()
        framework.start()

        framework.register_class(MyPortfolio, domain=PortfolioDomain.SWING)
        portfolio = framework.create_portfolio("MyPortfolio")
        framework.initialize_portfolio(portfolio.portfolio_id)
        ...
        framework.archive_portfolio(portfolio.portfolio_id)
        framework.stop()

    ─── Thread safety ──────────────────────────────────────────────────
    All public methods are thread-safe.
    """

    # ── Module-level singleton ─────────────────────────────────────────
    _instance:     Optional["PortfolioFramework"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PortfolioFramework":
        """Return the shared framework instance, creating it if needed."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton — for testing only."""
        with cls._instance_lock:
            cls._instance = None

    # ── Constructor ────────────────────────────────────────────────────

    def __init__(
        self,
        environment:  str                  = "production",
        enable_audit: bool                 = True,
        max_portfolios: int                = 10_000,
    ) -> None:
        self._lock           = threading.RLock()
        self._status         = FrameworkStatus.INITIALIZING
        self._started_at:    Optional[float] = None
        self._max_portfolios = max_portfolios

        # Infrastructure components
        self._class_registry  = PortfolioClassRegistry()
        self._event_history   = EventHistory(max_size=5_000)
        self._dispatcher      = EventDispatcher(history=self._event_history)
        self._session_manager = SessionManager()
        self._catalog         = PortfolioCatalog(self._class_registry)

        # Runtime context shared across all portfolio instances
        self._context = PortfolioRuntimeContext(
            environment    = environment,
            enable_audit   = enable_audit,
            enable_events  = True,
        )

        # Factory and loader wired to this registry + context
        self._factory = PortfolioFactory(self._class_registry, self._context)
        self._loader  = PortfolioLoader(self._class_registry)

        # Live portfolio instances: portfolio_id → BasePortfolio
        self._portfolios:  Dict[str, "BasePortfolio"] = {}

        # Counters
        self._total_created   = 0
        self._total_archived  = 0
        self._total_failed    = 0

        log.debug("PortfolioFramework constructed (env=%s)", environment)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Framework lifecycle
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def start(self) -> None:
        """Transition the framework to RUNNING status."""
        with self._lock:
            if self._status == FrameworkStatus.RUNNING:
                return
            self._started_at = time.time()
            self._status     = FrameworkStatus.RUNNING
        self._dispatch(FrameworkStartedEvent(framework_version=_FRAMEWORK_VERSION))
        log.info("PortfolioFramework started (v%s)", _FRAMEWORK_VERSION)

    def stop(self) -> None:
        """Transition the framework to STOPPED; archive all active portfolios."""
        with self._lock:
            if self._status == FrameworkStatus.STOPPED:
                return
            uptime = time.time() - (self._started_at or time.time())
            self._status = FrameworkStatus.STOPPED
        self._dispatch(FrameworkStoppedEvent(uptime_seconds=uptime))
        log.info("PortfolioFramework stopped (uptime=%.1fs)", uptime)

    def _assert_running(self) -> None:
        if not self._status.is_accepting:
            raise RuntimeError(
                f"PortfolioFramework is {self._status.value} — call start() first"
            )

    @property
    def status(self) -> FrameworkStatus:
        with self._lock:
            return self._status

    @property
    def is_running(self) -> bool:
        return self._status.is_accepting

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Class registration
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def register_class(
        self,
        cls:          Type["BasePortfolio"],
        *,
        class_name:   str                              = "",
        domain:       PortfolioDomain                  = PortfolioDomain.CUSTOM,
        version:      str                              = "1.0.0",
        description:  str                              = "",
        capabilities: Optional[frozenset]              = None,
        tags:         Optional[frozenset]              = None,
        overwrite:    bool                             = False,
    ) -> PortfolioClassEntry:
        """Register a portfolio class for factory use."""
        entry = self._class_registry.register(
            cls,
            class_name   = class_name,
            domain       = domain,
            version      = version,
            description  = description,
            capabilities = capabilities,
            tags         = tags,
            overwrite    = overwrite,
        )
        self._dispatch(
            PortfolioRegisteredEvent(
                portfolio_id = entry.class_name,
                domain       = domain.value,
                class_name   = entry.class_name,
            )
        )
        return entry

    def load_class(self, dotted_path: str, **kwargs: Any) -> PortfolioClassEntry:
        """Load and register a portfolio class from its dotted module path."""
        result = self._loader.load_class(dotted_path, **kwargs)
        if not result.success:
            raise RuntimeError(f"Failed to load {dotted_path!r}: {result.error}")
        return result.entry  # type: ignore[return-value]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Portfolio creation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_portfolio(
        self,
        class_name:   str,
        *,
        portfolio_id: str                             = "",
        name:         str                             = "",
        domain:       Optional[PortfolioDomain]       = None,
        metadata:     Optional[PortfolioMetadata]     = None,
        kwargs:       Optional[Dict[str, Any]]        = None,
    ) -> "BasePortfolio":
        """
        Create and register a portfolio instance.
        Does NOT start the lifecycle — call initialize_portfolio() next.
        """
        self._assert_running()
        with self._lock:
            if len(self._portfolios) >= self._max_portfolios:
                raise RuntimeError(
                    f"Portfolio capacity exceeded: {self._max_portfolios}"
                )

        result = self._factory.create(
            class_name   = class_name,
            portfolio_id = portfolio_id,
            name         = name,
            domain       = domain,
            metadata     = metadata,
            kwargs       = kwargs,
        )
        if not result.success:
            self._total_failed += 1
            raise RuntimeError(
                f"Failed to create portfolio (class={class_name!r}): {result.error}"
            )

        portfolio = result.portfolio  # type: ignore[assignment]
        with self._lock:
            self._portfolios[portfolio.portfolio_id] = portfolio
            self._total_created += 1

        log.info(
            "Portfolio created: %s (id=%s)", portfolio.name, portfolio.portfolio_id
        )
        return portfolio

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Portfolio lifecycle management
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def initialize_portfolio(self, portfolio_id: str) -> None:
        """Run initialize() → load_configuration() → marks INITIALIZED."""
        p = self._get_or_raise(portfolio_id)
        try:
            p._framework_initialize()
            self._dispatch(
                PortfolioInitializedEvent(
                    portfolio_id = portfolio_id,
                    profile_name = p.configuration.profile_name if p.configuration else "",
                    environment  = self._context.environment,
                )
            )
            log.info("Portfolio initialized: %s", portfolio_id)
        except Exception as exc:
            self._dispatch(PortfolioFailedEvent(
                portfolio_id = portfolio_id,
                error        = str(exc),
            ))
            raise

    def prepare_portfolio(self, portfolio_id: str) -> None:
        """Run validate_inputs() + prepare() → transitions to READY."""
        p = self._get_or_raise(portfolio_id)
        try:
            p._framework_ready()
        except Exception as exc:
            self._dispatch(PortfolioFailedEvent(
                portfolio_id = portfolio_id,
                error        = str(exc),
            ))
            raise

    def construct_portfolio(self, portfolio_id: str) -> None:
        """Run construct() + allocate() → transitions to CONSTRUCTED."""
        p = self._get_or_raise(portfolio_id)
        try:
            p._framework_construct()
            p._framework_activate()
            self._session_manager.open_session(portfolio_id)
        except Exception as exc:
            self._dispatch(PortfolioFailedEvent(
                portfolio_id = portfolio_id,
                error        = str(exc),
            ))
            raise

    def monitor_portfolio(self, portfolio_id: str) -> None:
        """Trigger a monitoring tick for the portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._framework_monitor()

    def evaluate_portfolio(self, portfolio_id: str) -> None:
        """Trigger an evaluation cycle for the portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._framework_evaluate()

    def rebalance_portfolio(self, portfolio_id: str) -> None:
        """Trigger a rebalance for the portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._framework_rebalance()
        session = self._session_manager.get_active_session(portfolio_id)
        if session:
            session.record_rebalance()

    def publish_portfolio(self, portfolio_id: str) -> None:
        """Trigger a publish cycle for the portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._framework_publish()

    def archive_portfolio(self, portfolio_id: str, reason: str = "") -> None:
        """Archive a portfolio (terminal — removes from active registry)."""
        p = self._get_or_raise(portfolio_id)
        p._framework_archive(reason=reason)
        with self._lock:
            self._portfolios.pop(portfolio_id, None)
            self._total_archived += 1
        self._session_manager.close_session(portfolio_id, reason=reason)
        self._dispatch(PortfolioArchivedEvent(
            portfolio_id = portfolio_id,
            reason       = reason,
        ))

    def pause_portfolio(self, portfolio_id: str, reason: str = "") -> None:
        """Pause an active portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._lifecycle.transition(
            PortfolioLifecycleState.PAUSED, reason=reason
        )

    def resume_portfolio(self, portfolio_id: str) -> None:
        """Resume a paused portfolio."""
        p = self._get_or_raise(portfolio_id)
        p._lifecycle.transition(PortfolioLifecycleState.ACTIVE)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Query API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_portfolio(self, portfolio_id: str) -> Optional["BasePortfolio"]:
        with self._lock:
            return self._portfolios.get(portfolio_id)

    def list_portfolios(self) -> List[str]:
        """Return IDs of all active portfolios."""
        with self._lock:
            return list(self._portfolios.keys())

    def portfolios_by_domain(self, domain: PortfolioDomain) -> List["BasePortfolio"]:
        with self._lock:
            return [
                p for p in self._portfolios.values()
                if p.metadata.domain == domain
            ]

    def portfolio_details(self, portfolio_id: str) -> dict[str, Any]:
        """Return info dict for a portfolio."""
        p = self._get_or_raise(portfolio_id)
        return p.get_info()

    def portfolio_state(self, portfolio_id: str) -> dict[str, Any]:
        """Return state snapshot dict for a portfolio."""
        p = self._get_or_raise(portfolio_id)
        return p.state_snapshot.to_dict()

    def portfolio_lifecycle(self, portfolio_id: str) -> dict[str, Any]:
        """Return lifecycle dict for a portfolio."""
        p = self._get_or_raise(portfolio_id)
        return p._lifecycle.to_dict()

    def portfolio_history(self, portfolio_id: str) -> list[dict]:
        """Return lifecycle transition history for a portfolio."""
        p = self._get_or_raise(portfolio_id)
        return [t.to_dict() for t in p._lifecycle.history()]

    def portfolio_capabilities(self, portfolio_id: str) -> List[str]:
        """Return capability list for a portfolio."""
        p = self._get_or_raise(portfolio_id)
        return sorted(c.value for c in p.capabilities())

    def portfolio_configuration(self, portfolio_id: str) -> Optional[dict[str, Any]]:
        """Return configuration dict if the portfolio has been initialized."""
        p = self._get_or_raise(portfolio_id)
        return p.configuration.to_dict() if p.configuration else None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Event API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def publish_event(self, event: PortfolioEvent) -> int:
        """Publish an arbitrary event through the framework dispatcher."""
        return self._dispatch(event)

    def subscribe_events(self, handler, *, event_types=None, portfolio_ids=None,
                         priority=None, name="") -> str:
        """Subscribe to framework events. Returns handler_id."""
        from iios.investment.portfolio.core.event_dispatcher import EventPriority as EP
        return self._dispatcher.subscribe(
            handler,
            event_types   = event_types,
            portfolio_ids = portfolio_ids,
            priority      = priority or EP.NORMAL,
            name          = name,
        )

    def unsubscribe_events(self, handler_id: str) -> bool:
        return self._dispatcher.unsubscribe(handler_id)

    @property
    def event_history(self) -> EventHistory:
        return self._event_history

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Integration configuration
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def configure_integrations(self, refs: IntegrationRefs) -> None:
        """Inject integration clients into the shared context."""
        self._context.integrations = refs
        log.info("Integration refs configured: %s", refs.to_dict())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Statistics / health
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def stats(self) -> FrameworkStatistics:
        """Return a point-in-time statistics snapshot."""
        with self._lock:
            uptime = (
                time.time() - self._started_at
                if self._started_at else 0.0
            )
            active = sum(
                1 for p in self._portfolios.values()
                if p._lifecycle.is_operational
            )
            return FrameworkStatistics(
                status              = self._status.value,
                registered_classes  = self._class_registry.active_count(),
                active_portfolios   = active,
                total_portfolios    = len(self._portfolios),
                archived_portfolios = self._total_archived,
                failed_portfolios   = self._total_failed,
                events_dispatched   = self._event_history.count(),
                uptime_seconds      = uptime,
                started_at          = self._started_at,
            )

    @property
    def catalog(self) -> PortfolioCatalog:
        return self._catalog

    @property
    def class_registry(self) -> PortfolioClassRegistry:
        return self._class_registry

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Internal helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_or_raise(self, portfolio_id: str) -> "BasePortfolio":
        with self._lock:
            p = self._portfolios.get(portfolio_id)
        if p is None:
            raise KeyError(f"Portfolio not found: {portfolio_id!r}")
        return p

    def _dispatch(self, event: PortfolioEvent) -> int:
        try:
            return self._dispatcher.dispatch(event)
        except Exception as exc:
            log.error("Event dispatch failed: %s", exc)
            return 0
