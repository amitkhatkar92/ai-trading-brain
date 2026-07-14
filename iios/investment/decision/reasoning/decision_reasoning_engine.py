"""iios/investment/decision/reasoning/decision_reasoning_engine.py
DecisionReasoningEngine — main facade for the Decision Reasoning Engine.

Transformation pipeline:
  EvidenceSnapshot → ReasoningSnapshot

The engine is deterministic, auditable, traceable, and version-controlled.
It does NOT produce investment scores, recommendations, or confidence estimates.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.hypothesis_registry import HypothesisRegistry
from iios.investment.decision.reasoning.reasoning_confidence import ReasoningConfidence
from iios.investment.decision.reasoning.reasoning_constants import (
    DEFAULT_REASONING_TIMEOUT_SECS,
    ReasoningEngineStatus,
)
from iios.investment.decision.reasoning.reasoning_health import ReasoningHealth
from iios.investment.decision.reasoning.reasoning_history import ReasoningHistory
from iios.investment.decision.reasoning.reasoning_pipeline import (
    BaseReasoningModule,
    ReasoningContext,
    ReasoningPipeline,
)
from iios.investment.decision.reasoning.reasoning_quality import ReasoningQuality
from iios.investment.decision.reasoning.reasoning_snapshot import (
    ReasoningSnapshot,
    build_reasoning_snapshot,
)
from iios.investment.decision.reasoning.reasoning_statistics import ReasoningStatisticsTracker
from iios.investment.decision.reasoning.reasoning_trace import ReasoningTrace


class DecisionReasoningEngine:
    """
    Singleton-safe facade. Instantiate once per application.
    All public methods are thread-safe.

    Consumed by downstream Decision Intelligence engines via `reason()` /
    `reason_sync()`.  Returns an immutable `ReasoningSnapshot`.
    """

    def __init__(
        self,
        pipeline:    ReasoningPipeline          | None = None,
        history:     ReasoningHistory            | None = None,
        stats:       ReasoningStatisticsTracker  | None = None,
        quality:     ReasoningQuality            | None = None,
        confidence:  ReasoningConfidence         | None = None,
        health:      ReasoningHealth             | None = None,
        hyp_registry: HypothesisRegistry         | None = None,
        timeout_secs: float = DEFAULT_REASONING_TIMEOUT_SECS,
    ) -> None:
        self._lock        = threading.RLock()
        self._pipeline    = pipeline     or ReasoningPipeline()
        self._history     = history      or ReasoningHistory()
        self._stats       = stats        or ReasoningStatisticsTracker()
        self._quality     = quality      or ReasoningQuality()
        self._confidence  = confidence   or ReasoningConfidence()
        self._health      = health       or ReasoningHealth()
        self._hyp_reg     = hyp_registry or HypothesisRegistry()
        self._timeout     = timeout_secs
        self._status      = ReasoningEngineStatus.INITIALIZING
        self._ver_counter: Dict[str, int] = {}  # subject_id → version

    # ----------------------------------------------------------------- lifecycle

    def start(self) -> None:
        with self._lock:
            self._status = ReasoningEngineStatus.READY

    def stop(self) -> None:
        with self._lock:
            self._status = ReasoningEngineStatus.STOPPED

    @property
    def status(self) -> ReasoningEngineStatus:
        return self._status

    # ----------------------------------------------------------------- main API

    async def reason(
        self,
        evidence_snapshot: EvidenceSnapshot,
        decision_id:       Optional[str] = None,
    ) -> ReasoningSnapshot:
        """
        Async entry point.
        Receives an EvidenceSnapshot, returns a ReasoningSnapshot.
        """
        if not self._status.is_operational:
            raise RuntimeError(
                f"DecisionReasoningEngine is not operational (status={self._status.value})."
            )

        decision_id = decision_id or evidence_snapshot.decision_id
        subject_id  = evidence_snapshot.subject_id
        subject_type = evidence_snapshot.subject_type

        with self._lock:
            self._status = ReasoningEngineStatus.REASONING

        try:
            ctx = ReasoningContext(
                decision_id=decision_id,
                subject_id=subject_id,
                subject_type=subject_type,
                evidence_snapshot=evidence_snapshot,
            )
            pipeline_result = await self._pipeline.execute(ctx)

            # Compute quality and confidence
            qs = self._quality.score(
                chain=pipeline_result.chain,
                logic_result=pipeline_result.logic_result,
                total_evidence_items=evidence_snapshot.item_count,
            )
            self._confidence.compute(
                chain=pipeline_result.chain,
                logic_result=pipeline_result.logic_result,
                total_evidence_items=evidence_snapshot.item_count,
            )

            # Version
            with self._lock:
                version = self._ver_counter.get(subject_id, 0) + 1
                self._ver_counter[subject_id] = version

            snapshot = build_reasoning_snapshot(
                decision_id=decision_id,
                subject_id=subject_id,
                subject_type=subject_type,
                evidence_snapshot_id=evidence_snapshot.snapshot_id,
                chain=pipeline_result.chain,
                hypotheses=pipeline_result.hypotheses,
                argument_reports=pipeline_result.argument_reports,
                context_profile=pipeline_result.context_profile,
                logic_result=pipeline_result.logic_result,
                quality_score=qs,
                primary_hypothesis=pipeline_result.primary_hypothesis,
                version=version,
                reasoning_start=pipeline_result.reasoning_start,
            )

            # Persist
            self._history.record(snapshot)
            self._stats.record(snapshot)
            self._health.record_success(qs, snapshot.reasoning_duration_ms)
            self._hyp_reg.register(decision_id, list(pipeline_result.hypotheses))

        except Exception:
            self._health.record_failure()
            raise
        finally:
            with self._lock:
                if self._status == ReasoningEngineStatus.REASONING:
                    self._status = ReasoningEngineStatus.READY

        return snapshot

    def reason_sync(
        self,
        evidence_snapshot: EvidenceSnapshot,
        decision_id:       Optional[str] = None,
    ) -> ReasoningSnapshot:
        return asyncio.run(self.reason(evidence_snapshot, decision_id))

    # ----------------------------------------------------------------- query API

    def get_snapshot(self, snapshot_id: str) -> Optional[ReasoningSnapshot]:
        return self._history.get(snapshot_id)

    def get_history(self, subject_id: str) -> List[ReasoningSnapshot]:
        return self._history.for_subject(subject_id)

    def get_latest(self, subject_id: str) -> Optional[ReasoningSnapshot]:
        return self._history.latest_for_subject(subject_id)

    def get_trace(self, snapshot_id: str) -> Optional[ReasoningTrace]:
        snap = self._history.get(snapshot_id)
        if snap is None:
            return None
        return ReasoningTrace(snap.reasoning_chain)

    def get_hypotheses(self, decision_id: str):
        return self._hyp_reg.get_all(decision_id)

    def stats(self) -> Dict[str, Any]:
        return {
            "status":   self._status.value,
            "history":  self._history.stats(),
            "stats":    self._stats.summary().to_dict(),
            "health":   self._health.report().to_dict(),
        }
