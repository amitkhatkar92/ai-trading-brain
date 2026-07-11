"""iios/investment/market/volatility/strategy_volatility_mapper.py
Builds a StrategyCompatibility object from the current vol regime.
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    StrategyCompatibility,
    VolatilityRegimeType,
    VolatilityState,
)
from iios.investment.market.volatility import strategy_permissions as sp


class StrategyVolatilityMapper:
    """Maps current volatility regime to strategy compatibility."""

    def evaluate(
        self,
        regime: VolatilityRegimeType,
        state: VolatilityState,
        behaviour: BehaviourSnapshot,
    ) -> StrategyCompatibility:
        permissions = sp.get_permissions(regime)
        recommended = sp.get_recommended(regime)
        restricted  = sp.get_restricted(regime)

        # Dynamic adjustments based on behaviour
        permissions = self._apply_behaviour_overrides(
            permissions, regime, state, behaviour
        )
        # Re-derive restricted after overrides
        restricted = [s for s, allowed in permissions.items() if not allowed]
        recommended = [s for s in recommended if permissions.get(s, False)]

        return StrategyCompatibility(
            permissions=permissions,
            recommended=recommended,
            restricted=restricted,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _apply_behaviour_overrides(
        self,
        permissions: dict[str, bool],
        regime: VolatilityRegimeType,
        state: VolatilityState,
        behaviour: BehaviourSnapshot,
    ) -> dict[str, bool]:
        from iios.investment.market.volatility.models import (
            VolatilityBehaviour,
            StrategyType,
        )

        perm = dict(permissions)

        # During climax/shock: disable mean reversion regardless of regime
        if behaviour.behaviour in (
            VolatilityBehaviour.CLIMAX,
            VolatilityBehaviour.ACCELERATING,
        ):
            perm[StrategyType.MEAN_REVERSION.value] = False
            perm[StrategyType.POSITION_TRADING.value] = False

        # During deep compression: enable breakout (prime setup)
        if (
            behaviour.behaviour == VolatilityBehaviour.COMPRESSING
            and behaviour.compression_score > 0.60
        ):
            perm[StrategyType.BREAKOUT.value] = True

        # Persistence: momentum works well
        if (
            behaviour.behaviour == VolatilityBehaviour.PERSISTENT
            and state.normalized_volatility > 0.25
        ):
            perm[StrategyType.MOMENTUM.value] = True

        return perm
