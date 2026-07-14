"""iios/investment/strategy/migration/strategy_migration_engine.py
Main facade for the strategy migration system.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_catalog import LegacyCatalog
from iios.investment.strategy.migration.legacy_discovery import (
    DiscoveryConfig,
    DiscoveryResult,
    LegacyDiscoveryEngine,
)
from iios.investment.strategy.migration.migration_audit import AuditEntry, MigrationAudit
from iios.investment.strategy.migration.migration_events import MigrationEventBus
from iios.investment.strategy.migration.migration_pipeline import (
    MigrationPipeline,
    PipelineConfig,
)
from iios.investment.strategy.migration.migration_report import MigrationReport
from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.migration_statistics import MigrationStatistics
from iios.investment.strategy.migration.migration_status import MigrationStatus
from iios.investment.strategy.migration.migration_summary import (
    MigrationSummary,
    MigrationSummaryBuilder,
)
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter
from iios.investment.strategy.migration.validation_report import ValidationReport
from iios.investment.strategy.migration.behavior_validator import BehaviorTestCase


class StrategyMigrationEngine:
    """
    Central facade for the Strategy Migration Framework.

    Coordinates discovery, validation, adaptation, verification, and reporting
    for migrating legacy strategies into the IIOS framework.

    Usage:
        engine = StrategyMigrationEngine()
        result = engine.discover()
        session = engine.migrate("Breakout_Volume")
        summary = engine.summary()
    """

    def __init__(
        self,
        config:      Optional[PipelineConfig]    = None,
        event_bus:   Optional[MigrationEventBus] = None,
        max_workers: int                         = 4,
    ) -> None:
        self._config     = config or PipelineConfig(max_workers=max_workers)
        self._event_bus  = event_bus or MigrationEventBus()
        self._discovery  = LegacyDiscoveryEngine()
        self._pipeline   = MigrationPipeline(
            config=self._config,
            event_bus=self._event_bus,
        )
        self._summary_builder = MigrationSummaryBuilder()
        self._lock            = threading.RLock()
        self._last_discovery: Optional[DiscoveryResult] = None

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover(self, config: Optional[DiscoveryConfig] = None) -> DiscoveryResult:
        """Scan all legacy sources and populate the catalog."""
        result = self._discovery.discover()
        with self._lock:
            self._last_discovery = result
        return result

    # ── Migration ─────────────────────────────────────────────────────────────

    def migrate(
        self,
        strategy_name: str,
        test_cases:    Optional[List[BehaviorTestCase]] = None,
    ) -> Optional[MigrationSession]:
        """
        Migrate a single strategy by name.
        Returns None if strategy not found in catalog.
        """
        metadata = self._discovery.get_catalog().get(strategy_name)
        if metadata is None:
            return None
        results = self._pipeline.run([metadata], test_cases=test_cases)
        return results[0] if results else None

    def migrate_all(
        self,
        approved_only: bool                          = False,
        test_cases:    Optional[List[BehaviorTestCase]] = None,
    ) -> List[MigrationSession]:
        """Migrate all discovered strategies."""
        catalog = self._discovery.get_catalog()
        metadatas = (
            [m for m in catalog.all() if m.is_approved]
            if approved_only
            else list(catalog.all())
        )
        return self._pipeline.run(metadatas, test_cases=test_cases)

    def migrate_batch(
        self,
        names:      List[str],
        test_cases: Optional[List[BehaviorTestCase]] = None,
    ) -> List[MigrationSession]:
        """Migrate a named subset of strategies."""
        catalog   = self._discovery.get_catalog()
        metadatas = [
            m for m in catalog.all()
            if m.strategy_name in names
        ]
        return self._pipeline.run(metadatas, test_cases=test_cases)

    # ── Rollback ──────────────────────────────────────────────────────────────

    def rollback(self, strategy_name: str) -> bool:
        """Roll back a migrated strategy."""
        return self._pipeline.rollback(strategy_name)

    # ── Status / session queries ──────────────────────────────────────────────

    def get_status(self, strategy_name: str) -> Optional[MigrationStatus]:
        session = self._pipeline.get_session(strategy_name)
        return session.status if session else None

    def get_session(self, strategy_name: str) -> Optional[MigrationSession]:
        return self._pipeline.get_session(strategy_name)

    def get_report(self, strategy_name: str) -> Optional[MigrationReport]:
        return self._pipeline.get_report(strategy_name)

    def get_adapter(self, strategy_name: str) -> Optional[LegacyStrategyAdapter]:
        return self._pipeline.adapter_registry().get_by_name(strategy_name)

    def compatibility_report(self, strategy_name: str) -> Optional[ValidationReport]:
        session = self._pipeline.get_session(strategy_name)
        return session.validation_report if session else None

    # ── Listing ───────────────────────────────────────────────────────────────

    def list_legacy_strategies(self) -> List[str]:
        return self._discovery.get_catalog().names()

    def migration_history(self, strategy_name: str) -> List[AuditEntry]:
        meta = self._discovery.get_catalog().get(strategy_name)
        if meta is None:
            return []
        return self._pipeline.audit().get(meta.strategy_id)

    # ── Reporting ─────────────────────────────────────────────────────────────

    def summary(self) -> MigrationSummary:
        """Build a summary over all sessions and reports."""
        all_sessions = []
        all_reports  = []
        catalog      = self._discovery.get_catalog()
        for name in catalog.names():
            session = self._pipeline.get_session(name)
            if session:
                all_sessions.append(session)
                report = self._pipeline.get_report(name)
                if report:
                    all_reports.append(report)
        return self._summary_builder.build(all_sessions, all_reports)

    def stats(self) -> Dict[str, Any]:
        return self._pipeline.stats().summary()

    def catalog(self) -> LegacyCatalog:
        return self._discovery.get_catalog()

    @property
    def event_bus(self) -> MigrationEventBus:
        return self._event_bus
