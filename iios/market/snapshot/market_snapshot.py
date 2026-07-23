"""
market_snapshot.py — iios.market.snapshot
==========================================
Immutable published Market Snapshot — the single authoritative
representation of the complete Market Intelligence subsystem.

Performs NO analysis, NO calculations, NO policy evaluation,
NO execution.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    HealthStatus,
    SnapshotIntegrity,
    SnapshotStatus,
)
from .market_snapshot_metadata import SnapshotMetadata


# ===========================================================================
# Section value objects — all frozen, all serialisable
# ===========================================================================

@dataclass(frozen=True)
class MarketSummary:
    """Aggregated market-level summary."""
    overall_score:     float
    market_health:     str
    market_regime:     str
    trend_direction:   str
    trend_strength:    str
    market_confidence: float
    market_status:     str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":     round(self.overall_score, 2),
            "market_health":     self.market_health,
            "market_regime":     self.market_regime,
            "trend_direction":   self.trend_direction,
            "trend_strength":    self.trend_strength,
            "market_confidence": round(self.market_confidence, 4),
            "market_status":     self.market_status,
        }


@dataclass(frozen=True)
class RegimeSummary:
    """Market regime summary."""
    primary_regime:    str
    secondary_regime:  str
    regime_confidence: float
    regime_stability:  float
    regime_duration:   int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_regime":    self.primary_regime,
            "secondary_regime":  self.secondary_regime,
            "regime_confidence": round(self.regime_confidence, 4),
            "regime_stability":  round(self.regime_stability, 4),
            "regime_duration":   self.regime_duration,
        }


@dataclass(frozen=True)
class TrendSummary:
    """Trend and momentum summary."""
    primary_trend:    str
    secondary_trend:  str
    momentum_strength: float
    trend_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_trend":     self.primary_trend,
            "secondary_trend":   self.secondary_trend,
            "momentum_strength": round(self.momentum_strength, 4),
            "trend_confidence":  round(self.trend_confidence, 4),
        }


@dataclass(frozen=True)
class SectorSummary:
    """Sector analysis summary."""
    sector_rankings:  Tuple[str, ...]
    leading_sectors:  Tuple[str, ...]
    weak_sectors:     Tuple[str, ...]
    sector_rotation:  str
    sector_strength:  float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_rankings": list(self.sector_rankings),
            "leading_sectors": list(self.leading_sectors),
            "weak_sectors":    list(self.weak_sectors),
            "sector_rotation": self.sector_rotation,
            "sector_strength": round(self.sector_strength, 2),
        }


@dataclass(frozen=True)
class BreadthSummary:
    """Market breadth summary."""
    advance_decline:  float
    market_breadth:   str
    participation:    float
    breadth_strength: str
    breadth_score:    float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advance_decline":  round(self.advance_decline, 4),
            "market_breadth":   self.market_breadth,
            "participation":    round(self.participation, 4),
            "breadth_strength": self.breadth_strength,
            "breadth_score":    round(self.breadth_score, 2),
        }


@dataclass(frozen=True)
class VolatilitySummary:
    """Volatility summary."""
    current_volatility:    float
    historical_volatility: float
    implied_volatility:    float
    volatility_trend:      str
    volatility_score:      float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_volatility":    round(self.current_volatility, 4),
            "historical_volatility": round(self.historical_volatility, 4),
            "implied_volatility":    round(self.implied_volatility, 4),
            "volatility_trend":      self.volatility_trend,
            "volatility_score":      round(self.volatility_score, 2),
        }


@dataclass(frozen=True)
class LiquiditySummary:
    """Liquidity summary."""
    market_liquidity: str
    volume_profile:   str
    liquidity_trend:  str
    liquidity_score:  float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_liquidity": self.market_liquidity,
            "volume_profile":   self.volume_profile,
            "liquidity_trend":  self.liquidity_trend,
            "liquidity_score":  round(self.liquidity_score, 2),
        }


@dataclass(frozen=True)
class CorrelationSummary:
    """Correlation summary."""
    sector_correlations:     float
    index_correlations:      float
    intermarket_correlations: float
    correlation_score:        float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_correlations":      round(self.sector_correlations, 4),
            "index_correlations":       round(self.index_correlations, 4),
            "intermarket_correlations": round(self.intermarket_correlations, 4),
            "correlation_score":        round(self.correlation_score, 2),
        }


@dataclass(frozen=True)
class ForecastSummary:
    """Consolidated forecast summary."""
    intraday_forecast:   str
    short_term_forecast: str
    trend_forecast:      str
    volatility_forecast: str
    forecast_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intraday_forecast":   self.intraday_forecast,
            "short_term_forecast": self.short_term_forecast,
            "trend_forecast":      self.trend_forecast,
            "volatility_forecast": self.volatility_forecast,
            "forecast_confidence": round(self.forecast_confidence, 4),
        }


@dataclass(frozen=True)
class SystemHealth:
    """Subsystem and pipeline health summary."""
    subsystem_status:  Dict[str, str]
    validation_status: str
    snapshot_integrity: str
    pipeline_health:   str
    framework_health:  str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_status":   dict(self.subsystem_status),
            "validation_status":  self.validation_status,
            "snapshot_integrity": self.snapshot_integrity,
            "pipeline_health":    self.pipeline_health,
            "framework_health":   self.framework_health,
        }


@dataclass(frozen=True)
class AuditInfo:
    """Audit and lineage information."""
    analytics_version:  str
    model_versions:     Dict[str, str]
    policy_versions:    Dict[str, str]
    validation_summary: Dict[str, Any]
    audit_trail:        Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analytics_version":  self.analytics_version,
            "model_versions":     dict(self.model_versions),
            "policy_versions":    dict(self.policy_versions),
            "validation_summary": dict(self.validation_summary),
            "audit_trail":        list(self.audit_trail),
        }


@dataclass(frozen=True)
class SnapshotStats:
    """Snapshot-level statistics."""
    analysis_duration_s:  float
    forecast_duration_s:  float
    snapshot_size_bytes:  int
    component_count:      int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_duration_s": round(self.analysis_duration_s, 4),
            "forecast_duration_s": round(self.forecast_duration_s, 4),
            "snapshot_size_bytes": self.snapshot_size_bytes,
            "component_count":     self.component_count,
        }


# ===========================================================================
# MarketSnapshot — the primary published object
# ===========================================================================

@dataclass(frozen=True)
class MarketSnapshot:
    """
    Immutable published representation of the complete Market Intelligence
    subsystem.

    This is the ONLY published artefact from the Market Intelligence
    subsystem.  Downstream subsystems MUST consume :class:`MarketSnapshot`
    instead of directly accessing Market Engine, Policy Framework, or
    Analytics Framework.

    No analysis, no calculations, no policy evaluation, no execution.

    Fields
    ------
    snapshot_id :          Unique snapshot identifier.
    market_session_id :    Source market session identifier.
    market_analysis_id :   Source market analysis identifier.
    workflow_id :          Originating workflow identifier.
    exchange :             Exchange identifier.
    market :               Market name / description.
    market_type :          Market type string.
    timeframe :            Analysis timeframe string.
    trading_session :      Trading session string.
    market_status :        Market operational status.
    lifecycle_state :      Lifecycle state at snapshot time.
    market_version :       Market component version.
    framework_version :    Framework version string.
    snapshot_timestamp :   Wall-clock time the snapshot was taken.
    created_at :           Creation timestamp.
    updated_at :           Last update timestamp.
    status :               Snapshot publication status.
    version :              Monotonically increasing version counter.
    is_valid :             True when snapshot passed all validation checks.

    Summary sections
    ----------------
    market_summary
    regime_summary
    trend_summary
    sector_summary
    breadth_summary
    volatility_summary
    liquidity_summary
    correlation_summary
    forecast_summary
    system_health
    audit_info
    snapshot_stats
    metadata
    """
    # Core identifiers
    snapshot_id:         str
    market_session_id:   str
    market_analysis_id:  str
    workflow_id:         str
    exchange:            str
    market:              str
    market_type:         str
    timeframe:           str
    trading_session:     str
    market_status:       str
    lifecycle_state:     str
    market_version:      str
    framework_version:   str
    snapshot_timestamp:  float
    created_at:          float
    updated_at:          float

    # Status
    status:              SnapshotStatus
    version:             int
    is_valid:            bool

    # Summary sections (all optional — may be None if data not available)
    market_summary:      Optional[MarketSummary]
    regime_summary:      Optional[RegimeSummary]
    trend_summary:       Optional[TrendSummary]
    sector_summary:      Optional[SectorSummary]
    breadth_summary:     Optional[BreadthSummary]
    volatility_summary:  Optional[VolatilitySummary]
    liquidity_summary:   Optional[LiquiditySummary]
    correlation_summary: Optional[CorrelationSummary]
    forecast_summary:    Optional[ForecastSummary]
    system_health:       Optional[SystemHealth]
    audit_info:          Optional[AuditInfo]
    snapshot_stats:      Optional[SnapshotStats]
    metadata:            Optional[SnapshotMetadata]

    @property
    def is_published(self) -> bool:
        return self.status == SnapshotStatus.PUBLISHED

    @property
    def is_archived(self) -> bool:
        return self.status == SnapshotStatus.ARCHIVED

    @property
    def integrity(self) -> SnapshotIntegrity:
        """Classify how much data is present."""
        section_count = sum(1 for s in [
            self.market_summary, self.regime_summary, self.trend_summary,
            self.sector_summary, self.breadth_summary, self.volatility_summary,
            self.liquidity_summary, self.correlation_summary, self.forecast_summary,
        ] if s is not None)
        if section_count >= 7:
            return SnapshotIntegrity.COMPLETE
        if section_count >= 4:
            return SnapshotIntegrity.PARTIAL
        if section_count >= 1:
            return SnapshotIntegrity.MINIMAL
        return SnapshotIntegrity.EMPTY

    @property
    def overall_score(self) -> float:
        """Convenience accessor for the overall market score."""
        return self.market_summary.overall_score if self.market_summary else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Core identifiers
            "snapshot_id":          self.snapshot_id,
            "market_session_id":    self.market_session_id,
            "market_analysis_id":   self.market_analysis_id,
            "workflow_id":          self.workflow_id,
            "exchange":             self.exchange,
            "market":               self.market,
            "market_type":          self.market_type,
            "timeframe":            self.timeframe,
            "trading_session":      self.trading_session,
            "market_status":        self.market_status,
            "lifecycle_state":      self.lifecycle_state,
            "market_version":       self.market_version,
            "framework_version":    self.framework_version,
            "snapshot_timestamp":   self.snapshot_timestamp,
            "created_at":           self.created_at,
            "updated_at":           self.updated_at,
            # Status
            "status":               self.status.value,
            "version":              self.version,
            "is_valid":             self.is_valid,
            "integrity":            self.integrity.value,
            # Summary sections
            "market_summary":       self.market_summary.to_dict()      if self.market_summary      else None,
            "regime_summary":       self.regime_summary.to_dict()      if self.regime_summary      else None,
            "trend_summary":        self.trend_summary.to_dict()       if self.trend_summary       else None,
            "sector_summary":       self.sector_summary.to_dict()      if self.sector_summary      else None,
            "breadth_summary":      self.breadth_summary.to_dict()     if self.breadth_summary     else None,
            "volatility_summary":   self.volatility_summary.to_dict()  if self.volatility_summary  else None,
            "liquidity_summary":    self.liquidity_summary.to_dict()   if self.liquidity_summary   else None,
            "correlation_summary":  self.correlation_summary.to_dict() if self.correlation_summary else None,
            "forecast_summary":     self.forecast_summary.to_dict()    if self.forecast_summary    else None,
            "system_health":        self.system_health.to_dict()       if self.system_health       else None,
            "audit_info":           self.audit_info.to_dict()          if self.audit_info          else None,
            "snapshot_stats":       self.snapshot_stats.to_dict()      if self.snapshot_stats      else None,
            "metadata":             self.metadata.to_dict()            if self.metadata            else None,
        }
