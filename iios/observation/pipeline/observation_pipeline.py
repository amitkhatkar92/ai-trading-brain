"""
iios/observation/pipeline/observation_pipeline.py
=================================================
ObservationPipeline — orchestrates the full observation processing
pipeline: validate → classify → enrich → accept/reject.

The pipeline is stateless; all state lives in the Observation objects
and the repository.  Thread-safe; supports batch ingestion.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    ObservationStatus,
    PipelineStage,
    SYSTEM_OBSERVER,
)
from ..observation_exceptions import ObservationPipelineError
from ..models.observation        import Observation
from ..models.observation_record import ObservationRecord, ProcessingEvent
from ..validators.observation_validator  import ObservationValidator, get_observation_validator
from ..classifiers.observation_classifier import ObservationClassifier, get_observation_classifier
from ..enrichment.observation_enricher    import ObservationEnricher, get_observation_enricher

__all__ = [
    "PipelineResult",
    "ObservationPipeline",
    "get_observation_pipeline",
    "reset_observation_pipeline",
]

_LOG  = logging.getLogger("iios.observation.pipeline")
_lock = threading.Lock()
_pipeline: Optional["ObservationPipeline"] = None


@dataclass
class PipelineResult:
    """Output from a single pipeline run."""

    obs_id:      str
    success:     bool
    final_status: ObservationStatus
    record:      ObservationRecord
    rejection_reason: str         = ""
    total_ms:    float            = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":          self.obs_id,
            "success":         self.success,
            "final_status":    self.final_status.value,
            "rejection_reason":self.rejection_reason,
            "total_ms":        self.total_ms,
        }


class ObservationPipeline:
    """Full observation processing pipeline.

    Stages:
      INGEST → VALIDATE → CLASSIFY → ENRICH → STORE → PUBLISH

    Each stage updates the observation status and appends a
    ``ProcessingEvent`` to the ``ObservationRecord``.
    """

    def __init__(
        self,
        validator:  Optional[ObservationValidator]  = None,
        classifier: Optional[ObservationClassifier] = None,
        enricher:   Optional[ObservationEnricher]   = None,
    ) -> None:
        self._validator  = validator  or get_observation_validator()
        self._classifier = classifier or get_observation_classifier()
        self._enricher   = enricher   or get_observation_enricher()

    def process(
        self,
        obs:   Observation,
        actor: str = SYSTEM_OBSERVER,
    ) -> PipelineResult:
        """Run a single observation through the full pipeline."""
        t0     = time.perf_counter()
        record = ObservationRecord(observation=obs)

        try:
            # ── 1: Ingest ──────────────────────────────────────────────────
            ts = time.perf_counter()
            obs.mark_collected(actor)
            record.add_event(PipelineStage.INGEST, obs.status, actor,
                             (time.perf_counter() - ts) * 1_000.0, "collected")

            # ── 2: Validate ────────────────────────────────────────────────
            ts = time.perf_counter()
            obs.transition(ObservationStatus.VALIDATING, actor)
            val_result = self._validator.validate(obs)
            dur_ms = (time.perf_counter() - ts) * 1_000.0
            obs.context.validation_rounds += 1

            if val_result.failed:
                reason = "; ".join(val_result.violations)
                obs.reject(reason, actor)
                record.add_event(PipelineStage.VALIDATE, obs.status, actor, dur_ms,
                                 f"FAIL: {reason}", {"violations": val_result.violations})
                record.pipeline_failures += 1
                total_ms = (time.perf_counter() - t0) * 1_000.0
                return PipelineResult(
                    obs_id=obs.id, success=False,
                    final_status=obs.status, record=record,
                    rejection_reason=reason, total_ms=total_ms,
                )

            obs.validation_passed = True
            obs.validation_notes  = val_result.warnings
            obs.transition(ObservationStatus.VALIDATED, actor)
            record.add_event(PipelineStage.VALIDATE, obs.status, actor, dur_ms,
                             "PASS", {"warnings": val_result.warnings})

            # ── 3: Classify ────────────────────────────────────────────────
            ts = time.perf_counter()
            obs.transition(ObservationStatus.CLASSIFYING, actor)
            clf_result = self._classifier.classify(obs)
            dur_ms = (time.perf_counter() - ts) * 1_000.0

            obs.mark_classified(
                clf_result.label, clf_result.confidence, clf_result.method.value, actor
            )
            obs.metadata.domain = clf_result.domain
            # Merge tags
            existing = set(obs.metadata.tags)
            for t in clf_result.tags_added:
                if t not in existing:
                    obs.metadata.tags.append(t)
                    existing.add(t)

            record.add_event(PipelineStage.CLASSIFY, obs.status, actor, dur_ms,
                             f"label={clf_result.label}", clf_result.to_dict())

            # ── 4: Enrich ──────────────────────────────────────────────────
            ts = time.perf_counter()
            obs.transition(ObservationStatus.ENRICHING, actor)
            enr_result = self._enricher.enrich(obs, round_number=1)
            dur_ms = (time.perf_counter() - ts) * 1_000.0

            obs.mark_enriched(actor)
            record.add_event(PipelineStage.ENRICH, obs.status, actor, dur_ms,
                             f"quality={enr_result.quality.value}", enr_result.to_dict())

            # ── 5: Accept ──────────────────────────────────────────────────
            ts = time.perf_counter()
            obs.accept(actor)
            record.add_event(PipelineStage.STORE, obs.status, actor,
                             (time.perf_counter() - ts) * 1_000.0, "accepted")

            record.pipeline_passes += 1
            total_ms = (time.perf_counter() - t0) * 1_000.0
            record.total_processing_ms = total_ms

            return PipelineResult(
                obs_id=obs.id, success=True,
                final_status=obs.status, record=record,
                total_ms=total_ms,
            )

        except Exception as exc:
            _LOG.exception("Pipeline error for '%s': %s", obs.id[:32], exc)
            if not obs.is_terminal:
                try:
                    obs.reject(str(exc), actor)
                except Exception:
                    pass
            record.pipeline_failures += 1
            total_ms = (time.perf_counter() - t0) * 1_000.0
            return PipelineResult(
                obs_id=obs.id, success=False,
                final_status=obs.status, record=record,
                rejection_reason=str(exc), total_ms=total_ms,
            )

    def process_batch(
        self,
        observations: list[Observation],
        actor:        str = SYSTEM_OBSERVER,
    ) -> list[PipelineResult]:
        return [self.process(obs, actor) for obs in observations]


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_pipeline() -> ObservationPipeline:
    global _pipeline
    if _pipeline is None:
        with _lock:
            if _pipeline is None:
                _pipeline = ObservationPipeline()
    return _pipeline


def reset_observation_pipeline() -> None:
    global _pipeline
    with _lock:
        _pipeline = None
