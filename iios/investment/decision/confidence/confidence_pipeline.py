"""iios/investment/decision/confidence/confidence_pipeline.py
ConfidencePipeline — 6-stage pipeline that transforms inputs into a ConfidenceSnapshot.
Also defines BaseConfidenceModule ABC for pluggable confidence methodologies.
"""
from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.calibration_engine import (
    CalibrationEngine,
    CalibrationResult,
)
from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceQualityGrade,
)
from iios.investment.decision.confidence.confidence_snapshot import (
    ConfidenceSnapshot,
    build_confidence_snapshot,
)
from iios.investment.decision.confidence.evidence_confidence import (
    EvidenceConfidenceEstimator,
    EvidenceConfidenceResult,
)
from iios.investment.decision.confidence.historical_confidence import (
    HistoricalConfidenceAnalyzer,
    HistoricalConfidenceResult,
)
from iios.investment.decision.confidence.overall_confidence import (
    OverallConfidenceEstimator,
    OverallConfidenceResult,
)
from iios.investment.decision.confidence.reasoning_confidence import (
    ReasoningConfidenceEstimator,
    ReasoningConfidenceResult,
)
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


# ── Scoring snapshot protocol ─────────────────────────────────────────────────
# Consumed from the (future) Decision Scoring Engine.
# Only the fields required by confidence estimation are declared here.

class ScoringSnapshotProtocol:
    """
    Structural protocol for the Decision Scoring Engine output.
    The confidence engine reads ONLY these fields.
    """
    snapshot_id:      str
    decision_id:      str
    subject_id:       str
    score_confidence: float    # 0–100 self-reported confidence


# ── Mutable context ────────────────────────────────────────────────────────────

@dataclass
class ConfidenceContext:
    decision_id:          str
    subject_id:           str
    subject_type:         str
    version:              int
    evidence_snapshot:    EvidenceSnapshot
    reasoning_snapshot:   ReasoningSnapshot
    scoring_snapshot:     Optional[Any]       # ScoringSnapshotProtocol | None
    confidence_series:    List[float]         # prior overall_confidence values for subject
    # ── populated by stages ───────────────────────────────────────────────
    evidence_result:      Optional[EvidenceConfidenceResult]   = None
    reasoning_result:     Optional[ReasoningConfidenceResult]  = None
    historical_result:    Optional[HistoricalConfidenceResult] = None
    calibration_result:   Optional[CalibrationResult]          = None
    overall_result:       Optional[OverallConfidenceResult]    = None
    extra_steps:          List[Any]                            = field(default_factory=list)
    metadata:             Dict[str, Any]                       = field(default_factory=dict)


# ── Pluggable module base ──────────────────────────────────────────────────────

class BaseConfidenceModule(ABC):
    """
    Extension point for pluggable confidence estimation methodologies.
    Subclasses may implement Bayesian, ensemble, probabilistic, or AI-based models.
    """

    @property
    @abstractmethod
    def module_name(self) -> str: ...

    @abstractmethod
    async def execute(self, context: ConfidenceContext) -> None:
        """Mutate context in-place (e.g. adjust overall_result.decision_confidence)."""
        ...


# ── Pipeline result ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelineResult:
    snapshot:           ConfidenceSnapshot
    evidence_result:    EvidenceConfidenceResult
    reasoning_result:   ReasoningConfidenceResult
    historical_result:  HistoricalConfidenceResult
    calibration_result: CalibrationResult


# ── Pipeline ───────────────────────────────────────────────────────────────────

class ConfidencePipeline:
    """
    6-stage pipeline:
      Stage 1: Evidence confidence
      Stage 2: Reasoning confidence
      Stage 3: Historical confidence
      Stage 4: Overall confidence assembly
      Stage 5: Calibration
      Stage 6: Snapshot construction + extra modules
    """

    def __init__(
        self,
        evidence_estimator:    Optional[EvidenceConfidenceEstimator]   = None,
        reasoning_estimator:   Optional[ReasoningConfidenceEstimator]  = None,
        historical_analyzer:   Optional[HistoricalConfidenceAnalyzer]  = None,
        overall_estimator:     Optional[OverallConfidenceEstimator]    = None,
        calibration_engine:    Optional[CalibrationEngine]             = None,
        extra_modules:         Optional[List[BaseConfidenceModule]]    = None,
    ) -> None:
        self._ev   = evidence_estimator   or EvidenceConfidenceEstimator()
        self._re   = reasoning_estimator  or ReasoningConfidenceEstimator()
        self._hi   = historical_analyzer  or HistoricalConfidenceAnalyzer()
        self._ov   = overall_estimator    or OverallConfidenceEstimator()
        self._cal  = calibration_engine   or CalibrationEngine()
        self._extra = extra_modules or []

    async def execute(self, ctx: ConfidenceContext) -> PipelineResult:
        start = datetime.now(timezone.utc)

        # ── Stage 1: Evidence confidence ─────────────────────────────────
        loop = asyncio.get_event_loop()
        ev_result = await loop.run_in_executor(
            None, self._ev.estimate, ctx.evidence_snapshot
        )
        ctx.evidence_result = ev_result

        # ── Stage 2: Reasoning confidence ────────────────────────────────
        re_result = await loop.run_in_executor(
            None, self._re.estimate, ctx.reasoning_snapshot
        )
        ctx.reasoning_result = re_result

        # ── Stage 3: Historical confidence ───────────────────────────────
        hi_result = await loop.run_in_executor(
            None,
            self._hi.analyze,
            ctx.subject_id,
            ctx.confidence_series,
            ctx.version,
            ev_result.overall,   # use evidence confidence as current proxy
        )
        ctx.historical_result = hi_result

        # ── Stage 4: Overall confidence assembly ─────────────────────────
        scoring_conf   = 0.0
        scoring_available = False
        scoring_snap_id = None

        if ctx.scoring_snapshot is not None:
            scoring_conf      = float(getattr(ctx.scoring_snapshot, "score_confidence", 0.0))
            scoring_available = True
            scoring_snap_id   = getattr(ctx.scoring_snapshot, "snapshot_id", None)

        ov_result = self._ov.estimate(
            decision_id=ctx.decision_id,
            subject_id=ctx.subject_id,
            subject_type=ctx.subject_type,
            version=ctx.version,
            evidence_result=ev_result,
            reasoning_result=re_result,
            historical_result=hi_result,
            calibration_result=CalibrationResult(  # placeholder; overwritten in stage 5
                raw_confidence=0.0,
                calibrated_conf=0.0,
                adjustment=0.0,
                status=CalibrationStatus.INSUFFICIENT_DATA,
                bucket_count=0,
                record_count=0,
                computed_at=start,
            ),
            scoring_confidence=scoring_conf,
            scoring_available=scoring_available,
        )
        ctx.overall_result = ov_result

        # ── Stage 5: Calibration ─────────────────────────────────────────
        raw_overall = ov_result.decision_confidence.overall_confidence
        cal_result = await loop.run_in_executor(
            None, self._cal.calibrate, raw_overall
        )
        ctx.calibration_result = cal_result

        # Rebuild with actual calibration
        ov_final = self._ov.estimate(
            decision_id=ctx.decision_id,
            subject_id=ctx.subject_id,
            subject_type=ctx.subject_type,
            version=ctx.version,
            evidence_result=ev_result,
            reasoning_result=re_result,
            historical_result=hi_result,
            calibration_result=cal_result,
            scoring_confidence=scoring_conf,
            scoring_available=scoring_available,
        )
        ctx.overall_result = ov_final

        # ── Stage 6: Snapshot + extra modules ────────────────────────────
        quality_grade = ConfidenceQualityGrade.from_score(
            ov_final.decision_confidence.overall_confidence
        )
        snapshot = build_confidence_snapshot(
            decision_confidence=ov_final.decision_confidence,
            evidence_snapshot_id=ctx.evidence_snapshot.snapshot_id,
            reasoning_snapshot_id=ctx.reasoning_snapshot.snapshot_id,
            scoring_snapshot_id=scoring_snap_id,
            calibration_status=cal_result.status,
            quality_grade=quality_grade,
            estimation_start=start,
            version=ctx.version,
        )

        # Extra pluggable modules (Bayesian, ensemble, etc.)
        for module in self._extra:
            await module.execute(ctx)

        return PipelineResult(
            snapshot=snapshot,
            evidence_result=ev_result,
            reasoning_result=re_result,
            historical_result=hi_result,
            calibration_result=cal_result,
        )
