"""tests/unit/investment/portfolio/construction/test_construction_engine.py

Tests for WeightAssigner, RuleChain, BlueprintAssembler, and ConstructionEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.construction.construction_engine import (
    BlueprintAssembler,
    ConstructionEngine,
    RuleChain,
    WeightAssigner,
)
from iios.investment.portfolio.construction.construction_types import (
    ConstructionDirection,
    ConstructionType,
    WeightingMethod,
)
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    InvestmentRecommendation,
)
from tests.unit.investment.portfolio.construction.conftest import make_recs, _rec


class TestWeightAssigner:
    def _req(self, method: WeightingMethod = WeightingMethod.EQUAL, **kw) -> ConstructionRequest:
        return ConstructionRequest(
            portfolio_id=kw.pop("portfolio_id", "PF"),
            weighting_method=method,
            target_cash_pct=0.05,
            allow_short=kw.pop("allow_short", False),
            short_exposure_pct=kw.pop("short_exposure_pct", 0.0),
            **kw,
        )

    def test_equal_weight_sums_to_invested(self):
        recs = make_recs(5)
        req  = self._req(WeightingMethod.EQUAL)
        wa   = WeightAssigner()
        weights = wa.assign(recs, req)
        total = sum(weights.values())
        # Should sum to (1 - 0.05) = 0.95
        assert abs(total - 0.95) < 1e-6

    def test_conviction_weights_proportional(self):
        r1 = _rec("AAA", conviction=0.6)
        r2 = _rec("BBB", conviction=0.4)
        req = self._req(WeightingMethod.CONVICTION)
        wa  = WeightAssigner()
        weights = wa.assign([r1, r2], req)
        # 0.6 : 0.4 ratio
        ratio = weights["AAA"] / weights["BBB"]
        assert abs(ratio - 1.5) < 1e-4

    def test_confidence_weights(self):
        r1 = _rec("A", confidence=0.8)
        r2 = _rec("B", confidence=0.2)
        req = self._req(WeightingMethod.CONFIDENCE)
        wa  = WeightAssigner()
        w   = wa.assign([r1, r2], req)
        assert w["A"] > w["B"]

    def test_risk_adjusted_weights(self):
        r1 = _rec("SAFE", confidence=0.8, risk_score=0.1)
        r2 = _rec("RISKY", confidence=0.8, risk_score=0.9)
        req = self._req(WeightingMethod.RISK_ADJUSTED)
        wa  = WeightAssigner()
        w   = wa.assign([r1, r2], req)
        assert w["SAFE"] > w["RISKY"]

    def test_composite_weights(self):
        recs = make_recs(4)
        req  = self._req(WeightingMethod.COMPOSITE)
        wa   = WeightAssigner()
        w    = wa.assign(recs, req)
        assert len(w) == 4
        assert abs(sum(w.values()) - 0.95) < 1e-4

    def test_sector_equal_weights(self):
        recs = [
            _rec("A1", sector="tech"),
            _rec("A2", sector="tech"),
            _rec("B1", sector="finance"),
        ]
        req = self._req(WeightingMethod.SECTOR_EQUAL)
        wa  = WeightAssigner()
        w   = wa.assign(recs, req)
        # tech: each gets 0.5 * (1-0.05) / 2; finance: 0.5 * (1-0.05) / 1
        assert abs(w["A1"] - w["A2"]) < 1e-6
        assert w["B1"] > w["A1"]

    def test_no_recs_returns_empty(self):
        req = self._req()
        wa  = WeightAssigner()
        w   = wa.assign([], req)
        assert w == {}


class TestRuleChain:
    def test_default_chain_has_rules(self):
        chain = RuleChain.default()
        assert len(chain._rules) >= 2

    def test_apply_returns_applications(self):
        recs = make_recs(5)
        req  = ConstructionRequest(portfolio_id="PF", max_single_weight=0.10)
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        chain    = RuleChain.default()
        apps     = chain.apply(weights, req)
        # Applications list — may be empty if no weights exceed cap
        assert isinstance(apps, list)

    def test_max_cap_rule_applied(self):
        from iios.investment.portfolio.construction.construction_rules import MaxWeightCapRule
        # Two recs, request caps at 0.40; equal weight of 0.475 each would violate
        recs = [_rec("A"), _rec("B")]
        req  = ConstructionRequest(portfolio_id="PF", max_single_weight=0.40, target_cash_pct=0.05)
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        rule = MaxWeightCapRule()
        rule.apply(weights, req)
        for v in weights.values():
            assert abs(v) <= 0.40 + 1e-6


class TestBlueprintAssembler:
    def test_assemble_basic(self):
        recs = make_recs(5)
        req  = ConstructionRequest(portfolio_id="PF-1")
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        assembler = BlueprintAssembler()
        bp = assembler.assemble(weights, recs, req, version=1)
        assert bp.portfolio_id == "PF-1"
        assert bp.version == 1
        assert bp.total_slots == 5
        assert bp.long_count == 5

    def test_assemble_weight_sum(self):
        recs = make_recs(5)
        req  = ConstructionRequest(portfolio_id="PF-1")
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        assembler = BlueprintAssembler()
        bp = assembler.assemble(weights, recs, req)
        total = sum(s.target_weight for s in bp.slots)
        assert abs(total - bp.long_weight_sum) < 1e-4

    def test_sector_weights_populated(self):
        recs = [
            _rec("A", sector="tech"),
            _rec("B", sector="tech"),
            _rec("C", sector="finance"),
        ]
        req = ConstructionRequest(portfolio_id="PF")
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        assembler = BlueprintAssembler()
        bp = assembler.assemble(weights, recs, req)
        assert "tech" in bp.sector_weights
        assert "finance" in bp.sector_weights

    def test_slots_have_recommendation_ids(self):
        recs = make_recs(3)
        req  = ConstructionRequest(portfolio_id="PF")
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        assembler = BlueprintAssembler()
        bp = assembler.assemble(weights, recs, req)
        for slot in bp.slots:
            assert slot.recommendation_id != ""

    def test_to_dict_roundtrip(self):
        recs = make_recs(3)
        req  = ConstructionRequest(portfolio_id="PF")
        assigner = WeightAssigner()
        weights  = assigner.assign(recs, req)
        assembler = BlueprintAssembler()
        bp = assembler.assemble(weights, recs, req)
        d  = bp.to_dict()
        assert d["portfolio_id"] == "PF"
        assert len(d["slots"]) == 3


class TestConstructionEngine:
    def test_build_blueprint_success(self, recs_10, long_only_request):
        engine = ConstructionEngine()
        bp = engine.build_blueprint(recs_10, long_only_request)
        assert bp.total_slots == 10
        assert bp.portfolio_id == long_only_request.portfolio_id

    def test_empty_recs_raises(self, long_only_request):
        engine = ConstructionEngine()
        with pytest.raises((ValueError, Exception)):
            engine.build_blueprint([], long_only_request)

    def test_version_increments(self, recs_5, long_only_request):
        engine = ConstructionEngine()
        bp1 = engine.build_blueprint(recs_5, long_only_request, version=1)
        bp2 = engine.build_blueprint(recs_5, long_only_request, version=2)
        assert bp1.version == 1
        assert bp2.version == 2

    def test_run_count_increments(self, recs_5, long_only_request):
        engine = ConstructionEngine()
        engine.build_blueprint(recs_5, long_only_request)
        engine.build_blueprint(recs_5, long_only_request)
        assert engine.run_count == 2

    def test_error_count_on_failure(self, long_only_request):
        engine = ConstructionEngine()
        try:
            engine.build_blueprint([], long_only_request)
        except Exception:
            pass
        assert engine.error_count == 1

    def test_recent_runs(self, recs_5, long_only_request):
        engine = ConstructionEngine()
        engine.build_blueprint(recs_5, long_only_request)
        runs = engine.recent_runs()
        assert len(runs) == 1
        assert runs[0].succeeded

    def test_determinism(self, recs_5, long_only_request):
        engine = ConstructionEngine()
        bp1 = engine.build_blueprint(recs_5, long_only_request, version=1)
        bp2 = engine.build_blueprint(recs_5, long_only_request, version=1)
        # Same inputs → same slot weights
        for s1, s2 in zip(
            sorted(bp1.slots, key=lambda s: s.symbol),
            sorted(bp2.slots, key=lambda s: s.symbol),
        ):
            assert abs(s1.target_weight - s2.target_weight) < 1e-8
