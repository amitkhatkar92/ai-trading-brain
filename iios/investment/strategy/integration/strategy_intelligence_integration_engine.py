"""iios/investment/strategy/integration/strategy_intelligence_integration_engine.py

Strategy Intelligence Integration & Validation Engine — main facade.

This engine is the SINGLE orchestration, validation, QA, and publishing layer
for all Strategy Intelligence.  It:
  - Integrates outputs from every Strategy Intelligence Engine
  - Validates consistency
  - Detects and resolves conflicting intelligence
  - Measures completeness and confidence
  - Publishes one canonical StrategySnapshot

Downstream components (Decision Layer, Portfolio AI, Execution Layer, IIOS)
MUST consume ONLY the StrategySnapshot produced here.

INVARIANT: this engine NEVER independently calculates strategy evaluation,
opportunities, portfolio state, risk, learning, migration, or debate results.
It integrates pre-computed intelligence from those engines.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional

from iios.common.async_exec.async_execution_manager import get_execution_manager as _get_exec_manager
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext, bind_error_context

from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    make_update,
)
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)
from iios.investment.strategy.integration.consistency_validator import ConsistencyValidator
from iios.investment.strategy.integration.conflict_engine import ConflictEngine
from iios.investment.strategy.integration.strategy_quality import QualityFramework, QualityReport
from iios.investment.strategy.integration.strategy_confidence import ConfidenceCalculator
from iios.investment.strategy.integration.strategy_summary import build_strategy_summary
from iios.investment.strategy.integration.strategy_snapshot import (
    StrategySnapshot,
    build_snapshot,
)
from iios.investment.strategy.integration.snapshot_cache import SnapshotCache
from iios.investment.strategy.integration.strategy_statistics import StrategyStatisticsTracker
from iios.investment.strategy.integration.quality_history import QualityHistory
from iios.investment.strategy.integration.quality_statistics import QualityStatisticsTracker
from iios.investment.strategy.integration.health_monitor import HealthMonitor, HealthMonitorConfig
from iios.investment.strategy.integration.validation_report import ValidationReport
from iios.investment.strategy.integration.conflict_classifier import Conflict
from iios.investment.strategy.integration.integration_events import (
    IntegrationEventBus,
    IntegrationEvent,
)
from iios.investment.strategy.integration.integration_constants import (
    IntegrationEventType,
    IntegrationStatus,
)

from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

_log = get_logger(__name__, engine_id="iios:strategy:intelligence:integration")
_audit = get_audit_logger(
    __name__,
    engine_id = "iios:strategy:intelligence:integration",
    component = "StrategyIntelligenceIntegrationEngine",
)


class StrategyIntelligenceIntegrationEngine(LifecycleAwareMixin):
    """
    Single orchestration and publishing facade for all Strategy Intelligence.

    Usage (async):
        engine = StrategyIntelligenceIntegrationEngine()
        await engine.submit_update(update)
        snapshot = await engine.get_snapshot("STRAT-001")

    Usage (sync / non-async context):
        engine = StrategyIntelligenceIntegrationEngine()
        engine.submit_update_sync(update)
        snapshot = engine.get_snapshot_sync("STRAT-001")
    """

    VERSION   = "1.0.0"
    SYSTEM_ID = "iios:strategy:intelligence:integration"

    def __init__(
        self,
        aggregator:           Optional[StrategyIntelligenceAggregator] = None,
        consistency_validator: Optional[ConsistencyValidator]           = None,
        conflict_engine:      Optional[ConflictEngine]                  = None,
        quality_framework:    Optional[QualityFramework]                = None,
        confidence_calculator: Optional[ConfidenceCalculator]          = None,
        snapshot_cache:       Optional[SnapshotCache]                   = None,
        stats_tracker:        Optional[StrategyStatisticsTracker]       = None,
        quality_history:      Optional[QualityHistory]                  = None,
        quality_stats:        Optional[QualityStatisticsTracker]        = None,
        event_bus:            Optional[IntegrationEventBus]             = None,
        health_monitor:       Optional[HealthMonitor]                   = None,
        health_config:        Optional[HealthMonitorConfig]             = None,
    ) -> None:
        self._aggregator       = aggregator      or StrategyIntelligenceAggregator()
        self._validator        = consistency_validator or ConsistencyValidator(
            aggregation_engine=self._aggregator._engine,
        )
        self._conflict_engine  = conflict_engine or ConflictEngine()
        self._quality          = quality_framework or QualityFramework(
            aggregation_engine=self._aggregator._engine,
        )
        self._confidence       = confidence_calculator or ConfidenceCalculator()
        self._cache            = snapshot_cache or SnapshotCache()
        self._stats            = stats_tracker  or StrategyStatisticsTracker()
        self._q_history        = quality_history or QualityHistory()
        self._q_stats          = quality_stats   or QualityStatisticsTracker()
        self._event_bus        = event_bus       or IntegrationEventBus()
        self._status           = IntegrationStatus.INITIALIZING
        self._health: HealthMonitor = health_monitor or HealthMonitor(
            aggregator=self._aggregator,
            config=health_config or HealthMonitorConfig(),
        )
        # Background thread coordination
        self._health_loop: "asyncio.AbstractEventLoop | None" = None
        self._health_loop_lock = threading.Lock()

    # ================================================================
    # Lifecycle
    # ================================================================

    def _on_start(self) -> None:
        """Start the background health monitor in a persistent daemon thread."""
        started_event = threading.Event()

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            with self._health_loop_lock:
                self._health_loop = loop
            started_event.set()
            try:
                loop.run_until_complete(self._health.start())
                loop.run_forever()
            finally:
                # Clean up pending tasks before closing
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()
                with self._health_loop_lock:
                    self._health_loop = None

        t = threading.Thread(target=_run, daemon=True, name="strategy-health-monitor")
        t.start()
        started_event.wait(timeout=5.0)
        self._set_status(IntegrationStatus.HEALTHY)
        self._event_bus.emit_simple(
            IntegrationEventType.ENGINE_STARTED,
            strategy_id="system",
            payload={"status": IntegrationStatus.HEALTHY.value},
            source="StrategyIntelligenceIntegrationEngine",
        )
        _log.info("StrategyIntelligenceIntegrationEngine started (health monitor in background).")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION,
            health_monitor="background_daemon_started",
        )

    def _on_stop(self) -> None:
        """Stop the health monitor loop gracefully."""
        with self._health_loop_lock:
            loop = self._health_loop

        if loop is not None and loop.is_running():
            async def _stop_and_exit() -> None:
                try:
                    await self._health.stop()
                except Exception as exc:
                    _log.warning("Health monitor failed to stop cleanly.", exc=exc)
                loop.stop()

            asyncio.run_coroutine_threadsafe(_stop_and_exit(), loop)
        self._set_status(IntegrationStatus.FAILED)
        self._event_bus.emit_simple(
            IntegrationEventType.ENGINE_STOPPED,
            strategy_id="system",
            payload={"status": IntegrationStatus.FAILED.value},
            source="StrategyIntelligenceIntegrationEngine",
        )
        _log.info("StrategyIntelligenceIntegrationEngine stopped.")
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION,
            health_monitor="background_daemon_stopped",
        )

    def _set_status(self, s: IntegrationStatus) -> None:
        self._status = s

    # ================================================================
    # Async core API
    # ================================================================

    async def submit_update(self, update: IntelligenceUpdate) -> None:
        """
        Accept a new intelligence update from any source engine.
        Invalidates the cached snapshot for the strategy so the next
        get_snapshot() call rebuilds it.
        """
        self._aggregator.submit(update)
        self._stats.record_update(update)
        self._health.record_seen(update.source)
        self._cache.invalidate(update.strategy_id)

        self._event_bus.emit_simple(
            IntegrationEventType.UPDATE_RECEIVED,
            strategy_id=update.strategy_id,
            payload={"source": update.source.value, "update_id": update.update_id},
            source=update.source.value,
        )

    async def get_snapshot(self, strategy_id: str) -> Optional[StrategySnapshot]:
        """
        Return the latest canonical StrategySnapshot for a strategy.
        Rebuilds from aggregated intelligence if the cache was invalidated.
        """
        cached = self._cache.get(strategy_id)
        if cached is not None:
            return cached

        state = self._aggregator.state(strategy_id)
        if state is None:
            return None

        return await self._build_and_cache(strategy_id, state)

    async def get_snapshot_batch(
        self,
        strategy_ids: List[str],
    ) -> Dict[str, Optional[StrategySnapshot]]:
        coros = [self.get_snapshot(sid) for sid in strategy_ids]
        results = await asyncio.gather(*coros)
        return dict(zip(strategy_ids, results))

    # ================================================================
    # Sync wrappers
    # ================================================================

    def submit_update_sync(self, update: IntelligenceUpdate) -> None:
        with bind_error_context(ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "submit_update_sync",
            stage     = "strategy_intelligence_integration",
        )):
            try:
                _get_exec_manager().execute_sync(
                    self.submit_update,
                    update,
                    operation = "strategy.submit_update_sync",
                    engine_id = self.SYSTEM_ID,
                )
            except Exception as exc:
                _get_err_mgr().report_failure(self.SYSTEM_ID, exc)
                raise

    def get_snapshot_sync(self, strategy_id: str) -> Optional[StrategySnapshot]:
        with bind_error_context(ErrorContext(
            engine_id = self.SYSTEM_ID,
            operation = "get_snapshot_sync",
            stage     = "strategy_intelligence_integration",
        )):
            try:
                return _get_exec_manager().execute_sync(
                    self.get_snapshot,
                    strategy_id,
                    operation = "strategy.get_snapshot_sync",
                    engine_id = self.SYSTEM_ID,
                )
            except Exception as exc:
                _get_err_mgr().report_failure(self.SYSTEM_ID, exc)
                raise

    # ================================================================
    # Internal snapshot builder
    # ================================================================

    async def _build_and_cache(
        self,
        strategy_id: str,
        state,
    ) -> StrategySnapshot:
        # 1 — validate consistency
        self._status = IntegrationStatus.VALIDATING
        validation: ValidationReport = self._validator.validate(state)

        # 2 — detect / resolve conflicts
        resolved_conflicts, unresolved_conflicts = self._conflict_engine.process(state)
        all_active: List[Conflict] = (
            self._conflict_engine.active_conflicts(strategy_id)
        )

        # 3 — compute quality, confidence, freshness
        quality: QualityReport = self._quality.compute(
            strategy_id, state, all_active
        )
        self._q_history.record(quality)
        self._q_stats.record(quality)

        freshness = self._aggregator._engine.freshness_score(strategy_id)
        completeness = self._aggregator.completeness(strategy_id)

        conf_components = self._confidence.compute(
            state=state,
            active_conflicts=all_active,
            completeness=completeness,
            freshness_score=freshness,
        )

        # 4 — build summary
        intelligence_score = (
            quality.overall_score * 0.60
            + conf_components.final_confidence * 0.40
        )
        summary = build_strategy_summary(
            state=state,
            overall_score=intelligence_score,
            completeness=completeness,
            active_conflicts=len(all_active),
        )

        # 5 — build snapshot
        snapshot = build_snapshot(
            state=state,
            summary=summary,
            validation_report=validation,
            active_conflicts=all_active,
            intelligence_score=intelligence_score,
            quality_score=quality.overall_score,
            confidence_score=conf_components.final_confidence,
            freshness_score=freshness,
        )

        # 6 — cache, stats, events
        self._cache.set(snapshot)
        self._stats.record_snapshot(strategy_id, len(all_active))

        self._status = IntegrationStatus.PUBLISHING
        self._event_bus.emit_simple(
            IntegrationEventType.SNAPSHOT_PUBLISHED,
            strategy_id=strategy_id,
            payload={
                "snapshot_id":        snapshot.snapshot_id,
                "intelligence_score": snapshot.intelligence_score,
                "quality_score":      snapshot.quality_score,
                "status":             snapshot.status.value,
            },
            source="StrategyIntelligenceIntegrationEngine",
        )
        self._status = IntegrationStatus.HEALTHY
        return snapshot

    # ================================================================
    # Query API (Task 8)
    # ================================================================

    def get_current_snapshot(self, strategy_id: str) -> Optional[StrategySnapshot]:
        return self._cache.get(strategy_id)

    def get_quality_report(self, strategy_id: str) -> Optional[QualityReport]:
        rpts = self._q_history.for_strategy(strategy_id)
        return rpts[-1] if rpts else None

    def get_active_conflicts(self, strategy_id: str) -> List[Conflict]:
        return self._conflict_engine.active_conflicts(strategy_id)

    def get_confidence_score(self, strategy_id: str) -> Optional[float]:
        snap = self._cache.get(strategy_id)
        return snap.confidence_score if snap else None

    def get_validation_report(self, strategy_id: str) -> Optional[ValidationReport]:
        snap = self._cache.get(strategy_id)
        return snap.validation_report if snap else None

    def get_engine_health(self):
        return self._health.get_health()

    def known_strategies(self) -> List[str]:
        return self._aggregator.known_strategies()

    def stats(self) -> Dict[str, Any]:
        return {
            "status":          self._status.value,
            "known_strategies": len(self.known_strategies()),
            "cache_size":      self._cache.size(),
            "quality_stats":   self._q_stats.summary().to_dict(),
            "aggregator_stats": self._aggregator.stats(),
            "health":          self._health.snapshot_dict(),
        }

    # ================================================================
    # Properties
    # ================================================================

    @property
    def event_bus(self) -> IntegrationEventBus:
        return self._event_bus

    @property
    def aggregator(self) -> StrategyIntelligenceAggregator:
        return self._aggregator

    @property
    def status(self) -> IntegrationStatus:
        return self._status
