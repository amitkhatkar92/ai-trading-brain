"""iios/execution/positions/risk/position_risk_events.py
==================================================
RiskEvent — immutable domain event emitted when risk state changes.
Factory functions for each of the 8 risk event types.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .constants import ACTOR_RISK, VERSION, RiskEventType, RiskLevel


@dataclass(frozen=True)
class RiskEvent:
    """
    Immutable record of a single risk state change or trigger.
    """

    event_id:        str
    event_type:      RiskEventType
    position_id:     str
    portfolio_id:    str
    strategy_id:     str
    risk_level:      RiskLevel
    previous_level:  Optional[RiskLevel]
    drawdown_pct:    Decimal
    margin_pct:      Decimal
    unrealized_pnl:  Decimal
    correlation_id:  str
    emitted_by:      str
    occurred_at:     float
    version:         str = VERSION
    metadata:        Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "position_id":    self.position_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "risk_level":     self.risk_level.value,
            "previous_level": self.previous_level.value if self.previous_level else None,
            "drawdown_pct":   str(self.drawdown_pct),
            "margin_pct":     str(self.margin_pct),
            "unrealized_pnl": str(self.unrealized_pnl),
            "correlation_id": self.correlation_id,
            "emitted_by":     self.emitted_by,
            "occurred_at":    self.occurred_at,
            "version":        self.version,
        }


# ── Internal factory ─────────────────────────────────────────────────────────

def _make_event(
    event_type:     RiskEventType,
    position_id:    str,
    risk_level:     RiskLevel,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    *,
    portfolio_id:   str = "",
    strategy_id:    str = "",
    previous_level: Optional[RiskLevel] = None,
    correlation_id: str = "",
    emitted_by:     str = ACTOR_RISK,
    metadata:       Optional[Dict[str, Any]] = None,
) -> RiskEvent:
    return RiskEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        risk_level=risk_level,
        previous_level=previous_level,
        drawdown_pct=drawdown_pct,
        margin_pct=margin_pct,
        unrealized_pnl=unrealized_pnl,
        correlation_id=correlation_id,
        emitted_by=emitted_by,
        occurred_at=time.time(),
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_risk_evaluated_event(
    position_id:    str,
    risk_level:     RiskLevel,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_EVALUATED,
        position_id, risk_level,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_risk_updated_event(
    position_id:    str,
    risk_level:     RiskLevel,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_UPDATED,
        position_id, risk_level,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_risk_warning_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_WARNING,
        position_id, RiskLevel.WARNING,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_risk_critical_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_CRITICAL,
        position_id, RiskLevel.CRITICAL,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_stop_loss_triggered_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.STOP_LOSS_TRIGGERED,
        position_id, RiskLevel.CRITICAL,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_take_profit_triggered_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.TAKE_PROFIT_TRIGGERED,
        position_id, RiskLevel.NORMAL,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_liquidation_warning_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.LIQUIDATION_WARNING,
        position_id, RiskLevel.LIQUIDATION_PENDING,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )


def make_risk_recovered_event(
    position_id:    str,
    drawdown_pct:   Decimal,
    margin_pct:     Decimal,
    unrealized_pnl: Decimal,
    **kwargs: Any,
) -> RiskEvent:
    return _make_event(
        RiskEventType.RISK_RECOVERED,
        position_id, RiskLevel.RECOVERED,
        drawdown_pct, margin_pct, unrealized_pnl,
        **kwargs,
    )
