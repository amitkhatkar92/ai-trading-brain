"""
iios/observation/enrichment/observation_enricher.py
====================================================
ObservationEnricher — adds contextual metadata to observations.

Each enricher pass is registered as an ``EnricherPlugin``.
The default set adds tags, normalises confidence, and computes
a quality score.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..observation_constants import (
    EnrichmentType,
    MAX_ENRICHMENT_ROUNDS,
    SYSTEM_OBSERVER,
    ObservationQuality,
)
from ..models.observation import Observation

__all__ = [
    "EnrichmentResult",
    "ObservationEnricher",
    "get_observation_enricher",
    "reset_observation_enricher",
]

_LOG  = logging.getLogger("iios.observation.enricher")
_lock = threading.Lock()
_enricher: Optional["ObservationEnricher"] = None

EnricherPlugin = Callable[[Observation], None]


def _compute_quality(obs: Observation) -> tuple[ObservationQuality, float]:
    """Simple heuristic quality score from observation attributes."""
    score = 0.5  # baseline

    # Content presence
    if obs.content is not None:
        score += 0.15

    # Title presence
    if obs.title:
        score += 0.05

    # Confidence
    score += obs.metadata.confidence * 0.20

    # Source info
    if obs.source_info.instrument:
        score += 0.05
    if obs.source_info.exchange:
        score += 0.05

    score = min(1.0, score)

    if   score >= 0.80: quality = ObservationQuality.EXCELLENT
    elif score >= 0.60: quality = ObservationQuality.GOOD
    elif score >= 0.40: quality = ObservationQuality.FAIR
    else:               quality = ObservationQuality.POOR

    return quality, round(score, 4)


@dataclass
class EnrichmentResult:
    """Summary of an enrichment pass."""

    enrichers_applied: list[str]       = field(default_factory=list)
    tags_added:        list[str]       = field(default_factory=list)
    attributes_set:    dict[str, Any]  = field(default_factory=dict)
    quality:           ObservationQuality = ObservationQuality.FAIR
    quality_score:     float           = 0.5
    duration_ms:       float           = 0.0
    round_number:      int             = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "enrichers_applied": self.enrichers_applied,
            "tags_added":        self.tags_added,
            "attributes_set":    dict(self.attributes_set),
            "quality":           self.quality.value,
            "quality_score":     self.quality_score,
            "duration_ms":       self.duration_ms,
            "round_number":      self.round_number,
        }


class ObservationEnricher:
    """Pluggable observation enricher.

    Built-in enrichments applied in order:
    1. Quality scoring
    2. Tag normalisation (lowercase, dedupe)
    3. Metadata completeness fill-in

    Additional ``EnricherPlugin`` callables can be registered via
    ``register_plugin()``.
    """

    def __init__(self) -> None:
        self._plugins: list[tuple[str, EnricherPlugin]] = []
        self._lock    = threading.RLock()

    def register_plugin(self, name: str, fn: EnricherPlugin) -> None:
        with self._lock:
            self._plugins.append((name, fn))

    def enrich(
        self,
        obs:          Observation,
        round_number: int = 1,
    ) -> EnrichmentResult:
        if round_number > MAX_ENRICHMENT_ROUNDS:
            _LOG.warning("Max enrichment rounds reached for '%s'", obs.uid[:8])
            return EnrichmentResult(round_number=round_number)

        t0 = time.perf_counter()
        applied:    list[str]      = []
        tags_added: list[str]      = []
        attrs_set:  dict[str, Any] = {}

        # ── Built-in: quality score ────────────────────────────────────────
        quality, q_score = _compute_quality(obs)
        obs.metadata.quality       = quality
        obs.metadata.quality_score = q_score
        applied.append("quality_scorer")
        attrs_set["quality"] = quality.value
        attrs_set["quality_score"] = q_score

        # ── Built-in: tag normalisation ────────────────────────────────────
        normalised = list({t.strip().lower() for t in obs.metadata.tags if t.strip()})
        if normalised != obs.metadata.tags:
            obs.metadata.tags = normalised
            applied.append("tag_normaliser")
            tags_added = [t for t in normalised if t not in obs.metadata.tags]

        # ── Built-in: metadata fill-in ────────────────────────────────────
        if not obs.metadata.observed_at:
            obs.metadata.observed_at = obs.created_at
            applied.append("observed_at_filler")
            attrs_set["observed_at"] = obs.metadata.observed_at

        # ── Custom plugins ─────────────────────────────────────────────────
        with self._lock:
            plugins = list(self._plugins)
        for name, fn in plugins:
            try:
                fn(obs)
                applied.append(name)
            except Exception as exc:
                _LOG.warning("Enricher plugin '%s' failed: %s", name, exc)

        obs.context.enrichment_rounds = round_number

        duration_ms = (time.perf_counter() - t0) * 1_000.0
        return EnrichmentResult(
            enrichers_applied = applied,
            tags_added        = tags_added,
            attributes_set    = attrs_set,
            quality           = quality,
            quality_score     = q_score,
            duration_ms       = duration_ms,
            round_number      = round_number,
        )

    def enrich_batch(
        self, observations: list[Observation]
    ) -> dict[str, EnrichmentResult]:
        return {obs.id: self.enrich(obs) for obs in observations}


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_enricher() -> ObservationEnricher:
    global _enricher
    if _enricher is None:
        with _lock:
            if _enricher is None:
                _enricher = ObservationEnricher()
    return _enricher


def reset_observation_enricher() -> None:
    global _enricher
    with _lock:
        _enricher = None
