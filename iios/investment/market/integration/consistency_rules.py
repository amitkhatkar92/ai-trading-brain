"""iios/investment/market/integration/consistency_rules.py
Built-in cross-engine consistency rules.

Each rule is a pure predicate over AggregationState; True = conflict detected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import ConflictSeverity, ConflictType


@dataclass(frozen=True)
class ConsistencyRule:
    name:          str
    conflict_type: ConflictType
    severity:      ConflictSeverity
    engines:       List[str]
    description:   str
    check:         Callable[[AggregationState], bool]   # True → issue exists


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _both_present(state: AggregationState, *fields) -> bool:
    """Return True if all named attributes of state are non-None."""
    return all(getattr(state, f, None) is not None for f in fields)


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------

BUILT_IN_RULES: List[ConsistencyRule] = [

    # ── Trend vs Regime ──────────────────────────────────────────────────────
    ConsistencyRule(
        name="trend_up_in_bear_regime",
        conflict_type=ConflictType.TREND_REGIME,
        severity=ConflictSeverity.HIGH,
        engines=["market_regime", "trend"],
        description="Trend is strongly UP but regime is BEAR — possible regime lag or false rally.",
        check=lambda s: (
            _both_present(s, "market_regime", "trend_direction")
            and s.market_regime == "bear"
            and s.trend_direction == "up"
            and s.trend_strength > 65.0
        ),
    ),
    ConsistencyRule(
        name="trend_down_in_bull_regime",
        conflict_type=ConflictType.TREND_REGIME,
        severity=ConflictSeverity.HIGH,
        engines=["market_regime", "trend"],
        description="Trend is strongly DOWN but regime is BULL — potential distribution phase.",
        check=lambda s: (
            _both_present(s, "market_regime", "trend_direction")
            and s.market_regime == "bull"
            and s.trend_direction == "down"
            and s.trend_strength > 65.0
        ),
    ),

    # ── Trend vs Volatility ──────────────────────────────────────────────────
    ConsistencyRule(
        name="strong_trend_in_extreme_volatility",
        conflict_type=ConflictType.TREND_VOLATILITY,
        severity=ConflictSeverity.MEDIUM,
        engines=["trend", "volatility"],
        description="High trend strength with extreme volatility — signals may be noise-inflated.",
        check=lambda s: (
            _both_present(s, "trend_direction", "volatility_regime")
            and s.volatility_regime == "extreme"
            and s.trend_strength > 70.0
        ),
    ),
    ConsistencyRule(
        name="low_volatility_signals_stale_trend",
        conflict_type=ConflictType.TREND_VOLATILITY,
        severity=ConflictSeverity.LOW,
        engines=["trend", "volatility"],
        description="Volatility is very low but trend strength is very high — possible complacency.",
        check=lambda s: (
            _both_present(s, "volatility_regime", "trend_direction")
            and s.volatility_regime == "low"
            and s.trend_strength > 80.0
        ),
    ),

    # ── Breakout vs Liquidity ─────────────────────────────────────────────────
    ConsistencyRule(
        name="breakout_in_crisis_liquidity",
        conflict_type=ConflictType.BREAKOUT_LIQUIDITY,
        severity=ConflictSeverity.HIGH,
        engines=["opportunity", "volume_liquidity"],
        description="Active breakout opportunities but liquidity is in crisis — execution risk high.",
        check=lambda s: (
            _both_present(s, "liquidity_regime")
            and s.liquidity_regime == "crisis"
            and s.active_opportunities > 3
        ),
    ),

    # ── Breadth vs Sector Rotation ────────────────────────────────────────────
    ConsistencyRule(
        name="positive_breadth_all_sectors_lagging",
        conflict_type=ConflictType.BREADTH_SECTOR,
        severity=ConflictSeverity.MEDIUM,
        engines=["breadth", "sector_rotation"],
        description="Market breadth is positive but most sectors are lagging — breadth may be narrow.",
        check=lambda s: (
            _both_present(s, "breadth_regime")
            and s.breadth_regime == "positive"
            and len(s.lagging_sectors) > len(s.leading_sectors) + 2
        ),
    ),
    ConsistencyRule(
        name="negative_breadth_sector_strength",
        conflict_type=ConflictType.BREADTH_SECTOR,
        severity=ConflictSeverity.MEDIUM,
        engines=["breadth", "sector_rotation"],
        description="Market breadth is negative but multiple sectors are leading — mixed rotation.",
        check=lambda s: (
            _both_present(s, "breadth_regime")
            and s.breadth_regime == "negative"
            and len(s.leading_sectors) > 3
        ),
    ),

    # ── Correlation vs Regime ─────────────────────────────────────────────────
    ConsistencyRule(
        name="correlation_crisis_in_bull_regime",
        conflict_type=ConflictType.CORRELATION_REGIME,
        severity=ConflictSeverity.HIGH,
        engines=["correlation", "market_regime"],
        description="Correlation regime is CRISIS (de-risking) but market regime shows BULL.",
        check=lambda s: (
            _both_present(s, "correlation_regime", "market_regime")
            and s.correlation_regime == "crisis"
            and s.market_regime == "bull"
        ),
    ),
    ConsistencyRule(
        name="elevated_correlation_trend_down",
        conflict_type=ConflictType.CORRELATION_REGIME,
        severity=ConflictSeverity.MEDIUM,
        engines=["correlation", "trend"],
        description="Elevated correlation with downtrend — systemic risk event likely.",
        check=lambda s: (
            _both_present(s, "correlation_regime", "trend_direction")
            and s.correlation_regime in ("elevated", "crisis")
            and s.trend_direction == "down"
        ),
    ),

    # ── Opportunity vs Risk ───────────────────────────────────────────────────
    ConsistencyRule(
        name="many_opportunities_crisis_regime",
        conflict_type=ConflictType.OPPORTUNITY_RISK,
        severity=ConflictSeverity.CRITICAL,
        engines=["opportunity", "market_regime"],
        description="High number of active opportunities in a CRISIS regime — false positives likely.",
        check=lambda s: (
            _both_present(s, "market_regime")
            and s.market_regime == "crisis"
            and s.active_opportunities > 5
        ),
    ),
    ConsistencyRule(
        name="opportunity_extreme_volatility",
        conflict_type=ConflictType.OPPORTUNITY_RISK,
        severity=ConflictSeverity.HIGH,
        engines=["opportunity", "volatility"],
        description="Opportunities active under extreme volatility — high whipsaw risk.",
        check=lambda s: (
            _both_present(s, "volatility_regime")
            and s.volatility_regime == "extreme"
            and s.active_opportunities > 0
        ),
    ),

    # ── Cross-engine ──────────────────────────────────────────────────────────
    ConsistencyRule(
        name="bear_regime_positive_breadth",
        conflict_type=ConflictType.CROSS_ENGINE,
        severity=ConflictSeverity.MEDIUM,
        engines=["market_regime", "breadth"],
        description="Bear regime with positive breadth — could signal bear market rally.",
        check=lambda s: (
            _both_present(s, "market_regime", "breadth_regime")
            and s.market_regime == "bear"
            and s.breadth_regime == "positive"
            and s.breadth_score > 60.0
        ),
    ),
    ConsistencyRule(
        name="bull_regime_negative_breadth",
        conflict_type=ConflictType.CROSS_ENGINE,
        severity=ConflictSeverity.MEDIUM,
        engines=["market_regime", "breadth"],
        description="Bull regime with negative breadth — potential distribution or leadership narrowing.",
        check=lambda s: (
            _both_present(s, "market_regime", "breadth_regime")
            and s.market_regime == "bull"
            and s.breadth_regime == "negative"
            and s.breadth_score < 40.0
        ),
    ),
]
