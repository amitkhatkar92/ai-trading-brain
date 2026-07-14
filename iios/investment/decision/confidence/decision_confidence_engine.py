"""iios/investment/decision/confidence/decision_confidence_engine.py
DecisionConfidenceEngine — authoritative confidence estimation facade for IIOS.

Responsibilities:
  - Initialise runtime
  - Receive EvidenceSnapshot, ReasoningSnapshot, optional ScoringSnapshot
  - Estimate confidence through the 6-stage pipeline
  - Maintain per-subject history, version tracking, and statistics
  - Publish ConfidenceSnapshot
  - Provide query APIs

This engine NEVER:
  - Scores investment opportunities
  - Generates Buy/Sell/Hold recommendations
  - Executes trades
  - Independently evaluates markets, companies, or strategies
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.calibration_engine import CalibrationEngine
from iios.investment.decision.confidence.calibration_statistics import (
    CalibrationStatisticsTracker,
)
from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceEngineStatus,
    DEFAULT_CONFIDENCE_TIMEOUT_SECS,
)
from iios.investment.decision.confidence.confidence_health import ConfidenceHealthMonitor
from iios.investment.decision.confidence.confidence_history import ConfidenceHistory
from iios.investment.decision.confidence.confidence_pipeline import (
    BaseConfidenceModule,
    ConfidenceContext,
    ConfidencePipeline,
)
from iios.investment.decision.confidence.confidence_quality import (
    ConfidenceQualityEvaluator,
    ConfidenceQualityReport,
)
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.confidence.confidence_statistics import (
    ConfidenceStatisticsTracker,
)
from iios.investment.decision.confidence.confidence_validator import (
    ConfidenceValidationResult,
    ConfidenceValidator,
)
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot

log = logging.getLogger(__name__)


class DecisionConfidenceEngine:
    """
    Thread-safe, async-capable confidence estimation engine.

    Typical lifecycle:
        engine = DecisionConfidenceEngine()
        engine.start()
        snapshot = engine.estimate_sync(evidence_snap, reasoning_snap)
        # or
        snapshot = await engine.estimate(evidence_snap, reasoning_snap)
        engine.stop()
    """

    def __init__(
        self,
        pipeline:        Optional[ConfidencePipeline]             = None,
        history:         Optional[ConfidenceHistory]              = None,
        statistics:      Optional[ConfidenceStatisticsTracker]    = None,
        cal_statistics:  Optional[CalibrationStatisticsTracker]   = None,
        quality:         Optional[ConfidenceQualityEvaluator]     = None,
        validator:       Optional[ConfidenceValidator]            = None,
        health:          Optional[ConfidenceHealthMonitor]        = None,
        calibration_engine: Optional[CalibrationEngine]          = None,
        timeout_secs:    float = DEFAULT_CONFIDENCE_TIMEOUT_SECS,
    ) -> None:
        self._pipeline   = pipeline    or ConfidencePipeline()
        self._history    = history     or ConfidenceHistory()
        self._stats      = statistics  or ConfidenceStatisticsTracker()
        self._cal_stats  = cal_statistics or CalibrationStatisticsTracker()
        self._quality    = quality     or ConfidenceQualityEvaluator()
        self._validator  = validator   or ConfidenceValidator()
        self._health     = health      or ConfidenceHealthMonitor()
        self._cal_engine = calibration_engine or CalibrationEngine()
        self._timeout    = timeout_secs
        self._lock       = threading.RLock()
        # subject_id → version counter
        self._versions: Dict[str, int] = {}
        self._status: ConfidenceEngineStatus = ConfidenceEngineStatus.INITIALIZING

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            self._status = ConfidenceEngineStatus.READY
        log.info("DecisionConfidenceEngine started.")

    def stop(self) -> None:
        with self._lock:
            self._status = ConfidenceEngineStatus.STOPPED
        log.info("DecisionConfidenceEngine stopped.")

    @property
    def status(self) -> ConfidenceEngineStatus:
        return self._status

    # ── Primary API ────────────────────────────────────────────────────────

    async def estimate(
        self,
        evidence_snapshot:  EvidenceSnapshot,
        reasoning_snapshot: ReasoningSnapshot,
        scoring_snapshot:   Optional[Any] = None,
    ) -> ConfidenceSnapshot:
        """
        Async confidence estimation.
        Returns a ConfidenceSnapshot — the canonical output.
        """
        if not self._status.is_operational:
            raise RuntimeError(
                f"DecisionConfidenceEngine is not operational (status={self._status.value}). "
                "Call start() first."
            )

        with self._lock:
            self._status = ConfidenceEngineStatus.ESTIMATING

        start_ts = time.perf_counter()

        try:
            subject_id  = evidence_snapshot.subject_id
            decision_id = evidence_snapshot.decision_id

            version = self._next_version(subject_id)
            series  = self._history.confidence_series(subject_id)

            ctx = ConfidenceContext(
                decision_id=decision_id,
                subject_id=subject_id,
                subject_type=evidence_snapshot.subject_type,
                version=version,
                evidence_snapshot=evidence_snapshot,
                reasoning_snapshot=reasoning_snapshot,
                scoring_snapshot=scoring_snapshot,
                confidence_series=series,
            )

            result = await asyncio.wait_for(
                self._pipeline.execute(ctx),
                timeout=self._timeout,
            )
            snapshot = result.snapshot

            # ── Store ────────────────────────────────────────────────────
            self._history.record(snapshot)

            duration_ms = (time.perf_counter() - start_ts) * 1000.0

            # ── Telemetry ────────────────────────────────────────────────
            self._stats.record_success(
                overall_confidence=snapshot.overall_confidence,
                duration_ms=duration_ms,
                evidence_confidence=snapshot.decision_confidence.evidence_confidence,
                reasoning_confidence=snapshot.decision_confidence.reasoning_confidence,
            )
            self._cal_stats.record(
                raw_confidence=result.calibration_result.raw_confidence,
                calibrated_conf=result.calibration_result.calibrated_conf,
                status=result.calibration_result.status,
            )
            self._health.record_success(snapshot.overall_confidence, duration_ms)

            log.debug(
                "Confidence estimated for %s v%d: overall=%.1f level=%s",
                subject_id, version, snapshot.overall_confidence,
                snapshot.confidence_level.value,
            )
            return snapshot

        except Exception as exc:
            self._stats.record_failure()
            self._health.record_failure()
            log.error("Confidence estimation failed for %s: %s", decision_id, exc)
            raise

        finally:
            with self._lock:
                if self._status == ConfidenceEngineStatus.ESTIMATING:
                    self._status = ConfidenceEngineStatus.READY

    def estimate_sync(
        self,
        evidence_snapshot:  EvidenceSnapshot,
        reasoning_snapshot: ReasoningSnapshot,
        scoring_snapshot:   Optional[Any] = None,
    ) -> ConfidenceSnapshot:
        """Synchronous wrapper for estimate()."""
        if not self._status.is_operational:
            raise RuntimeError(
                "DecisionConfidenceEngine is not operational. Call start() first."
            )
        return asyncio.run(self.estimate(evidence_snapshot, reasoning_snapshot, scoring_snapshot))

    # ── Feedback ───────────────────────────────────────────────────────────

    def record_outcome(
        self,
        decision_id:    str,
        raw_confidence: float,
        was_correct:    bool,
    ) -> None:
        """Feed back a historical outcome for calibration improvement."""
        self._cal_engine.record_outcome(decision_id, raw_confidence, was_correct)

    # ── Query API ──────────────────────────────────────────────────────────

    def get_snapshot(self, snapshot_id: str) -> Optional[ConfidenceSnapshot]:
        return self._history.get(snapshot_id)

    def get_history(self, subject_id: str) -> List[ConfidenceSnapshot]:
        return self._history.for_subject(subject_id)

    def get_latest(self, subject_id: str) -> Optional[ConfidenceSnapshot]:
        return self._history.latest_for_subject(subject_id)

    def get_quality(self, snapshot_id: str) -> Optional[ConfidenceQualityReport]:
        snap = self._history.get(snapshot_id)
        return self._quality.evaluate(snap) if snap else None

    def validate(self, snapshot_id: str) -> Optional[ConfidenceValidationResult]:
        snap = self._history.get(snapshot_id)
        return self._validator.validate(snap) if snap else None

    def confidence_series(self, subject_id: str) -> List[float]:
        return self._history.confidence_series(subject_id)

    def stats(self) -> Dict[str, Any]:
        return {
            "status":          self._status.value,
            "statistics":      self._stats.summary().to_dict(),
            "calibration":     self._cal_stats.summary().to_dict(),
            "health":          self._health.report().to_dict(),
            "history":         self._history.stats(),
            "known_subjects":  self._history.known_subjects(),
        }

    # ── Private ────────────────────────────────────────────────────────────

    def _next_version(self, subject_id: str) -> int:
        with self._lock:
            v = self._versions.get(subject_id, 0) + 1
            self._versions[subject_id] = v
            return v
