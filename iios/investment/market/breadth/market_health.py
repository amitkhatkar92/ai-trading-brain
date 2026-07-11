"""iios/investment/market/breadth/market_health.py
Market health snapshot builder.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.market.breadth.models import (
    BreadthData,
    HealthTrend,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)
from iios.investment.market.breadth import internal_strength as ist
from iios.investment.market.breadth import leadership_analysis as la


class MarketHealthAnalyzer:
    """Builds MarketHealthSnapshot from breadth + participation data."""

    def __init__(self) -> None:
        self._prev_breadth_pct: float = 0.5
        self._prev_health_score: float = 50.0

    def analyze(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
    ) -> MarketHealthSnapshot:
        strength = ist.internal_strength_score(breadth, participation)
        momentum = ist.internal_momentum(breadth, self._prev_breadth_pct)

        lead_sectors, lag_sectors = la.identify_leaders_and_laggers(participation)
        lead_breadth, lag_breadth = la.leadership_breadth(participation)
        quality = la.participation_quality(participation)

        health_score = self._compute_health_score(
            strength, lead_breadth, quality, participation
        )
        health_trend = self._determine_health_trend(
            health_score, self._prev_health_score, momentum
        )

        self._prev_breadth_pct   = breadth.breadth_pct
        self._prev_health_score  = health_score

        return MarketHealthSnapshot(
            health_score=round(health_score, 2),
            internal_strength=round(strength, 4),
            leadership_breadth=round(lead_breadth, 4),
            lagging_breadth=round(lag_breadth, 4),
            participation_quality=round(quality, 4),
            internal_momentum=round(momentum, 4),
            health_trend=health_trend,
            leading_sectors=lead_sectors,
            lagging_sectors=lag_sectors,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _compute_health_score(
        self,
        strength: float,
        leadership_breadth: float,
        quality: float,
        participation: ParticipationSnapshot,
    ) -> float:
        score = (
            strength          * 0.40
            + leadership_breadth * 0.25
            + quality            * 0.20
            + participation.above_ma50_pct * 0.15
        )
        return max(0.0, min(100.0, score * 100))

    def _determine_health_trend(
        self,
        current: float,
        previous: float,
        momentum: float,
    ) -> HealthTrend:
        delta = current - previous
        if delta > 5 or momentum > 0.20:
            return HealthTrend.IMPROVING
        if delta < -5 or momentum < -0.20:
            return HealthTrend.DETERIORATING
        return HealthTrend.STABLE
