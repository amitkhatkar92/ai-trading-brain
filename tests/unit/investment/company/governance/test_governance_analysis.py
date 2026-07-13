"""tests/unit/investment/company/governance/test_governance_analysis.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.board_profile import (
    build_board_composition, build_committee_structure,
)
from iios.investment.company.governance.governance_events import classify_events
from iios.investment.company.governance.governance_engine import GovernanceAnalysisEngine
from iios.investment.company.governance.management_profile import GovernanceProfile


@pytest.fixture
def engine():
    return GovernanceAnalysisEngine()


@pytest.fixture
def good_board(good_board_info):
    return build_board_composition(good_board_info)


@pytest.fixture
def good_committees(good_board_info):
    return build_committee_structure(good_board_info)


@pytest.fixture
def weak_board(weak_board_info):
    return build_board_composition(weak_board_info)


@pytest.fixture
def weak_committees(weak_board_info):
    return build_committee_structure(weak_board_info)


class TestGovernanceAnalysisEngine:
    def test_returns_profile(self, engine, good_board, good_committees):
        result = engine.compute(board=good_board, committees=good_committees)
        assert isinstance(result, GovernanceProfile)

    def test_good_governance(self, engine, good_board, good_committees):
        result = engine.compute(board=good_board, committees=good_committees,
                                ceo_chairman_same=False, is_family_controlled=False)
        assert result.overall_governance_score >= 55.0

    def test_weak_governance(self, engine, weak_board, weak_committees):
        events = classify_events(["accounting_fraud_2018", "regulatory_penalty_2021"])
        result = engine.compute(
            board=weak_board, committees=weak_committees,
            event_log=events,
            ceo_chairman_same=True, is_family_controlled=True,
            promoter_holding_pct=0.75,
        )
        assert result.overall_governance_score < 50.0

    def test_score_ranges(self, engine, good_board, good_committees):
        result = engine.compute(board=good_board, committees=good_committees)
        for score in [
            result.board_independence_score, result.board_diversity_score,
            result.committee_quality_score, result.overall_governance_score,
        ]:
            assert 0.0 <= score <= 100.0

    def test_sebi_standard(self, engine, good_board, good_committees):
        result = engine.compute(
            board=good_board, committees=good_committees,
            governance_standard="sebi",
        )
        assert isinstance(result, GovernanceProfile)
        assert result.governance_standard == "sebi"

    def test_ceo_chairman_penalty(self, engine, good_board, good_committees):
        s1 = engine.compute(board=good_board, committees=good_committees,
                            ceo_chairman_same=False)
        s2 = engine.compute(board=good_board, committees=good_committees,
                            ceo_chairman_same=True)
        assert s2.overall_governance_score <= s1.overall_governance_score

    def test_event_penalty(self, engine, good_board, good_committees):
        clean = engine.compute(board=good_board, committees=good_committees)
        events = classify_events(["accounting_fraud", "regulatory_penalty"])
        with_events = engine.compute(board=good_board, committees=good_committees,
                                     event_log=events)
        assert with_events.overall_governance_score < clean.overall_governance_score

    def test_empty_board_graceful(self, engine):
        board = build_board_composition(None)
        committees = build_committee_structure(None)
        result = engine.compute(board=board, committees=committees)
        assert isinstance(result, GovernanceProfile)


class TestGovernanceEvents:
    def test_classify_empty(self):
        el = classify_events([])
        assert el.high_severity_count == 0
        assert el.total_count == 0

    def test_classify_fraud(self):
        el = classify_events(["accounting_fraud_2020", "regulatory_penalty"])
        assert el.total_count == 2
        assert el.high_severity_count >= 1

    def test_classify_awards(self):
        el = classify_events(["award_best_governance", "disclosure_excellence"])
        # Positive events don't raise; no high-severity incidents
        assert el.high_severity_count == 0

    def test_classify_none(self):
        el = classify_events(None)
        assert el.total_count == 0
