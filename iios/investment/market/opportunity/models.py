"""iios/investment/market/opportunity/models.py
All domain models for the Institutional Market Opportunity Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class OpportunityCategory(str, Enum):
    TREND_FOLLOWING      = "trend_following"
    BREAKOUT_CANDIDATE   = "breakout_candidate"
    RETEST_CANDIDATE     = "retest_candidate"
    REVERSAL_CANDIDATE   = "reversal_candidate"
    MOMENTUM_CANDIDATE   = "momentum_candidate"
    MEAN_REVERSION       = "mean_reversion"
    SECTOR_ROTATION      = "sector_rotation"
    HIGH_RS              = "high_relative_strength"
    RECOVERY_CANDIDATE   = "recovery_candidate"
    DEFENSIVE_CANDIDATE  = "defensive_candidate"
    OBSERVATION_ONLY     = "observation_only"


class OpportunityLifecycleStage(str, Enum):
    DISCOVERED   = "discovered"
    EMERGING     = "emerging"
    GROWING      = "growing"
    HIGH_PRIORITY = "high_priority"
    CONFIRMED    = "confirmed"
    WEAKENING    = "weakening"
    EXPIRED      = "expired"
    ARCHIVED     = "archived"


class OpportunityPriority(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    NEW_OPPORTUNITY    = "new_opportunity"
    PRIORITY_UPGRADE   = "priority_upgrade"
    PRIORITY_DOWNGRADE = "priority_downgrade"
    LIFECYCLE_ADVANCE  = "lifecycle_advance"
    LIFECYCLE_DECAY    = "lifecycle_decay"
    CONFIDENCE_SURGE   = "confidence_surge"
    CONFIDENCE_DROP    = "confidence_drop"
    EXPIRATION         = "expiration"
    CATEGORY_CHANGE    = "category_change"


class OpportunityEventType(str, Enum):
    DISCOVERED   = "discovered"
    UPGRADED     = "upgraded"
    DOWNGRADED   = "downgraded"
    CONFIRMED    = "confirmed"
    WEAKENING    = "weakening"
    EXPIRED      = "expired"
    ARCHIVED     = "archived"
    RANK_CHANGE  = "rank_change"


class ScanScope(str, Enum):
    FULL_MARKET = "full_market"
    WATCHLIST   = "watchlist"
    PORTFOLIO   = "portfolio"
    SECTOR      = "sector"
    INDUSTRY    = "industry"
    THEME       = "theme"
    CUSTOM      = "custom"


class RankingModel(str, Enum):
    COMPOSITE    = "composite"
    MOMENTUM     = "momentum"
    QUALITY      = "quality"
    RISK_ADJUSTED = "risk_adjusted"
    CUSTOM       = "custom"


# ── Intelligence Context ──────────────────────────────────────────────────────

@dataclass
class IntelligenceContext:
    """Pre-computed intelligence from upstream IIOS engines.

    The Opportunity Engine never re-calculates any of these.
    Each value is the canonical output of its respective engine.
    """
    # Market Structure / Regime (from Market Structure + Regime engines)
    market_regime:          Optional[str] = None       # "bull" | "bear" | "sideways" …
    trend_stage:            Optional[str] = None       # "up" | "down" | "ranging" …
    trend_strength:         float = 50.0               # 0-100
    structure_score:        float = 50.0               # 0-100

    # Volume & Liquidity (from Volume & Liquidity Intelligence Engine)
    volume_ratio:           float = 1.0                # current / 20d avg
    volume_trend:           Optional[str] = None       # "expanding" | "contracting"
    liquidity_score:        float = 50.0               # 0-100

    # Volatility (from Volatility Intelligence Engine)
    volatility_regime:      Optional[str] = None       # "low" | "medium" | "high"
    volatility_percentile:  float = 0.5                # 0-1

    # Breadth (from Market Breadth Intelligence Engine)
    breadth_score:          float = 50.0               # 0-100
    breadth_regime:         Optional[str] = None
    above_ma20_pct:         float = 0.5                # fraction of sector above 20MA

    # Sector Rotation (from Sector Rotation Intelligence Engine)
    sector_rs_score:        float = 50.0               # 0-100
    sector_stage:           Optional[str] = None       # SectorStage value
    sector_rank:            int = 0                    # 1 = top sector
    sector_momentum:        float = 50.0               # 0-100

    # Correlation (from Correlation & Intermarket Intelligence Engine)
    correlation_regime:     Optional[str] = None
    systemic_risk_score:    float = 0.0                # 0-1

    # Company / Fundamental (from Company Intelligence Engine, if available)
    fundamental_score:      float = 50.0               # 0-100
    earnings_quality:       float = 50.0               # 0-100

    # Risk (from Risk Intelligence Engine)
    risk_score:             float = 50.0               # 0-100 (higher = safer)
    risk_regime:            Optional[str] = None

    # Raw price data (normalised)
    price:                  float = 0.0
    return_1bar:            float = 0.0
    return_5bar:            float = 0.0
    return_20bar:           float = 0.0
    return_60bar:           float = 0.0
    rs_vs_market:           float = 50.0               # 0-100 relative strength vs index

    # Extra context free-form
    metadata:               Dict[str, Any] = field(default_factory=dict)


# ── Asset Observation ─────────────────────────────────────────────────────────

@dataclass
class AssetObservation:
    """Complete snapshot of one asset at one time step, with pre-computed intelligence."""
    symbol:      str
    sector:      str
    industry:    str
    bar_index:   int
    timestamp:   float
    intelligence: IntelligenceContext = field(default_factory=IntelligenceContext)
    metadata:    Dict[str, Any] = field(default_factory=dict)


# ── Opportunity ───────────────────────────────────────────────────────────────

@dataclass
class Opportunity:
    """Core representation of a discovered investment opportunity."""
    opportunity_id:        str
    symbol:                str
    sector:                str
    industry:              str

    # Classification
    primary_category:      OpportunityCategory
    secondary_categories:  List[OpportunityCategory] = field(default_factory=list)

    # Priority & confidence
    priority:              OpportunityPriority = OpportunityPriority.MEDIUM
    priority_score:        float = 50.0          # 0-100
    confidence:            float = 0.5           # 0-1

    # Lifecycle
    lifecycle_stage:       OpportunityLifecycleStage = OpportunityLifecycleStage.DISCOVERED
    discovered_at_bar:     int = 0
    last_updated_bar:      int = 0
    stage_duration_bars:   int = 1

    # Ranking
    rank:                  int = 0               # 1 = best
    composite_score:       float = 50.0          # 0-100

    # Explanation
    discovery_reason:      str = ""
    evidence_keys:         List[str] = field(default_factory=list)
    risk_summary:          str = ""

    # Context snapshot at discovery
    market_regime:         Optional[str] = None
    sector_stage:          Optional[str] = None
    trend_stage:           Optional[str] = None

    metadata:              Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(
        symbol: str,
        sector: str,
        industry: str,
        primary_category: OpportunityCategory,
        bar_index: int,
    ) -> "Opportunity":
        return Opportunity(
            opportunity_id=str(uuid.uuid4()),
            symbol=symbol,
            sector=sector,
            industry=industry,
            primary_category=primary_category,
            discovered_at_bar=bar_index,
            last_updated_bar=bar_index,
        )

    def is_active(self) -> bool:
        return self.lifecycle_stage not in (
            OpportunityLifecycleStage.EXPIRED,
            OpportunityLifecycleStage.ARCHIVED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":       self.opportunity_id,
            "symbol":               self.symbol,
            "sector":               self.sector,
            "industry":             self.industry,
            "primary_category":     self.primary_category.value,
            "secondary_categories": [c.value for c in self.secondary_categories],
            "priority":             self.priority.value,
            "priority_score":       round(self.priority_score, 2),
            "confidence":           round(self.confidence, 4),
            "lifecycle_stage":      self.lifecycle_stage.value,
            "discovered_at_bar":    self.discovered_at_bar,
            "last_updated_bar":     self.last_updated_bar,
            "stage_duration_bars":  self.stage_duration_bars,
            "rank":                 self.rank,
            "composite_score":      round(self.composite_score, 2),
            "discovery_reason":     self.discovery_reason,
            "evidence_keys":        list(self.evidence_keys),
            "risk_summary":         self.risk_summary,
            "market_regime":        self.market_regime,
            "sector_stage":         self.sector_stage,
        }


# ── Alert ─────────────────────────────────────────────────────────────────────

@dataclass
class OpportunityAlert:
    alert_id:       str
    alert_type:     AlertType
    opportunity_id: str
    symbol:         str
    bar_index:      int
    severity:       float           # 0-1
    description:    str
    old_value:      Optional[str] = None
    new_value:      Optional[str] = None

    @staticmethod
    def make(
        alert_type: AlertType,
        opp: "Opportunity",
        bar_index: int,
        severity: float,
        description: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ) -> "OpportunityAlert":
        return OpportunityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            opportunity_id=opp.opportunity_id,
            symbol=opp.symbol,
            bar_index=bar_index,
            severity=severity,
            description=description,
            old_value=old_value,
            new_value=new_value,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":       self.alert_id,
            "alert_type":     self.alert_type.value,
            "opportunity_id": self.opportunity_id,
            "symbol":         self.symbol,
            "bar_index":      self.bar_index,
            "severity":       round(self.severity, 4),
            "description":    self.description,
            "old_value":      self.old_value,
            "new_value":      self.new_value,
        }


# ── Event ─────────────────────────────────────────────────────────────────────

@dataclass
class OpportunityEvent:
    event_type:     OpportunityEventType
    opportunity_id: str
    symbol:         str
    bar_index:      int
    description:    str
    severity:       float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type":     self.event_type.value,
            "opportunity_id": self.opportunity_id,
            "symbol":         self.symbol,
            "bar_index":      self.bar_index,
            "description":    self.description,
            "severity":       round(self.severity, 4),
        }


# ── Ranking ───────────────────────────────────────────────────────────────────

@dataclass
class RankingScore:
    opportunity_id:   str
    symbol:           str
    composite_score:  float    # 0-100
    trend_score:      float
    momentum_score:   float
    flow_score:       float
    sector_score:     float
    risk_adj_score:   float
    quality_score:    float
    rank:             int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":  self.opportunity_id,
            "symbol":          self.symbol,
            "composite_score": round(self.composite_score, 2),
            "trend_score":     round(self.trend_score, 2),
            "momentum_score":  round(self.momentum_score, 2),
            "flow_score":      round(self.flow_score, 2),
            "sector_score":    round(self.sector_score, 2),
            "risk_adj_score":  round(self.risk_adj_score, 2),
            "quality_score":   round(self.quality_score, 2),
            "rank":            self.rank,
        }


# ── Explanation ───────────────────────────────────────────────────────────────

@dataclass
class Evidence:
    key:         str
    value:       str
    weight:      float     # 0-1, contribution to opportunity
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key":         self.key,
            "value":       self.value,
            "weight":      round(self.weight, 4),
            "description": self.description,
        }


@dataclass
class OpportunityExplanation:
    opportunity_id: str
    symbol:         str
    summary:        str
    why_discovered: str
    evidence:       List[Evidence]
    risk_summary:   str
    confidence_explanation: str
    market_context: str
    strategy_suitability: List[str]    # which strategies this suits

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":          self.opportunity_id,
            "symbol":                  self.symbol,
            "summary":                 self.summary,
            "why_discovered":          self.why_discovered,
            "evidence":                [e.to_dict() for e in self.evidence],
            "risk_summary":            self.risk_summary,
            "confidence_explanation":  self.confidence_explanation,
            "market_context":          self.market_context,
            "strategy_suitability":    list(self.strategy_suitability),
        }


# ── Snapshot ──────────────────────────────────────────────────────────────────

@dataclass
class OpportunitySnapshotData:
    """Primary output of InstitutionalMarketOpportunityEngine.update()."""
    snapshot_id:         str
    bar_index:           int
    timestamp:           float

    opportunities:       List[Opportunity]     # sorted by rank
    new_discoveries:     List[Opportunity]
    expired:             List[Opportunity]
    alerts:              List[OpportunityAlert]
    events:              List[OpportunityEvent]

    # Summary stats
    total_active:        int
    high_priority_count: int
    critical_count:      int
    new_count:           int
    expired_count:       int

    # Top opportunities by category
    top_by_category:     Dict[str, List[str]]  # category → symbols

    # Context
    market_regime:       Optional[str] = None
    breadth_regime:      Optional[str] = None
    scan_scope:          str = ScanScope.FULL_MARKET.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "bar_index":           self.bar_index,
            "timestamp":           self.timestamp,
            "opportunities":       [o.to_dict() for o in self.opportunities],
            "new_discoveries":     [o.to_dict() for o in self.new_discoveries],
            "expired":             [o.to_dict() for o in self.expired],
            "alerts":              [a.to_dict() for a in self.alerts],
            "events":              [e.to_dict() for e in self.events],
            "total_active":        self.total_active,
            "high_priority_count": self.high_priority_count,
            "critical_count":      self.critical_count,
            "new_count":           self.new_count,
            "expired_count":       self.expired_count,
            "top_by_category":     {k: list(v) for k, v in self.top_by_category.items()},
            "market_regime":       self.market_regime,
            "breadth_regime":      self.breadth_regime,
        }
