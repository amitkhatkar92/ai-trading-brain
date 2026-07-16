"""iios/execution/positions/risk/position_risk_threshold.py
==================================================
RiskThreshold — escalation thresholds for the Position Risk module.

Defines the percentage levels at which the risk level escalates from
NORMAL → WATCH → WARNING → CRITICAL → LIQUIDATION_PENDING.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from .constants import (
    DEFAULT_CRITICAL_DRAWDOWN_PCT,
    DEFAULT_CRITICAL_MARGIN_PCT,
    DEFAULT_LIQUIDATION_DRAWDOWN_PCT,
    DEFAULT_LIQUIDATION_MARGIN_PCT,
    DEFAULT_WARNING_DRAWDOWN_PCT,
    DEFAULT_WARNING_MARGIN_PCT,
    DEFAULT_WATCH_DRAWDOWN_PCT,
    DEFAULT_WATCH_MARGIN_PCT,
)
from .exceptions import RiskLimitsError


@dataclass(frozen=True)
class RiskThreshold:
    """
    Escalation thresholds used by ``RiskMonitor`` when evaluating
    the current risk level of a position.

    Drawdown thresholds are fractions of ``peak_pnl`` (0–1).
    Margin thresholds are fractions of total margin capacity (0–1).

    Evaluation order
    ~~~~~~~~~~~~~~~~
    1. If drawdown ≥ liquidation_drawdown_pct  → LIQUIDATION_PENDING
    2. If drawdown ≥ critical_drawdown_pct     → CRITICAL
    3. If drawdown ≥ warning_drawdown_pct      → WARNING
    4. If drawdown ≥ watch_drawdown_pct        → WATCH
    5. Same logic applied to margin_pct
    6. Highest of the two determines the risk level.
    7. Recovery path: level only de-escalates one step per evaluation.
    """

    # Drawdown thresholds (fraction of peak PnL)
    watch_drawdown_pct:       Decimal = DEFAULT_WATCH_DRAWDOWN_PCT
    warning_drawdown_pct:     Decimal = DEFAULT_WARNING_DRAWDOWN_PCT
    critical_drawdown_pct:    Decimal = DEFAULT_CRITICAL_DRAWDOWN_PCT
    liquidation_drawdown_pct: Decimal = DEFAULT_LIQUIDATION_DRAWDOWN_PCT

    # Margin utilization thresholds (fraction of total margin)
    watch_margin_pct:         Decimal = DEFAULT_WATCH_MARGIN_PCT
    warning_margin_pct:       Decimal = DEFAULT_WARNING_MARGIN_PCT
    critical_margin_pct:      Decimal = DEFAULT_CRITICAL_MARGIN_PCT
    liquidation_margin_pct:   Decimal = DEFAULT_LIQUIDATION_MARGIN_PCT

    def __post_init__(self) -> None:
        # Verify drawdown thresholds are ordered
        if not (self.watch_drawdown_pct
                < self.warning_drawdown_pct
                < self.critical_drawdown_pct
                < self.liquidation_drawdown_pct):
            raise RiskLimitsError(
                "Drawdown thresholds must be strictly increasing: "
                "watch < warning < critical < liquidation"
            )
        # Verify margin thresholds are ordered
        if not (self.watch_margin_pct
                < self.warning_margin_pct
                < self.critical_margin_pct
                <= self.liquidation_margin_pct):
            raise RiskLimitsError(
                "Margin thresholds must be strictly increasing: "
                "watch < warning < critical ≤ liquidation"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "watch_drawdown_pct":       str(self.watch_drawdown_pct),
            "warning_drawdown_pct":     str(self.warning_drawdown_pct),
            "critical_drawdown_pct":    str(self.critical_drawdown_pct),
            "liquidation_drawdown_pct": str(self.liquidation_drawdown_pct),
            "watch_margin_pct":         str(self.watch_margin_pct),
            "warning_margin_pct":       str(self.warning_margin_pct),
            "critical_margin_pct":      str(self.critical_margin_pct),
            "liquidation_margin_pct":   str(self.liquidation_margin_pct),
        }


# ── Default instance ──────────────────────────────────────────────────────────

DEFAULT_RISK_THRESHOLDS = RiskThreshold()
