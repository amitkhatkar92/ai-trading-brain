"""iios/investment/portfolio/construction/construction_engine.py

Core construction engine: weight assignment, rule application, and
blueprint assembly.  This is the deterministic heart of the construction
pipeline — it never optimises, never executes, never analyses markets.

Pipeline:
  1. SecuritySelector  → ranked, eligible recommendations
  2. WeightAssigner    → raw weights from a WeightingMethod
  3. RuleChain         → deterministic adjustments (cap, min-size, neutral)
  4. BlueprintAssembler → immutable PortfolioBlueprint
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_rules import (
    CashReserveRule,
    MarketNeutralRule,
    MaxWeightCapRule,
    MinWeightFloorRule,
    ConstructionRule,
    WeightMap,
)
from iios.investment.portfolio.construction.construction_types import (
    BLUEPRINT_SCHEMA_VERSION,
    MIN_SLOT_WEIGHT,
    WEIGHT_CAP_MAX_ITER,
    WEIGHT_SUM_TOLERANCE,
    AssetClass,
    ConstructionDirection,
    ConstructionType,
    MarketCapCategory,
    WeightingMethod,
)
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    PortfolioBlueprint,
    PortfolioSlot,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WeightAssigner
# ---------------------------------------------------------------------------

class WeightAssigner:
    """
    Assigns raw (pre-rule) weights to an ordered list of recommendations
    using a deterministic WeightingMethod.

    Returns a WeightMap: symbol → signed weight (negative for shorts).
    Long pool and short pool are weighted independently then scaled to
    (1 - cash_reserve) and short_exposure respectively.
    """

    def assign(
        self,
        recommendations: List[Any],
        request: ConstructionRequest,
    ) -> WeightMap:
        """Produce a signed WeightMap from ranked recommendations."""
        longs  = [r for r in recommendations if r.direction == ConstructionDirection.LONG]
        shorts = [r for r in recommendations if r.direction == ConstructionDirection.SHORT]

        investable = 1.0 - request.target_cash_pct
        weights: WeightMap = {}

        if longs:
            long_raw = self._raw_weights(longs, request.weighting_method)
            total    = sum(long_raw.values()) or 1.0
            for sym, w in long_raw.items():
                weights[sym] = (w / total) * investable

        if shorts and request.allow_short:
            short_raw = self._raw_weights(shorts, request.weighting_method)
            total     = sum(short_raw.values()) or 1.0
            for sym, w in short_raw.items():
                weights[sym] = -((w / total) * request.short_exposure_pct)

        return weights

    # ------------------------------------------------------------------

    def _raw_weights(
        self,
        recs: List[Any],
        method: WeightingMethod,
    ) -> Dict[str, float]:
        if not recs:
            return {}

        n = len(recs)

        if method == WeightingMethod.EQUAL:
            return {r.symbol: 1.0 / n for r in recs}

        if method == WeightingMethod.CONVICTION:
            total = sum(r.conviction for r in recs) or 1.0
            return {r.symbol: r.conviction / total for r in recs}

        if method == WeightingMethod.CONFIDENCE:
            total = sum(r.confidence for r in recs) or 1.0
            return {r.symbol: r.confidence / total for r in recs}

        if method == WeightingMethod.RISK_ADJUSTED:
            scores = {r.symbol: r.quality_score for r in recs}
            total  = sum(scores.values()) or 1.0
            return {s: v / total for s, v in scores.items()}

        if method == WeightingMethod.SECTOR_EQUAL:
            return self._sector_equal(recs)

        if method == WeightingMethod.COMPOSITE:
            scores = {r.symbol: r.composite_score for r in recs}
            total  = sum(scores.values()) or 1.0
            return {s: v / total for s, v in scores.items()}

        if method == WeightingMethod.MANUAL:
            total = sum(r.manual_weight for r in recs) or 1.0
            return {r.symbol: r.manual_weight / total for r in recs}

        # Fallback: equal
        return {r.symbol: 1.0 / n for r in recs}

    @staticmethod
    def _sector_equal(recs: List[Any]) -> Dict[str, float]:
        """Equal weight per sector, equal holdings per sector."""
        sectors: Dict[str, List[Any]] = {}
        for r in recs:
            sectors.setdefault(r.sector, []).append(r)
        n_sectors = len(sectors)
        result: Dict[str, float] = {}
        for sec_recs in sectors.values():
            per_holding = 1.0 / (n_sectors * len(sec_recs))
            for r in sec_recs:
                result[r.symbol] = per_holding
        return result


# ---------------------------------------------------------------------------
# RuleChain
# ---------------------------------------------------------------------------

class RuleChain:
    """Ordered sequence of ConstructionRules applied to a WeightMap."""

    def __init__(self, rules: Optional[List[ConstructionRule]] = None) -> None:
        self._rules: List[ConstructionRule] = rules if rules is not None else []

    @classmethod
    def default(cls) -> "RuleChain":
        return cls([
            MaxWeightCapRule(),
            MinWeightFloorRule(),
            CashReserveRule(),
            MarketNeutralRule(),
        ])

    def apply(self, weights: WeightMap, request: ConstructionRequest) -> List[Any]:
        """Apply all rules in order; return list of RuleApplication records."""
        applications = []
        for rule in self._rules:
            app = rule.apply(weights, request)
            if app.symbols_changed:
                applications.append(app)
        return applications


# ---------------------------------------------------------------------------
# BlueprintAssembler
# ---------------------------------------------------------------------------

class BlueprintAssembler:
    """
    Assembles an immutable PortfolioBlueprint from a WeightMap and
    the ranked recommendations that produced it.

    Slots with abs_weight < MIN_SLOT_WEIGHT are dropped silently.
    Weights are rounded to 8 decimal places for determinism.
    """

    def assemble(
        self,
        weights: WeightMap,
        recommendations: List[Any],
        request: ConstructionRequest,
        version: int = 1,
    ) -> PortfolioBlueprint:
        rec_map = {r.symbol: r for r in recommendations}
        slots: List[PortfolioSlot] = []
        rank = 1

        for sym, w in sorted(weights.items(), key=lambda kv: -abs(kv[1])):
            if abs(w) < MIN_SLOT_WEIGHT:
                continue
            rec = rec_map.get(sym)
            if rec is None:
                continue

            slots.append(PortfolioSlot(
                symbol              = sym,
                name                = rec.name,
                direction           = rec.direction,
                target_weight       = round(w, 8),
                min_weight          = request.min_single_weight,
                max_weight          = request.max_single_weight,
                sector              = rec.sector,
                industry            = rec.industry,
                asset_class         = rec.asset_class,
                market_cap_category = rec.market_cap_category,
                recommendation_id   = rec.rec_id,
                source_decision_id  = rec.source_decision_id,
                rationale           = rec.rationale,
                conviction          = rec.conviction,
                confidence          = rec.confidence,
                risk_score          = rec.risk_score,
                rank                = rank,
            ))
            rank += 1

        long_slots  = [s for s in slots if s.is_long]
        short_slots = [s for s in slots if s.is_short]

        long_wsum   = round(sum(s.target_weight for s in long_slots), 8)
        short_wsum  = round(sum(abs(s.target_weight) for s in short_slots), 8)
        cash_weight = round(max(0.0, 1.0 - long_wsum - short_wsum), 8)
        net_exp     = round(long_wsum - short_wsum, 8)
        gross_exp   = round(long_wsum + short_wsum, 8)

        sector_w      = self._group_weights(slots, lambda s: s.sector)
        industry_w    = self._group_weights(slots, lambda s: s.industry)
        asset_class_w = self._group_weights(slots, lambda s: s.asset_class.value)
        market_cap_w  = self._group_weights(slots, lambda s: s.market_cap_category.value)

        return PortfolioBlueprint(
            portfolio_id         = request.portfolio_id,
            version              = version,
            schema_version       = BLUEPRINT_SCHEMA_VERSION,
            construction_type    = request.construction_type,
            weighting_method     = request.weighting_method,
            objective            = request.objective,
            slots                = tuple(slots),
            cash_weight          = cash_weight,
            long_count           = len(long_slots),
            short_count          = len(short_slots),
            long_weight_sum      = long_wsum,
            short_weight_sum     = short_wsum,
            net_exposure         = net_exp,
            gross_exposure       = gross_exp,
            sector_weights       = sector_w,
            industry_weights     = industry_w,
            asset_class_weights  = asset_class_w,
            market_cap_weights   = market_cap_w,
            recommendation_ids   = tuple(s.recommendation_id for s in slots),
            source_decision_ids  = tuple(
                s.source_decision_id for s in slots if s.source_decision_id
            ),
            request_id           = request.request_id,
            created_by           = "ConstructionEngine",
        )

    @staticmethod
    def _group_weights(
        slots: List[PortfolioSlot],
        key_fn: Any,
    ) -> Dict[str, float]:
        groups: Dict[str, float] = {}
        for s in slots:
            k = key_fn(s)
            groups[k] = round(groups.get(k, 0.0) + abs(s.target_weight), 8)
        return groups


# ---------------------------------------------------------------------------
# ConstructionEngine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineRunRecord:
    """Lightweight record of a single ConstructionEngine run."""

    run_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:   str   = ""
    portfolio_id: str   = ""
    succeeded:    bool  = False
    slots_built:  int   = 0
    duration_ms:  float = 0.0
    run_at:       float = field(default_factory=time.time)
    error:        str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":       self.run_id,
            "request_id":   self.request_id,
            "portfolio_id": self.portfolio_id,
            "succeeded":    self.succeeded,
            "slots_built":  self.slots_built,
            "duration_ms":  round(self.duration_ms, 2),
            "run_at":       self.run_at,
            "error":        self.error,
        }


class ConstructionEngine:
    """
    Assembles a PortfolioBlueprint from ranked recommendations.

    Responsibilities:
      • Assign weights via WeightAssigner
      • Apply deterministic rule chain (cap, min-size, cash reserve, neutral)
      • Assemble and return an immutable PortfolioBlueprint

    This class does NOT:
      • Select or filter recommendations (SecuritySelector's job)
      • Validate constraints (ConstraintEngine's job)
      • Optimise weights
      • Execute orders
    """

    def __init__(
        self,
        rule_chain: Optional[RuleChain] = None,
        weight_assigner: Optional[WeightAssigner] = None,
        assembler: Optional[BlueprintAssembler] = None,
    ) -> None:
        self._assigner  = weight_assigner or WeightAssigner()
        self._rules     = rule_chain or RuleChain.default()
        self._assembler = assembler or BlueprintAssembler()
        self._run_history: List[EngineRunRecord] = []
        self._run_count = 0
        self._error_count = 0

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def build_blueprint(
        self,
        recommendations: List[Any],
        request: ConstructionRequest,
        *,
        version: int = 1,
    ) -> PortfolioBlueprint:
        """
        Build a deterministic PortfolioBlueprint from ranked recommendations.

        Args:
            recommendations: Pre-filtered, ranked InvestmentRecommendations.
            request:         ConstructionRequest controlling parameters.
            version:         Blueprint version number (1 for new, n+1 for re-constructions).

        Returns:
            PortfolioBlueprint (immutable).

        Raises:
            ValueError: If recommendations is empty after filtering.
        """
        t0 = time.monotonic()
        try:
            weights = self._assigner.assign(recommendations, request)
            if not weights:
                raise ValueError("Weight assignment produced an empty weight map — no eligible recommendations")

            self._rules.apply(weights, request)
            blueprint = self._assembler.assemble(weights, recommendations, request, version=version)

            duration_ms = (time.monotonic() - t0) * 1000.0
            self._run_count += 1
            self._run_history.append(EngineRunRecord(
                request_id   = request.request_id,
                portfolio_id = request.portfolio_id,
                succeeded    = True,
                slots_built  = blueprint.total_slots,
                duration_ms  = duration_ms,
            ))
            logger.debug(
                "ConstructionEngine built blueprint %s — %d slots in %.1f ms",
                blueprint.blueprint_id, blueprint.total_slots, duration_ms,
            )
            return blueprint

        except Exception as exc:
            self._error_count += 1
            duration_ms = (time.monotonic() - t0) * 1000.0
            self._run_history.append(EngineRunRecord(
                request_id   = request.request_id,
                portfolio_id = request.portfolio_id,
                succeeded    = False,
                duration_ms  = duration_ms,
                error        = str(exc),
            ))
            raise

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def recent_runs(self, n: int = 10) -> List[EngineRunRecord]:
        return list(self._run_history[-n:])
