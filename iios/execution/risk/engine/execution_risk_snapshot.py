"""iios/execution/risk/engine/execution_risk_snapshot.py
==================================================
Snapshot types for the Execution Risk Engine.

EvaluationSummary  — lightweight per-evaluation summary.
RiskEngineSnapshot — point-in-time snapshot of the full engine state.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.execution.risk.lifecycle import ExecutionRisk

from .constants import VERSION
from .execution_risk_statistics import EngineRiskStatistics


# ── EvaluationSummary ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvaluationSummary:
    """Lightweight, serialisable summary of a single evaluation."""

    evaluation_id:  str
    risk_category:  str     # RiskCategory.value
    state:          str     # RiskState.value
    outcome:        Optional[str]   # set only after evaluation finishes
    rule_count:     int
    elapsed_ms:     float
    portfolio_id:   str
    strategy_id:    str
    execution_id:   str
    created_at:     float

    @classmethod
    def from_risk(
        cls,
        risk:       ExecutionRisk,
        rule_count: int   = 0,
        elapsed_ms: float = 0.0,
    ) -> "EvaluationSummary":
        return cls(
            evaluation_id=risk.risk_id,
            risk_category=risk.risk_category.value,
            state=risk.state.value,
            outcome=None,           # outcome resolved by caller if needed
            rule_count=rule_count,
            elapsed_ms=elapsed_ms,
            portfolio_id=risk.portfolio_id,
            strategy_id=risk.strategy_id,
            execution_id=risk.execution_id,
            created_at=risk.created_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "risk_category": self.risk_category,
            "state":         self.state,
            "outcome":       self.outcome,
            "rule_count":    self.rule_count,
            "elapsed_ms":    self.elapsed_ms,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "execution_id":  self.execution_id,
            "created_at":    self.created_at,
        }


# ── RiskEngineSnapshot ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RiskEngineSnapshot:
    """
    Immutable point-in-time snapshot of the Execution Risk Engine state.

    Produced by ``RiskEngine.snapshot()`` and ``RiskManager.snapshot()``.
    """

    snapshot_id:           str
    total_evaluations:     int
    active_count:          int
    passed_count:          int
    blocked_count:         int
    failed_count:          int
    registered_rule_count: int
    summaries:             Tuple[EvaluationSummary, ...]
    statistics:            EngineRiskStatistics
    taken_at:              float
    version:               str = VERSION
    metadata:              Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return self.total_evaluations == 0

    @property
    def is_healthy(self) -> bool:
        """True if no evaluations are in a failed state."""
        return self.failed_count == 0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "total_evaluations":     self.total_evaluations,
            "active_count":          self.active_count,
            "passed_count":          self.passed_count,
            "blocked_count":         self.blocked_count,
            "failed_count":          self.failed_count,
            "registered_rule_count": self.registered_rule_count,
            "summaries":             [s.to_dict() for s in self.summaries],
            "statistics":            self.statistics.to_dict(),
            "taken_at":              self.taken_at,
            "version":               self.version,
            "is_empty":              self.is_empty,
            "is_healthy":            self.is_healthy,
            "metadata":              dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_engine_risk_snapshot(
    evaluations: List[ExecutionRisk],
    statistics:  EngineRiskStatistics,
    rule_count:  int,
    *,
    metadata: Dict[str, Any] | None = None,
) -> RiskEngineSnapshot:
    """Build a ``RiskEngineSnapshot`` from live registry state."""
    from iios.execution.risk.lifecycle import RiskState

    active_states  = {RiskState.PENDING_EVALUATION, RiskState.EVALUATING}
    pass_states    = {RiskState.PASSED, RiskState.WARNING, RiskState.OVERRIDDEN}
    blocked_states = {RiskState.BLOCKED}
    failed_states  = {RiskState.FAILED}

    active_count  = sum(1 for r in evaluations if r.state in active_states)
    passed_count  = sum(1 for r in evaluations if r.state in pass_states)
    blocked_count = sum(1 for r in evaluations if r.state in blocked_states)
    failed_count  = sum(1 for r in evaluations if r.state in failed_states)

    summaries = tuple(EvaluationSummary.from_risk(r) for r in evaluations)

    return RiskEngineSnapshot(
        snapshot_id=str(uuid.uuid4()),
        total_evaluations=len(evaluations),
        active_count=active_count,
        passed_count=passed_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        registered_rule_count=rule_count,
        summaries=summaries,
        statistics=statistics,
        taken_at=time.time(),
        metadata=metadata or {},
    )
