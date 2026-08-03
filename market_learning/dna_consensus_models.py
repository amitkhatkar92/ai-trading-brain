"""
dna_consensus_models.py — Typed models for the MLS DNAConsensusEngine.

MLS Phase 4.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .dna_discovery_models import SeparationDirection


# ─── enumerations ─────────────────────────────────────────────────────────────

class ConsensusLevel(str, Enum):
    """Temporal horizon at which consensus has been validated."""
    DAILY     = "DAILY"
    WEEKLY    = "WEEKLY"
    MONTHLY   = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY    = "YEARLY"
    MASTER    = "MASTER"


class ConsensusState(str, Enum):
    """Lifecycle state in the extended consensus lifecycle (Phase 4)."""
    DISCOVERED    = "DISCOVERED"    # first observation
    REPLICATED    = "REPLICATED"    # 2–4 observations
    VERIFIED      = "VERIFIED"      # 5–9 observations
    INSTITUTIONAL = "INSTITUTIONAL" # 10+ obs, consensus_score >= threshold
    WEAKENING     = "WEAKENING"     # institutional but confidence declining
    DRIFTING      = "DRIFTING"      # any state with significant measured drift
    RETIRED       = "RETIRED"       # absent for retirement_days consecutive days


class DriftType(str, Enum):
    """Category of detected DNA drift."""
    STATISTICAL = "STATISTICAL"  # effect-size mean shift between windows
    REGIME      = "REGIME"       # regime composition changing over time
    SECTOR      = "SECTOR"       # concentration in fewer market conditions
    FEATURE     = "FEATURE"      # declining confidence signal
    TEMPORAL    = "TEMPORAL"     # appearance frequency declining


# ─── exceptions ───────────────────────────────────────────────────────────────

class DNAConsensusError(Exception):
    """General DNAConsensusEngine error."""


class ConsensusLibraryNotFoundError(DNAConsensusError):
    """No consensus library found on disk."""


# ─── confidence evolution ─────────────────────────────────────────────────────

@dataclass
class ConfidencePoint:
    """Single data point in a confidence time series."""
    date:       str
    confidence: float
    effect_abs: float
    regime:     str
    lifecycle:  str   # ConsensusState value at this observation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date":       self.date,
            "confidence": self.confidence,
            "effect_abs": self.effect_abs,
            "regime":     self.regime,
            "lifecycle":  self.lifecycle,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConfidencePoint:
        return cls(
            date=d["date"],
            confidence=float(d["confidence"]),
            effect_abs=float(d["effect_abs"]),
            regime=d["regime"],
            lifecycle=d["lifecycle"],
        )


@dataclass
class ConfidenceEvolution:
    """Complete confidence history for one (feature_name, direction) pair."""
    feature_name:    str
    direction:       str           # SeparationDirection.value
    level:           ConsensusLevel
    points:          List[ConfidencePoint]
    trend_slope:     float         # OLS slope of confidence vs time index
    trend_direction: str           # IMPROVING / DECLINING / STABLE
    window_days:     int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name":    self.feature_name,
            "direction":       self.direction,
            "level":           self.level.value,
            "points":          [p.to_dict() for p in self.points],
            "trend_slope":     self.trend_slope,
            "trend_direction": self.trend_direction,
            "window_days":     self.window_days,
        }


# ─── drift ────────────────────────────────────────────────────────────────────

@dataclass
class DriftMeasurement:
    """Measurement of one drift dimension."""
    drift_type:     DriftType
    magnitude:      float     # [0, 1]
    explanation:    str       # human-readable, reproducible description
    is_significant: bool      # magnitude >= consensus_drift_threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_type":     self.drift_type.value,
            "magnitude":      self.magnitude,
            "explanation":    self.explanation,
            "is_significant": self.is_significant,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DriftMeasurement:
        return cls(
            drift_type=DriftType(d["drift_type"]),
            magnitude=float(d["magnitude"]),
            explanation=d["explanation"],
            is_significant=bool(d["is_significant"]),
        )


@dataclass
class DriftReport:
    """All drift dimensions for one (feature_name, direction) pair."""
    drift_report_id:      str
    feature_name:         str
    direction:            str    # SeparationDirection.value
    trading_date:         str
    drifts:               List[DriftMeasurement]
    max_drift:            float
    has_significant_drift: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_report_id":      self.drift_report_id,
            "feature_name":         self.feature_name,
            "direction":            self.direction,
            "trading_date":         self.trading_date,
            "drifts":               [dm.to_dict() for dm in self.drifts],
            "max_drift":            self.max_drift,
            "has_significant_drift": self.has_significant_drift,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DriftReport:
        return cls(
            drift_report_id=d["drift_report_id"],
            feature_name=d["feature_name"],
            direction=d["direction"],
            trading_date=d["trading_date"],
            drifts=[DriftMeasurement.from_dict(dm) for dm in d["drifts"]],
            max_drift=float(d["max_drift"]),
            has_significant_drift=bool(d["has_significant_drift"]),
        )


# ─── stability summary ────────────────────────────────────────────────────────

@dataclass
class DNAStability:
    """Four-metric stability assessment for one ConsensusDNA."""
    feature_name:       str
    direction:          str    # SeparationDirection.value
    replication_freq:   float  # [0, 1]
    temporal_stability: float  # [0, 1]
    regime_consistency: float  # [0, 1]
    sector_consistency: float  # [0, 1]
    is_stable:          bool   # all four >= config thresholds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name":       self.feature_name,
            "direction":          self.direction,
            "replication_freq":   self.replication_freq,
            "temporal_stability": self.temporal_stability,
            "regime_consistency": self.regime_consistency,
            "sector_consistency": self.sector_consistency,
            "is_stable":          self.is_stable,
        }


# ─── consensus dna ────────────────────────────────────────────────────────────

@dataclass
class ConsensusDNA:
    """
    Institutional knowledge record for one (feature_name, direction) pair.

    Accumulates evidence from daily DNACharacteristic observations and
    maintains all metrics necessary to reproduce every state transition.
    """
    consensus_id:          str                # CON-{sha256[:8]}
    feature_name:          str
    direction:             SeparationDirection
    consensus_state:       ConsensusState
    consensus_score:       float              # [0, 1] weighted reproducible score
    replication_frequency: float              # occurrences / days_span [0, 1]
    evidence_count:        int                # total observations
    temporal_stability:    float              # 1 − CV of effect_abs [0, 1]
    regime_consistency:    float              # distinct_regimes / 5 [0, 1]
    sector_consistency:    float              # aliased to regime_consistency (Phase 4)
    confidence_trend:      float              # OLS slope of confidence series
    feature_persistence:   float             # appearances / window_days [0, 1]
    first_seen:            str               # ISO date
    last_seen:             str               # ISO date
    all_observations:      List[Dict[str, Any]]  # {date, effect_abs, confidence, regime}
    regime_counts:         Dict[str, int]    # regime label → appearance count
    level:                 ConsensusLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus_id":          self.consensus_id,
            "feature_name":          self.feature_name,
            "direction":             self.direction.value,
            "consensus_state":       self.consensus_state.value,
            "consensus_score":       self.consensus_score,
            "replication_frequency": self.replication_frequency,
            "evidence_count":        self.evidence_count,
            "temporal_stability":    self.temporal_stability,
            "regime_consistency":    self.regime_consistency,
            "sector_consistency":    self.sector_consistency,
            "confidence_trend":      self.confidence_trend,
            "feature_persistence":   self.feature_persistence,
            "first_seen":            self.first_seen,
            "last_seen":             self.last_seen,
            "all_observations":      self.all_observations,
            "regime_counts":         self.regime_counts,
            "level":                 self.level.value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConsensusDNA:
        return cls(
            consensus_id=d["consensus_id"],
            feature_name=d["feature_name"],
            direction=SeparationDirection(d["direction"]),
            consensus_state=ConsensusState(d["consensus_state"]),
            consensus_score=float(d["consensus_score"]),
            replication_frequency=float(d["replication_frequency"]),
            evidence_count=int(d["evidence_count"]),
            temporal_stability=float(d["temporal_stability"]),
            regime_consistency=float(d["regime_consistency"]),
            sector_consistency=float(d["sector_consistency"]),
            confidence_trend=float(d["confidence_trend"]),
            feature_persistence=float(d["feature_persistence"]),
            first_seen=d["first_seen"],
            last_seen=d["last_seen"],
            all_observations=list(d["all_observations"]),
            regime_counts=dict(d["regime_counts"]),
            level=ConsensusLevel(d["level"]),
        )


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class ConsensusStatistics:
    """Aggregate metrics for the current consensus library."""
    as_of_date:               str
    total_consensus_dna:      int
    institutional_count:      int
    weakening_count:          int
    drifting_count:           int
    retired_count:            int
    avg_consensus_score:      float
    avg_replication_freq:     float
    top_institutional_feature: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of_date":               self.as_of_date,
            "total_consensus_dna":      self.total_consensus_dna,
            "institutional_count":      self.institutional_count,
            "weakening_count":          self.weakening_count,
            "drifting_count":           self.drifting_count,
            "retired_count":            self.retired_count,
            "avg_consensus_score":      self.avg_consensus_score,
            "avg_replication_freq":     self.avg_replication_freq,
            "top_institutional_feature": self.top_institutional_feature,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConsensusStatistics:
        return cls(
            as_of_date=d.get("as_of_date", ""),
            total_consensus_dna=int(d.get("total_consensus_dna", 0)),
            institutional_count=int(d.get("institutional_count", 0)),
            weakening_count=int(d.get("weakening_count", 0)),
            drifting_count=int(d.get("drifting_count", 0)),
            retired_count=int(d.get("retired_count", 0)),
            avg_consensus_score=float(d.get("avg_consensus_score", 0.0)),
            avg_replication_freq=float(d.get("avg_replication_freq", 0.0)),
            top_institutional_feature=d.get("top_institutional_feature"),
        )


# ─── consensus library ────────────────────────────────────────────────────────

@dataclass
class ConsensusLibrary:
    """
    Complete institutional DNA knowledge base.

    Persisted to data/mls/consensus/library.json and rebuilt on each update().
    master_consensus contains only INSTITUTIONAL-state entries.
    """
    library_id:       str                   # MLS-LIB-YYYYMMDD
    as_of_date:       str
    all_consensus:    List[ConsensusDNA]
    master_consensus: List[ConsensusDNA]    # state == INSTITUTIONAL
    drift_reports:    List[DriftReport]
    statistics:       ConsensusStatistics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_id":       self.library_id,
            "as_of_date":       self.as_of_date,
            "all_consensus":    [c.to_dict() for c in self.all_consensus],
            "master_consensus": [c.to_dict() for c in self.master_consensus],
            "drift_reports":    [dr.to_dict() for dr in self.drift_reports],
            "statistics":       self.statistics.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConsensusLibrary:
        all_c  = [ConsensusDNA.from_dict(c)  for c in d.get("all_consensus", [])]
        master = [ConsensusDNA.from_dict(c)  for c in d.get("master_consensus", [])]
        drs    = [DriftReport.from_dict(dr)  for dr in d.get("drift_reports", [])]
        stats  = ConsensusStatistics.from_dict(d.get("statistics", {}))
        return cls(
            library_id=d["library_id"],
            as_of_date=d["as_of_date"],
            all_consensus=all_c,
            master_consensus=master,
            drift_reports=drs,
            statistics=stats,
        )
