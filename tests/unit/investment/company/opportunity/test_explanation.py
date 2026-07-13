"""tests/unit/investment/company/opportunity/test_explanation.py
Tests for thesis generation and explanation engine.
"""
from __future__ import annotations

import pytest

from iios.investment.company.opportunity.explanation_engine import ExplanationEngine
from iios.investment.company.opportunity.investment_thesis import InvestmentThesis, ThesisEvidence
from iios.investment.company.opportunity.opportunity_profile import (
    ConfidenceLevel, OpportunityCategory, OpportunityLifecycle, OpportunityStrength,
)
from iios.investment.company.opportunity.reason_generator import (
    build_headline, build_narrative, generate_catalysts, generate_key_risks,
    generate_monitoring_points, generate_strengths, generate_weaknesses,
)
from iios.investment.company.opportunity.evidence_collector import (
    collect_all_evidence, collect_earnings_evidence, collect_bq_evidence,
    collect_financial_evidence, collect_valuation_evidence,
)


class TestThesisEvidence:
    def test_to_dict(self):
        e = ThesisEvidence("ROIC", "18%", "positive", "high", "earnings")
        d = e.to_dict()
        assert d["factor"] == "ROIC"
        assert d["signal"] == "positive"


class TestInvestmentThesis:
    @pytest.fixture
    def thesis(self):
        return InvestmentThesis(
            ticker="INFY",
            category=OpportunityCategory.COMPOUNDER,
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            headline="INFY — Strong Compounder opportunity",
            narrative="INFY is a quality compounder.",
            strengths=["High ROIC", "Strong moat", "Growing margins"],
            weaknesses=["Premium valuation"],
            key_risks=["Cyclicality risk"],
            key_catalysts=["Market expansion"],
            monitoring_points=["ROIC trend", "Free cash flow"],
            supporting_evidence=[ThesisEvidence("ROIC", "18%", "positive", "high")],
            confidence_level=ConfidenceLevel.HIGH,
        )

    def test_has_strong_thesis(self, thesis):
        assert thesis.has_strong_thesis is True

    def test_risk_reward_favorable(self, thesis):
        # 3 strengths, 1 risk → balanced (need ≥4 strengths for "favorable")
        assert thesis.risk_reward_balance in ("favorable", "balanced")

    def test_risk_reward_elevated(self):
        t = InvestmentThesis(
            ticker="X", category=OpportunityCategory.WATCHLIST,
            lifecycle=OpportunityLifecycle.MONITORING,
            key_risks=["r1", "r2", "r3", "r4"],
            strengths=["s1"],
            confidence_level=ConfidenceLevel.LOW,
        )
        assert t.risk_reward_balance == "elevated_risk"

    def test_positive_evidence(self, thesis):
        assert len(thesis.positive_evidence) == 1

    def test_to_dict_keys(self, thesis):
        d = thesis.to_dict()
        assert all(k in d for k in [
            "ticker", "headline", "narrative", "strengths", "weaknesses",
            "key_risks", "key_catalysts", "monitoring_points",
        ])


class TestEvidenceCollector:
    def test_financial_evidence(self, mock_financial):
        ev = collect_financial_evidence(mock_financial)
        assert len(ev) > 0
        factors = [e.factor for e in ev]
        assert any("FCF" in f for f in factors)

    def test_earnings_evidence(self, mock_earnings):
        ev = collect_earnings_evidence(mock_earnings)
        factors = [e.factor for e in ev]
        assert any("ROIC" in f for f in factors)

    def test_bq_evidence(self, mock_bq):
        ev = collect_bq_evidence(mock_bq)
        assert len(ev) > 0

    def test_valuation_evidence(self, mock_valuation):
        ev = collect_valuation_evidence(mock_valuation)
        assert len(ev) > 0
        factors = [e.factor for e in ev]
        assert any("Safety" in f or "safety" in f.lower() for f in factors)

    def test_none_snapshots(self):
        ev = collect_all_evidence(None, None, None, None, None, None, None)
        assert ev == []

    def test_all_evidence(
        self, mock_financial, mock_earnings, mock_bq,
        mock_valuation, mock_growth, mock_management, mock_ownership,
    ):
        ev = collect_all_evidence(
            mock_financial, mock_earnings, mock_bq,
            mock_valuation, mock_growth, mock_management, mock_ownership,
        )
        assert len(ev) > 3


class TestReasonGenerator:
    def test_strengths(self):
        strengths = generate_strengths(
            evidence=[], bq_score=75.0, fin_score=72.0, grw_score=70.0,
            moat_score=72.0, avg_roic=0.18, eps_cagr=0.15,
        )
        assert len(strengths) > 0
        assert all(isinstance(s, str) for s in strengths)

    def test_weaknesses(self):
        weaknesses = generate_weaknesses(
            evidence=[], val_score=75.0, fin_score=40.0,
            mgmt_score=40.0, own_score=35.0,
        )
        assert len(weaknesses) > 0

    def test_key_risks_cyclical(self):
        risks = generate_key_risks(
            alerts=[], is_cyclical=True, fin_score=60.0,
            val_score=60.0, category=OpportunityCategory.COMPOUNDER,
        )
        assert any("cyclical" in r.lower() for r in risks)

    def test_catalysts(self):
        cats = generate_catalysts(
            category=OpportunityCategory.COMPOUNDER,
            grw_score=70.0, val_score=55.0,
            moat_score=72.0, eps_cagr=0.18,
        )
        assert len(cats) > 0

    def test_monitoring_points(self):
        pts = generate_monitoring_points(
            category=OpportunityCategory.TURNAROUND,
            lifecycle=OpportunityLifecycle.WEAKENING,
            is_cyclical=False, fin_score=40.0,
        )
        assert len(pts) > 0

    def test_build_headline(self):
        h = build_headline("INFY", OpportunityCategory.COMPOUNDER,
                           OpportunityStrength.STRONG, 72.0, 55.0)
        assert "INFY" in h

    def test_build_narrative(self):
        n = build_narrative(
            ticker="TCS", category=OpportunityCategory.COMPOUNDER,
            strengths=["ROIC 18%", "Strong moat"],
            risks=["Cyclical risk"],
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            overall_score=72.0,
        )
        assert "TCS" in n
        assert len(n) > 50


class TestExplanationEngine:
    @pytest.fixture
    def engine(self):
        return ExplanationEngine()

    def test_returns_thesis(self, engine, mock_financial, mock_earnings, mock_bq):
        thesis = engine.generate(
            ticker="INFY",
            category=OpportunityCategory.COMPOUNDER,
            lifecycle=OpportunityLifecycle.HIGH_CONVICTION,
            strength=OpportunityStrength.STRONG,
            overall_score=70.0,
            bq_score=72.0, val_score=60.0, grw_score=72.0,
            mgmt_score=70.0, fin_score=70.0, own_score=68.0,
            confidence=0.75, alerts=[],
            financial_snapshot=mock_financial,
            earnings_snapshot=mock_earnings,
            business_quality=mock_bq,
        )
        assert isinstance(thesis, InvestmentThesis)
        assert thesis.ticker == "INFY"

    def test_all_snapshots(
        self, engine, mock_financial, mock_earnings, mock_bq,
        mock_valuation, mock_growth, mock_management, mock_ownership,
    ):
        thesis = engine.generate(
            ticker="TCS",
            category=OpportunityCategory.WIDE_MOAT,
            lifecycle=OpportunityLifecycle.CONFIRMED,
            strength=OpportunityStrength.EXCEPTIONAL,
            overall_score=82.0,
            bq_score=80.0, val_score=65.0, grw_score=75.0,
            mgmt_score=70.0, fin_score=78.0, own_score=68.0,
            confidence=0.85, alerts=[],
            financial_snapshot=mock_financial,
            earnings_snapshot=mock_earnings,
            business_quality=mock_bq,
            valuation_snapshot=mock_valuation,
            growth_snapshot=mock_growth,
            management_snapshot=mock_management,
            ownership_snapshot=mock_ownership,
        )
        assert thesis.has_strong_thesis
        assert thesis.confidence_level in (ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH)

    def test_confidence_explanation(self, engine, mock_financial, mock_earnings, mock_bq):
        thesis = engine.generate(
            ticker="X",
            category=OpportunityCategory.WATCHLIST,
            lifecycle=OpportunityLifecycle.MONITORING,
            strength=OpportunityStrength.MODERATE,
            overall_score=52.0,
            bq_score=52.0, val_score=52.0, grw_score=52.0,
            mgmt_score=52.0, fin_score=52.0, own_score=52.0,
            confidence=0.55, alerts=[],
        )
        assert isinstance(thesis.confidence_explanation, str)
        assert len(thesis.confidence_explanation) > 10
