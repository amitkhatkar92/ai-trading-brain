"""iios/investment/market/structure/models.py
All shared enums and dataclasses for the Institutional Market Structure Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Re-export from market_constants for convenience ────────────────────────
from iios.investment.market.market_constants import (
    TrendDirection,
    MarketStrength,
    MarketPhase,
)


# ── Enums ──────────────────────────────────────────────────────────────────

class SwingType(str, Enum):
    HIGH = "high"
    LOW  = "low"


class SwingStrength(str, Enum):
    MAJOR        = "major"
    INTERMEDIATE = "intermediate"
    MINOR        = "minor"


class SwingRelation(str, Enum):
    HIGHER_HIGH  = "HH"
    HIGHER_LOW   = "HL"
    LOWER_HIGH   = "LH"
    LOWER_LOW    = "LL"
    EQUAL_HIGH   = "EH"
    EQUAL_LOW    = "EL"


class TrendPhase(str, Enum):
    IMPULSE       = "impulse"
    CORRECTION    = "correction"
    REVERSAL      = "reversal"
    CONTINUATION  = "continuation"
    ACCELERATION  = "acceleration"
    EXHAUSTION    = "exhaustion"


class StructurePhase(str, Enum):
    ACCUMULATION = "accumulation"
    MARKUP       = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN     = "markdown"
    EXPANSION    = "expansion"
    CONTRACTION  = "contraction"
    COMPRESSION  = "compression"


class ZoneType(str, Enum):
    SUPPORT            = "support"
    RESISTANCE         = "resistance"
    SUPPLY             = "supply"
    DEMAND             = "demand"
    FLIP               = "flip"
    BROKEN_SUPPORT     = "broken_support"
    BROKEN_RESISTANCE  = "broken_resistance"


class ZoneStrength(str, Enum):
    MAJOR    = "major"
    MODERATE = "moderate"
    MINOR    = "minor"


class BreakoutType(str, Enum):
    BULLISH          = "bullish"
    BEARISH          = "bearish"
    FAILED_BULLISH   = "failed_bullish"
    FAILED_BEARISH   = "failed_bearish"
    RETEST_BULLISH   = "retest_bullish"
    RETEST_BEARISH   = "retest_bearish"
    RANGE            = "range"
    VOLATILITY       = "volatility"
    VOLUME           = "volume"


class BreakoutStatus(str, Enum):
    CONFIRMED = "confirmed"
    FAILED    = "failed"
    RETESTING = "retesting"
    PENDING   = "pending"


class ConsolidationType(str, Enum):
    RANGE              = "range"
    RECTANGLE          = "rectangle"
    COMPRESSION        = "compression"
    VOLATILITY_SQUEEZE = "volatility_squeeze"
    BALANCE_AREA       = "balance_area"


# ── Dataclasses ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bar:
    """Normalized OHLCV bar."""
    index: int       # 0-based position in series
    timestamp: float  # unix epoch
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "1d"

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0

    @property
    def typical(self) -> float:
        return (self.high + self.low + self.close) / 3.0

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


@dataclass
class SwingPoint:
    index: int
    timestamp: float
    price: float          # high for swing high, low for swing low
    swing_type: SwingType
    strength: SwingStrength
    volume: float
    bar_range: float      # range of the pivot bar
    left_bars: int        # confirmation bars to the left
    right_bars: int       # confirmation bars to the right
    relation: Optional[SwingRelation] = None  # vs previous swing of same type


@dataclass
class SwingSequence:
    highs: List[SwingPoint] = field(default_factory=list)  # most recent first
    lows: List[SwingPoint] = field(default_factory=list)   # most recent first
    timeframe: str = "1d"


@dataclass
class TrendState:
    direction: TrendDirection
    strength: MarketStrength
    phase: TrendPhase
    leg_count: int
    current_leg_height: float
    total_displacement: float
    correction_depth: float    # 0-1
    start_index: int
    start_price: float
    last_swing_index: int
    last_swing_price: float
    confirmed: bool            # True once we have 2+ confirming legs


@dataclass
class TrendTransition:
    from_direction: TrendDirection
    to_direction: TrendDirection
    trigger_index: int
    trigger_price: float
    trigger_swing: SwingPoint
    transition_type: str       # "break_of_structure", "change_of_character", "reversal"
    confirmed: bool = False


@dataclass
class Zone:
    zone_id: str
    zone_type: ZoneType
    upper: float
    lower: float
    strength: ZoneStrength
    touch_count: int
    first_touch_index: int
    last_touch_index: int
    first_touch_price: float
    origin_swing_count: int
    broken: bool = False
    broken_index: Optional[int] = None
    retested_after_break: bool = False

    @property
    def mid(self) -> float:
        return (self.upper + self.lower) / 2.0

    @property
    def width(self) -> float:
        return self.upper - self.lower


@dataclass
class BreakoutEvent:
    breakout_id: str
    breakout_type: BreakoutType
    status: BreakoutStatus
    zone: Zone
    trigger_index: int
    trigger_price: float
    trigger_volume: float
    avg_volume_20: float
    close_beyond: float
    bars_since_break: int = 0
    retest_price: Optional[float] = None
    retest_index: Optional[int] = None

    @property
    def volume_confirmation(self) -> bool:
        return self.trigger_volume > self.avg_volume_20 * 1.2


@dataclass
class ConsolidationState:
    consolidation_type: ConsolidationType
    start_index: int
    high_bound: float
    low_bound: float
    bar_count: int
    avg_range: float
    initial_range: float
    tightest_range: float
    volume_trend: str   # "increasing", "decreasing", "neutral"
    active: bool = True

    @property
    def range_width(self) -> float:
        return self.high_bound - self.low_bound

    @property
    def compression_ratio(self) -> float:
        """<1 means tighter than initial."""
        if self.initial_range == 0:
            return 1.0
        return self.avg_range / self.initial_range


@dataclass
class StructureQualityScore:
    overall: float
    swing_confidence: float
    trend_confidence: float
    zone_confidence: float
    breakout_confidence: float
    data_quality: float
    bar_count: int
    valid_swing_count: int

    @property
    def grade(self) -> str:
        if self.overall >= 80:
            return "A"
        if self.overall >= 65:
            return "B"
        if self.overall >= 50:
            return "C"
        if self.overall >= 35:
            return "D"
        return "F"


@dataclass
class MarketStructureSnapshot:
    """Complete market structure at a point in time."""
    symbol: str
    timeframe: str
    bar_index: int
    timestamp: float

    # Core structure
    trend: TrendState
    structure_phase: StructurePhase

    # Swings
    last_swing_high: Optional[SwingPoint]
    last_swing_low: Optional[SwingPoint]
    swing_sequence: SwingSequence

    # Zones
    active_zones: List[Zone]
    nearest_resistance: Optional[Zone]
    nearest_support: Optional[Zone]

    # Events
    active_breakout: Optional[BreakoutEvent]
    consolidation: Optional[ConsolidationState]
    last_transition: Optional[TrendTransition]

    # Quality
    quality: StructureQualityScore

    def to_dict(self) -> Dict[str, Any]:
        def _swing(s: Optional[SwingPoint]) -> Optional[Dict[str, Any]]:
            if s is None:
                return None
            return {
                "index": s.index,
                "price": s.price,
                "type": s.swing_type.value,
                "strength": s.strength.value,
                "relation": s.relation.value if s.relation else None,
            }

        def _zone(z: Optional[Zone]) -> Optional[Dict[str, Any]]:
            if z is None:
                return None
            return {
                "zone_id": z.zone_id,
                "type": z.zone_type.value,
                "upper": z.upper,
                "lower": z.lower,
                "strength": z.strength.value,
                "touch_count": z.touch_count,
                "broken": z.broken,
            }

        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp,
            "trend": {
                "direction": self.trend.direction.value,
                "strength": self.trend.strength.value,
                "phase": self.trend.phase.value,
                "leg_count": self.trend.leg_count,
                "confirmed": self.trend.confirmed,
            },
            "structure_phase": self.structure_phase.value,
            "last_swing_high": _swing(self.last_swing_high),
            "last_swing_low": _swing(self.last_swing_low),
            "active_zones": [_zone(z) for z in self.active_zones],
            "nearest_resistance": _zone(self.nearest_resistance),
            "nearest_support": _zone(self.nearest_support),
            "quality": {
                "overall": self.quality.overall,
                "grade": self.quality.grade,
                "swing_confidence": self.quality.swing_confidence,
                "trend_confidence": self.quality.trend_confidence,
            },
        }
