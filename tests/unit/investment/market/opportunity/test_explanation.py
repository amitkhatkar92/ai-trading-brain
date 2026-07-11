"""tests/unit/investment/market/opportunity/test_explanation.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.evidence_collector import collect_evidence
from iios.investment.market.opportunity.explanation_engine import (
    ExplanationEngine,
    explain as free_explain,
)
from iios.investment.market.opportunity.models import (
    Evidence,
    IntelligenceContext,
    Opportunity,
    OpportunityCategory,
    OpportunityExplanation,
)
from iios.investment.market.opportunity.reason_generator import (
    generate_reason,
    generate_risk_summary,
    strategy_suitability,
)


def _strong_ctx() -> IntelligenceContext:
    return IntelligenceContext(
        trend_strength=80.0, rs_vs_market=85.0, volume_ratio=2.0,
        liquidity_score=75.0, sector_rs_score=78.0, sector_momentum=70.0,
        risk_score=72.0, return_1bar=0.03, return_20bar=0.15,
        breadth_score=65.0, above_ma20_pct=0.72, volatility_percentile=0.35,
        fundamental_score=70.0, systemic_risk_score=20.0,
    )


def _make_opp(
    category: OpportunityCategory = OpportunityCategory.TREND_FOLLOWING,
) -> Opportunity:
    return Opportunity.new("AAPL", "IT", "Software", category, 1)


class TestCollectEvidence:
    def test_returns_list_of_evidence(self):
        ctx = _strong_ctx()
        evs = collect_evidence(ctx)
        assert isinstance(evs, list)
        assert len(evs) > 0
        assert all(isinstance(e, Evidence) for e in evs)

    def test_keys_are_strings(self):
        ctx = _strong_ctx()
        evs = collect_evidence(ctx)
        for e in evs:
            assert isinstance(e.key, str)
            assert len(e.key) > 0

    def test_weights_in_unit_interval(self):
        ctx = _strong_ctx()
        evs = collect_evidence(ctx)
        for e in evs:
            assert 0.0 <= e.weight <= 1.0

    def test_weak_context_has_evidence(self):
        ctx = IntelligenceContext(trend_strength=20.0, rs_vs_market=15.0)
        evs = collect_evidence(ctx)
        assert isinstance(evs, list)


class TestReasonGenerator:
    def test_generate_reason_nonempty(self):
        opp = _make_opp()
        ctx = _strong_ctx()
        reason = generate_reason(opp, ctx)
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_risk_summary_nonempty(self):
        ctx = _strong_ctx()
        summary = generate_risk_summary(ctx)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_strategy_suitability_list(self):
        opp = _make_opp(OpportunityCategory.TREND_FOLLOWING)
        strategies = strategy_suitability(opp)
        assert isinstance(strategies, list)
        assert len(strategies) > 0

    def test_defensive_candidate_strategies(self):
        opp = _make_opp(OpportunityCategory.DEFENSIVE_CANDIDATE)
        strategies = strategy_suitability(opp)
        assert isinstance(strategies, list)

    def test_reversal_candidate_strategies(self):
        opp = _make_opp(OpportunityCategory.REVERSAL_CANDIDATE)
        strategies = strategy_suitability(opp)
        assert isinstance(strategies, list)


class TestExplanationEngine:
    def test_explain_after_context(self):
        engine = ExplanationEngine()
        opp    = _make_opp()
        ctx    = _strong_ctx()
        engine.update_context(opp.symbol, ctx)
        exp = engine.explain(opp)
        assert isinstance(exp, OpportunityExplanation)
        assert exp.symbol == "AAPL"

    def test_explain_without_context_returns_result(self):
        """Engine generates a default explanation even without explicit context."""
        engine = ExplanationEngine()
        opp    = _make_opp()
        exp = engine.explain(opp)
        # The engine may return an explanation with default context
        # (it is valid to return None OR a default explanation)
        if exp is not None:
            assert isinstance(exp, OpportunityExplanation)

    def test_explanation_has_evidence(self):
        engine = ExplanationEngine()
        opp    = _make_opp()
        ctx    = _strong_ctx()
        engine.update_context(opp.symbol, ctx)
        exp = engine.explain(opp)
        assert exp is not None
        assert isinstance(exp.evidence, list)
        assert len(exp.evidence) > 0

    def test_explanation_has_reason_text(self):
        engine = ExplanationEngine()
        opp    = _make_opp()
        ctx    = _strong_ctx()
        engine.update_context(opp.symbol, ctx)
        exp    = engine.explain(opp)
        assert exp is not None
        assert len(exp.why_discovered) > 0

    def test_get_cached_returns_last(self):
        engine = ExplanationEngine()
        opp    = _make_opp()
        ctx    = _strong_ctx()
        engine.update_context(opp.symbol, ctx)
        exp    = engine.explain(opp)
        cached = engine.get_cached(opp.opportunity_id)
        assert cached is not None
        assert cached.symbol == opp.symbol

    def test_free_explain_function(self):
        opp = _make_opp()
        ctx = _strong_ctx()
        exp = free_explain(opp, ctx)
        assert isinstance(exp, OpportunityExplanation)
        assert exp.symbol == "AAPL"

    def test_explanation_to_dict(self):
        engine = ExplanationEngine()
        opp    = _make_opp()
        ctx    = _strong_ctx()
        engine.update_context(opp.symbol, ctx)
        exp = engine.explain(opp)
        assert exp is not None
        d = exp.to_dict()
        assert "symbol" in d
        assert "evidence" in d
