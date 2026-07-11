"""tests/unit/investment/market/opportunity/test_scanners.py"""
from __future__ import annotations

import pytest

from iios.investment.market.opportunity.market_scanner import MarketScanner
from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityCategory,
    ScanScope,
)
from iios.investment.market.opportunity.opportunity_category import BUILT_IN_RULES
from iios.investment.market.opportunity.opportunity_scanner import OpportunityScanner
from iios.investment.market.opportunity.universe_scanner import Universe, UniverseScanner
from iios.investment.market.opportunity.watchlist_scanner import WatchlistScanner


class TestMarketScanner:
    def test_scan_returns_opportunities(self, obs_batch):
        scanner = MarketScanner()
        results = scanner.scan(obs_batch)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_scan_returns_correct_symbols(self, obs_batch):
        scanner  = MarketScanner()
        results  = scanner.scan(obs_batch)
        returned = {o.symbol for o in results}
        input_   = {o.symbol for o in obs_batch}
        assert returned.issubset(input_)

    def test_strong_asset_always_included(self, make_strong):
        scanner = MarketScanner()
        obs     = [make_strong("AAPL")]
        results = scanner.scan(obs)
        syms    = [o.symbol for o in results]
        assert "AAPL" in syms

    def test_custom_rules(self, obs_batch):
        from iios.investment.market.opportunity.opportunity_category import CategoryRule
        custom_rule = CategoryRule(
            category=OpportunityCategory.HIGH_RS,
            rs_vs_market_min=0.0,   # matches everything
        )
        scanner = MarketScanner(rules=[custom_rule])
        results = scanner.scan(obs_batch)
        assert len(results) == len(obs_batch)
        for r in results:
            assert r.primary_category is OpportunityCategory.HIGH_RS


class TestWatchlistScanner:
    def test_scan_only_watchlisted(self, obs_batch):
        scanner = WatchlistScanner()
        scanner.set_watchlist({"AAPL", "MSFT"})
        results = scanner.scan(obs_batch)
        returned = {o.symbol for o in results}
        assert returned.issubset({"AAPL", "MSFT"})

    def test_add_and_remove(self, obs_batch):
        scanner = WatchlistScanner()
        scanner.add("GOOG")
        scanner.add("AAPL")
        scanner.remove("GOOG")
        results  = scanner.scan(obs_batch)
        returned = {o.symbol for o in results}
        assert "GOOG" not in returned

    def test_empty_watchlist_returns_nothing(self, obs_batch):
        scanner = WatchlistScanner()
        results = scanner.scan(obs_batch)
        assert results == []


class TestUniverseScanner:
    def test_scan_named_universe(self, obs_batch):
        scanner  = UniverseScanner()
        universe = Universe(name="tech", scope=ScanScope.SECTOR, symbols={"AAPL", "MSFT"})
        scanner.register(universe)
        results  = scanner.scan(obs_batch, "tech")
        returned = {o.symbol for o in results}
        assert returned.issubset({"AAPL", "MSFT"})

    def test_unknown_universe_returns_empty(self, obs_batch):
        scanner = UniverseScanner()
        results = scanner.scan(obs_batch, "NOPE")
        assert results == []

    def test_deregister_removes_universe(self, obs_batch):
        scanner  = UniverseScanner()
        universe = Universe(name="temp", scope=ScanScope.THEME, symbols={"AAPL"})
        scanner.register(universe)
        scanner.deregister("temp")
        results = scanner.scan(obs_batch, "temp")
        assert results == []

    def test_sector_universe_filters_by_sector(self, obs_batch):
        scanner  = UniverseScanner()
        universe = Universe(name="IT", scope=ScanScope.SECTOR, sectors={"Information Technology"})
        scanner.register(universe)
        results = scanner.scan(obs_batch, "IT")
        for opp in results:
            assert opp.sector == "Information Technology"


class TestOpportunityScanner:
    def test_full_market_scan(self, obs_batch):
        scanner = OpportunityScanner()
        results = scanner.scan(obs_batch, ScanScope.FULL_MARKET)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_watchlist_scope(self, obs_batch):
        scanner = OpportunityScanner()
        scanner.add_to_watchlist("AAPL")
        results = scanner.scan(obs_batch, ScanScope.WATCHLIST)
        returned = {o.symbol for o in results}
        assert "AAPL" in returned

    def test_universe_scope(self, obs_batch):
        scanner  = OpportunityScanner()
        universe = Universe(name="myUni", scope=ScanScope.THEME, symbols={"MSFT"})
        scanner.register_universe(universe)
        results  = scanner.scan(obs_batch, ScanScope.THEME, universe_name="myUni")
        returned = {o.symbol for o in results}
        assert returned.issubset({"MSFT"})

    def test_set_rules(self, obs_batch):
        from iios.investment.market.opportunity.opportunity_category import CategoryRule
        scanner = OpportunityScanner()
        new_rule = CategoryRule(
            category=OpportunityCategory.HIGH_RS,
            rs_vs_market_min=0.0,
        )
        scanner.set_rules([new_rule])
        results = scanner.scan(obs_batch, ScanScope.FULL_MARKET)
        assert len(results) == len(obs_batch)

    def test_empty_observations(self):
        scanner = OpportunityScanner()
        results = scanner.scan([], ScanScope.FULL_MARKET)
        assert results == []
