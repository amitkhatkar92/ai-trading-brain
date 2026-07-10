"""core/backtest.py — The primary backtest entity that tracks lifecycle."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import BacktestStatus
from iios.integration.research.backtesting.core.backtest_configuration import BacktestConfiguration
from iios.integration.research.backtesting.core.backtest_metadata import BacktestMetadata


@dataclass
class Backtest:
    """
    Persistent entity representing one backtest run.

    Created by BacktestManager, stored in BacktestRegistry,
    updated as the simulation progresses.
    """

    strategy_id:    str                     = ""
    strategy_name:  str                     = ""
    configuration:  BacktestConfiguration   = field(default_factory=BacktestConfiguration)

    backtest_id:    str                     = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str                     = ""
    status:         BacktestStatus          = BacktestStatus.PENDING

    session_id:     Optional[str]           = None
    result_id:      Optional[str]           = None
    error_message:  Optional[str]           = None

    created_at:     float                   = field(default_factory=time.time)
    updated_at:     float                   = field(default_factory=time.time)
    started_at:     Optional[float]         = None
    completed_at:   Optional[float]         = None

    tags:           list[str]               = field(default_factory=list)
    metadata:       BacktestMetadata        = field(default_factory=BacktestMetadata)

    # ── State helpers ─────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.status in (
            BacktestStatus.COMPLETED,
            BacktestStatus.FAILED,
            BacktestStatus.CANCELLED,
            BacktestStatus.ARCHIVED,
        )

    def is_running(self) -> bool:
        return self.status == BacktestStatus.RUNNING

    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at if self.completed_at is not None else time.time()
        return end - self.started_at

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "backtest_id":   self.backtest_id,
            "request_id":    self.request_id,
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "status":        self.status.value,
            "session_id":    self.session_id,
            "result_id":     self.result_id,
            "error_message": self.error_message,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
            "started_at":    self.started_at,
            "completed_at":  self.completed_at,
            "elapsed_sec":   self.elapsed_sec(),
            "tags":          list(self.tags),
            "configuration": self.configuration.to_dict(),
            "metadata":      self.metadata.to_dict(),
        }
