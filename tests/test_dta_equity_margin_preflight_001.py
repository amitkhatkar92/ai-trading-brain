"""
tests/test_dta_equity_margin_preflight_001.py
=================================================
DTA-EQUITY-MARGIN-PREFLIGHT-001

Root cause (found via real 7-trading-day production review, 2026-11-02):
16 real BROKER_REJECTED_ORDER "insufficient funds" failures in one ~10-day
window (GAIL/SBIN/BAJAJFINSV/TATACONSUM/PETRONET/COALINDIA/CASTROLIND).
CapitalRiskEngine/PortfolioAllocationAI size trades off a STATIC
TOTAL_CAPITAL constant and never subtract capital already locked in
currently-open positions, so approved orders can exceed real available
margin by the time they reach the broker.

Verifies OrderManager._check_available_funds() -- a pre-flight check
reusing the exact get_fund_limits() field names (availabelBalance/
availableBalance) options_order_manager.py's live execution path
already uses, applied to equity for the first time.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from execution_engine.order_manager import OrderManager


def _make_om(paper_mode: bool, broker):
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = paper_mode
    om._broker = broker
    return om


class TestEquityMarginPreflight:
    def test_t01_paper_mode_always_skips_check(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": 0.0}}
        om = _make_om(paper_mode=True, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=100, price=1000.0)
        assert result is None
        broker.get_fund_limits.assert_not_called()

    def test_t02_broker_without_get_fund_limits_skips_check(self):
        class BareBroker:
            pass
        om = _make_om(paper_mode=False, broker=BareBroker())
        result = om._check_available_funds("RELIANCE", "BUY", qty=100, price=1000.0)
        assert result is None

    def test_t03_sufficient_funds_returns_none(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": 100000.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None

    def test_t04_insufficient_funds_blocks_with_detail(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": 500.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("GAIL", "BUY", qty=12, price=167.2)
        assert result is not None
        assert "required=" in result and "available=" in result

    def test_t05_availableBalance_fallback_used_when_typo_key_absent(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availableBalance": 100000.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None

    def test_t06_fails_open_when_broker_raises(self):
        broker = MagicMock()
        broker.get_fund_limits.side_effect = RuntimeError("boom")
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None

    def test_t07_fails_open_on_malformed_response(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None

    def test_t08_fails_open_on_negative_available_funds(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": -50.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None

    def test_t09_exact_boundary_is_sufficient(self):
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": 2000.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("RELIANCE", "BUY", qty=2, price=1000.0)
        assert result is None  # exactly equal -- not strictly less than, so allowed

    def test_t10_reproduces_real_live_scenario(self):
        """Real production values from the 2026-11-02 review: GAIL BUY qty=12
        at entry 167.2 required ~Rs.2866.47 more than was available."""
        broker = MagicMock()
        broker.get_fund_limits.return_value = {"data": {"availabelBalance": 143.0}}
        om = _make_om(paper_mode=False, broker=broker)
        result = om._check_available_funds("GAIL", "BUY", qty=12, price=167.2)
        assert result is not None
