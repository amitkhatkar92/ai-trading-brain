"""
market_breadth_engine.py — iios.market.analytics
=================================================
Advance/decline breadth analysis sub-engine.

C12 Market Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict

from .constants import BREADTH_HEALTHY, BREADTH_UNHEALTHY
from .market_analytics_context import MarketAnalyticsContext
from .market_analytics_response import BreadthResult


class MarketBreadthEngine:
    """
    Stateless breadth analysis sub-engine.

    Expects ``breadth_data`` dict with optional keys:
    ``advancing``, ``declining``, ``unchanged``,
    ``new_highs``, ``new_lows``.
    """

    def run(
        self,
        context:      MarketAnalyticsContext,
        request_data: Dict[str, Any],
    ) -> BreadthResult:
        bd = request_data.get("breadth_data", {})

        advancing  = int(bd.get("advancing",  0))
        declining  = int(bd.get("declining",  0))
        unchanged  = int(bd.get("unchanged",  0))
        new_highs  = int(bd.get("new_highs",  0))
        new_lows   = int(bd.get("new_lows",   0))

        total = advancing + declining + unchanged
        if total <= 0:
            # No data — neutral defaults
            return BreadthResult(
                advance_decline_ratio = 1.0,
                advancing_pct         = 0.0,
                declining_pct         = 0.0,
                unchanged_pct         = 0.0,
                new_highs             = 0,
                new_lows              = 0,
                breadth_score         = 50.0,
                is_healthy            = True,
                description           = "No breadth data available — neutral defaults used",
            )

        advancing_pct = advancing / total
        declining_pct = declining / total
        unchanged_pct = unchanged / total
        adr           = advancing / declining if declining > 0 else float(advancing)
        breadth_score = min(100.0, max(0.0, advancing_pct * 100.0))
        is_healthy    = advancing_pct >= BREADTH_HEALTHY

        # Adjust score for new-highs / new-lows
        total_extremes = new_highs + new_lows
        if total_extremes > 0:
            nh_ratio = new_highs / total_extremes
            breadth_score = breadth_score * 0.8 + nh_ratio * 20.0

        description = (
            f"Breadth: {advancing_pct:.1%} advancing, {declining_pct:.1%} declining; "
            f"ADR={adr:.2f}; {'HEALTHY' if is_healthy else 'UNHEALTHY'}"
        )

        return BreadthResult(
            advance_decline_ratio = adr,
            advancing_pct         = advancing_pct,
            declining_pct         = declining_pct,
            unchanged_pct         = unchanged_pct,
            new_highs             = new_highs,
            new_lows              = new_lows,
            breadth_score         = breadth_score,
            is_healthy            = is_healthy,
            description           = description,
        )
