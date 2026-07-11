"""iios/investment/market/volatility/volatility_constraints.py
Quantitative constraints per volatility regime (position sizing, stop width, etc.).

Downstream risk / position-sizing engines should query these values rather
than implementing regime-specific logic themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from iios.investment.market.volatility.models import VolatilityRegimeType


@dataclass(frozen=True)
class VolatilityConstraints:
    """Regime-specific quantitative constraints for a single trade/position."""
    max_position_size_pct: float    # max % of portfolio in one position
    max_leverage: float             # max gross leverage
    stop_width_multiplier: float    # multiply by ATR/range to set stop
    min_rr_ratio: float             # minimum risk-reward ratio required
    max_open_positions: int         # max simultaneous positions
    require_confirmation: bool      # must wait for confirming signal
    reduce_exposure: bool           # must reduce existing exposure
    halt_new_entries: bool          # no new entries permitted

    def to_dict(self) -> Dict[str, object]:
        return {
            "max_position_size_pct": self.max_position_size_pct,
            "max_leverage": self.max_leverage,
            "stop_width_multiplier": self.stop_width_multiplier,
            "min_rr_ratio": self.min_rr_ratio,
            "max_open_positions": self.max_open_positions,
            "require_confirmation": self.require_confirmation,
            "reduce_exposure": self.reduce_exposure,
            "halt_new_entries": self.halt_new_entries,
        }


_CONSTRAINTS: Dict[VolatilityRegimeType, VolatilityConstraints] = {
    VolatilityRegimeType.VERY_LOW: VolatilityConstraints(
        max_position_size_pct=8.0,
        max_leverage=2.0,
        stop_width_multiplier=1.5,
        min_rr_ratio=1.5,
        max_open_positions=10,
        require_confirmation=False,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.COMPRESSION: VolatilityConstraints(
        max_position_size_pct=6.0,
        max_leverage=2.0,
        stop_width_multiplier=1.5,
        min_rr_ratio=2.0,
        max_open_positions=8,
        require_confirmation=True,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.LOW: VolatilityConstraints(
        max_position_size_pct=7.0,
        max_leverage=2.0,
        stop_width_multiplier=1.5,
        min_rr_ratio=1.5,
        max_open_positions=10,
        require_confirmation=False,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.NORMAL: VolatilityConstraints(
        max_position_size_pct=5.0,
        max_leverage=1.5,
        stop_width_multiplier=2.0,
        min_rr_ratio=2.0,
        max_open_positions=8,
        require_confirmation=False,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.ELEVATED: VolatilityConstraints(
        max_position_size_pct=4.0,
        max_leverage=1.25,
        stop_width_multiplier=2.5,
        min_rr_ratio=2.5,
        max_open_positions=6,
        require_confirmation=True,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.EXPANSION: VolatilityConstraints(
        max_position_size_pct=3.5,
        max_leverage=1.25,
        stop_width_multiplier=3.0,
        min_rr_ratio=2.5,
        max_open_positions=5,
        require_confirmation=True,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.HIGH: VolatilityConstraints(
        max_position_size_pct=2.5,
        max_leverage=1.0,
        stop_width_multiplier=3.5,
        min_rr_ratio=3.0,
        max_open_positions=4,
        require_confirmation=True,
        reduce_exposure=True,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.EXTREME: VolatilityConstraints(
        max_position_size_pct=1.5,
        max_leverage=1.0,
        stop_width_multiplier=5.0,
        min_rr_ratio=4.0,
        max_open_positions=2,
        require_confirmation=True,
        reduce_exposure=True,
        halt_new_entries=True,
    ),
    VolatilityRegimeType.SHOCK: VolatilityConstraints(
        max_position_size_pct=0.5,
        max_leverage=1.0,
        stop_width_multiplier=8.0,
        min_rr_ratio=5.0,
        max_open_positions=1,
        require_confirmation=True,
        reduce_exposure=True,
        halt_new_entries=True,
    ),
    VolatilityRegimeType.RECOVERY: VolatilityConstraints(
        max_position_size_pct=3.0,
        max_leverage=1.0,
        stop_width_multiplier=3.0,
        min_rr_ratio=2.5,
        max_open_positions=5,
        require_confirmation=True,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
    VolatilityRegimeType.UNKNOWN: VolatilityConstraints(
        max_position_size_pct=2.0,
        max_leverage=1.0,
        stop_width_multiplier=3.0,
        min_rr_ratio=2.5,
        max_open_positions=4,
        require_confirmation=True,
        reduce_exposure=False,
        halt_new_entries=False,
    ),
}


def get_constraints(regime: VolatilityRegimeType) -> VolatilityConstraints:
    return _CONSTRAINTS.get(regime, _CONSTRAINTS[VolatilityRegimeType.UNKNOWN])
