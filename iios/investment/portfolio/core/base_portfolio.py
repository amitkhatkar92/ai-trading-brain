"""iios/investment/portfolio/core/base_portfolio.py

Abstract base class for all portfolios managed by the Institutional
Portfolio Framework.  Every portfolio — long-term, intraday, options,
crypto, etc. — must inherit from BasePortfolio.

The framework calls lifecycle methods in strict order.  Portfolios
implement the abstract methods; the framework handles state transitions,
event dispatch, and error recovery.
"""
from __future__ import annotations

import abc
import logging
import threading
import time
import uuid
from typing import Any, Optional

from iios.investment.portfolio.core.framework_context import PortfolioRuntimeContext
from iios.investment.portfolio.core.portfolio_configuration import PortfolioConfiguration
from iios.investment.portfolio.core.portfolio_lifecycle import LifecycleError, PortfolioLifecycle
from iios.investment.portfolio.core.portfolio_metadata import PortfolioMetadata
from iios.investment.portfolio.core.portfolio_state import PortfolioStateStore, PortfolioStateSnapshot
from iios.investment.portfolio.core.portfolio_types import PortfolioCapability, PortfolioLifecycleState

log = logging.getLogger(__name__)


class BasePortfolio(abc.ABC):
    """
    Abstract base for all IIOS-managed portfolios.

    ─── Framework contract ────────────────────────────────────────────
    The framework calls lifecycle methods in this sequence:

        initialize()            → transitions to INITIALIZED
        load_configuration()    → loads config, marks configured
        validate_inputs()       → validates config & state
        prepare()               → pre-construction setup
        construct()             → builds initial positions
        allocate()              → initial capital allocation
        [ACTIVE]
        monitor()               → continuous monitoring
        evaluate()              → periodic performance evaluation
        rebalance()             → triggered rebalancing
        publish()               → publish state to downstream consumers
        archive()               → graceful shutdown, store to history

    ─── Subclass responsibilities ──────────────────────────────────────
    Implement every abstract method.
    Never mutate self._lifecycle, self._state, or self._context directly
    — use the provided property accessors or call super() methods.

    ─── What this class does NOT do ────────────────────────────────────
    It does NOT implement allocation algorithms.
    It does NOT optimize portfolios.
    It does NOT rebalance with specific logic.
    It does NOT calculate performance metrics.
    """

    def __init__(
        self,
        metadata:  PortfolioMetadata,
        context:   PortfolioRuntimeContext,
    ) -> None:
        self._metadata   = metadata
        self._context    = context
        self._config:    Optional[PortfolioConfiguration] = None
        self._state      = PortfolioStateStore(metadata.portfolio_id)
        self._lifecycle  = PortfolioLifecycle(metadata.portfolio_id)
        self._lock       = threading.RLock()

        log.debug("BasePortfolio created: %s (%s)", metadata.name, metadata.portfolio_id)

    # ------------------------------------------------------------------
    # Identity (read-only properties)
    # ------------------------------------------------------------------

    @property
    def portfolio_id(self) -> str:
        return self._metadata.portfolio_id

    @property
    def name(self) -> str:
        return self._metadata.name

    @property
    def metadata(self) -> PortfolioMetadata:
        return self._metadata

    @property
    def configuration(self) -> Optional[PortfolioConfiguration]:
        return self._config

    @property
    def lifecycle_state(self) -> PortfolioLifecycleState:
        return self._lifecycle.current_state

    @property
    def state_snapshot(self) -> PortfolioStateSnapshot:
        return self._state.snapshot()

    @property
    def context(self) -> PortfolioRuntimeContext:
        return self._context

    # ------------------------------------------------------------------
    # Capability inspection
    # ------------------------------------------------------------------

    def has_capability(self, cap: PortfolioCapability) -> bool:
        return self._metadata.has_capability(cap)

    def capabilities(self) -> frozenset:
        return self._metadata.capabilities

    # ------------------------------------------------------------------
    # Abstract lifecycle methods — MUST be implemented by every portfolio
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def initialize(self) -> None:
        """
        Perform one-time initialisation for this portfolio instance.
        Called once before load_configuration().
        Must NOT load data or connect to external systems here.
        """

    @abc.abstractmethod
    def load_configuration(self) -> PortfolioConfiguration:
        """
        Load and return the validated configuration for this portfolio.
        The framework stores the result via self._config.
        """

    @abc.abstractmethod
    def validate_inputs(self) -> bool:
        """
        Validate that all required configuration, data, and preconditions
        are met.  Return True if valid.
        Raise ValueError with a descriptive message if invalid.
        """

    @abc.abstractmethod
    def prepare(self) -> None:
        """
        Pre-construction preparation.  Typically: warm caches, fetch
        universe, load benchmarks, resolve dependencies.
        Called once before construct().
        """

    @abc.abstractmethod
    def construct(self) -> None:
        """
        Build the initial portfolio structure.  This may include defining
        the target universe, asset class buckets, and initial allocations.
        Does NOT execute trades — defines the intended structure.
        """

    @abc.abstractmethod
    def allocate(self) -> None:
        """
        Perform initial capital allocation across the constructed portfolio.
        Framework calls this once, immediately after construct().
        Allocation algorithms are implemented here by subclasses.
        """

    @abc.abstractmethod
    def rebalance(self) -> None:
        """
        Execute a rebalancing cycle.  Called by the framework when the
        configured rebalancing trigger fires.  Must NOT make external
        decisions — receive them as inputs from the intelligence layer.
        """

    @abc.abstractmethod
    def evaluate(self) -> None:
        """
        Perform a periodic evaluation of portfolio state.  May update
        internal metrics, check thresholds, or prepare reports.
        Does NOT modify positions.
        """

    @abc.abstractmethod
    def monitor(self) -> None:
        """
        Continuous monitoring tick.  Called repeatedly while ACTIVE/MONITORING.
        Must be fast (< 200 ms) — block if necessary only with explicit timeout.
        Check risk limits, data freshness, position validity.
        """

    @abc.abstractmethod
    def publish(self) -> None:
        """
        Publish current portfolio state to downstream consumers:
        audit layer, execution layer, monitoring dashboard, knowledge layer.
        """

    @abc.abstractmethod
    def archive(self) -> None:
        """
        Graceful shutdown.  Flush pending operations, persist final state,
        release resources.  After archive(), no lifecycle method will be
        called again.
        """

    # ------------------------------------------------------------------
    # Concrete framework hooks (called by the framework, not the subclass)
    # ------------------------------------------------------------------

    def _framework_initialize(self) -> None:
        """Framework entry point for initialization. Wraps initialize()."""
        with self._lock:
            self._lifecycle.transition(PortfolioLifecycleState.INITIALIZED)
            try:
                self.initialize()
                self._state.record_initialize()
                cfg = self.load_configuration()
                self._config = cfg
                self._state.mark_configured()
                log.info("Portfolio initialized: %s", self.portfolio_id)
            except Exception as exc:
                self._state.record_error(str(exc))
                self._lifecycle.force_to(PortfolioLifecycleState.FAILED, reason=str(exc))
                raise

    def _framework_ready(self) -> None:
        """Framework entry point for validation and preparation."""
        with self._lock:
            try:
                valid = self.validate_inputs()
                if not valid:
                    raise ValueError("validate_inputs() returned False")
                self._state.mark_validated()
                self.prepare()
                self._state.mark_prepared()
                self._lifecycle.transition(PortfolioLifecycleState.READY)
            except Exception as exc:
                self._state.record_error(str(exc))
                self._lifecycle.force_to(PortfolioLifecycleState.FAILED, reason=str(exc))
                raise

    def _framework_construct(self) -> None:
        """Framework entry point for construction and initial allocation."""
        with self._lock:
            self._lifecycle.transition(PortfolioLifecycleState.CONSTRUCTED)
            try:
                self.construct()
                self._state.mark_constructed()
                self.allocate()
                self._state.record_allocate()
                log.info("Portfolio constructed: %s", self.portfolio_id)
            except Exception as exc:
                self._state.record_error(str(exc))
                self._lifecycle.force_to(PortfolioLifecycleState.FAILED, reason=str(exc))
                raise

    def _framework_activate(self) -> None:
        """Framework entry point to transition to ACTIVE."""
        with self._lock:
            self._lifecycle.transition(PortfolioLifecycleState.ACTIVE)

    def _framework_monitor(self) -> None:
        """Framework monitoring tick."""
        try:
            self.monitor()
            self._state.record_monitor()
        except Exception as exc:
            self._state.record_error(str(exc))
            log.error("monitor() failed for %s: %s", self.portfolio_id, exc)

    def _framework_evaluate(self) -> None:
        """Framework evaluation tick."""
        try:
            self.evaluate()
            self._state.record_evaluate()
        except Exception as exc:
            self._state.record_error(str(exc))
            log.error("evaluate() failed for %s: %s", self.portfolio_id, exc)

    def _framework_rebalance(self, trigger: str = "framework") -> None:
        """Framework rebalance trigger."""
        with self._lock:
            self._lifecycle.transition(PortfolioLifecycleState.REBALANCED)
        try:
            self.rebalance()
            self._state.record_rebalance()
            with self._lock:
                self._lifecycle.transition(PortfolioLifecycleState.ACTIVE)
        except Exception as exc:
            self._state.record_error(str(exc))
            self._lifecycle.force_to(PortfolioLifecycleState.FAILED, reason=str(exc))
            raise

    def _framework_publish(self) -> None:
        """Framework publish hook."""
        try:
            self.publish()
            self._state.record_publish()
        except Exception as exc:
            self._state.record_error(str(exc))
            log.error("publish() failed for %s: %s", self.portfolio_id, exc)

    def _framework_archive(self, reason: str = "") -> None:
        """Framework archive — terminal lifecycle step."""
        with self._lock:
            self._lifecycle.transition(
                PortfolioLifecycleState.ARCHIVED, reason=reason
            )
        try:
            self.archive()
            log.info("Portfolio archived: %s (reason=%s)", self.portfolio_id, reason)
        except Exception as exc:
            self._state.record_error(str(exc))
            log.error("archive() failed for %s: %s", self.portfolio_id, exc)

    # ------------------------------------------------------------------
    # Info / diagnostics
    # ------------------------------------------------------------------

    def get_info(self) -> dict[str, Any]:
        return {
            "portfolio_id":   self.portfolio_id,
            "name":           self.name,
            "domain":         self._metadata.domain.value,
            "lifecycle_state":self.lifecycle_state.value,
            "is_operational": self._lifecycle.is_operational,
            "version":        self._state.version,
            "capabilities":   sorted(c.value for c in self._metadata.capabilities),
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.portfolio_id!r} "
            f"name={self.name!r} state={self.lifecycle_state.value!r}>"
        )
