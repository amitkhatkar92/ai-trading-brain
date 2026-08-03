"""
population_classifier_models.py — Typed models for the MLS PopulationClassifier.

MLS Phase 2.

Pure data.  No business logic.  All fields JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class ClassifierType(str, Enum):
    """Eight independent classification dimensions."""
    PERFORMANCE       = "PERFORMANCE"
    SECTOR            = "SECTOR"
    REGIME            = "REGIME"
    LIQUIDITY         = "LIQUIDITY"
    VOLATILITY        = "VOLATILITY"
    MARKET_CAP        = "MARKET_CAP"
    VOLUME_EXPANSION  = "VOLUME_EXPANSION"
    RELATIVE_STRENGTH = "RELATIVE_STRENGTH"


class GroupLabel(str, Enum):
    """All possible population group labels across all classifier types."""

    # Performance — exclusive, exhaustive
    TOP_1PCT     = "TOP_1PCT"
    TOP_5PCT     = "TOP_5PCT"
    TOP_10PCT    = "TOP_10PCT"
    NEUTRAL      = "NEUTRAL"
    BOTTOM_10PCT = "BOTTOM_10PCT"
    BOTTOM_5PCT  = "BOTTOM_5PCT"
    BOTTOM_1PCT  = "BOTTOM_1PCT"

    # Sector relative
    SECTOR_WINNER  = "SECTOR_WINNER"
    SECTOR_LOSER   = "SECTOR_LOSER"
    SECTOR_NEUTRAL = "SECTOR_NEUTRAL"

    # Regime alignment
    REGIME_ALIGNED   = "REGIME_ALIGNED"
    REGIME_DIVERGENT = "REGIME_DIVERGENT"

    # Liquidity
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"
    MID_LIQUIDITY  = "MID_LIQUIDITY"
    LOW_LIQUIDITY  = "LOW_LIQUIDITY"

    # Volatility
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    MID_VOLATILITY  = "MID_VOLATILITY"
    LOW_VOLATILITY  = "LOW_VOLATILITY"

    # Market cap (liquidity proxy)
    LARGE_CAP = "LARGE_CAP"
    MID_CAP   = "MID_CAP"
    SMALL_CAP = "SMALL_CAP"

    # Volume expansion
    VOLUME_EXPANDING   = "VOLUME_EXPANDING"
    VOLUME_NORMAL      = "VOLUME_NORMAL"
    VOLUME_CONTRACTING = "VOLUME_CONTRACTING"

    # Relative strength
    RS_STRONG  = "RS_STRONG"
    RS_NEUTRAL = "RS_NEUTRAL"
    RS_WEAK    = "RS_WEAK"


# ─── exceptions ───────────────────────────────────────────────────────────────

class PopulationClassifierError(Exception):
    """General PopulationClassifier error."""


class ClassificationNotFoundError(PopulationClassifierError):
    """Classification result for the requested trading date does not exist."""


class OrphanStockError(PopulationClassifierError):
    """One or more stocks were not assigned to any population."""


# ─── population ───────────────────────────────────────────────────────────────

@dataclass
class Population:
    """A named group of stocks sharing a classification characteristic."""

    population_id:   str                # POP-YYYYMMDD-CLASSIFIER-LABEL
    trading_date:    str                # ISO date
    classifier_type: ClassifierType
    label:           GroupLabel
    member_count:    int                # len(members)
    members:         List[str]          # symbol list
    threshold_value: Optional[float]    # boundary value used, or None
    created_at:      str                # ISO datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "population_id":   self.population_id,
            "trading_date":    self.trading_date,
            "classifier_type": self.classifier_type.value,
            "label":           self.label.value,
            "member_count":    self.member_count,
            "members":         self.members,
            "threshold_value": self.threshold_value,
            "created_at":      self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Population:
        return cls(
            population_id=d["population_id"],
            trading_date=d["trading_date"],
            classifier_type=ClassifierType(d["classifier_type"]),
            label=GroupLabel(d["label"]),
            member_count=int(d["member_count"]),
            members=list(d["members"]),
            threshold_value=d.get("threshold_value"),
            created_at=d["created_at"],
        )


# ─── member ───────────────────────────────────────────────────────────────────

@dataclass
class PopulationMember:
    """
    A stock with all its population assignments across all classifier dimensions.

    One stock belongs to exactly ONE group per classifier type (8 classifiers =
    8 labels minimum), making multi-label membership across different dimensions
    automatic.
    """

    symbol:                str                 # NSE ticker
    trading_date:          str                 # ISO date
    population_ids:        List[str]           # all population_ids assigned
    labels:                List[str]           # GroupLabel values (display convenience)
    realized_return:       Optional[float]     # return used for performance classification
    classification_values: Dict[str, float]    # key features used for each dimension

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":                self.symbol,
            "trading_date":          self.trading_date,
            "population_ids":        self.population_ids,
            "labels":                self.labels,
            "realized_return":       self.realized_return,
            "classification_values": self.classification_values,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PopulationMember:
        return cls(
            symbol=d["symbol"],
            trading_date=d["trading_date"],
            population_ids=list(d["population_ids"]),
            labels=list(d["labels"]),
            realized_return=d.get("realized_return"),
            classification_values=d.get("classification_values", {}),
        )


# ─── result ───────────────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    """
    Complete classification of a daily market universe.

    Contains all populations (27 for 8 classifiers) and all members
    (one per symbol).  Every symbol is assigned to exactly one group
    per classifier type — no orphan stocks.
    """

    result_id:       str                    # MLS-CLS-YYYYMMDD
    trading_date:    str
    snapshot_id:     str                    # links back to MarketObserver snapshot
    universe_size:   int
    populations:     List[Population]
    members:         List[PopulationMember]
    outcomes_source: str                    # "external" | "feature_proxy"
    created_at:      str                    # ISO datetime

    # ── convenience queries ──────────────────────────────────────────────

    def get_population(self, label: GroupLabel) -> Optional[Population]:
        """Return the first population matching *label* across any classifier."""
        for p in self.populations:
            if p.label == label:
                return p
        return None

    def get_population_by_type(
        self, classifier_type: ClassifierType, label: GroupLabel
    ) -> Optional[Population]:
        """Return the population for a specific (classifier_type, label) pair."""
        for p in self.populations:
            if p.classifier_type == classifier_type and p.label == label:
                return p
        return None

    def get_member(self, symbol: str) -> Optional[PopulationMember]:
        """Return the member record for *symbol*, or None."""
        for m in self.members:
            if m.symbol == symbol:
                return m
        return None

    def populations_for(self, symbol: str) -> List[Population]:
        """Return all populations that *symbol* belongs to."""
        member = self.get_member(symbol)
        if member is None:
            return []
        pop_id_set = set(member.population_ids)
        return [p for p in self.populations if p.population_id in pop_id_set]

    # ── serialisation ────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "trading_date":    self.trading_date,
            "snapshot_id":     self.snapshot_id,
            "universe_size":   self.universe_size,
            "populations":     [p.to_dict() for p in self.populations],
            "members":         [m.to_dict() for m in self.members],
            "outcomes_source": self.outcomes_source,
            "created_at":      self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ClassificationResult:
        return cls(
            result_id=d["result_id"],
            trading_date=d["trading_date"],
            snapshot_id=d["snapshot_id"],
            universe_size=int(d["universe_size"]),
            populations=[Population.from_dict(p) for p in d["populations"]],
            members=[PopulationMember.from_dict(m) for m in d["members"]],
            outcomes_source=d["outcomes_source"],
            created_at=d["created_at"],
        )


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class PopulationStatistics:
    """Aggregate statistics for one classification result."""

    trading_date:            str
    universe_size:           int
    population_count:        int
    classifier_types_used:   List[str]
    avg_labels_per_symbol:   float
    max_labels_per_symbol:   int
    min_labels_per_symbol:   int
    performance_group_sizes: Dict[str, int]    # GroupLabel.value -> count
    outcomes_source:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading_date":            self.trading_date,
            "universe_size":           self.universe_size,
            "population_count":        self.population_count,
            "classifier_types_used":   self.classifier_types_used,
            "avg_labels_per_symbol":   self.avg_labels_per_symbol,
            "max_labels_per_symbol":   self.max_labels_per_symbol,
            "min_labels_per_symbol":   self.min_labels_per_symbol,
            "performance_group_sizes": self.performance_group_sizes,
            "outcomes_source":         self.outcomes_source,
        }
