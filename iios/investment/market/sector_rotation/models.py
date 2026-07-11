"""iios/investment/market/sector_rotation/models.py
Core domain models for the Institutional Sector Rotation Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Enums ─────────────────────────────────────────────────────────────────────

class SectorStage(str, Enum):
    EMERGING         = "emerging"
    LEADING          = "leading"
    MATURE           = "mature"
    WEAKENING        = "weakening"
    LAGGING          = "lagging"
    RECOVERING       = "recovering"
    OUTPERFORMING    = "outperforming"
    UNDERPERFORMING  = "underperforming"
    UNKNOWN          = "unknown"


class RotationType(str, Enum):
    INTO_DEFENSIVES    = "into_defensives"
    INTO_CYCLICALS     = "into_cyclicals"
    INTO_GROWTH        = "into_growth"
    INTO_VALUE         = "into_value"
    OUT_OF_DEFENSIVES  = "out_of_defensives"
    OUT_OF_CYCLICALS   = "out_of_cyclicals"
    LEADERSHIP_CHANGE  = "leadership_change"
    BROAD_ROTATION     = "broad_rotation"
    SECTOR_SPECIFIC    = "sector_specific"
    NO_ROTATION        = "no_rotation"


class RotationStrength(str, Enum):
    WEAK     = "weak"
    MODERATE = "moderate"
    STRONG   = "strong"
    EXTREME  = "extreme"


class FlowType(str, Enum):
    ACCUMULATION          = "accumulation"
    DISTRIBUTION          = "distribution"
    NEUTRAL               = "neutral"
    INSTITUTIONAL_BUYING  = "institutional_buying"
    INSTITUTIONAL_SELLING = "institutional_selling"


class SectorEventType(str, Enum):
    LEADERSHIP_CHANGE   = "leadership_change"
    ROTATION_START      = "rotation_start"
    ROTATION_CONFIRMED  = "rotation_confirmed"
    SECTOR_BREAKOUT     = "sector_breakout"
    SECTOR_BREAKDOWN    = "sector_breakdown"
    EMERGING_LEADER     = "emerging_leader"
    FALLING_LEADER      = "falling_leader"
    RECOVERY_START      = "recovery_start"
    STAGE_TRANSITION    = "stage_transition"
    CAPITULATION        = "capitulation"


class TaxonomyType(str, Enum):
    GICS   = "GICS"
    ICB    = "ICB"
    NSE    = "NSE"
    CUSTOM = "CUSTOM"


class SectorCharacter(str, Enum):
    DEFENSIVE = "defensive"
    CYCLICAL  = "cyclical"
    GROWTH    = "growth"
    VALUE     = "value"
    UNKNOWN   = "unknown"


# ── Input types ───────────────────────────────────────────────────────────────

@dataclass
class SecurityData:
    """Single security's data at one time step."""
    symbol: str
    return_pct: float             # e.g. 0.01 = 1%
    sector: str
    industry: str
    subsector: str = ""
    market_cap: float = 0.0       # billions
    volume: float = 0.0
    price: float = 0.0
    avg_volume_20d: float = 0.0   # for volume ratio
    volatility: float = 0.0
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume_ratio(self) -> float:
        if self.avg_volume_20d < 1e-9:
            return 1.0
        return self.volume / self.avg_volume_20d

    @property
    def is_advancing(self) -> bool:
        return self.return_pct > 0.0

    @property
    def is_declining(self) -> bool:
        return self.return_pct < 0.0


@dataclass
class MarketSnapshot:
    """Cross-sectional snapshot of all securities at one time step."""
    bar_index:       int
    timestamp:       float
    securities:      List[SecurityData]
    benchmark_return: float = 0.0   # index/market return for relative comparison
    taxonomy:        str = TaxonomyType.GICS.value

    @property
    def total(self) -> int:
        return len(self.securities)

    def by_sector(self) -> Dict[str, List[SecurityData]]:
        result: Dict[str, List[SecurityData]] = {}
        for s in self.securities:
            result.setdefault(s.sector, []).append(s)
        return result

    def by_industry(self) -> Dict[str, List[SecurityData]]:
        result: Dict[str, List[SecurityData]] = {}
        for s in self.securities:
            result.setdefault(s.industry, []).append(s)
        return result

    def sectors(self) -> List[str]:
        return sorted({s.sector for s in self.securities})

    def industries(self) -> List[str]:
        return sorted({s.industry for s in self.securities})


# ── Sector performance ────────────────────────────────────────────────────────

@dataclass
class SectorPerformance:
    sector: str
    bar_index: int
    # Absolute returns (weighted average of securities)
    return_1bar:  float
    return_5bar:  float
    return_20bar: float
    return_60bar: float
    # Relative returns vs benchmark
    rel_return_1bar:  float
    rel_return_5bar:  float
    rel_return_20bar: float
    # Breadth & participation
    breadth_pct:      float   # fraction advancing
    avg_volume_ratio: float
    # Scores 0-100
    momentum_score:   float
    strength_score:   float
    n_securities:     int
    # Character metadata
    sector_character: str = SectorCharacter.UNKNOWN.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector":           self.sector,
            "bar_index":        self.bar_index,
            "return_1bar":      round(self.return_1bar, 4),
            "return_5bar":      round(self.return_5bar, 4),
            "return_20bar":     round(self.return_20bar, 4),
            "return_60bar":     round(self.return_60bar, 4),
            "rel_return_1bar":  round(self.rel_return_1bar, 4),
            "rel_return_5bar":  round(self.rel_return_5bar, 4),
            "rel_return_20bar": round(self.rel_return_20bar, 4),
            "breadth_pct":      round(self.breadth_pct, 4),
            "avg_volume_ratio": round(self.avg_volume_ratio, 4),
            "momentum_score":   round(self.momentum_score, 2),
            "strength_score":   round(self.strength_score, 2),
            "n_securities":     self.n_securities,
        }


# ── Industry profile ──────────────────────────────────────────────────────────

@dataclass
class IndustryProfile:
    industry: str
    sector: str
    bar_index: int
    return_1bar:         float
    return_5bar:         float
    return_20bar:        float
    rel_to_sector:       float   # industry return - sector return
    rel_to_benchmark:    float
    momentum_score:      float   # 0-100
    breadth_pct:         float
    n_securities:        int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry":       self.industry,
            "sector":         self.sector,
            "return_1bar":    round(self.return_1bar, 4),
            "return_5bar":    round(self.return_5bar, 4),
            "return_20bar":   round(self.return_20bar, 4),
            "rel_to_sector":  round(self.rel_to_sector, 4),
            "rel_to_benchmark": round(self.rel_to_benchmark, 4),
            "momentum_score": round(self.momentum_score, 2),
            "breadth_pct":    round(self.breadth_pct, 4),
            "n_securities":   self.n_securities,
        }


# ── Relative strength ─────────────────────────────────────────────────────────

@dataclass
class RelativeStrengthScore:
    symbol: str
    vs_benchmark: float    # raw RS vs index
    vs_group:     float    # RS vs peer group (sector or industry)
    composite:    float    # 0-100 composite RS score
    rank:         int      # 1 = strongest
    percentile:   float    # 0-1; 1.0 = top

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":       self.symbol,
            "vs_benchmark": round(self.vs_benchmark, 4),
            "vs_group":     round(self.vs_group, 4),
            "composite":    round(self.composite, 2),
            "rank":         self.rank,
            "percentile":   round(self.percentile, 4),
        }


# ── Capital flow ──────────────────────────────────────────────────────────────

@dataclass
class CapitalFlowProfile:
    sector: str
    bar_index: int
    flow_type:           FlowType
    flow_intensity:      float   # 0-1
    volume_ratio:        float   # sector avg volume / 20d avg
    accumulation_score:  float   # 0-100  (100 = pure buying)
    distribution_score:  float   # 0-100
    net_flow_signal:     float   # -1 to 1  (1 = max inflow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector":              self.sector,
            "bar_index":           self.bar_index,
            "flow_type":           self.flow_type.value,
            "flow_intensity":      round(self.flow_intensity, 4),
            "volume_ratio":        round(self.volume_ratio, 4),
            "accumulation_score":  round(self.accumulation_score, 2),
            "distribution_score":  round(self.distribution_score, 2),
            "net_flow_signal":     round(self.net_flow_signal, 4),
        }


# ── Rotation ──────────────────────────────────────────────────────────────────

@dataclass
class RotationSignal:
    rotation_type:  RotationType
    strength:       RotationStrength
    from_sectors:   List[str]
    to_sectors:     List[str]
    confidence:     float     # 0-1
    bars_active:    int
    confirmed:      bool
    description:    str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rotation_type":  self.rotation_type.value,
            "strength":       self.strength.value,
            "from_sectors":   list(self.from_sectors),
            "to_sectors":     list(self.to_sectors),
            "confidence":     round(self.confidence, 4),
            "bars_active":    self.bars_active,
            "confirmed":      self.confirmed,
            "description":    self.description,
        }


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@dataclass
class SectorLifecycleProfile:
    sector:               str
    stage:                SectorStage
    stage_duration_bars:  int
    previous_stage:       Optional[SectorStage]
    stage_confidence:     float   # 0-1
    transition_probability: float # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector":                self.sector,
            "stage":                 self.stage.value,
            "stage_duration_bars":   self.stage_duration_bars,
            "previous_stage":        self.previous_stage.value if self.previous_stage else None,
            "stage_confidence":      round(self.stage_confidence, 4),
            "transition_probability": round(self.transition_probability, 4),
        }


# ── Confidence ────────────────────────────────────────────────────────────────

@dataclass
class SectorConfidenceScore:
    leadership_confidence: float   # 0-1
    rotation_confidence:   float   # 0-1
    strength_score:        float   # 0-100
    flow_confidence:       float   # 0-1
    overall_score:         float   # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leadership_confidence": round(self.leadership_confidence, 4),
            "rotation_confidence":   round(self.rotation_confidence, 4),
            "strength_score":        round(self.strength_score, 2),
            "flow_confidence":       round(self.flow_confidence, 4),
            "overall_score":         round(self.overall_score, 2),
        }


# ── Ranking ───────────────────────────────────────────────────────────────────

@dataclass
class SectorRankEntry:
    rank:              int
    sector:            str
    composite_score:   float   # 0-100
    relative_strength: float   # RS vs benchmark (-)
    momentum:          float   # momentum score 0-100
    flow_signal:       float   # net flow signal -1 to 1
    lifecycle_stage:   SectorStage
    rank_change:       int     # positive = improved rank vs prev bar

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank":              self.rank,
            "sector":            self.sector,
            "composite_score":   round(self.composite_score, 2),
            "relative_strength": round(self.relative_strength, 4),
            "momentum":          round(self.momentum, 2),
            "flow_signal":       round(self.flow_signal, 4),
            "lifecycle_stage":   self.lifecycle_stage.value,
            "rank_change":       self.rank_change,
        }


# ── Events ────────────────────────────────────────────────────────────────────

@dataclass
class SectorEvent:
    event_type:      SectorEventType
    sector:          str
    bar_index:       int
    severity:        float   # 0-1
    description:     str
    from_stage:      Optional[SectorStage] = None
    to_stage:        Optional[SectorStage] = None
    related_sectors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type":      self.event_type.value,
            "sector":          self.sector,
            "bar_index":       self.bar_index,
            "severity":        round(self.severity, 4),
            "description":     self.description,
            "from_stage":      self.from_stage.value if self.from_stage else None,
            "to_stage":        self.to_stage.value if self.to_stage else None,
            "related_sectors": list(self.related_sectors),
        }


# ── Primary output ────────────────────────────────────────────────────────────

@dataclass
class SectorIntelligenceSnapshot:
    """Primary output of InstitutionalSectorRotationEngine."""
    snapshot_id:        str
    bar_index:          int
    timestamp:          float
    taxonomy:           str

    sector_rankings:    List[SectorRankEntry]
    sector_perf:        Dict[str, SectorPerformance]
    industry_profiles:  Dict[str, IndustryProfile]
    rotation_signals:   List[RotationSignal]
    rs_scores:          Dict[str, RelativeStrengthScore]
    capital_flows:      Dict[str, CapitalFlowProfile]
    lifecycle_profiles: Dict[str, SectorLifecycleProfile]
    confidence:         SectorConfidenceScore
    active_events:      List[SectorEvent]
    last_event:         Optional[SectorEvent]

    # Quick-access summary
    leaders:  List[str]    # top sectors by rank
    laggards: List[str]    # bottom sectors by rank
    emerging: List[str]    # EMERGING stage sectors

    # Cross-engine context
    market_regime:     Optional[str] = None
    breadth_regime:    Optional[str] = None
    volatility_regime: Optional[str] = None
    correlation_regime: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "bar_index":         self.bar_index,
            "timestamp":         self.timestamp,
            "taxonomy":          self.taxonomy,
            "sector_rankings":   [r.to_dict() for r in self.sector_rankings],
            "sector_perf":       {k: v.to_dict() for k, v in self.sector_perf.items()},
            "industry_profiles": {k: v.to_dict() for k, v in self.industry_profiles.items()},
            "rotation_signals":  [s.to_dict() for s in self.rotation_signals],
            "rs_scores":         {k: v.to_dict() for k, v in self.rs_scores.items()},
            "capital_flows":     {k: v.to_dict() for k, v in self.capital_flows.items()},
            "lifecycle_profiles": {k: v.to_dict() for k, v in self.lifecycle_profiles.items()},
            "confidence":        self.confidence.to_dict(),
            "active_events":     [e.to_dict() for e in self.active_events],
            "last_event":        self.last_event.to_dict() if self.last_event else None,
            "leaders":           list(self.leaders),
            "laggards":          list(self.laggards),
            "emerging":          list(self.emerging),
            "market_regime":     self.market_regime,
            "breadth_regime":    self.breadth_regime,
            "volatility_regime": self.volatility_regime,
        }
