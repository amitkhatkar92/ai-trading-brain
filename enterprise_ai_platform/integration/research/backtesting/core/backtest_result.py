"""core/backtest_result.py — Immutable result produced after a simulation completes."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BacktestResult:
    """
    Stores every artefact produced by a completed backtest run.

    - equity_curve: list of (unix_timestamp, portfolio_equity)
    - trade_log:    list of trade dictionaries (one per completed trade)
    - metrics:      flat dict of all computed performance metrics
    - report:       structured report dict produced by ReportGenerator
    """

    backtest_id:  str                                   = ""
    result_id:    str                                   = field(default_factory=lambda: str(uuid.uuid4()))
    is_success:   bool                                  = False

    # ── Core artefacts ────────────────────────────────────────────────────────
    equity_curve: list[tuple[float, float]]             = field(default_factory=list)
    trade_log:    list[dict[str, Any]]                  = field(default_factory=list)
    metrics:      dict[str, Any]                        = field(default_factory=dict)
    report:       dict[str, Any]                        = field(default_factory=dict)

    # ── Summary ───────────────────────────────────────────────────────────────
    bar_count:    int                                   = 0
    trade_count:  int                                   = 0
    duration_sec: float                                 = 0.0
    error:        Optional[str]                         = None

    created_at:   float                                 = field(default_factory=time.time)
    metadata:     dict[str, Any]                        = field(default_factory=dict)

    # ── Metric accessors ──────────────────────────────────────────────────────

    def has_metric(self, key: str) -> bool:
        return key in self.metrics

    def get_metric(self, key: str, default: Any = None) -> Any:
        return self.metrics.get(key, default)

    def add_trade(self, trade: dict[str, Any]) -> None:
        self.trade_log.append(trade)
        self.trade_count = len(self.trade_log)

    def set_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":    self.result_id,
            "backtest_id":  self.backtest_id,
            "is_success":   self.is_success,
            "bar_count":    self.bar_count,
            "trade_count":  self.trade_count,
            "duration_sec": self.duration_sec,
            "error":        self.error,
            "metrics":      dict(self.metrics),
            "report":       dict(self.report),
            "created_at":   self.created_at,
        }
