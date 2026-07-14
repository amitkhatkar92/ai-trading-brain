"""Tests for the StrategyMigrationEngine facade."""
import pytest

from iios.investment.strategy.migration.strategy_migration_engine import (
    StrategyMigrationEngine,
)
from iios.investment.strategy.migration.migration_pipeline import PipelineConfig
from iios.investment.strategy.migration.migration_status import MigrationStatus
from iios.investment.strategy.migration.migration_summary import MigrationSummary
from iios.investment.strategy.migration.legacy_catalog import LegacyCatalog


class TestStrategyMigrationEngine:
    def setup_method(self):
        self.engine = StrategyMigrationEngine(
            config=PipelineConfig(
                auto_approve=True,
                require_behavior_equivalence=False,
            )
        )
        # Discover first so catalog is populated
        self.engine.discover()

    def test_discover_returns_result(self):
        result = self.engine.discover()
        assert result.total_discovered >= 13

    def test_list_legacy_strategies(self):
        names = self.engine.list_legacy_strategies()
        assert "Breakout_Volume" in names

    def test_migrate_single(self):
        session = self.engine.migrate("Breakout_Volume")
        assert session is not None
        assert session.status in (
            MigrationStatus.COMPLETED,
            MigrationStatus.APPROVAL_PENDING,
            MigrationStatus.FAILED,
        )

    def test_migrate_unknown_returns_none(self):
        session = self.engine.migrate("NonExistent_Strategy_XYZ")
        assert session is None

    def test_get_status(self):
        self.engine.migrate("Momentum_Retest")
        status = self.engine.get_status("Momentum_Retest")
        assert status is not None
        assert isinstance(status, MigrationStatus)

    def test_get_session(self):
        self.engine.migrate("Trend_Pullback")
        session = self.engine.get_session("Trend_Pullback")
        assert session is not None

    def test_get_report(self):
        self.engine.migrate("Mean_Reversion")
        report = self.engine.get_report("Mean_Reversion")
        assert report is not None

    def test_get_adapter(self):
        self.engine.migrate("Equity_Breakout")
        adapter = self.engine.get_adapter("Equity_Breakout")
        # adapter exists if migration succeeded
        status = self.engine.get_status("Equity_Breakout")
        if status == MigrationStatus.COMPLETED:
            assert adapter is not None

    def test_migrate_batch(self):
        sessions = self.engine.migrate_batch(["Breakout_Volume", "Momentum_Retest"])
        assert len(sessions) == 2

    def test_summary_after_migrations(self):
        self.engine.migrate("Iron_Condor_Range")
        summary = self.engine.summary()
        assert isinstance(summary, MigrationSummary)
        assert summary.total_strategies >= 1

    def test_stats_dict(self):
        self.engine.migrate("Short_Straddle_IV_Spike")
        stats = self.engine.stats()
        assert isinstance(stats, dict)
        assert "total_attempts" in stats

    def test_catalog_returns_legacy_catalog(self):
        catalog = self.engine.catalog()
        assert isinstance(catalog, LegacyCatalog)

    def test_event_bus_accessible(self):
        bus = self.engine.event_bus
        assert bus is not None

    def test_compatibility_report_after_migration(self):
        self.engine.migrate("Hedging_Model")
        report = self.engine.compatibility_report("Hedging_Model")
        if report is not None:
            assert "strategy_id" in report.to_dict()

    def test_migrate_all_populates_sessions(self):
        sessions = self.engine.migrate_all()
        assert len(sessions) >= 13

    def test_migration_history(self):
        self.engine.migrate("ETF_NAV_Arb")
        history = self.engine.migration_history("ETF_NAV_Arb")
        assert isinstance(history, list)

    def test_rollback(self):
        self.engine.migrate("Long_Straddle_Pre_Event")
        result = self.engine.rollback("Long_Straddle_Pre_Event")
        assert isinstance(result, bool)

    def test_summary_to_dict(self):
        self.engine.migrate("Equity_Retest")
        d = self.engine.summary().to_dict()
        assert "total_strategies" in d
        assert "success_rate" in d

    def test_multiple_discoveries_idempotent(self):
        r1 = self.engine.discover()
        r2 = self.engine.discover()
        assert r1.total_discovered == r2.total_discovered

    def test_migrate_batch_empty(self):
        sessions = self.engine.migrate_batch([])
        assert sessions == []

    def test_get_status_none_for_unmigrated(self):
        status = self.engine.get_status("Never_Migrated_Strategy")
        assert status is None
