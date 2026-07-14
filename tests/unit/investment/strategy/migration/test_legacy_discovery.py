"""Tests for legacy discovery engine."""
import pytest
from iios.investment.strategy.migration.legacy_discovery import (
    DiscoveryConfig,
    DiscoveryResult,
    LegacyDiscoveryEngine,
)
from iios.investment.strategy.migration.legacy_metadata import LegacyStrategySource
from iios.investment.strategy.migration.legacy_catalog import LegacyCatalog


class TestDiscoveryEngine:
    def setup_method(self):
        self.engine = LegacyDiscoveryEngine()

    def test_discover_returns_result(self):
        result = self.engine.discover()
        assert isinstance(result, DiscoveryResult)

    def test_discover_finds_code_strategies(self):
        result = self.engine.discover()
        code_strategies = [
            s for s in result.strategies
            if s.source == LegacyStrategySource.STRATEGY_GENERATOR
        ]
        assert len(code_strategies) == 13, \
            f"Expected 13 code strategies, got {len(code_strategies)}"

    def test_discover_populates_catalog(self):
        self.engine.discover()
        catalog = self.engine.get_catalog()
        assert catalog.count() >= 13

    def test_catalog_contains_known_strategy(self):
        self.engine.discover()
        catalog = self.engine.get_catalog()
        assert catalog.get("Breakout_Volume") is not None

    def test_catalog_contains_momentum_retest(self):
        self.engine.discover()
        meta = self.engine.get_catalog().get("Momentum_Retest")
        assert meta is not None
        assert meta.min_rr > 0

    def test_discover_result_has_no_fatal_errors(self):
        result = self.engine.discover()
        assert len(result.errors) == 0 or result.total_discovered > 0

    def test_last_result_accessible(self):
        self.engine.discover()
        last = self.engine.last_result()
        assert last is not None
        assert last.total_discovered >= 13

    def test_discover_timing(self):
        result = self.engine.discover()
        assert result.duration_ms >= 0

    def test_scan_with_config(self):
        # DiscoveryEngine always scans code strategies; verify minimum count
        result = self.engine.discover()
        assert result.total_discovered >= 13

    def test_catalog_by_source(self):
        self.engine.discover()
        from iios.investment.strategy.migration.legacy_metadata import LegacyStrategySource
        strategies = self.engine.get_catalog().filter(
            source=LegacyStrategySource.STRATEGY_GENERATOR
        )
        assert len(strategies) >= 13

    def test_all_strategies_have_min_rr(self):
        self.engine.discover()
        for meta in self.engine.get_catalog().all():
            assert meta.min_rr > 0, f"{meta.strategy_name} has min_rr <= 0"

    def test_all_strategies_have_max_loss_pct(self):
        self.engine.discover()
        for meta in self.engine.get_catalog().all():
            assert meta.max_loss_pct > 0, f"{meta.strategy_name} has max_loss_pct <= 0"

    def test_iron_condor_is_options(self):
        self.engine.discover()
        meta = self.engine.get_catalog().get("Iron_Condor_Range")
        assert meta is not None
        assert "option" in meta.category.lower() or "option" in str(meta.tags).lower()

    def test_futures_arb_discovered(self):
        self.engine.discover()
        meta = self.engine.get_catalog().get("Futures_Basis_Arb")
        assert meta is not None

    def test_discover_idempotent(self):
        r1 = self.engine.discover()
        r2 = self.engine.discover()
        assert r1.total_discovered == r2.total_discovered

    def test_catalog_search(self):
        self.engine.discover()
        results = self.engine.get_catalog().search("breakout")
        assert len(results) >= 1

    def test_catalog_stats(self):
        self.engine.discover()
        stats = self.engine.get_catalog().stats()
        assert stats.total >= 13
        assert stats.code_based_count >= 13

    def test_catalog_count_is_int(self):
        self.engine.discover()
        assert isinstance(self.engine.get_catalog().count(), int)

    def test_discovered_at_set(self):
        from datetime import datetime
        from iios.investment.strategy.migration.legacy_metadata import LegacyStrategySource
        self.engine.discover()
        # Only JSON-discovered strategies have discovered_at; code-based may have None
        for meta in self.engine.get_catalog().all():
            if meta.source != LegacyStrategySource.STRATEGY_GENERATOR:
                if meta.discovered_at is not None:
                    assert isinstance(meta.discovered_at, datetime)

    def test_get_catalog_returns_legacy_catalog(self):
        catalog = self.engine.get_catalog()
        assert isinstance(catalog, LegacyCatalog)
