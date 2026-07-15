"""iios/investment/workflow/workflow_history.py
WorkflowRunRecord — immutable record of one completed pipeline run.
WorkflowHistory — bounded thread-safe history of completed runs.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from iios.investment.workflow.workflow_types import WorkflowStage


@dataclass(frozen=True)
class WorkflowRunRecord:
    """
    Immutable audit record for one completed workflow run.
    Stored in WorkflowHistory for query and replay.
    """

    run_id:              str              # globally unique run identifier
    workflow_id:         str              # identity of the workflow class
    request_id:          str              # originating InvestmentRequest ID
    portfolio_id:        str              # portfolio that was updated
    started_at:          str              # ISO-8601 UTC
    completed_at:        str              # ISO-8601 UTC
    terminal_stage:      WorkflowStage    # PUBLISHED / FAILED / CANCELLED
    total_duration_ms:   float
    n_stages_completed:  int
    n_retries:           int
    n_errors:            int
    n_warnings:          int
    snapshot_id:         Optional[str]    # ID of published PortfolioIntelligenceSnapshot
    market_quality:      Optional[float]  # 0.0-1.0
    company_quality:     Optional[float]
    strategy_quality:    Optional[float]
    decision_quality:    Optional[float]
    portfolio_quality:   Optional[float]
    is_published:        bool
    errors:              tuple            # tuple of str
    warnings:            tuple            # tuple of str
    stage_durations_ms:  Dict[str, float] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.terminal_stage == WorkflowStage.PUBLISHED

    def to_dict(self) -> dict:
        return {
            "run_id":             self.run_id,
            "workflow_id":        self.workflow_id,
            "request_id":         self.request_id,
            "portfolio_id":       self.portfolio_id,
            "started_at":         self.started_at,
            "completed_at":       self.completed_at,
            "terminal_stage":     self.terminal_stage.value,
            "total_duration_ms":  round(self.total_duration_ms, 2),
            "n_stages_completed": self.n_stages_completed,
            "n_retries":          self.n_retries,
            "n_errors":           self.n_errors,
            "n_warnings":         self.n_warnings,
            "snapshot_id":        self.snapshot_id,
            "market_quality":     self.market_quality,
            "company_quality":    self.company_quality,
            "strategy_quality":   self.strategy_quality,
            "decision_quality":   self.decision_quality,
            "portfolio_quality":  self.portfolio_quality,
            "is_published":       self.is_published,
            "succeeded":          self.succeeded,
            "errors":             list(self.errors),
            "warnings":           list(self.warnings),
            "stage_durations_ms": self.stage_durations_ms,
        }


class WorkflowHistory:
    """
    Thread-safe bounded history of completed workflow runs.

    Supports query by portfolio_id, success status, and most-recent records.
    """

    def __init__(self, max_runs: int = 200) -> None:
        if max_runs < 1:
            raise ValueError("max_runs must be >= 1")
        self._max    = max_runs
        self._lock   = threading.RLock()
        self._runs:  Deque[WorkflowRunRecord] = deque(maxlen=max_runs)
        # Index by run_id for O(1) lookup
        self._index: Dict[str, WorkflowRunRecord] = {}

    def add(self, record: WorkflowRunRecord) -> None:
        """Append a completed run record."""
        with self._lock:
            if len(self._runs) == self._max and self._runs:
                oldest = self._runs[0]
                self._index.pop(oldest.run_id, None)
            self._runs.append(record)
            self._index[record.run_id] = record

    def get(self, run_id: str) -> Optional[WorkflowRunRecord]:
        with self._lock:
            return self._index.get(run_id)

    def recent(self, n: int = 20) -> List[WorkflowRunRecord]:
        """Most recent *n* runs, newest-first."""
        with self._lock:
            result = list(self._runs)
        result.reverse()
        return result[:n]

    def for_portfolio(self, portfolio_id: str, n: int = 20) -> List[WorkflowRunRecord]:
        """Runs for a specific portfolio, newest-first."""
        with self._lock:
            result = [r for r in self._runs if r.portfolio_id == portfolio_id]
        result.reverse()
        return result[:n]

    def successful(self, n: int = 20) -> List[WorkflowRunRecord]:
        """Most recent *n* successful (PUBLISHED) runs."""
        with self._lock:
            result = [r for r in self._runs if r.succeeded]
        result.reverse()
        return result[:n]

    def failed(self, n: int = 20) -> List[WorkflowRunRecord]:
        """Most recent *n* failed runs."""
        with self._lock:
            result = [r for r in self._runs if not r.succeeded]
        result.reverse()
        return result[:n]

    @property
    def total_runs(self) -> int:
        with self._lock:
            return len(self._runs)

    @property
    def total_successful(self) -> int:
        with self._lock:
            return sum(1 for r in self._runs if r.succeeded)

    def to_dict(self) -> dict:
        with self._lock:
            runs = list(self._runs)
        return {
            "total_runs":       len(runs),
            "total_successful": sum(1 for r in runs if r.succeeded),
            "recent":           [r.to_dict() for r in reversed(runs)][:10],
        }
