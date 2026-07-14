"""iios/investment/portfolio/construction/portfolio_blueprint.py

Core data models for the Portfolio Construction Engine.

InvestmentRecommendation  — input from validated decision pipelines.
PortfolioSlot             — a single position in the blueprint.
PortfolioBlueprint        — the fully-constructed, immutable blueprint.
ConstructionRequest       — parameters driving a construction run.
ConstructionResult        — full output of a construction run.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    BLUEPRINT_SCHEMA_VERSION,
    ConstructionDirection,
    ConstructionStatus,
    ConstructionType,
    MarketCapCategory,
    RESULT_SCHEMA_VERSION,
    SelectionCriterion,
    WeightingMethod,
)


# ---------------------------------------------------------------------------
# InvestmentRecommendation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InvestmentRecommendation:
    """
    A validated investment recommendation consumed by the construction engine.

    This is the boundary object between Decision / Market Intelligence pipelines
    and the Construction Engine.  It carries enough information to:
      • determine eligibility (asset class, sector, market cap)
      • rank candidates (conviction, confidence, risk_score)
      • assign deterministic weights
      • trace back to the originating decision (source_decision_id)

    The engine NEVER looks beyond this object to re-analyse markets or
    companies independently.
    """

    rec_id:              str                 = field(default_factory=lambda: str(uuid.uuid4()))
    symbol:              str                 = ""
    name:                str                 = ""
    direction:           ConstructionDirection = ConstructionDirection.LONG

    # Quality dimensions [0, 1] — higher is better for conviction / confidence;
    # lower is better for risk_score.
    conviction:          float               = 0.5   # Strength of the recommendation
    confidence:          float               = 0.5   # Decision engine confidence
    risk_score:          float               = 0.5   # 0 = no risk, 1 = extreme risk

    # Classification
    sector:              str                 = "unknown"
    industry:            str                 = "unknown"
    asset_class:         AssetClass          = AssetClass.EQUITY
    market_cap_category: MarketCapCategory   = MarketCapCategory.UNKNOWN

    # Traceability
    source_decision_id:  str                 = ""
    rationale:           str                 = ""
    analyst:             str                 = ""

    # Optional manual weight (used only with WeightingMethod.MANUAL)
    manual_weight:       float               = 0.0

    # Timestamps
    created_at:          float               = field(default_factory=time.time)
    valid_until:         float               = 0.0   # 0 = no expiry

    # Extra metadata (free-form, must be serialisable)
    attributes:          Dict[str, Any]      = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_long(self) -> bool:
        return self.direction == ConstructionDirection.LONG

    @property
    def is_short(self) -> bool:
        return self.direction == ConstructionDirection.SHORT

    @property
    def is_expired(self) -> bool:
        """True if valid_until is set and has passed."""
        return self.valid_until > 0 and time.time() > self.valid_until

    @property
    def quality_score(self) -> float:
        """confidence × (1 − risk_score).  Used in RISK_ADJUSTED weighting."""
        return self.confidence * (1.0 - self.risk_score)

    @property
    def composite_score(self) -> float:
        """40% conviction + 40% confidence + 20% quality.  Deterministic composite."""
        return (
            0.40 * self.conviction
            + 0.40 * self.confidence
            + 0.20 * self.quality_score
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_id":              self.rec_id,
            "symbol":              self.symbol,
            "name":                self.name,
            "direction":           self.direction.value,
            "conviction":          round(self.conviction, 4),
            "confidence":          round(self.confidence, 4),
            "risk_score":          round(self.risk_score, 4),
            "quality_score":       round(self.quality_score, 4),
            "composite_score":     round(self.composite_score, 4),
            "sector":              self.sector,
            "industry":            self.industry,
            "asset_class":         self.asset_class.value,
            "market_cap_category": self.market_cap_category.value,
            "source_decision_id":  self.source_decision_id,
            "rationale":           self.rationale,
            "analyst":             self.analyst,
            "manual_weight":       self.manual_weight,
            "created_at":          self.created_at,
            "valid_until":         self.valid_until,
            "attributes":          dict(self.attributes),
        }


# ---------------------------------------------------------------------------
# PortfolioSlot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioSlot:
    """
    A single position in a PortfolioBlueprint.

    target_weight is expressed as a fraction of total portfolio value.
    Long positions have positive weights; short positions have negative weights.
    """

    slot_id:             str                 = field(default_factory=lambda: str(uuid.uuid4()))
    symbol:              str                 = ""
    name:                str                 = ""
    direction:           ConstructionDirection = ConstructionDirection.LONG

    # Weight bounds [0, 1] — enforced by the ConstraintEngine before finalisation
    target_weight:       float               = 0.0   # Final assigned weight
    min_weight:          float               = 0.0   # Hard lower bound
    max_weight:          float               = 1.0   # Hard upper bound

    # Classification (copied from the source recommendation)
    sector:              str                 = "unknown"
    industry:            str                 = "unknown"
    asset_class:         AssetClass          = AssetClass.EQUITY
    market_cap_category: MarketCapCategory   = MarketCapCategory.UNKNOWN

    # Traceability
    recommendation_id:   str                 = ""
    source_decision_id:  str                 = ""
    rationale:           str                 = ""

    # Quality dimensions at selection time
    conviction:          float               = 0.5
    confidence:          float               = 0.5
    risk_score:          float               = 0.5

    # Rank assigned by the SecuritySelector (1 = best)
    rank:                int                 = 0

    added_at:            float               = field(default_factory=time.time)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_long(self) -> bool:
        return self.direction == ConstructionDirection.LONG

    @property
    def is_short(self) -> bool:
        return self.direction == ConstructionDirection.SHORT

    @property
    def abs_weight(self) -> float:
        return abs(self.target_weight)

    @property
    def weight_within_bounds(self) -> bool:
        aw = self.abs_weight
        return self.min_weight <= aw <= self.max_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id":             self.slot_id,
            "symbol":              self.symbol,
            "name":                self.name,
            "direction":           self.direction.value,
            "target_weight":       round(self.target_weight, 6),
            "min_weight":          round(self.min_weight, 6),
            "max_weight":          round(self.max_weight, 6),
            "sector":              self.sector,
            "industry":            self.industry,
            "asset_class":         self.asset_class.value,
            "market_cap_category": self.market_cap_category.value,
            "recommendation_id":   self.recommendation_id,
            "source_decision_id":  self.source_decision_id,
            "rationale":           self.rationale,
            "conviction":          round(self.conviction, 4),
            "confidence":          round(self.confidence, 4),
            "risk_score":          round(self.risk_score, 4),
            "rank":                self.rank,
            "added_at":            self.added_at,
        }


# ---------------------------------------------------------------------------
# PortfolioBlueprint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioBlueprint:
    """
    The immutable, version-stamped plan for constructing a portfolio.

    A blueprint is produced by ConstructionEngine and consumed by:
      • ConstraintEngine  (validates constraint compliance)
      • PortfolioValidator (validates completeness and integrity)
      • Downstream execution layer (fills actual orders)

    Every blueprint is deterministic: given the same inputs and the same
    ConstructionRequest, the same blueprint must always be produced.
    """

    blueprint_id:        str                 = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str                 = ""
    version:             int                 = 1
    schema_version:      str                 = BLUEPRINT_SCHEMA_VERSION
    construction_type:   ConstructionType    = ConstructionType.LONG_ONLY
    weighting_method:    WeightingMethod     = WeightingMethod.EQUAL
    objective:           str                 = ""

    # All position slots — stored as a tuple for immutability
    slots:               Tuple[PortfolioSlot, ...] = field(default_factory=tuple)

    # Weight summary (cash = 1 - sum(long_weights) + sum(abs(short_weights)))
    cash_weight:         float               = 0.0
    long_count:          int                 = 0
    short_count:         int                 = 0
    long_weight_sum:     float               = 0.0
    short_weight_sum:    float               = 0.0   # Absolute sum of short weights
    net_exposure:        float               = 0.0   # long_weight_sum - short_weight_sum
    gross_exposure:      float               = 0.0   # long_weight_sum + short_weight_sum

    # Composition breakdowns
    sector_weights:      Dict[str, float]    = field(default_factory=dict)
    industry_weights:    Dict[str, float]    = field(default_factory=dict)
    asset_class_weights: Dict[str, float]    = field(default_factory=dict)
    market_cap_weights:  Dict[str, float]    = field(default_factory=dict)

    # Traceability
    recommendation_ids:  Tuple[str, ...]     = field(default_factory=tuple)
    source_decision_ids: Tuple[str, ...]     = field(default_factory=tuple)
    request_id:          str                 = ""

    # Provenance
    created_at:          float               = field(default_factory=time.time)
    created_by:          str                 = "ConstructionEngine"
    construction_version: str               = "1.0.0"

    # Free-form metadata
    metadata:            Dict[str, Any]      = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def total_slots(self) -> int:
        return len(self.slots)

    @property
    def is_empty(self) -> bool:
        return len(self.slots) == 0

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(s.symbol for s in self.slots)

    @property
    def long_slots(self) -> Tuple[PortfolioSlot, ...]:
        return tuple(s for s in self.slots if s.is_long)

    @property
    def short_slots(self) -> Tuple[PortfolioSlot, ...]:
        return tuple(s for s in self.slots if s.is_short)

    def get_slot(self, symbol: str) -> Optional[PortfolioSlot]:
        for s in self.slots:
            if s.symbol == symbol:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id":        self.blueprint_id,
            "portfolio_id":        self.portfolio_id,
            "version":             self.version,
            "schema_version":      self.schema_version,
            "construction_type":   self.construction_type.value,
            "weighting_method":    self.weighting_method.value,
            "objective":           self.objective,
            "slots":               [s.to_dict() for s in self.slots],
            "cash_weight":         round(self.cash_weight, 6),
            "long_count":          self.long_count,
            "short_count":         self.short_count,
            "long_weight_sum":     round(self.long_weight_sum, 6),
            "short_weight_sum":    round(self.short_weight_sum, 6),
            "net_exposure":        round(self.net_exposure, 6),
            "gross_exposure":      round(self.gross_exposure, 6),
            "sector_weights":      {k: round(v, 6) for k, v in self.sector_weights.items()},
            "industry_weights":    {k: round(v, 6) for k, v in self.industry_weights.items()},
            "asset_class_weights": {k: round(v, 6) for k, v in self.asset_class_weights.items()},
            "market_cap_weights":  {k: round(v, 6) for k, v in self.market_cap_weights.items()},
            "recommendation_ids":  list(self.recommendation_ids),
            "source_decision_ids": list(self.source_decision_ids),
            "request_id":          self.request_id,
            "created_at":          self.created_at,
            "created_by":          self.created_by,
            "construction_version":self.construction_version,
            "metadata":            dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ConstructionRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstructionRequest:
    """
    All parameters controlling a single portfolio construction run.

    Passed to PortfolioConstructionEngine.construct().
    """

    request_id:             str                          = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str                          = ""
    construction_type:      ConstructionType             = ConstructionType.LONG_ONLY
    weighting_method:       WeightingMethod              = WeightingMethod.EQUAL
    selection_criterion:    SelectionCriterion           = SelectionCriterion.COMPOSITE

    # Holdings limits
    max_holdings:           int                          = 30
    min_holdings:           int                          = 5
    target_cash_pct:        float                        = 0.05   # 5% cash reserve

    # Long / short parameters
    allow_short:            bool                         = False
    short_exposure_pct:     float                        = 0.0    # as fraction of portfolio

    # Selection quality thresholds
    min_conviction:         float                        = 0.3
    min_confidence:         float                        = 0.3
    max_risk_score:         float                        = 0.8

    # Universe filters (empty frozenset = allow all)
    sectors_allowed:        FrozenSet[str]               = field(default_factory=frozenset)
    sectors_excluded:       FrozenSet[str]               = field(default_factory=frozenset)
    asset_classes_allowed:  FrozenSet[AssetClass]        = field(default_factory=frozenset)
    market_caps_allowed:    FrozenSet[MarketCapCategory] = field(default_factory=frozenset)

    # Single-security weight bounds (fractions)
    max_single_weight:      float                        = 0.10   # 10% max per holding
    min_single_weight:      float                        = 0.005  # 0.5% min per holding

    # Concentration limits
    max_sector_weight:      float                        = 0.30   # 30% per sector
    max_asset_class_weight: float                        = 0.70   # 70% per asset class

    # Objective description (free text, stored in blueprint)
    objective:              str                          = ""

    # Provenance
    requested_by:           str                          = "system"
    requested_at:           float                        = field(default_factory=time.time)

    # Free-form extras
    metadata:               Dict[str, Any]               = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":             self.request_id,
            "portfolio_id":           self.portfolio_id,
            "construction_type":      self.construction_type.value,
            "weighting_method":       self.weighting_method.value,
            "selection_criterion":    self.selection_criterion.value,
            "max_holdings":           self.max_holdings,
            "min_holdings":           self.min_holdings,
            "target_cash_pct":        self.target_cash_pct,
            "allow_short":            self.allow_short,
            "short_exposure_pct":     self.short_exposure_pct,
            "min_conviction":         self.min_conviction,
            "min_confidence":         self.min_confidence,
            "max_risk_score":         self.max_risk_score,
            "sectors_allowed":        sorted(self.sectors_allowed),
            "sectors_excluded":       sorted(self.sectors_excluded),
            "asset_classes_allowed":  sorted(v.value for v in self.asset_classes_allowed),
            "market_caps_allowed":    sorted(v.value for v in self.market_caps_allowed),
            "max_single_weight":      self.max_single_weight,
            "min_single_weight":      self.min_single_weight,
            "max_sector_weight":      self.max_sector_weight,
            "max_asset_class_weight": self.max_asset_class_weight,
            "objective":              self.objective,
            "requested_by":           self.requested_by,
            "requested_at":           self.requested_at,
            "metadata":               dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ConstructionResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstructionResult:
    """
    Full output of a PortfolioConstructionEngine.construct() call.

    Carries the blueprint (if successful), validation findings, quality
    scores, warnings, errors, and full provenance.
    """

    result_id:             str                      = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:            str                      = ""
    portfolio_id:          str                      = ""
    status:                ConstructionStatus       = ConstructionStatus.PENDING
    schema_version:        str                      = RESULT_SCHEMA_VERSION

    # Blueprint is present on success, None on failure
    blueprint:             Optional[PortfolioBlueprint] = None

    # Counts from the run
    recommendations_in:    int                      = 0
    recommendations_selected: int                   = 0

    # Serialisable summaries of validation and quality (populated post-build)
    validation_summary:    Dict[str, Any]           = field(default_factory=dict)
    constraint_summary:    Dict[str, Any]           = field(default_factory=dict)
    quality_summary:       Dict[str, Any]           = field(default_factory=dict)

    # Non-blocking warnings and blocking errors
    warnings:              Tuple[str, ...]           = field(default_factory=tuple)
    errors:                Tuple[str, ...]           = field(default_factory=tuple)

    # Performance
    duration_ms:           float                    = 0.0
    created_at:            float                    = field(default_factory=time.time)
    construction_version:  str                      = "1.0.0"

    # Provenance
    metadata:              Dict[str, Any]           = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def succeeded(self) -> bool:
        return self.status == ConstructionStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == ConstructionStatus.FAILED

    @property
    def has_blueprint(self) -> bool:
        return self.blueprint is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":                self.result_id,
            "request_id":               self.request_id,
            "portfolio_id":             self.portfolio_id,
            "status":                   self.status.value,
            "schema_version":           self.schema_version,
            "blueprint":                self.blueprint.to_dict() if self.blueprint else None,
            "recommendations_in":       self.recommendations_in,
            "recommendations_selected": self.recommendations_selected,
            "validation_summary":       dict(self.validation_summary),
            "constraint_summary":       dict(self.constraint_summary),
            "quality_summary":          dict(self.quality_summary),
            "warnings":                 list(self.warnings),
            "errors":                   list(self.errors),
            "duration_ms":              round(self.duration_ms, 2),
            "created_at":               self.created_at,
            "construction_version":     self.construction_version,
            "metadata":                 dict(self.metadata),
        }
