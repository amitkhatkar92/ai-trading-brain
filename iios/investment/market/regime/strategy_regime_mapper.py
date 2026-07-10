"""iios/investment/market/regime/strategy_regime_mapper.py
Facade for strategy-regime compatibility queries.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from iios.investment.market.regime.models import RegimeType, StrategyCompatibility
from iios.investment.market.regime.strategy_permissions import REGIME_PERMISSIONS
from iios.investment.market.regime.regime_constraints import RegimeConstraintEngine


class StrategyRegimeMapper:
    """
    Facade that answers strategy compatibility questions for a given regime.
    Uses REGIME_PERMISSIONS and RegimeConstraintEngine internally.
    """

    def __init__(
        self,
        constraints: Optional[RegimeConstraintEngine] = None,
    ) -> None:
        self._constraints = constraints or RegimeConstraintEngine()

    def compatibility(self, regime: RegimeType) -> StrategyCompatibility:
        """Full StrategyCompatibility for a regime."""
        return REGIME_PERMISSIONS.get(regime, REGIME_PERMISSIONS[RegimeType.UNKNOWN])

    def is_allowed(self, strategy_type: str, regime: RegimeType) -> bool:
        return self.compatibility(regime).is_allowed(strategy_type)

    def is_blocked(self, strategy_type: str, regime: RegimeType) -> bool:
        return self.compatibility(regime).is_blocked(strategy_type)

    def is_discouraged(self, strategy_type: str, regime: RegimeType) -> bool:
        return self.compatibility(regime).is_discouraged(strategy_type)

    def preferred_timeframes(self, regime: RegimeType) -> List[str]:
        return self.compatibility(regime).preferred_timeframes

    def preferred_risk_profile(self, regime: RegimeType) -> str:
        return self.compatibility(regime).preferred_risk_profile

    def max_position_size(self, regime: RegimeType) -> float:
        return self.compatibility(regime).max_position_size_pct

    def allowed_strategies(self, regime: RegimeType) -> List[str]:
        return self.compatibility(regime).allowed

    def blocked_strategies(self, regime: RegimeType) -> List[str]:
        return self.compatibility(regime).blocked

    def check_trade(
        self,
        strategy_type: str,
        regime: RegimeType,
        direction: str,
        structure_quality: float = 50.0,
        trend_confirmed: bool = False,
    ) -> Tuple[bool, str]:
        """
        Full gate check: permission + constraint.
        Returns (allowed, reason).
        """
        # Permission check
        compat = self.compatibility(regime)
        if compat.is_blocked(strategy_type):
            return False, f"Strategy '{strategy_type}' is blocked in {regime.value} regime"

        # Constraint check
        allowed, reason = self._constraints.check(
            strategy_type=strategy_type,
            regime=regime,
            direction=direction,
            structure_quality=structure_quality,
            trend_confirmed=trend_confirmed,
        )
        if not allowed:
            return False, reason

        return True, "Trade permitted"
