"""iios/execution/positions/risk/position_risk_limits.py
==================================================
RiskLimits — per-position risk limit configuration.

Defines the absolute and relative thresholds that determine when
risk events such as stop-loss and take-profit are triggered.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .constants import DEFAULT_MAX_EXPOSURE, DEFAULT_MAX_LOSS, VERSION
from .exceptions import RiskLimitsError


@dataclass(frozen=True)
class RiskLimits:
    """
    Per-position execution risk limits.

    Fields
    ------
    max_loss
        Maximum absolute loss in currency units before stop-loss fires.
        Compared against ``(-unrealized_pnl)``.  Must be > 0.

    take_profit
        Maximum absolute gain before take-profit fires.
        ``None`` means no take-profit limit.  When set, must be > 0.

    max_drawdown_pct
        Maximum drawdown as a fraction of peak unrealized PnL (0–1).
        E.g. ``Decimal("0.50")`` = 50% drawdown from peak triggers action.

    max_exposure
        Maximum current market exposure in currency units.
        ``Decimal("0")`` means no exposure limit.

    max_margin_utilization_pct
        Maximum fraction of total margin that may be consumed (0–1).
        E.g. ``Decimal("0.90")`` = 90% utilization ceiling.

    stop_loss_price
        Optional specific price level below which stop-loss fires
        (for LONG positions; for SHORT positions the logic is reversed).

    take_profit_price
        Optional specific price level above which take-profit fires.
    """

    max_loss:                   Decimal          = DEFAULT_MAX_LOSS
    take_profit:                Optional[Decimal] = None
    max_drawdown_pct:           Decimal          = Decimal("0.50")
    max_exposure:               Decimal          = DEFAULT_MAX_EXPOSURE
    max_margin_utilization_pct: Decimal          = Decimal("0.90")
    stop_loss_price:            Optional[Decimal] = None
    take_profit_price:          Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.max_loss <= Decimal("0"):
            raise RiskLimitsError("max_loss must be > 0")
        if self.take_profit is not None and self.take_profit <= Decimal("0"):
            raise RiskLimitsError("take_profit must be > 0 when set")
        if not (Decimal("0") < self.max_drawdown_pct <= Decimal("1")):
            raise RiskLimitsError("max_drawdown_pct must be in (0, 1]")
        if not (Decimal("0") < self.max_margin_utilization_pct <= Decimal("1")):
            raise RiskLimitsError("max_margin_utilization_pct must be in (0, 1]")

    @property
    def has_take_profit(self) -> bool:
        return self.take_profit is not None

    @property
    def has_stop_loss_price(self) -> bool:
        return self.stop_loss_price is not None

    @property
    def has_take_profit_price(self) -> bool:
        return self.take_profit_price is not None

    @property
    def has_exposure_limit(self) -> bool:
        return self.max_exposure > Decimal("0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_loss":                   str(self.max_loss),
            "take_profit":                str(self.take_profit) if self.take_profit else None,
            "max_drawdown_pct":           str(self.max_drawdown_pct),
            "max_exposure":               str(self.max_exposure),
            "max_margin_utilization_pct": str(self.max_margin_utilization_pct),
            "stop_loss_price":            str(self.stop_loss_price) if self.stop_loss_price else None,
            "take_profit_price":          str(self.take_profit_price) if self.take_profit_price else None,
        }


# ── Default instance ──────────────────────────────────────────────────────────

DEFAULT_RISK_LIMITS = RiskLimits()
