"""iios/investment/market/integration/models.py
All domain types for the Market Intelligence Integration & Validation Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ── Enumerations ──────────────────────────────────────────────────────────────

class EngineSource(str, Enum):
    MARKET_STRUCTURE  = "market_structure"
    MARKET_REGIME     = "market_regime"
    TREND             = "trend"
    VOLUME_LIQUIDITY  = "volume_liquidity"
    VOLATILITY        = "volatility"
    BREADTH           = "breadth"
    CORRELATION       = "correlation"
    SECTOR_ROTATION   = "sector_rotation"
    OPPORTUNITY       = "opportunity"
    UNKNOWN           = "unknown"


class MarketStateLabel(str, Enum):
    RISK_ON     = "risk_on"
    RISK_OFF    = "risk_off"
    TRANSITION  = "transition"
    CRISIS      = "crisis"
    RECOVERY    = "recovery"
    NEUTRAL     = "neutral"
    UNKNOWN     = "unknown"


class ConflictSeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class ConflictType(str, Enum):
    TREND_REGIME      = "trend_regime"
    TREND_VOLATILITY  = "trend_volatility"
    BREAKOUT_LIQUIDITY = "breakout_liquidity"
    BREADTH_SECTOR    = "breadth_sector"
    CORRELATION_REGIME = "correlation_regime"
    OPPORTUNITY_RISK  = "opportunity_risk"
    CROSS_ENGINE      = "cross_engine"


class ValidationStatus(str, Enum):
    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"


class HealthStatus(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"
    STALE    = "stale"
    MISSING  = "missing"
    FAILED   = "failed"


# ── Input types ───────────────────────────────────────────────────────────────

@dataclass
class EnginePayload:
    """Wrapper around a single upstream engine's output for one bar."""
    engine_name: str
    source:      EngineSource
    payload:     Any
    bar_index:   int
    timestamp:   float
    version:     int = 1

    def get_attr(self, *names: str, default: Any = None) -> Any:
        """Duck-type accessor: tries each name against payload attributes/dict keys."""
        for name in names:
            if isinstance(self.payload, dict):
                if name in self.payload:
                    return self.payload[name]
            elif hasattr(self.payload, name):
                val = getattr(self.payload, name, None)
                if val is not None:
                    return val
        return default


@dataclass
class IntelligenceBundle:
    """Aggregated inputs from all upstream engines for one bar."""
    bar_index: int
    timestamp: float
    payloads:  Dict[str, EnginePayload] = field(default_factory=dict)

    def add(self, payload: EnginePayload) -> None:
        self.payloads[payload.engine_name] = payload

    def get(self, engine_name: str) -> Optional[EnginePayload]:
        return self.payloads.get(engine_name)

    @property
    def engine_names(self) -> Set[str]:
        return set(self.payloads.keys())


# ── Validation ────────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    rule_name:        str
    conflict_type:    ConflictType
    severity:         ConflictSeverity
    description:      str
    engines_involved: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name":        self.rule_name,
            "conflict_type":    self.conflict_type.value,
            "severity":         self.severity.value,
            "description":      self.description,
            "engines_involved": list(self.engines_involved),
        }


@dataclass
class ValidationReport:
    bar_index:    int
    status:       ValidationStatus
    issues:       List[ValidationIssue] = field(default_factory=list)
    passed_rules: int = 0
    failed_rules: int = 0
    warned_rules: int = 0

    @property
    def has_critical(self) -> bool:
        return any(i.severity is ConflictSeverity.CRITICAL for i in self.issues)

    @property
    def has_high(self) -> bool:
        return any(i.severity is ConflictSeverity.HIGH for i in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index":    self.bar_index,
            "status":       self.status.value,
            "issues":       [i.to_dict() for i in self.issues],
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warned_rules": self.warned_rules,
        }


# ── Conflicts ─────────────────────────────────────────────────────────────────

@dataclass
class Conflict:
    conflict_id:      str
    conflict_type:    ConflictType
    severity:         ConflictSeverity
    engines:          List[str]
    description:      str
    engine_a_signal:  str
    engine_b_signal:  str
    resolved:         bool = False
    resolution:       Optional[str] = None

    @staticmethod
    def new(
        conflict_type:   ConflictType,
        severity:        ConflictSeverity,
        engines:         List[str],
        description:     str,
        engine_a_signal: str = "",
        engine_b_signal: str = "",
    ) -> "Conflict":
        return Conflict(
            conflict_id=str(uuid.uuid4()),
            conflict_type=conflict_type,
            severity=severity,
            engines=engines,
            description=description,
            engine_a_signal=engine_a_signal,
            engine_b_signal=engine_b_signal,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":     self.conflict_id,
            "conflict_type":   self.conflict_type.value,
            "severity":        self.severity.value,
            "engines":         list(self.engines),
            "description":     self.description,
            "engine_a_signal": self.engine_a_signal,
            "engine_b_signal": self.engine_b_signal,
            "resolved":        self.resolved,
            "resolution":      self.resolution,
        }


@dataclass
class ConflictSummary:
    bar_index:  int
    total:      int
    critical:   int
    high:       int
    medium:     int
    low:        int
    resolved:   int
    unresolved: int
    conflicts:  List[Conflict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index":  self.bar_index,
            "total":      self.total,
            "critical":   self.critical,
            "high":       self.high,
            "medium":     self.medium,
            "low":        self.low,
            "resolved":   self.resolved,
            "unresolved": self.unresolved,
            "conflicts":  [c.to_dict() for c in self.conflicts],
        }


# ── Quality ───────────────────────────────────────────────────────────────────

@dataclass
class QualityDimension:
    name:    str
    score:   float    # 0-100
    weight:  float
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":    self.name,
            "score":   round(self.score, 2),
            "weight":  round(self.weight, 3),
            "details": self.details,
        }


@dataclass
class QualityScore:
    bar_index:    int
    overall:      float    # 0-100 weighted
    completeness: float
    consistency:  float
    freshness:    float
    reliability:  float
    dimensions:   List[QualityDimension] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index":    self.bar_index,
            "overall":      round(self.overall, 2),
            "completeness": round(self.completeness, 2),
            "consistency":  round(self.consistency, 2),
            "freshness":    round(self.freshness, 2),
            "reliability":  round(self.reliability, 2),
            "dimensions":   [d.to_dict() for d in self.dimensions],
        }


# ── Health ────────────────────────────────────────────────────────────────────

@dataclass
class EngineHealthRecord:
    engine_name:      str
    status:           HealthStatus
    last_update_bar:  int
    last_update_ts:   float
    staleness_bars:   int = 0
    error_count:      int = 0
    last_error:       Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name":     self.engine_name,
            "status":          self.status.value,
            "last_update_bar": self.last_update_bar,
            "last_update_ts":  self.last_update_ts,
            "staleness_bars":  self.staleness_bars,
            "error_count":     self.error_count,
            "last_error":      self.last_error,
        }


# ── Snapshot ──────────────────────────────────────────────────────────────────

@dataclass
class MarketIntelligenceSnapshot:
    """Single canonical output: the ONLY market intelligence interface for
    downstream IIOS components."""
    snapshot_id:           str
    bar_index:             int
    timestamp:             float
    market_state_label:    MarketStateLabel
    market_regime:         Optional[str]
    trend_direction:       Optional[str]
    trend_strength:        float
    volatility_regime:     Optional[str]
    breadth_regime:        Optional[str]
    correlation_regime:    Optional[str]
    liquidity_regime:      Optional[str]
    sector_rotation_phase: Optional[str]
    leading_sectors:       List[str]
    lagging_sectors:       List[str]
    active_opportunities:  int
    top_opportunity_symbols: List[str]
    overall_confidence:    float    # 0-100
    quality:               QualityScore
    validation:            ValidationReport
    conflicts:             ConflictSummary
    engine_health:         Dict[str, EngineHealthRecord]
    engines_received:      List[str]
    missing_engines:       List[str]
    summary_text:          str
    metadata:              Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def empty(bar_index: int, timestamp: float) -> "MarketIntelligenceSnapshot":
        empty_q   = QualityScore(bar_index, 0.0, 0.0, 0.0, 0.0, 0.0)
        empty_v   = ValidationReport(bar_index, ValidationStatus.PASSED)
        empty_c   = ConflictSummary(bar_index, 0, 0, 0, 0, 0, 0, 0)
        return MarketIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            bar_index=bar_index, timestamp=timestamp,
            market_state_label=MarketStateLabel.UNKNOWN,
            market_regime=None, trend_direction=None, trend_strength=50.0,
            volatility_regime=None, breadth_regime=None, correlation_regime=None,
            liquidity_regime=None, sector_rotation_phase=None,
            leading_sectors=[], lagging_sectors=[],
            active_opportunities=0, top_opportunity_symbols=[],
            overall_confidence=0.0, quality=empty_q, validation=empty_v,
            conflicts=empty_c, engine_health={}, engines_received=[],
            missing_engines=[], summary_text="No data",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "bar_index":             self.bar_index,
            "timestamp":             self.timestamp,
            "market_state_label":    self.market_state_label.value,
            "market_regime":         self.market_regime,
            "trend_direction":       self.trend_direction,
            "trend_strength":        round(self.trend_strength, 2),
            "volatility_regime":     self.volatility_regime,
            "breadth_regime":        self.breadth_regime,
            "correlation_regime":    self.correlation_regime,
            "liquidity_regime":      self.liquidity_regime,
            "sector_rotation_phase": self.sector_rotation_phase,
            "leading_sectors":       list(self.leading_sectors),
            "lagging_sectors":       list(self.lagging_sectors),
            "active_opportunities":  self.active_opportunities,
            "top_opportunity_symbols": list(self.top_opportunity_symbols),
            "overall_confidence":    round(self.overall_confidence, 2),
            "quality":               self.quality.to_dict(),
            "validation":            self.validation.to_dict(),
            "conflicts":             self.conflicts.to_dict(),
            "engines_received":      list(self.engines_received),
            "missing_engines":       list(self.missing_engines),
            "summary_text":          self.summary_text,
        }
