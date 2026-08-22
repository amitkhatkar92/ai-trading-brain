"""
mlc_models.py — Data models for MarketLearningCoordinator.

Output models for the MLC pipeline runs, stages, telemetry, and health.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── Enumerations ─────────────────────────────────────────────────────────────

class LearningStageType(Enum):
    STRATEGY_LEARNING   = "strategy_learning"
    AMLS                = "amls"
    DNA_REINFORCEMENT   = "dna_reinforcement"
    IDR_REFRESH         = "idr_refresh"
    PIG_REFRESH         = "pig_refresh"
    SUMMARY             = "summary"


class LearningStageStatus(Enum):
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    COMPLETE  = "COMPLETE"
    FAILED    = "FAILED"
    SKIPPED   = "SKIPPED"


class LearningHealth(Enum):
    HEALTHY  = "HEALTHY"    # all enabled stages completed
    DEGRADED = "DEGRADED"   # one or more stages failed but pipeline finished
    FAILED   = "FAILED"     # pipeline aborted or all critical stages failed


# ─── Stage ────────────────────────────────────────────────────────────────────

@dataclass
class LearningStage:
    """Record for one pipeline stage."""
    stage_type:   LearningStageType
    name:         str
    status:       LearningStageStatus         = LearningStageStatus.PENDING
    started_at:   Optional[str]               = None
    ended_at:     Optional[str]               = None
    duration_ms:  Optional[float]             = None
    output:       Dict[str, Any]              = field(default_factory=dict)
    error:        Optional[str]               = None

    def mark_start(self) -> None:
        self.status     = LearningStageStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def mark_complete(self, output: Optional[Dict[str, Any]] = None) -> None:
        self.status    = LearningStageStatus.COMPLETE
        self.ended_at  = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self.output    = output or {}
        self._calc_duration()

    def mark_failed(self, error: str) -> None:
        self.status   = LearningStageStatus.FAILED
        self.ended_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self.error    = error
        self._calc_duration()

    def mark_skipped(self, reason: str = "") -> None:
        self.status = LearningStageStatus.SKIPPED
        self.error  = reason or None

    def _calc_duration(self) -> None:
        try:
            if self.started_at and self.ended_at:
                t0 = datetime.fromisoformat(self.started_at)
                t1 = datetime.fromisoformat(self.ended_at)
                self.duration_ms = (t1 - t0).total_seconds() * 1000.0
        except Exception:
            pass

    @property
    def succeeded(self) -> bool:
        return self.status == LearningStageStatus.COMPLETE

    @property
    def failed(self) -> bool:
        return self.status == LearningStageStatus.FAILED


# ─── Telemetry ────────────────────────────────────────────────────────────────

@dataclass
class LearningTelemetry:
    """Aggregate counters collected across all pipeline stages."""
    # Stage 1 — Strategy Learning
    strategy_learning_ran:  bool = False
    trades_processed:       int  = 0

    # Stage 2 — AMLS
    amls_ran:               bool = False
    dna_updated:            bool = False
    amls_duration_ms:       float = 0.0

    # Stage 3 — DNA Reinforcement
    dre_ran:                bool = False
    dna_reinforced:         int  = 0
    dre_trades_attempted:   int  = 0

    # Stage 4 — IDR Refresh
    repository_updates:     int  = 0
    idr_total_dna:          int  = 0

    # Stage 5 — PIG Refresh
    gateway_refresh:        bool = False

    # Summary
    knowledge_generated:    int  = 0  # total IDR + DRE writes


# ─── Run ──────────────────────────────────────────────────────────────────────

@dataclass
class LearningRun:
    """Complete record for one MarketLearningCoordinator pipeline execution."""
    run_id:           str
    trading_date:     str
    started_at:       str
    ended_at:         Optional[str]   = None
    total_duration_ms: Optional[float] = None
    stages:           List[LearningStage] = field(default_factory=list)
    telemetry:        Optional[LearningTelemetry] = None
    health:           LearningHealth  = LearningHealth.HEALTHY

    def stage(self, stage_type: LearningStageType) -> Optional[LearningStage]:
        """Return the stage record for the given type, or None."""
        for s in self.stages:
            if s.stage_type == stage_type:
                return s
        return None

    @property
    def stages_ok(self) -> int:
        return sum(1 for s in self.stages if s.succeeded)

    @property
    def stages_failed(self) -> int:
        return sum(1 for s in self.stages if s.failed)

    @property
    def stages_skipped(self) -> int:
        return sum(1 for s in self.stages
                   if s.status == LearningStageStatus.SKIPPED)

    def to_dict(self) -> Dict[str, Any]:
        tel = self.telemetry
        return {
            "run_id":            self.run_id,
            "trading_date":      self.trading_date,
            "started_at":        self.started_at,
            "ended_at":          self.ended_at,
            "total_duration_ms": self.total_duration_ms,
            "health":            self.health.value,
            "stages_ok":         self.stages_ok,
            "stages_failed":     self.stages_failed,
            "stages_skipped":    self.stages_skipped,
            "telemetry": {
                "strategy_learning_ran": tel.strategy_learning_ran if tel else False,
                "trades_processed":      tel.trades_processed      if tel else 0,
                "amls_ran":              tel.amls_ran               if tel else False,
                "dna_updated":           tel.dna_updated            if tel else False,
                "dre_ran":               tel.dre_ran                if tel else False,
                "dna_reinforced":        tel.dna_reinforced         if tel else 0,
                "repository_updates":    tel.repository_updates     if tel else 0,
                "gateway_refresh":       tel.gateway_refresh        if tel else False,
                "knowledge_generated":   tel.knowledge_generated    if tel else 0,
            } if tel else None,
            "stages": [
                {
                    "name":        s.name,
                    "stage_type":  s.stage_type.value,
                    "status":      s.status.value,
                    "duration_ms": s.duration_ms,
                    "error":       s.error,
                }
                for s in self.stages
            ],
        }


# ─── Summary ──────────────────────────────────────────────────────────────────

@dataclass
class LearningSummary:
    """High-level summary returned by status()."""
    run_id:             str
    trading_date:       str
    stages_total:       int
    stages_ok:          int
    stages_failed:      int
    stages_skipped:     int
    total_duration_ms:  float
    pipeline_healthy:   bool
    health:             LearningHealth
    telemetry:          Optional[LearningTelemetry] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":            self.run_id,
            "trading_date":      self.trading_date,
            "stages_total":      self.stages_total,
            "stages_ok":         self.stages_ok,
            "stages_failed":     self.stages_failed,
            "stages_skipped":    self.stages_skipped,
            "total_duration_ms": self.total_duration_ms,
            "pipeline_healthy":  self.pipeline_healthy,
            "health":            self.health.value,
        }


# ─── Exceptions ───────────────────────────────────────────────────────────────

class MLCError(Exception):
    """Base exception for MarketLearningCoordinator errors."""


class MLCStageError(MLCError):
    """Raised when a critical stage fails unrecoverably."""
    def __init__(self, stage_name: str, reason: str):
        super().__init__(f"[MLC] Stage '{stage_name}' error: {reason}")
        self.stage_name = stage_name
        self.reason     = reason


# ─── Factory helpers ──────────────────────────────────────────────────────────

def make_run_id(trading_date: str) -> str:
    """Generate a deterministic run ID for a given trading date."""
    uid = str(uuid.uuid4())[:8]
    return f"mlc-{trading_date}-{uid}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
