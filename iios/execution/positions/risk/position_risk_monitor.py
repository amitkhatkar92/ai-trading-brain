"""iios/execution/positions/risk/position_risk_monitor.py
==================================================
RiskMonitor — pure evaluation service that determines the current
risk level and triggers for a single PositionRiskState.

NO LifecycleAwareMixin — stateless, reusable service.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from .constants import RiskEventType, RiskLevel
from .position_risk_limits import RiskLimits
from .position_risk_state import PositionRiskState
from .position_risk_threshold import RiskThreshold


@dataclass
class RiskEvaluationResult:
    """
    Outcome produced by ``RiskMonitor.evaluate()``.

    Consumers (usually ``PositionRiskManager``) apply these instructions
    back to the ``PositionRiskState`` and emit the listed events.
    """

    new_risk_level:         RiskLevel
    stop_loss_triggered:    bool
    take_profit_triggered:  bool
    liquidation_warning:    bool
    events_to_emit:         List[RiskEventType] = field(default_factory=list)
    drawdown_pct:           Decimal = Decimal("0")
    margin_utilization_pct: Decimal = Decimal("0")


class RiskMonitor:
    """
    Stateless risk evaluation engine.

    Algorithm
    ---------
    1. Compute drawdown_pct from peak_pnl.
    2. Compute margin_utilization_pct.
    3. Check stop-loss trigger conditions.
    4. Check take-profit trigger conditions.
    5. Map drawdown_pct → risk level via thresholds (highest wins).
    6. Map margin_pct   → risk level via thresholds (highest wins).
    7. Use the higher of the two levels as new_risk_level.
    8. Determine events to emit based on transitions and trigger flags.
    9. Return RiskEvaluationResult.
    """

    def evaluate(
        self,
        risk_state:  PositionRiskState,
        limits:      RiskLimits,
        thresholds:  RiskThreshold,
    ) -> RiskEvaluationResult:
        drawdown_pct   = risk_state.execution_drawdown_pct
        margin_pct     = risk_state.margin_utilization_pct
        unrealized     = risk_state.unrealized_pnl
        previous_level = risk_state.risk_level

        # ── Stop-loss trigger ─────────────────────────────────────────────────
        stop_loss_triggered = risk_state.stop_loss_triggered
        if not stop_loss_triggered:
            # Max-loss: |unrealized| >= max_loss when in a loss
            if unrealized < Decimal("0") and abs(unrealized) >= limits.max_loss:
                stop_loss_triggered = True
            # Stop-loss price: currently only flagged externally; price checks
            # are handled at execution layer

        # ── Take-profit trigger ───────────────────────────────────────────────
        take_profit_triggered = risk_state.take_profit_triggered
        if not take_profit_triggered and limits.has_take_profit:
            if unrealized >= limits.take_profit:  # type: ignore[operator]
                take_profit_triggered = True

        # ── Determine level from drawdown thresholds ──────────────────────────
        dd_level = self._level_from_drawdown(drawdown_pct, thresholds)

        # ── Determine level from margin thresholds ────────────────────────────
        mg_level = self._level_from_margin(margin_pct, thresholds)

        # ── Compose new level ─────────────────────────────────────────────────
        raw_level = max(dd_level, mg_level, key=lambda l: _LEVEL_RANK[l])

        # Adjust for active trigger flags
        if stop_loss_triggered or take_profit_triggered:
            raw_level = max(raw_level, RiskLevel.CRITICAL, key=lambda l: _LEVEL_RANK[l])

        # Liquidation check
        liq_warning = raw_level in (
            RiskLevel.LIQUIDATION_PENDING, RiskLevel.LIQUIDATED
        )

        # Keep LIQUIDATED terminal — cannot de-escalate
        if risk_state.liquidation_state:
            raw_level = RiskLevel.LIQUIDATED

        # ── Build events list ─────────────────────────────────────────────────
        events: List[RiskEventType] = [RiskEventType.RISK_EVALUATED]

        if raw_level != previous_level:
            events.append(RiskEventType.RISK_UPDATED)

        if raw_level == RiskLevel.WARNING and previous_level != RiskLevel.WARNING:
            events.append(RiskEventType.RISK_WARNING)

        if raw_level == RiskLevel.CRITICAL and previous_level != RiskLevel.CRITICAL:
            events.append(RiskEventType.RISK_CRITICAL)

        if liq_warning and not risk_state.liquidation_warning:
            events.append(RiskEventType.LIQUIDATION_WARNING)

        if stop_loss_triggered and not risk_state.stop_loss_triggered:
            events.append(RiskEventType.STOP_LOSS_TRIGGERED)

        if take_profit_triggered and not risk_state.take_profit_triggered:
            events.append(RiskEventType.TAKE_PROFIT_TRIGGERED)

        if (
            previous_level not in (RiskLevel.NORMAL, RiskLevel.RECOVERED)
            and raw_level in (RiskLevel.NORMAL, RiskLevel.RECOVERING, RiskLevel.RECOVERED)
        ):
            events.append(RiskEventType.RISK_RECOVERED)

        return RiskEvaluationResult(
            new_risk_level=raw_level,
            stop_loss_triggered=stop_loss_triggered,
            take_profit_triggered=take_profit_triggered,
            liquidation_warning=liq_warning,
            events_to_emit=events,
            drawdown_pct=drawdown_pct,
            margin_utilization_pct=margin_pct,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _level_from_drawdown(
        drawdown_pct: Decimal,
        t:            RiskThreshold,
    ) -> RiskLevel:
        if drawdown_pct >= t.liquidation_drawdown_pct:
            return RiskLevel.LIQUIDATION_PENDING
        if drawdown_pct >= t.critical_drawdown_pct:
            return RiskLevel.CRITICAL
        if drawdown_pct >= t.warning_drawdown_pct:
            return RiskLevel.WARNING
        if drawdown_pct >= t.watch_drawdown_pct:
            return RiskLevel.WATCH
        return RiskLevel.NORMAL

    @staticmethod
    def _level_from_margin(
        margin_pct: Decimal,
        t:          RiskThreshold,
    ) -> RiskLevel:
        if margin_pct >= t.liquidation_margin_pct:
            return RiskLevel.LIQUIDATION_PENDING
        if margin_pct >= t.critical_margin_pct:
            return RiskLevel.CRITICAL
        if margin_pct >= t.warning_margin_pct:
            return RiskLevel.WARNING
        if margin_pct >= t.watch_margin_pct:
            return RiskLevel.WATCH
        return RiskLevel.NORMAL


# ── Level rank (higher = more severe) ─────────────────────────────────────────

_LEVEL_RANK: dict[RiskLevel, int] = {
    RiskLevel.NORMAL:              0,
    RiskLevel.RECOVERING:          0,
    RiskLevel.RECOVERED:           0,
    RiskLevel.WATCH:               1,
    RiskLevel.WARNING:             2,
    RiskLevel.CRITICAL:            3,
    RiskLevel.LIQUIDATION_PENDING: 4,
    RiskLevel.LIQUIDATED:          5,
}
