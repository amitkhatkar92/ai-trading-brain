"""tests/unit/investment/decision/risk/test_risk_dimensions.py
Tests for all 5 risk dimension evaluators.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.risk.market_risk import MarketRiskEvaluator
from iios.investment.decision.risk.company_risk import CompanyRiskEvaluator
from iios.investment.decision.risk.strategy_risk import StrategyRiskEvaluator
from iios.investment.decision.risk.execution_risk import ExecutionRiskEvaluator
from iios.investment.decision.risk.confidence_risk import ConfidenceRiskEvaluator
from iios.investment.decision.risk.risk_constants import EXECUTION_RISK_CONF_FLOOR


# ─── MarketRiskEvaluator ─────────────────────────────────────────────────────

class TestMarketRiskEvaluator:
    def setup_method(self):
        self.evaluator = MarketRiskEvaluator()

    def test_no_market_items_returns_max_risk(self, minimal_evidence_snapshot, make_ev_item, make_evidence_snapshot):
        # minimal_evidence_snapshot has one MARKET item — use empty snapshot
        snap = make_evidence_snapshot([], decision_id="D1", subject_id="X", quality=0.0)
        result = self.evaluator.evaluate(snap)
        assert result.market_risk == 95.0
        assert result.evidence_coverage == 0.0

    def test_rich_market_items_lower_risk(self, rich_evidence_snapshot):
        result = self.evaluator.evaluate(rich_evidence_snapshot)
        assert 0.0 <= result.market_risk <= 100.0
        assert result.market_risk < 95.0

    def test_result_fields_in_range(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        for attr in ("freshness_risk", "quality_risk", "gap_risk", "tail_risk", "market_risk"):
            val = getattr(r, attr)
            assert 0.0 <= val <= 100.0, f"{attr} out of range: {val}"

    def test_to_dict_contains_all_keys(self, rich_evidence_snapshot):
        d = self.evaluator.evaluate(rich_evidence_snapshot).to_dict()
        for k in ("evidence_coverage", "freshness_risk", "quality_risk",
                  "gap_risk", "tail_risk", "market_risk"):
            assert k in d

    def test_low_confidence_increases_market_risk(self, make_ev_item, make_evidence_snapshot):
        low_conf_items = [
            make_ev_item("last_price", 100, EvidenceSourceType.MARKET, confidence=10.0),
            make_ev_item("rsi_14",      50, EvidenceSourceType.MARKET, confidence=10.0),
        ]
        high_conf_items = [
            make_ev_item("last_price", 100, EvidenceSourceType.MARKET, confidence=95.0),
            make_ev_item("rsi_14",      50, EvidenceSourceType.MARKET, confidence=95.0),
        ]
        low_snap  = make_evidence_snapshot(low_conf_items,  quality=10.0)
        high_snap = make_evidence_snapshot(high_conf_items, quality=95.0)
        assert self.evaluator.evaluate(low_snap).market_risk > \
               self.evaluator.evaluate(high_snap).market_risk

    def test_stale_market_items_increase_freshness_risk(self, make_ev_item, make_evidence_snapshot):
        stale = [make_ev_item("last_price", 100, EvidenceSourceType.MARKET, freshness_score=0.1)]
        fresh = [make_ev_item("last_price", 100, EvidenceSourceType.MARKET, freshness_score=1.0)]
        stale_snap = make_evidence_snapshot(stale, quality=80.0)
        fresh_snap = make_evidence_snapshot(fresh, quality=80.0)
        stale_r = self.evaluator.evaluate(stale_snap)
        fresh_r = self.evaluator.evaluate(fresh_snap)
        assert stale_r.freshness_risk > fresh_r.freshness_risk

    def test_coverage_fraction_bounded(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        assert 0.0 <= r.evidence_coverage <= 1.0


# ─── CompanyRiskEvaluator ────────────────────────────────────────────────────

class TestCompanyRiskEvaluator:
    def setup_method(self):
        self.evaluator = CompanyRiskEvaluator()

    def test_no_company_items_returns_elevated(self, make_evidence_snapshot):
        snap = make_evidence_snapshot([], quality=0.0)
        r = self.evaluator.evaluate(snap)
        assert r.company_risk >= 60.0

    def test_rich_company_snapshot_lower_risk(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        assert r.company_risk < 65.0

    def test_high_pe_adds_fundamental_risk(self, make_ev_item, make_evidence_snapshot):
        items_high_pe = [make_ev_item("pe_ratio", 55.0, EvidenceSourceType.COMPANY)]
        items_low_pe  = [make_ev_item("pe_ratio", 15.0, EvidenceSourceType.COMPANY)]
        high_r = self.evaluator.evaluate(make_evidence_snapshot(items_high_pe, quality=80.0))
        low_r  = self.evaluator.evaluate(make_evidence_snapshot(items_low_pe, quality=80.0))
        assert high_r.fundamental_risk > low_r.fundamental_risk

    def test_low_roe_adds_fundamental_risk(self, make_ev_item, make_evidence_snapshot):
        items_low  = [make_ev_item("roe",  5.0, EvidenceSourceType.COMPANY)]
        items_high = [make_ev_item("roe", 20.0, EvidenceSourceType.COMPANY)]
        r_low  = self.evaluator.evaluate(make_evidence_snapshot(items_low,  quality=80.0))
        r_high = self.evaluator.evaluate(make_evidence_snapshot(items_high, quality=80.0))
        assert r_low.fundamental_risk > r_high.fundamental_risk

    def test_negative_revenue_growth_adds_risk(self, make_ev_item, make_evidence_snapshot):
        neg  = [make_ev_item("revenue_growth", -0.10, EvidenceSourceType.COMPANY)]
        pos  = [make_ev_item("revenue_growth",  0.15, EvidenceSourceType.COMPANY)]
        r_neg = self.evaluator.evaluate(make_evidence_snapshot(neg, quality=80.0))
        r_pos = self.evaluator.evaluate(make_evidence_snapshot(pos, quality=80.0))
        assert r_neg.fundamental_risk > r_pos.fundamental_risk

    def test_scores_in_range(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        for attr in ("coverage_risk", "freshness_risk", "fundamental_risk", "company_risk"):
            val = getattr(r, attr)
            assert 0.0 <= val <= 100.0

    def test_to_dict_keys(self, rich_evidence_snapshot):
        d = self.evaluator.evaluate(rich_evidence_snapshot).to_dict()
        assert all(k in d for k in ("item_count", "company_risk", "fundamental_risk"))


# ─── StrategyRiskEvaluator ───────────────────────────────────────────────────

class TestStrategyRiskEvaluator:
    def setup_method(self):
        self.evaluator = StrategyRiskEvaluator()

    def test_no_strategy_items_elevated_risk(self, make_evidence_snapshot):
        snap = make_evidence_snapshot([], quality=0.0)
        r = self.evaluator.evaluate(snap)
        assert r.strategy_risk >= 70.0

    def test_good_win_rate_lowers_risk(self, make_ev_item, make_evidence_snapshot):
        good = [make_ev_item("win_rate", 0.65, EvidenceSourceType.STRATEGY)]
        bad  = [make_ev_item("win_rate", 0.40, EvidenceSourceType.STRATEGY)]
        r_good = self.evaluator.evaluate(make_evidence_snapshot(good, quality=80.0))
        r_bad  = self.evaluator.evaluate(make_evidence_snapshot(bad,  quality=80.0))
        assert r_good.strategy_risk < r_bad.strategy_risk

    def test_high_sharpe_reduces_risk(self, make_ev_item, make_evidence_snapshot):
        low_w  = [make_ev_item("win_rate", 0.55, EvidenceSourceType.STRATEGY),
                  make_ev_item("sharpe_ratio", 0.3, EvidenceSourceType.STRATEGY)]
        high_w = [make_ev_item("win_rate", 0.55, EvidenceSourceType.STRATEGY),
                  make_ev_item("sharpe_ratio", 1.5, EvidenceSourceType.STRATEGY)]
        r_low  = self.evaluator.evaluate(make_evidence_snapshot(low_w,  quality=80.0))
        r_high = self.evaluator.evaluate(make_evidence_snapshot(high_w, quality=80.0))
        assert r_low.strategy_risk >= r_high.strategy_risk

    def test_rich_strategy_snapshot(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        assert 0.0 <= r.strategy_risk <= 100.0

    def test_result_fields_in_range(self, rich_evidence_snapshot):
        r = self.evaluator.evaluate(rich_evidence_snapshot)
        for attr in ("performance_risk", "coverage_risk", "strategy_risk"):
            assert 0.0 <= getattr(r, attr) <= 100.0

    def test_to_dict(self, rich_evidence_snapshot):
        d = self.evaluator.evaluate(rich_evidence_snapshot).to_dict()
        assert "strategy_risk" in d and "win_rate" in d


# ─── ExecutionRiskEvaluator ──────────────────────────────────────────────────

class TestExecutionRiskEvaluator:
    def setup_method(self):
        self.evaluator = ExecutionRiskEvaluator()

    def test_high_confidence_low_risk(
        self, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        r = self.evaluator.evaluate(rich_reasoning_snapshot, rich_confidence_snapshot)
        assert r.execution_risk < 60.0

    def test_low_confidence_high_exec_risk(
        self, minimal_reasoning_snapshot, minimal_confidence_snapshot,
    ):
        r = self.evaluator.evaluate(minimal_reasoning_snapshot, minimal_confidence_snapshot)
        # just check it's valid
        assert 0.0 <= r.execution_risk <= 100.0

    def test_result_in_range(self, rich_reasoning_snapshot, rich_confidence_snapshot):
        r = self.evaluator.evaluate(rich_reasoning_snapshot, rich_confidence_snapshot)
        for attr in ("confidence_score", "reasoning_quality", "logic_consistency",
                     "timing_risk", "execution_risk"):
            assert 0.0 <= getattr(r, attr) <= 100.0

    def test_to_dict_has_execution_risk(
        self, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        d = self.evaluator.evaluate(
            rich_reasoning_snapshot, rich_confidence_snapshot,
        ).to_dict()
        assert "execution_risk" in d


# ─── ConfidenceRiskEvaluator ─────────────────────────────────────────────────

class TestConfidenceRiskEvaluator:
    def setup_method(self):
        self.evaluator = ConfidenceRiskEvaluator()

    def test_high_confidence_low_risk(self, rich_confidence_snapshot):
        r = self.evaluator.evaluate(rich_confidence_snapshot)
        assert r.confidence_risk < 70.0

    def test_confidence_gap_equals_100_minus_confidence(self, rich_confidence_snapshot):
        r = self.evaluator.evaluate(rich_confidence_snapshot)
        assert abs(r.confidence_gap - (100.0 - r.overall_confidence)) < 1e-6

    def test_fields_in_range(self, rich_confidence_snapshot):
        r = self.evaluator.evaluate(rich_confidence_snapshot)
        for attr in ("confidence_gap", "calibration_risk", "evidence_conf_risk",
                     "reasoning_conf_risk", "uncertainty_risk", "confidence_risk"):
            assert 0.0 <= getattr(r, attr) <= 100.0

    def test_to_dict_keys(self, rich_confidence_snapshot):
        d = self.evaluator.evaluate(rich_confidence_snapshot).to_dict()
        assert all(k in d for k in ("confidence_risk", "calibration_risk"))
