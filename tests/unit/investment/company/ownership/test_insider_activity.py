"""tests/unit/investment/company/ownership/test_insider_activity.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.insider_transactions import (
    InsiderTransaction, InsiderTransactionLog, build_transaction_log,
)
from iios.investment.company.ownership.executive_trading import analyze_executive_trading
from iios.investment.company.ownership.director_trading import analyze_director_trading
from iios.investment.company.ownership.insider_activity import InsiderActivityEngine
from iios.investment.company.ownership.ownership_profile import InsiderActivityLabel


@pytest.fixture
def engine():
    return InsiderActivityEngine()


class TestInsiderTransaction:
    def test_is_buy(self):
        t = InsiderTransaction(insider_role="CEO", transaction_type="buy", shares=10_000)
        assert t.is_buy is True
        assert t.is_sell is False

    def test_is_sell(self):
        t = InsiderTransaction(insider_role="CFO", transaction_type="sell", shares=5_000)
        assert t.is_sell is True
        assert t.is_buy is False


class TestInsiderTransactionLog:
    def test_buy_count(self):
        log = InsiderTransactionLog()
        log.transactions = [
            InsiderTransaction("CEO", "buy", 1000),
            InsiderTransaction("CFO", "sell", 2000),
            InsiderTransaction("Dir", "buy", 500),
        ]
        assert log.buy_count == 2
        assert log.sell_count == 1

    def test_net_shares(self):
        log = InsiderTransactionLog()
        log.transactions = [
            InsiderTransaction("CEO", "buy", 3000),
            InsiderTransaction("CFO", "sell", 1000),
        ]
        assert log.net_shares == 2000

    def test_net_buy_ratio(self):
        log = InsiderTransactionLog()
        log.transactions = [
            InsiderTransaction("CEO", "buy", 1000),
            InsiderTransaction("Dir", "buy", 500),
            InsiderTransaction("CFO", "sell", 200),
        ]
        assert log.net_buy_ratio == pytest.approx(2 / 3)

    def test_empty(self):
        log = InsiderTransactionLog()
        assert log.net_buy_ratio == pytest.approx(0.5)
        assert log.total_count == 0


class TestBuildTransactionLog:
    def test_from_raw(self):
        raw = [
            {"role": "CEO", "type": "buy", "shares": 5000},
            {"role": "CFO", "type": "sell", "shares": 2000},
        ]
        log = build_transaction_log(raw)
        assert log.buy_count == 1
        assert log.sell_count == 1

    def test_empty(self):
        log = build_transaction_log(None)
        assert log.total_count == 0


class TestExecutiveTrading:
    def test_from_good_data(self, good_insider_data):
        profile = analyze_executive_trading(good_insider_data)
        assert profile.ceo_ownership_pct == pytest.approx(2.5)
        assert profile.exec_buy_count_6m == 5
        assert 0.0 <= profile.exec_holding_score <= 100.0
        assert 0.0 <= profile.exec_alignment_score <= 100.0

    def test_net_sentiment_buying(self, good_insider_data):
        profile = analyze_executive_trading(good_insider_data)
        assert profile.net_exec_sentiment > 0

    def test_empty(self):
        profile = analyze_executive_trading(None)
        assert profile.exec_holding_score == pytest.approx(35.0)


class TestDirectorTrading:
    def test_from_data(self, good_insider_data):
        profile = analyze_director_trading(good_insider_data)
        assert 0.0 <= profile.board_holding_score <= 100.0
        assert 0.0 <= profile.board_conviction_score <= 100.0


class TestInsiderActivityEngine:
    def test_returns_profile(self, engine):
        from iios.investment.company.ownership.ownership_profile import InsiderActivityProfile
        result = engine.compute(None)
        assert isinstance(result, InsiderActivityProfile)

    def test_accumulating_label(self, engine, good_insider_data):
        result = engine.compute(good_insider_data)
        assert result.insider_activity_label in (
            InsiderActivityLabel.ACCUMULATING,
            InsiderActivityLabel.STEADY,
            InsiderActivityLabel.NEUTRAL,
        )

    def test_liquidating_label(self, engine, liquidating_insider_data):
        result = engine.compute(liquidating_insider_data)
        assert result.insider_activity_label in (
            InsiderActivityLabel.DISTRIBUTING,
            InsiderActivityLabel.LIQUIDATING,
        )

    def test_scores_in_range(self, engine, good_insider_data):
        result = engine.compute(good_insider_data)
        for s in [result.insider_holding_score, result.insider_buying_score,
                  result.alignment_score]:
            assert 0.0 <= s <= 100.0

    def test_no_activity_neutral(self, engine):
        result = engine.compute({"ceo_ownership_pct": 0.02})
        assert result.insider_activity_label == InsiderActivityLabel.UNKNOWN

    def test_from_raw_transactions(self, engine):
        result = engine.compute({
            "recent_transactions": [
                {"role": "CEO", "type": "buy", "shares": 10_000},
                {"role": "CFO", "type": "buy", "shares": 5_000},
                {"role": "Dir", "type": "sell", "shares": 1_000},
            ]
        })
        assert result.insider_buy_count_6m == 2
        assert result.insider_sell_count_6m == 1

    def test_management_snapshot_boost(self, engine, good_insider_data, mock_management):
        result_no_mgmt = engine.compute(good_insider_data)
        result_with_mgmt = engine.compute(good_insider_data, management_snapshot=mock_management)
        assert result_with_mgmt.alignment_score >= result_no_mgmt.alignment_score - 0.01
