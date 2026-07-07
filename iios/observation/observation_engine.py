"""
iios/observation/observation_engine.py
=======================================
ObservationEngine — master lifecycle controller for the Observation Layer.

The ObservationEngine is the single authoritative entry point for every
external input entering IIOS.  It initialises all subsystems, manages
startup/shutdown, and exposes the top-level observation API.

Usage::

    engine = get_observation_engine()
    engine.initialize()

    obs = engine.observe(
        content    = {"symbol": "^NSEI", "close": 24350.0},
        obs_type   = ObservationType.MARKET_DATA,
        title      = "NIFTY 50 close",
        instrument = "NIFTY",
    )
    # obs.status == ObservationStatus.ACCEPTED (or REJECTED)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .observation_constants import (
    ObservationDomain,
    ObservationPriority,
    ObservationSource,
    ObservationStatus,
    ObservationType,
    OBSERVATION_NAMESPACE,
    SYSTEM_OBSERVER,
)
from .observation_exceptions import (
    ObservationEngineError,
    ObservationEngineNotInitializedError,
)
from .models.observation            import Observation
from .models.observation_statistics import ObservationStatistics
from .observation_factory           import ObservationFactory, get_observation_factory
from .observation_manager           import ObservationManager, get_observation_manager
from .observation_context           import ObservationContext, get_observation_context
from .observation_registry          import ObservationRegistry, get_observation_registry
from .repositories.observation_repository import (
    ObservationRepository,
    get_observation_repository,
    reset_observation_repository,
)
from .repositories.observation_storage import (
    get_observation_storage,
    reset_observation_storage,
)
from .repositories.observation_cache import (
    get_observation_cache,
    reset_observation_cache,
)
from .pipeline.observation_pipeline import (
    ObservationPipeline,
    get_observation_pipeline,
    reset_observation_pipeline,
)
from .storage.observation_store import (
    get_observation_store,
    reset_observation_store,
)
from .validators.observation_validator   import get_observation_validator, reset_observation_validator
from .classifiers.observation_classifier import get_observation_classifier, reset_observation_classifier
from .enrichment.observation_enricher    import get_observation_enricher, reset_observation_enricher
from .quality.observation_quality        import get_quality_assessor, reset_quality_assessor
from .repositories.observation_query     import ObservationQuery

__all__ = [
    "ObservationEngine",
    "get_observation_engine",
    "reset_observation_engine",
]

_LOG  = logging.getLogger("iios.observation.engine")
_lock = threading.Lock()
_engine: Optional["ObservationEngine"] = None


class ObservationEngine:
    """Master controller for the Observation Layer.

    Lifecycle::

        engine = get_observation_engine()
        engine.initialize()
        # … use engine …
        engine.shutdown()
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._initialized = False
        self._startup_at: Optional[float] = None

        # Subsystem references (populated by initialize())
        self._factory:   Optional[ObservationFactory]   = None
        self._manager:   Optional[ObservationManager]   = None
        self._pipeline:  Optional[ObservationPipeline]  = None
        self._registry:  Optional[ObservationRegistry]  = None
        self._context:   Optional[ObservationContext]   = None
        self._repo:      Optional[ObservationRepository] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            _LOG.info("ObservationEngine: initialising …")
            t0 = time.perf_counter()

            self._factory  = get_observation_factory()
            self._repo     = get_observation_repository()
            self._pipeline = get_observation_pipeline()
            self._manager  = get_observation_manager()
            self._registry = get_observation_registry()
            self._context  = get_observation_context()

            self._initialized = True
            self._startup_at  = time.time()
            elapsed = (time.perf_counter() - t0) * 1_000.0
            _LOG.info("ObservationEngine: ready in %.1f ms", elapsed)

    def shutdown(self) -> None:
        with self._lock:
            if not self._initialized:
                return
            _LOG.info("ObservationEngine: shutting down …")
            self._initialized = False
            self._startup_at  = None
            _LOG.info("ObservationEngine: stopped")

    def _assert_ready(self) -> None:
        if not self._initialized:
            raise ObservationEngineNotInitializedError()

    # ── Primary API ───────────────────────────────────────────────────────────

    def observe(
        self,
        content:    Any,
        obs_type:   ObservationType       = ObservationType.UNKNOWN,
        title:      str                   = "",
        source:     ObservationSource     = ObservationSource.SYSTEM,
        domain:     ObservationDomain     = ObservationDomain.GENERAL,
        priority:   ObservationPriority   = ObservationPriority.MEDIUM,
        confidence: float                 = 0.5,
        instrument: str                   = "",
        exchange:   str                   = "",
        tags:       Optional[list[str]]   = None,
        actor:      str                   = SYSTEM_OBSERVER,
        ttl_seconds: int                  = 86_400,
    ) -> Observation:
        """Create an observation and run it through the full pipeline.

        This is the canonical entry point for all external data entering IIOS.
        """
        self._assert_ready()
        obs = self._factory.create(
            content     = content,
            obs_type    = obs_type,
            title       = title,
            source      = source,
            domain      = domain,
            priority    = priority,
            confidence  = confidence,
            instrument  = instrument,
            exchange    = exchange,
            tags        = tags,
            actor       = actor,
            ttl_seconds = ttl_seconds,
        )
        return self._manager.ingest(obs, actor)

    def observe_market_data(
        self,
        content:    dict[str, Any],
        instrument: str,
        exchange:   str           = "NSE",
        source:     ObservationSource = ObservationSource.YFINANCE,
        actor:      str           = SYSTEM_OBSERVER,
    ) -> Observation:
        self._assert_ready()
        obs = self._factory.create_market_data(
            content=content, instrument=instrument, exchange=exchange,
            source=source, actor=actor,
        )
        return self._manager.ingest(obs, actor)

    def observe_signal(
        self,
        content:    dict[str, Any],
        instrument: str,
        confidence: float = 0.70,
        actor:      str   = SYSTEM_OBSERVER,
    ) -> Observation:
        self._assert_ready()
        obs = self._factory.create_signal(
            content=content, instrument=instrument, confidence=confidence, actor=actor,
        )
        return self._manager.ingest(obs, actor)

    def observe_batch(
        self,
        items:  list[dict[str, Any]],
        actor:  str = SYSTEM_OBSERVER,
    ) -> tuple[list[Observation], list[Observation]]:
        """Create and ingest a batch. Returns (accepted, rejected)."""
        self._assert_ready()
        observations = self._factory.create_batch(items, actor)
        return self._manager.ingest_batch(observations, actor)

    def submit(self, obs: Observation, actor: str = SYSTEM_OBSERVER) -> Observation:
        """Submit a pre-built observation to the pipeline."""
        self._assert_ready()
        return self._manager.ingest(obs, actor)

    # ── Read API ──────────────────────────────────────────────────────────────

    def get(self, obs_id: str) -> Observation:
        self._assert_ready()
        return self._repo.get(obs_id)

    def get_or_none(self, obs_id: str) -> Optional[Observation]:
        self._assert_ready()
        return self._repo.get_or_none(obs_id)

    def find(self, query: ObservationQuery) -> list[Observation]:
        self._assert_ready()
        return self._repo.find(query)

    def count(self, query: Optional[ObservationQuery] = None) -> int:
        self._assert_ready()
        return self._repo.count(query)

    def list_accepted(self) -> list[Observation]:
        self._assert_ready()
        return self._repo.list_accepted()

    def list_pending(self) -> list[Observation]:
        self._assert_ready()
        return self._repo.list_pending()

    # ── Lifecycle management ──────────────────────────────────────────────────

    def archive(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        self._assert_ready()
        return self._manager.archive(obs_id, actor)

    def expire_stale(self, actor: str = SYSTEM_OBSERVER) -> list[str]:
        self._assert_ready()
        return self._manager.expire_stale(actor)

    def soft_delete(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        self._assert_ready()
        return self._manager.soft_delete(obs_id, actor)

    # ── Status / statistics ───────────────────────────────────────────────────

    def statistics(self) -> ObservationStatistics:
        self._assert_ready()
        return self._manager.statistics()

    def status(self) -> dict[str, Any]:
        return {
            "initialized":    self._initialized,
            "startup_at":     self._startup_at,
            "uptime_s":       round(time.time() - self._startup_at, 1) if self._startup_at else 0,
            "namespace":      OBSERVATION_NAMESPACE,
            "components":     self._registry.status() if self._registry else {},
        }

    def health(self) -> dict[str, Any]:
        stats = self.statistics() if self._initialized else None
        return {
            "status":      "healthy" if self._initialized else "not_initialized",
            "total_observations": stats.total_created   if stats else 0,
            "accepted":          stats.total_accepted   if stats else 0,
            "rejected":          stats.total_rejected   if stats else 0,
            "in_flight":         stats.total_in_flight  if stats else 0,
            "avg_pipeline_ms":   stats.avg_pipeline_ms  if stats else 0.0,
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_engine() -> ObservationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = ObservationEngine()
    return _engine


def reset_observation_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            try:
                _engine.shutdown()
            except Exception:
                pass
        _engine = None
