"""iios/investment/market/volatility/volatility_risk.py
Top-level risk assessor: assembles RiskProfile and detects risk events.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    RiskProfile,
    VolatilityEvent,
    VolatilityEventType,
    VolatilityRegimeType,
    VolatilityState,
    RiskLevel,
)
from iios.investment.market.volatility.risk_profile import RiskProfileBuilder


class VolatilityRiskAssessor:
    """
    Builds a RiskProfile and optionally emits a SHOCK event when overall
    risk exceeds the shock threshold.
    """

    SHOCK_THRESHOLD = 0.85

    def __init__(
        self,
        builder: Optional[RiskProfileBuilder] = None,
    ) -> None:
        self._builder = builder or RiskProfileBuilder()
        self._prev_risk_level: Optional[RiskLevel] = None

    def assess(
        self,
        state: VolatilityState,
        regime: VolatilityRegimeType,
        behaviour: BehaviourSnapshot,
        bar_index: int,
        symbol: str,
        timeframe: str,
    ) -> tuple[RiskProfile, Optional[VolatilityEvent]]:
        profile = self._builder.build(state, regime, behaviour)

        event: Optional[VolatilityEvent] = None
        if profile.overall_risk >= self.SHOCK_THRESHOLD:
            if self._prev_risk_level not in (RiskLevel.EXTREME, RiskLevel.VERY_HIGH):
                event = VolatilityEvent(
                    event_type=VolatilityEventType.SHOCK,
                    symbol=symbol,
                    timeframe=timeframe,
                    bar_index=bar_index,
                    severity=profile.overall_risk,
                    description=(
                        f"Risk shock: overall_risk={profile.overall_risk:.2f} "
                        f"regime={regime.value}"
                    ),
                )
        self._prev_risk_level = profile.risk_level
        return profile, event
