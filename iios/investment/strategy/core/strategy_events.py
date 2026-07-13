"""iios/investment/strategy/core/strategy_events.py
Institutional strategy event definitions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class StrategyEventType(str, Enum):
    """All event types emitted by the institutional strategy framework."""
    # Lifecycle
    STRATEGY_REGISTERED  = "strategy.registered"
    STRATEGY_LOADED      = "strategy.loaded"
    STRATEGY_INITIALIZED = "strategy.initialized"
    STRATEGY_READY       = "strategy.ready"
    STRATEGY_STARTED     = "strategy.started"
    STRATEGY_PAUSED      = "strategy.paused"
    STRATEGY_RESUMED     = "strategy.resumed"
    STRATEGY_COMPLETED   = "strategy.completed"
    STRATEGY_FAILED      = "strategy.failed"
    STRATEGY_ARCHIVED    = "strategy.archived"
    STRATEGY_UNLOADED    = "strategy.unloaded"
    # Signal pipeline
    SIGNAL_GENERATED     = "signal.generated"
    SIGNAL_VALIDATED     = "signal.validated"
    SIGNAL_REJECTED      = "signal.rejected"
    # Execution
    PLAN_CREATED         = "plan.created"
    TRADE_SUBMITTED      = "trade.submitted"
    TRADE_FILLED         = "trade.filled"
    TRADE_REJECTED       = "trade.rejected"
    # Risk
    RISK_REJECTED        = "risk.rejected"
    # Configuration
    CONFIG_UPDATED       = "config.updated"
    # Diagnostics
    ERROR                = "error"
    WARNING              = "warning"
    HEALTH_CHECK         = "health.check"


@dataclass
class StrategyEvent:
    """Immutable event record emitted by the institutional strategy framework."""
    event_type: StrategyEventType
    strategy_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    severity: str = "info"               # debug | info | warning | error | critical
    event_id: str = field(
        default_factory=lambda: f"sev-{uuid.uuid4().hex[:10]}"
    )
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "strategy_id": self.strategy_id,
            "session_id": self.session_id,
            "severity": self.severity,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }
