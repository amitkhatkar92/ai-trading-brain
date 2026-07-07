"""
iios/observation/quality/quality_engine.py
==========================================
QualityEngine — computes :class:`QualityScore` for observations.

Runs all eight dimension assessors, aggregates the weighted OQI,
updates the observation's metadata quality fields, and caches
recent scores to avoid recomputation.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from ..models.observation    import Observation
from .quality_score          import DEFAULT_WEIGHTS, QualityScore, DimensionScore, quality_tier
from .quality_assessment     import (
    CompletenessAssessor, AccuracyAssessor, ConsistencyAssessor,
    TimelinessAssessor,   ReliabilityAssessor, SourceTrustAssessor,
    FreshnessAssessor,    IntegrityAssessor,
)
from .quality_metrics        import QualityMetrics, get_quality_metrics
from ..validators.validation_exceptions import QualityEngineError

__all__ = [
    "QualityEngine",
    "get_quality_engine",
    "reset_quality_engine",
]

_LOG  = logging.getLogger("iios.observation.quality.engine")
_lock = threading.Lock()
_engine: Optional["QualityEngine"] = None

_CACHE_SIZE = 512


class QualityEngine:
    """Computes nine-dimension quality scores for observations.

    Parameters
    ----------
    metrics:
        :class:`QualityMetrics` instance for recording aggregate stats.
        Defaults to the global singleton.
    cache_size:
        Maximum number of :class:`QualityScore` objects to keep in the
        LRU cache (keyed by ``obs.id``).
    """

    def __init__(
        self,
        metrics:    Optional[QualityMetrics] = None,
        cache_size: int                      = _CACHE_SIZE,
    ) -> None:
        self._metrics    = metrics or get_quality_metrics()
        self._cache:      OrderedDict[str, QualityScore] = OrderedDict()
        self._cache_size  = cache_size
        self._lock        = threading.RLock()

        # Dimension assessors — one instance each
        self._assessors = [
            CompletenessAssessor(),
            AccuracyAssessor(),
            ConsistencyAssessor(),
            TimelinessAssessor(),
            ReliabilityAssessor(),
            SourceTrustAssessor(),
            FreshnessAssessor(),
            IntegrityAssessor(),
        ]

    # ── Score ─────────────────────────────────────────────────────────────────

    def score(self, obs: Observation, use_cache: bool = True) -> QualityScore:
        """Compute (or retrieve cached) quality score for *obs*."""
        if use_cache:
            with self._lock:
                cached = self._cache.get(obs.id)
                if cached is not None:
                    self._cache.move_to_end(obs.id)
                    return cached

        qs = self._compute(obs)

        # Write back quality to the observation's metadata
        obs.metadata.quality       = qs.tier
        obs.metadata.quality_score = qs.oqi

        self._cache_put(obs.id, qs)
        self._metrics.record(
            qs,
            source   = obs.source_info.source.value,
            obs_type = obs.obs_type.value,
        )
        _LOG.debug(
            "Quality: %s | OQI=%.3f [%s] | %.1fms",
            obs.uid[:8] + "…",
            qs.oqi,
            qs.tier.value,
            (time.time() - qs.computed_at) * 1_000,
        )
        return qs

    def score_batch(
        self,
        observations: list[Observation],
        use_cache:    bool = True,
    ) -> dict[str, QualityScore]:
        """Score a batch of observations.  Returns obs_id → QualityScore."""
        return {obs.id: self.score(obs, use_cache=use_cache) for obs in observations}

    # ── Internals ─────────────────────────────────────────────────────────────

    def _compute(self, obs: Observation) -> QualityScore:
        dim_scores: dict[str, DimensionScore] = {}
        for assessor in self._assessors:
            ds = assessor.assess(obs)
            dim_scores[ds.name] = ds

        oqi = sum(d.weighted for d in dim_scores.values())
        oqi = max(0.0, min(1.0, round(oqi, 4)))

        return QualityScore(
            obs_id       = obs.id,
            completeness = dim_scores["completeness"],
            accuracy     = dim_scores["accuracy"],
            consistency  = dim_scores["consistency"],
            timeliness   = dim_scores["timeliness"],
            reliability  = dim_scores["reliability"],
            source_trust = dim_scores["source_trust"],
            freshness    = dim_scores["freshness"],
            integrity    = dim_scores["integrity"],
            oqi          = oqi,
            tier         = quality_tier(oqi),
        )

    def _cache_put(self, key: str, qs: QualityScore) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                self._cache[key] = qs
                if len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)

    def invalidate(self, obs_id: str) -> None:
        """Remove *obs_id* from the score cache."""
        with self._lock:
            self._cache.pop(obs_id, None)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        return {
            "cache_size":  self.cache_size(),
            "cache_cap":   self._cache_size,
            "metrics":     self._metrics.summary(),
        }


# ── Singletons ────────────────────────────────────────────────────────────────

def get_quality_engine() -> QualityEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = QualityEngine()
    return _engine


def reset_quality_engine() -> None:
    global _engine
    with _lock:
        _engine = None
