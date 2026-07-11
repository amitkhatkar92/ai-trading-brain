"""iios/investment/market/liquidity/models.py
Enums and dataclasses for the Institutional Volume & Liquidity Intelligence Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ── Enums ──────────────────────────────────────────────────────────────────

class VolumeLevel(str, Enum):
    EXTREME_HIGH  = "extreme_high"    # > 3.0x avg
    VERY_HIGH     = "very_high"       # 2.0–3.0x avg
    HIGH          = "high"            # 1.5–2.0x avg
    ABOVE_AVERAGE = "above_average"   # 1.2–1.5x avg
    AVERAGE       = "average"         # 0.8–1.2x avg
    BELOW_AVERAGE = "below_average"   # 0.5–0.8x avg
    LOW           = "low"             # < 0.5x avg
    NONE          = "none"            # 0 or effectively zero


class VolumeTrend(str, Enum):
    EXPANDING    = "expanding"    # last 5 avg > last 20 avg * 1.20
    STABLE       = "stable"       # within ±20%
    CONTRACTING  = "contracting"  # last 5 avg < last 20 avg * 0.80
    SPIKING      = "spiking"      # single bar > 2.5x avg
    DRYING_UP    = "drying_up"    # last 3 bars all < 0.5x avg


class ParticipationBias(str, Enum):
    STRONG_BUY  = "strong_buy"    # balance > 0.6
    BUY         = "buy"           # balance 0.2–0.6
    NEUTRAL     = "neutral"       # balance -0.2–0.2
    SELL        = "sell"          # balance -0.6–-0.2
    STRONG_SELL = "strong_sell"   # balance < -0.6


class EffortResultType(str, Enum):
    CONFIRMED  = "confirmed"    # effort >= 0.5 AND result >= 0.5
    DIVERGENT  = "divergent"    # effort >= 0.6 AND result < 0.3
    CLIMAX     = "climax"       # effort > 0.85 AND result < 0.4
    ABSORPTION = "absorption"   # effort > 0.7 AND range/avg_range < 0.5
    EXHAUSTION = "exhaustion"   # effort < 0.3 AND result < 0.2
    NEUTRAL    = "neutral"      # fallback


class LiquidityEventType(str, Enum):
    EXPANSION           = "expansion"
    DRY_UP              = "dry_up"
    SHOCK               = "shock"
    HIGH_PARTICIPATION  = "high_participation"
    LOW_PARTICIPATION   = "low_participation"
    VOLUME_SPIKE        = "volume_spike"
    VOLUME_VACUUM       = "volume_vacuum"
    BUYING_CLIMAX       = "buying_climax"
    SELLING_CLIMAX      = "selling_climax"
    ABSORPTION_DETECTED = "absorption_detected"


# ── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class VolumeBar:
    """Enriched single-bar volume data."""
    index: int
    timestamp: float
    volume: float
    relative_volume: float       # vs 20-bar avg (1.0 = average)
    normalized_volume: float     # vs rolling max, range [0, 1]
    price_change: float          # abs(close - open)
    price_change_pct: float      # price_change / open * 100
    bar_range: float             # high - low
    is_up: bool                  # close >= open
    body_pct: float              # body / max(range, 0.001), [0,1]
    close_position: float        # (close - low) / max(range, 0.001), [0,1]
    volume_level: VolumeLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "volume": self.volume,
            "relative_volume": self.relative_volume,
            "normalized_volume": self.normalized_volume,
            "price_change": self.price_change,
            "price_change_pct": self.price_change_pct,
            "bar_range": self.bar_range,
            "is_up": self.is_up,
            "body_pct": self.body_pct,
            "close_position": self.close_position,
            "volume_level": self.volume_level.value,
        }


@dataclass
class VolumeProfile:
    """Rolling volume distribution over a window of bars."""
    period_bars: int
    avg_volume: float
    std_volume: float
    median_volume: float
    peak_volume: float
    min_volume: float
    recent_avg: float          # last 5 bars avg
    volume_trend: VolumeTrend
    up_volume: float           # cumulative volume on up bars
    down_volume: float         # cumulative volume on down bars
    up_down_ratio: float       # up_volume / max(down_volume, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_bars": self.period_bars,
            "avg_volume": self.avg_volume,
            "std_volume": self.std_volume,
            "median_volume": self.median_volume,
            "peak_volume": self.peak_volume,
            "min_volume": self.min_volume,
            "recent_avg": self.recent_avg,
            "volume_trend": self.volume_trend.value,
            "up_volume": self.up_volume,
            "down_volume": self.down_volume,
            "up_down_ratio": self.up_down_ratio,
        }


@dataclass
class ParticipationSnapshot:
    """Point-in-time participation analysis."""
    buying_participation: float        # 0-1 fraction of volume on buy side
    selling_participation: float       # 0-1 fraction on sell side
    institutional_participation: float # 0-1 estimated
    retail_participation: float        # 0-1 estimated
    participation_balance: float       # -1 to +1
    participation_bias: ParticipationBias
    participation_confidence: float    # 0-1
    participation_score: float         # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buying_participation": self.buying_participation,
            "selling_participation": self.selling_participation,
            "institutional_participation": self.institutional_participation,
            "retail_participation": self.retail_participation,
            "participation_balance": self.participation_balance,
            "participation_bias": self.participation_bias.value,
            "participation_confidence": self.participation_confidence,
            "participation_score": self.participation_score,
        }


@dataclass
class LiquidityProfile:
    """Liquidity characteristics over a rolling window."""
    availability: float    # 0-1: ease of execution
    stability: float       # 0-1: consistency across bars
    depth: float           # 0-1: volume vs historical max
    concentration: float   # 0-1: volume in few bars (high = less liquid)
    fragmentation: float   # 0-1 = 1 - concentration
    quality: float         # 0-100 composite
    liquidity_confidence: float  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability": self.availability,
            "stability": self.stability,
            "depth": self.depth,
            "concentration": self.concentration,
            "fragmentation": self.fragmentation,
            "quality": self.quality,
            "liquidity_confidence": self.liquidity_confidence,
        }


@dataclass
class EffortResultAnalysis:
    """Volume-price effort vs result (Wyckoff analysis)."""
    effort: float               # normalized volume [0,1]
    result: float               # normalized price change [0,1]
    ratio: float                # result / max(effort, 0.01)
    effort_result_type: EffortResultType
    is_confirmed: bool
    is_divergent: bool
    is_absorption: bool
    is_climax: bool
    absorption_strength: float  # 0-1
    climax_score: float         # 0-1
    initiative_buying: bool
    initiative_selling: bool
    responsive_buying: bool
    responsive_selling: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effort": self.effort,
            "result": self.result,
            "ratio": self.ratio,
            "effort_result_type": self.effort_result_type.value,
            "is_confirmed": self.is_confirmed,
            "is_divergent": self.is_divergent,
            "is_absorption": self.is_absorption,
            "is_climax": self.is_climax,
            "absorption_strength": self.absorption_strength,
            "climax_score": self.climax_score,
            "initiative_buying": self.initiative_buying,
            "initiative_selling": self.initiative_selling,
            "responsive_buying": self.responsive_buying,
            "responsive_selling": self.responsive_selling,
        }


@dataclass
class OrderFlowSnapshot:
    """Order flow state. Designed for OHLCV heuristic + future L2 extension."""
    # OHLCV-estimated
    estimated_buy_volume: float    # volume * close_position
    estimated_sell_volume: float   # volume * (1 - close_position)
    estimated_delta: float         # buy - sell
    cumulative_delta: float        # running sum since initialization
    buy_imbalance: float           # buy_vol / max(total_vol, 1), [0,1]
    sell_imbalance: float          # sell_vol / max(total_vol, 1), [0,1]
    net_imbalance: float           # (buy - sell) / max(total, 1), [-1,1]
    aggressive_buying: bool        # buy_imbalance > 0.65 AND rel_vol > 1.2
    aggressive_selling: bool       # buy_imbalance < 0.35 AND rel_vol > 1.2
    # L2 extension fields (always False/None until L2 is connected)
    has_l2_data: bool = False
    bid_ask_spread: Optional[float] = None
    market_depth_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_buy_volume": self.estimated_buy_volume,
            "estimated_sell_volume": self.estimated_sell_volume,
            "estimated_delta": self.estimated_delta,
            "cumulative_delta": self.cumulative_delta,
            "buy_imbalance": self.buy_imbalance,
            "sell_imbalance": self.sell_imbalance,
            "net_imbalance": self.net_imbalance,
            "aggressive_buying": self.aggressive_buying,
            "aggressive_selling": self.aggressive_selling,
            "has_l2_data": self.has_l2_data,
            "bid_ask_spread": self.bid_ask_spread,
            "market_depth_score": self.market_depth_score,
            "metadata": self.metadata,
        }


@dataclass
class LiquidityEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: LiquidityEventType = LiquidityEventType.VOLUME_SPIKE
    symbol: str = ""
    timeframe: str = "1d"
    timestamp: float = field(default_factory=time.time)
    bar_index: int = 0
    severity: float = 0.5    # 0-1
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "bar_index": self.bar_index,
            "severity": self.severity,
            "description": self.description,
            "metadata": self.metadata,
        }


def _default_volume_bar() -> VolumeBar:
    return VolumeBar(
        index=0, timestamp=0.0, volume=0.0,
        relative_volume=1.0, normalized_volume=0.5,
        price_change=0.0, price_change_pct=0.0,
        bar_range=0.0, is_up=True,
        body_pct=0.0, close_position=0.5,
        volume_level=VolumeLevel.AVERAGE,
    )


def _default_volume_profile() -> VolumeProfile:
    return VolumeProfile(
        period_bars=0, avg_volume=0.0, std_volume=0.0,
        median_volume=0.0, peak_volume=0.0, min_volume=0.0,
        recent_avg=0.0, volume_trend=VolumeTrend.STABLE,
        up_volume=0.0, down_volume=0.0, up_down_ratio=1.0,
    )


def _default_participation() -> ParticipationSnapshot:
    return ParticipationSnapshot(
        buying_participation=0.5, selling_participation=0.5,
        institutional_participation=0.5, retail_participation=0.5,
        participation_balance=0.0, participation_bias=ParticipationBias.NEUTRAL,
        participation_confidence=0.5, participation_score=50.0,
    )


def _default_liquidity_profile() -> LiquidityProfile:
    return LiquidityProfile(
        availability=0.5, stability=0.5, depth=0.5,
        concentration=0.5, fragmentation=0.5,
        quality=50.0, liquidity_confidence=0.5,
    )


def _default_effort_result() -> EffortResultAnalysis:
    return EffortResultAnalysis(
        effort=0.5, result=0.5, ratio=1.0,
        effort_result_type=EffortResultType.NEUTRAL,
        is_confirmed=False, is_divergent=False,
        is_absorption=False, is_climax=False,
        absorption_strength=0.0, climax_score=0.0,
        initiative_buying=False, initiative_selling=False,
        responsive_buying=False, responsive_selling=False,
    )


def _default_order_flow() -> OrderFlowSnapshot:
    return OrderFlowSnapshot(
        estimated_buy_volume=0.0, estimated_sell_volume=0.0,
        estimated_delta=0.0, cumulative_delta=0.0,
        buy_imbalance=0.5, sell_imbalance=0.5,
        net_imbalance=0.0, aggressive_buying=False,
        aggressive_selling=False,
    )


@dataclass
class VolumeLiquiditySnapshot:
    """Complete volume & liquidity intelligence at a point in time."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    timeframe: str = "1d"
    bar_index: int = 0
    timestamp: float = field(default_factory=time.time)

    volume_bar: VolumeBar = field(default_factory=_default_volume_bar)
    volume_profile: VolumeProfile = field(default_factory=_default_volume_profile)
    volume_level: VolumeLevel = VolumeLevel.AVERAGE
    volume_trend: VolumeTrend = VolumeTrend.STABLE
    volume_quality: float = 50.0

    participation: ParticipationSnapshot = field(default_factory=_default_participation)
    liquidity: LiquidityProfile = field(default_factory=_default_liquidity_profile)
    effort_result: EffortResultAnalysis = field(default_factory=_default_effort_result)
    order_flow: OrderFlowSnapshot = field(default_factory=_default_order_flow)

    active_events: List[LiquidityEvent] = field(default_factory=list)
    last_event: Optional[LiquidityEvent] = None

    overall_confidence: float = 0.5
    execution_readiness: float = 0.5
    liquidity_score: float = 50.0

    regime: str = "unknown"
    trend_stage: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "timestamp": self.timestamp,
            "volume_bar": self.volume_bar.to_dict(),
            "volume_profile": self.volume_profile.to_dict(),
            "volume_level": self.volume_level.value,
            "volume_trend": self.volume_trend.value,
            "volume_quality": self.volume_quality,
            "participation": self.participation.to_dict(),
            "liquidity": self.liquidity.to_dict(),
            "effort_result": self.effort_result.to_dict(),
            "order_flow": self.order_flow.to_dict(),
            "active_events": [e.to_dict() for e in self.active_events],
            "last_event": self.last_event.to_dict() if self.last_event else None,
            "overall_confidence": self.overall_confidence,
            "execution_readiness": self.execution_readiness,
            "liquidity_score": self.liquidity_score,
            "regime": self.regime,
            "trend_stage": self.trend_stage,
        }
