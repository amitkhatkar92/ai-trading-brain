"""iios/investment/strategy/core/strategy_session.py
Per-execution-cycle session tracking for institutional strategies.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .strategy_state import StrategyState


@dataclass
class SessionMetrics:
    """Counters gathered during a single execution cycle."""
    candidates_screened: int = 0
    candidates_evaluated: int = 0
    signals_generated: int = 0
    signals_validated: int = 0
    signals_rejected: int = 0
    risk_rejections: int = 0
    plan_produced: bool = False
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "candidates_screened": self.candidates_screened,
            "candidates_evaluated": self.candidates_evaluated,
            "signals_generated": self.signals_generated,
            "signals_validated": self.signals_validated,
            "signals_rejected": self.signals_rejected,
            "risk_rejections": self.risk_rejections,
            "plan_produced": self.plan_produced,
            "latency_ms": round(self.latency_ms, 3),
        }


@dataclass
class StrategySession:
    """Tracks the full lifecycle of a single execution cycle."""
    session_id: str = field(
        default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}"
    )
    strategy_id: str = ""
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    state: StrategyState = StrategyState.RUNNING
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    error: Optional[str] = None
    plan_id: Optional[str] = None
    symbol_count: int = 0

    @property
    def duration_ms(self) -> float:
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds() * 1_000

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def succeeded(self) -> bool:
        return self.plan_id is not None and not self.error

    def close(
        self,
        plan_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.plan_id = plan_id
        self.error = error
        self.state = StrategyState.FAILED if error else StrategyState.COMPLETED
        self.metrics.latency_ms = self.duration_ms
        self.metrics.plan_produced = plan_id is not None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "strategy_id": self.strategy_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "state": self.state.value,
            "duration_ms": round(self.duration_ms, 3),
            "plan_id": self.plan_id,
            "error": self.error,
            "symbol_count": self.symbol_count,
            "metrics": self.metrics.to_dict(),
        }
