"""tests/unit/investment/company/governance/test_leadership_models.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.executive_profile import (
    ExecutiveRecord, ExecutiveTeamProfile, build_executive_team,
)
from iios.investment.company.governance.board_profile import (
    BoardComposition, CommitteeStructure,
    build_board_composition, build_committee_structure,
)
from iios.investment.company.governance.management_profile import BoardIndependenceLevel


class TestExecutiveProfile:
    def test_build_from_info(self):
        info = {
            "ceo_tenure_years": 8.0,
            "cfo_tenure_years": 5.0,
            "executive_team_tenure_avg": 6.0,
            "leadership_changes_3y": 1,
            "ceo_is_founder": False,
            "ceo_chairman_same": False,
        }
        team = build_executive_team(info)
        assert team.ceo_tenure_years == 8.0
        assert team.cfo_tenure_years == 5.0
        assert team.leadership_changes_3y == 1
        assert team.is_founder_led is False

    def test_empty_info(self):
        team = build_executive_team(None)
        assert team.ceo_tenure_years is None
        assert team.leadership_changes_3y == 0

    def test_founder_led(self):
        info = {"ceo_is_founder": True, "ceo_tenure_years": 20.0}
        team = build_executive_team(info)
        assert team.is_founder_led is True

    def test_to_dict(self):
        team = ExecutiveTeamProfile(ceo_tenure_years=8.0)
        d = team.to_dict()
        assert d["ceo_tenure_years"] == 8.0
        assert "is_founder_led" in d

    def test_executive_records(self):
        info = {
            "executives": [
                {"role": "CEO", "name": "John Doe", "tenure_years": 8.0},
                {"role": "CFO", "name": "Jane Doe", "tenure_years": 5.0},
            ]
        }
        team = build_executive_team(info)
        assert len(team.executives) == 2
        assert team.executive_team_size == 2
        assert team.executives[0].role == "CEO"


class TestBoardProfile:
    def test_build_good_board(self, good_board_info):
        board = build_board_composition(good_board_info)
        assert board.total_directors == 10
        assert board.independent_directors == 7
        assert board.female_directors == 3
        assert board.independence_ratio == pytest.approx(0.7)
        assert board.independence_level == BoardIndependenceLevel.EXCELLENT

    def test_build_weak_board(self, weak_board_info):
        board = build_board_composition(weak_board_info)
        assert board.independence_ratio == pytest.approx(0.20)
        assert board.independence_level == BoardIndependenceLevel.WEAK

    def test_empty_board_info(self):
        board = build_board_composition(None)
        assert board.total_directors == 0
        assert board.independence_ratio is None
        assert board.independence_level == BoardIndependenceLevel.UNKNOWN

    def test_independence_levels(self):
        for n_indep, expected_level in [
            (8, BoardIndependenceLevel.EXCELLENT),
            (6, BoardIndependenceLevel.GOOD),
            (4, BoardIndependenceLevel.ADEQUATE),
            (2, BoardIndependenceLevel.WEAK),
        ]:
            board = build_board_composition({
                "total_directors": 10,
                "independent_directors": n_indep,
            })
            assert board.independence_level == expected_level

    def test_to_dict(self, good_board_info):
        board = build_board_composition(good_board_info)
        d = board.to_dict()
        assert d["total_directors"] == 10
        assert "independence_ratio" in d


class TestCommitteeStructure:
    def test_build_full_committees(self, good_board_info):
        committees = build_committee_structure(good_board_info)
        assert committees.has_audit_committee is True
        assert committees.has_remuneration_committee is True
        assert committees.has_risk_committee is True
        assert committees.has_nomination_committee is True
        assert committees.committee_count == 4

    def test_build_no_committees(self, weak_board_info):
        committees = build_committee_structure(weak_board_info)
        assert committees.has_audit_committee is False
        assert committees.committee_count == 0

    def test_empty_info(self):
        committees = build_committee_structure(None)
        assert committees.committee_count == 0

    def test_to_dict(self, good_board_info):
        committees = build_committee_structure(good_board_info)
        d = committees.to_dict()
        assert d["has_audit_committee"] is True
        assert d["committee_count"] == 4
