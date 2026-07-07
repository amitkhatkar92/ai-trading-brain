"""
iios/observation/observation_manager.py
========================================
ObservationManager — high-level CRUD and lifecycle operations.

The manager is the authoritative interface for all observation
read/write operations.  Callers should interact with the Manager
rather than the repository or storage directly.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Any, Optional

from .observation_constants import (
    DUPLICATE_WINDOW_SECONDS,
    SYSTEM_OBSERVER,
    DuplicatePolicy,
    ObservationStatus,
)
from .observation_exceptions import (
    ObservationDuplicateError,
    ObservationNotFoundError,
)
from .models.observation          import Observation
from .models.observation_statistics import ObservationStatistics, ObservationTypeStats
from .repositories.observation_repository import (
    ObservationRepository,
    get_observation_repository,
)
from .repositories.observation_query import ObservationQuery
from .storage.observation_store import ObservationStore, get_observation_store
from .pipeline.observation_pipeline import ObservationPipeline, get_observation_pipeline

__all__ = [
    "ObservationManager",
    "get_observation_manager",
    "reset_observation_manager",
]

_LOG  = logging.getLogger("iios.observation.manager")
_lock = threading.Lock()
_mgr: Optional["ObservationManager"] = None


class ObservationManager:
    """High-level observation lifecycle manager.

    Provides:
    - ingest()         — run full pipeline and persist
    - ingest_batch()   — bulk ingest
    - get/find/count   — read operations
    - archive/expire   — lifecycle transitions
    - statistics()     — engine-wide stats
    """

    def __init__(
        self,
        repo:     Optional[ObservationRepository] = None,
        store:    Optional[ObservationStore]       = None,
        pipeline: Optional[ObservationPipeline]   = None,
        duplicate_policy: DuplicatePolicy          = DuplicatePolicy.SKIP,
        duplicate_window: int                      = DUPLICATE_WINDOW_SECONDS,
    ) -> None:
        self._repo      = repo     or get_observation_repository()
        self._store     = store    or get_observation_store()
        self._pipeline  = pipeline or get_observation_pipeline()
        self._dup_policy = duplicate_policy
        self._dup_window = duplicate_window
        self._lock       = threading.RLock()

        # Stats counters
        self._total_ingested:  int   = 0
        self._total_accepted:  int   = 0
        self._total_rejected:  int   = 0
        self._total_duplicates: int  = 0
        self._pipeline_ms:     list[float] = []

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(
        self,
        obs:   Observation,
        actor: str = SYSTEM_OBSERVER,
    ) -> Observation:
        """Run *obs* through the pipeline and persist the result.

        Returns the (mutated) observation after all pipeline stages.
        """
        # Duplicate check
        if self._is_duplicate(obs):
            return self._handle_duplicate(obs, actor)

        result = self._pipeline.process(obs, actor)

        with self._lock:
            self._total_ingested += 1
            if result.success:
                self._total_accepted += 1
            else:
                self._total_rejected += 1
            self._pipeline_ms.append(result.total_ms)
            if len(self._pipeline_ms) > 1_000:
                self._pipeline_ms = self._pipeline_ms[-500:]

        # Persist
        self._store.save(obs)
        _LOG.debug(
            "Ingested: %s status=%s ms=%.1f",
            obs.id[:32], obs.status.value, result.total_ms,
        )
        return obs

    def ingest_batch(
        self,
        observations: list[Observation],
        actor:        str = SYSTEM_OBSERVER,
    ) -> tuple[list[Observation], list[Observation]]:
        """Ingest a batch. Returns (accepted, rejected) lists."""
        accepted: list[Observation] = []
        rejected: list[Observation] = []
        for obs in observations:
            result_obs = self.ingest(obs, actor)
            if result_obs.status == ObservationStatus.ACCEPTED:
                accepted.append(result_obs)
            else:
                rejected.append(result_obs)
        return accepted, rejected

    # ── Duplicate detection ───────────────────────────────────────────────────

    def _is_duplicate(self, obs: Observation) -> bool:
        """Check if an observation with the same checksum was recently accepted."""
        if not obs.checksum:
            return False
        cutoff = time.time() - self._dup_window
        q = (ObservationQuery()
             .with_status(ObservationStatus.ACCEPTED)
             .created_between(cutoff, time.time() + 1))
        recent = self._repo.find(q)
        return any(r.checksum == obs.checksum for r in recent)

    def _handle_duplicate(self, obs: Observation, actor: str) -> Observation:
        with self._lock:
            self._total_duplicates += 1

        if self._dup_policy == DuplicatePolicy.REJECT:
            obs.reject("duplicate", actor)
            self._store.save(obs)
            raise ObservationDuplicateError(
                f"Duplicate observation rejected: checksum={obs.checksum[:8]}",
                code="OBS-080",
            )
        elif self._dup_policy == DuplicatePolicy.SKIP:
            _LOG.debug("Duplicate skipped: %s", obs.id[:24])
            obs.reject("duplicate:skip", actor)
            return obs
        else:
            # OVERWRITE / MERGE / VERSION → just ingest as new (simplified)
            return obs

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, obs_id: str) -> Observation:
        return self._repo.get(obs_id)

    def get_or_none(self, obs_id: str) -> Optional[Observation]:
        return self._repo.get_or_none(obs_id)

    def find(self, query: ObservationQuery) -> list[Observation]:
        return self._repo.find(query)

    def count(self, query: Optional[ObservationQuery] = None) -> int:
        return self._repo.count(query)

    def list_accepted(self) -> list[Observation]:
        return self._repo.list_accepted()

    def list_pending(self) -> list[Observation]:
        return self._repo.list_pending()

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def archive(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        obs = self._repo.get(obs_id)
        obs.archive(actor)
        return self._repo.update(obs)

    def expire(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        obs = self._repo.get(obs_id)
        obs.expire(actor)
        return self._repo.update(obs)

    def soft_delete(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        return self._repo.soft_delete(obs_id, actor)

    def expire_stale(self, actor: str = SYSTEM_OBSERVER) -> list[str]:
        return self._store.expire_stale(actor)

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> ObservationStatistics:
        with self._lock:
            n   = len(self._pipeline_ms)
            avg = sum(self._pipeline_ms) / n if n > 0 else 0.0
            mx  = max(self._pipeline_ms) if n > 0 else 0.0
            mn  = min(self._pipeline_ms) if n > 0 else float("inf")

        repo_stats   = self._repo.statistics()
        storage_info = repo_stats.get("storage", {})
        by_status    = storage_info.get("by_status", {})

        in_flight = sum(
            by_status.get(s.value, 0) for s in [
                ObservationStatus.CREATED, ObservationStatus.COLLECTED,
                ObservationStatus.VALIDATING, ObservationStatus.VALIDATED,
                ObservationStatus.CLASSIFYING, ObservationStatus.CLASSIFIED,
                ObservationStatus.ENRICHING, ObservationStatus.ENRICHED,
            ]
        )

        with self._lock:
            return ObservationStatistics(
                total_created   = self._total_ingested,
                total_accepted  = self._total_accepted,
                total_rejected  = self._total_rejected,
                total_duplicates= self._total_duplicates,
                total_in_flight = in_flight,
                avg_pipeline_ms = round(avg, 2),
                max_pipeline_ms = round(mx, 2),
                min_pipeline_ms = round(mn, 2) if mn != float("inf") else 0.0,
                storage_size    = storage_info.get("total", 0),
            )


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_manager() -> ObservationManager:
    global _mgr
    if _mgr is None:
        with _lock:
            if _mgr is None:
                _mgr = ObservationManager()
    return _mgr


def reset_observation_manager() -> None:
    global _mgr
    with _lock:
        _mgr = None
