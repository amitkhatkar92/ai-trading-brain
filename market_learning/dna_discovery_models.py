"""
dna_discovery_models.py — Typed models for the MLS DNADiscoveryEngine.

MLS Phase 3.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class FeatureType(str, Enum):
    """Statistical nature of a feature value."""
    CONTINUOUS  = "CONTINUOUS"   # real-valued, e.g. mom_1d, rsi
    BINARY      = "BINARY"       # {0.0, 1.0}, e.g. volume_spike
    ORDINAL     = "ORDINAL"      # discrete ordered integers
    CATEGORICAL = "CATEGORICAL"  # unordered distinct values (rare in MLS)


class DNALifecycle(str, Enum):
    """Lifecycle stage for a DNACharacteristic."""
    DISCOVERED = "DISCOVERED"   # first observation
    REPLICATED = "REPLICATED"   # seen on 1 previous day
    VERIFIED   = "VERIFIED"     # seen on 2+ previous days
    STABLE     = "STABLE"       # seen on 4+ days, consistent direction
    WEAKENING  = "WEAKENING"    # effect size declining over last 3 appearances
    RETIRED    = "RETIRED"      # absent for retirement_days consecutive days


class SeparationDirection(str, Enum):
    """Direction of feature separation for a DNACharacteristic."""
    WINNERS_HIGHER  = "WINNERS_HIGHER"   # winner group has higher feature values
    WINNERS_LOWER   = "WINNERS_LOWER"    # loser group has higher feature values
    NEUTRALS_HIGHER = "NEUTRALS_HIGHER"  # neutral group higher than extremes
    NEUTRALS_LOWER  = "NEUTRALS_LOWER"   # neutral group lower than extremes


# ─── exceptions ───────────────────────────────────────────────────────────────

class DNADiscoveryError(Exception):
    """General DNADiscoveryEngine error."""


class InsufficientDataError(DNADiscoveryError):
    """Winner or loser group too small to run statistical analysis."""


class DiscoveryNotFoundError(DNADiscoveryError):
    """No discovery report exists for the requested trading date."""


# ─── feature evidence ─────────────────────────────────────────────────────────

@dataclass
class FeatureEvidence:
    """Raw statistical evidence for one feature's separation power."""

    feature_name:  str
    feature_type:  FeatureType
    # Group statistics (group_a = winners or neutrals, group_b = losers or extremes)
    winner_mean:   float
    winner_std:    float
    loser_mean:    float
    loser_std:     float
    # Effect size
    effect_size:   float       # signed Cohen's d (>0 means group_a higher)
    effect_abs:    float       # |Cohen's d|
    direction:     SeparationDirection
    # Bootstrap 95% CI for Cohen's d
    ci_low:        float
    ci_high:       float
    # Monotonic relationship
    spearman_corr: float       # Spearman r between feature and winner-label
    # Sample sizes
    n_winners:     int
    n_losers:      int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name":  self.feature_name,
            "feature_type":  self.feature_type.value,
            "winner_mean":   self.winner_mean,
            "winner_std":    self.winner_std,
            "loser_mean":    self.loser_mean,
            "loser_std":     self.loser_std,
            "effect_size":   self.effect_size,
            "effect_abs":    self.effect_abs,
            "direction":     self.direction.value,
            "ci_low":        self.ci_low,
            "ci_high":       self.ci_high,
            "spearman_corr": self.spearman_corr,
            "n_winners":     self.n_winners,
            "n_losers":      self.n_losers,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> FeatureEvidence:
        return cls(
            feature_name=d["feature_name"],
            feature_type=FeatureType(d["feature_type"]),
            winner_mean=float(d["winner_mean"]),
            winner_std=float(d["winner_std"]),
            loser_mean=float(d["loser_mean"]),
            loser_std=float(d["loser_std"]),
            effect_size=float(d["effect_size"]),
            effect_abs=float(d["effect_abs"]),
            direction=SeparationDirection(d["direction"]),
            ci_low=float(d["ci_low"]),
            ci_high=float(d["ci_high"]),
            spearman_corr=float(d["spearman_corr"]),
            n_winners=int(d["n_winners"]),
            n_losers=int(d["n_losers"]),
        )


# ─── dna characteristic ───────────────────────────────────────────────────────

@dataclass
class DNACharacteristic:
    """
    A single pre-move feature characteristic that reliably separates winners
    from losers before price movement.

    A characteristic is backed by FeatureEvidence and carries a lifecycle
    that tracks how many days it has been observed.
    """

    char_id:         str              # DNA-{sha256[:8]}
    feature_name:    str
    feature_type:    FeatureType
    direction:       SeparationDirection
    effect_size:     float            # signed Cohen's d
    effect_abs:      float            # |Cohen's d|
    confidence:      float            # weighted [0, 1] confidence score
    lifecycle:       DNALifecycle
    trading_date:    str              # ISO date this was discovered
    regime:          str              # market regime at discovery
    evidence:        FeatureEvidence
    first_seen:      str              # ISO date of earliest known occurrence
    last_seen:       str              # ISO date of most recent occurrence
    occurrence_count: int             # total times this characteristic was found

    def to_dict(self) -> Dict[str, Any]:
        return {
            "char_id":         self.char_id,
            "feature_name":    self.feature_name,
            "feature_type":    self.feature_type.value,
            "direction":       self.direction.value,
            "effect_size":     self.effect_size,
            "effect_abs":      self.effect_abs,
            "confidence":      self.confidence,
            "lifecycle":       self.lifecycle.value,
            "trading_date":    self.trading_date,
            "regime":          self.regime,
            "evidence":        self.evidence.to_dict(),
            "first_seen":      self.first_seen,
            "last_seen":       self.last_seen,
            "occurrence_count": self.occurrence_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DNACharacteristic:
        return cls(
            char_id=d["char_id"],
            feature_name=d["feature_name"],
            feature_type=FeatureType(d["feature_type"]),
            direction=SeparationDirection(d["direction"]),
            effect_size=float(d["effect_size"]),
            effect_abs=float(d["effect_abs"]),
            confidence=float(d["confidence"]),
            lifecycle=DNALifecycle(d["lifecycle"]),
            trading_date=d["trading_date"],
            regime=d["regime"],
            evidence=FeatureEvidence.from_dict(d["evidence"]),
            first_seen=d["first_seen"],
            last_seen=d["last_seen"],
            occurrence_count=int(d["occurrence_count"]),
        )


# ─── dna interaction ──────────────────────────────────────────────────────────

@dataclass
class DNAInteraction:
    """
    A pair of features whose joint signal separates winners from losers
    more than either feature alone.

    amplification = joint_effect / max_individual - 1.0
    """

    interaction_id: str          # INT-{sha256[:8]}
    features:       List[str]    # exactly 2 feature names
    joint_effect:   float        # |Cohen's d| of combined normalised signal
    max_individual: float        # max |Cohen's d| of individual features
    amplification:  float        # joint_effect / max_individual - 1.0
    trading_date:   str
    regime:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "features":       self.features,
            "joint_effect":   self.joint_effect,
            "max_individual": self.max_individual,
            "amplification":  self.amplification,
            "trading_date":   self.trading_date,
            "regime":         self.regime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DNAInteraction:
        return cls(
            interaction_id=d["interaction_id"],
            features=list(d["features"]),
            joint_effect=float(d["joint_effect"]),
            max_individual=float(d["max_individual"]),
            amplification=float(d["amplification"]),
            trading_date=d["trading_date"],
            regime=d["regime"],
        )


# ─── dna profiles ─────────────────────────────────────────────────────────────

@dataclass
class WinnerDNA:
    """
    DNA profile for the winner population:
    features where winners reliably exceed losers.
    """
    date:            str
    characteristics: List[DNACharacteristic]
    interactions:    List[DNAInteraction]
    population_ids:  List[str]       # contributing performance populations
    n_members:       int
    regime:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date":            self.date,
            "characteristics": [c.to_dict() for c in self.characteristics],
            "interactions":    [i.to_dict() for i in self.interactions],
            "population_ids":  self.population_ids,
            "n_members":       self.n_members,
            "regime":          self.regime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> WinnerDNA:
        return cls(
            date=d["date"],
            characteristics=[DNACharacteristic.from_dict(c) for c in d["characteristics"]],
            interactions=[DNAInteraction.from_dict(i) for i in d["interactions"]],
            population_ids=list(d["population_ids"]),
            n_members=int(d["n_members"]),
            regime=d["regime"],
        )


@dataclass
class LoserDNA:
    """
    DNA profile for the loser population:
    features where losers reliably exceed winners.
    """
    date:            str
    characteristics: List[DNACharacteristic]
    interactions:    List[DNAInteraction]
    population_ids:  List[str]
    n_members:       int
    regime:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date":            self.date,
            "characteristics": [c.to_dict() for c in self.characteristics],
            "interactions":    [i.to_dict() for i in self.interactions],
            "population_ids":  self.population_ids,
            "n_members":       self.n_members,
            "regime":          self.regime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LoserDNA:
        return cls(
            date=d["date"],
            characteristics=[DNACharacteristic.from_dict(c) for c in d["characteristics"]],
            interactions=[DNAInteraction.from_dict(i) for i in d["interactions"]],
            population_ids=list(d["population_ids"]),
            n_members=int(d["n_members"]),
            regime=d["regime"],
        )


@dataclass
class NeutralDNA:
    """
    DNA profile for the neutral population:
    features that distinguish neutral stocks from the extreme groups.
    """
    date:            str
    characteristics: List[DNACharacteristic]
    interactions:    List[DNAInteraction]
    population_ids:  List[str]
    n_members:       int
    regime:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date":            self.date,
            "characteristics": [c.to_dict() for c in self.characteristics],
            "interactions":    [i.to_dict() for i in self.interactions],
            "population_ids":  self.population_ids,
            "n_members":       self.n_members,
            "regime":          self.regime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NeutralDNA:
        return cls(
            date=d["date"],
            characteristics=[DNACharacteristic.from_dict(c) for c in d["characteristics"]],
            interactions=[DNAInteraction.from_dict(i) for i in d["interactions"]],
            population_ids=list(d["population_ids"]),
            n_members=int(d["n_members"]),
            regime=d["regime"],
        )


# ─── discovery report ─────────────────────────────────────────────────────────

@dataclass
class DiscoveryReport:
    """
    Complete DNA discovery output for one trading day.

    Contains winner, loser, and neutral DNA profiles plus the full
    list of all characteristics and interactions for cross-dimension queries.
    """

    report_id:          str                   # MLS-DNA-YYYYMMDD
    trading_date:       str
    snapshot_id:        str                   # links to MarketObserver snapshot
    classification_id:  str                   # links to ClassificationResult
    winner_dna:         WinnerDNA
    loser_dna:          LoserDNA
    neutral_dna:        NeutralDNA
    all_characteristics: List[DNACharacteristic]
    all_interactions:   List[DNAInteraction]
    regime:             str
    universe_size:      int
    created_at:         str

    def get_characteristic(self, feature_name: str) -> Optional[DNACharacteristic]:
        """Return the first characteristic for *feature_name*, or None."""
        for c in self.all_characteristics:
            if c.feature_name == feature_name:
                return c
        return None

    def characteristics_by_direction(
        self, direction: SeparationDirection
    ) -> List[DNACharacteristic]:
        """Return characteristics matching *direction*, sorted by effect_abs descending."""
        chars = [c for c in self.all_characteristics if c.direction == direction]
        return sorted(chars, key=lambda c: c.effect_abs, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "trading_date":       self.trading_date,
            "snapshot_id":        self.snapshot_id,
            "classification_id":  self.classification_id,
            "winner_dna":         self.winner_dna.to_dict(),
            "loser_dna":          self.loser_dna.to_dict(),
            "neutral_dna":        self.neutral_dna.to_dict(),
            "all_characteristics": [c.to_dict() for c in self.all_characteristics],
            "all_interactions":   [i.to_dict() for i in self.all_interactions],
            "regime":             self.regime,
            "universe_size":      self.universe_size,
            "created_at":         self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DiscoveryReport:
        return cls(
            report_id=d["report_id"],
            trading_date=d["trading_date"],
            snapshot_id=d["snapshot_id"],
            classification_id=d["classification_id"],
            winner_dna=WinnerDNA.from_dict(d["winner_dna"]),
            loser_dna=LoserDNA.from_dict(d["loser_dna"]),
            neutral_dna=NeutralDNA.from_dict(d["neutral_dna"]),
            all_characteristics=[DNACharacteristic.from_dict(c) for c in d["all_characteristics"]],
            all_interactions=[DNAInteraction.from_dict(i) for i in d["all_interactions"]],
            regime=d["regime"],
            universe_size=int(d["universe_size"]),
            created_at=d["created_at"],
        )


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class DNAStatistics:
    """Aggregate statistics for a single discovery report."""

    trading_date:             str
    total_characteristics:    int
    winner_characteristics:   int
    loser_characteristics:    int
    neutral_characteristics:  int
    total_interactions:       int
    top_winner_feature:       Optional[str]
    top_loser_feature:        Optional[str]
    avg_effect_size:          float
    lifecycle_distribution:   Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading_date":            self.trading_date,
            "total_characteristics":   self.total_characteristics,
            "winner_characteristics":  self.winner_characteristics,
            "loser_characteristics":   self.loser_characteristics,
            "neutral_characteristics": self.neutral_characteristics,
            "total_interactions":      self.total_interactions,
            "top_winner_feature":      self.top_winner_feature,
            "top_loser_feature":       self.top_loser_feature,
            "avg_effect_size":         self.avg_effect_size,
            "lifecycle_distribution":  self.lifecycle_distribution,
        }
