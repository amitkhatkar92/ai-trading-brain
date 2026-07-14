"""iios/investment/strategy/migration/migration_pipeline.py
Multi-strategy migration orchestrator.
"""
from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.migration_status import (
    MigrationStatus,
    RollbackReason,
)
from iios.investment.strategy.migration.migration_steps import MigrationStepExecutor, StepResult
from iios.investment.strategy.migration.migration_statistics import MigrationStatistics
from iios.investment.strategy.migration.migration_audit import MigrationAudit
from iios.investment.strategy.migration.migration_events import MigrationEventBus
from iios.investment.strategy.migration.adapter_factory import AdapterFactory
from iios.investment.strategy.migration.adapter_registry import AdapterRegistry
from iios.investment.strategy.migration.migration_validator import MigrationValidator
from iios.investment.strategy.migration.behavior_validator import (
    BehaviorValidator,
    BehaviorTestCase,
)
from iios.investment.strategy.migration.migration_report import (
    MigrationReport,
    build_migration_report,
)
from iios.investment.strategy.migration.migration_events import MigrationEventType


@dataclass
class PipelineConfig:
    """Configuration for the migration pipeline."""
    max_workers:                  int   = 4
    auto_approve:                 bool  = False
    stop_on_first_failure:        bool  = False
    require_behavior_equivalence: bool  = True
    equivalence_tolerance:        float = 1e-6
    max_warning_count:            int   = 10    # above this → REVIEW instead of APPROVE


class MigrationPipeline:
    """
    Orchestrates multi-strategy migration with optional parallelism.

    Pipeline per strategy:
    1. DISCOVERY      — locate metadata
    2. VALIDATION     — compatibility checks
    3. PREPARATION    — create adapter
    4. MIGRATION      — register adapter
    5. VERIFICATION   — equivalence check
    6. APPROVAL       — auto or pending
    """

    def __init__(
        self,
        config:   Optional[PipelineConfig] = None,
        event_bus: Optional[MigrationEventBus] = None,
    ) -> None:
        self._config         = config or PipelineConfig()
        self._event_bus      = event_bus or MigrationEventBus()
        self._adapter_factory = AdapterFactory()
        self._adapter_registry = AdapterRegistry()
        self._validator      = MigrationValidator()
        self._beh_validator  = BehaviorValidator()
        self._step_executor  = MigrationStepExecutor()
        self._stats          = MigrationStatistics()
        self._audit          = MigrationAudit()
        self._sessions:      Dict[str, MigrationSession] = {}
        self._lock           = threading.RLock()

    def run(
        self,
        metadatas:  List[LegacyStrategyMetadata],
        test_cases: Optional[List[BehaviorTestCase]] = None,
    ) -> List[MigrationSession]:
        """Migrate all strategies in the list (optionally in parallel)."""
        if not metadatas:
            return []

        results: List[MigrationSession] = []
        if self._config.max_workers <= 1:
            for meta in metadatas:
                session = self.run_single(meta, test_cases)
                results.append(session)
                if self._config.stop_on_first_failure and session.status == MigrationStatus.FAILED:
                    break
        else:
            with ThreadPoolExecutor(max_workers=self._config.max_workers) as pool:
                futures = {
                    pool.submit(self.run_single, meta, test_cases): meta
                    for meta in metadatas
                }
                for future in as_completed(futures):
                    try:
                        session = future.result()
                        results.append(session)
                        if (self._config.stop_on_first_failure
                                and session.status == MigrationStatus.FAILED):
                            pool.shutdown(wait=False, cancel_futures=True)
                            break
                    except Exception as exc:
                        meta = futures[future]
                        # Build a failed session
                        failed = MigrationSession.create(meta)
                        failed.mark_failed(str(exc))
                        results.append(failed)

        return results

    def run_single(
        self,
        metadata:   LegacyStrategyMetadata,
        test_cases: Optional[List[BehaviorTestCase]] = None,
    ) -> MigrationSession:
        """Run the full migration pipeline for one strategy."""
        session = MigrationSession.create(metadata)
        start   = time.monotonic()

        with self._lock:
            self._sessions[metadata.strategy_name] = session
        self._stats.record_attempt()

        self._audit.record_event(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            event_type="migration_started",
            after_state={"status": MigrationStatus.NOT_STARTED.value},
            session_id=session.session_id,
        )

        try:
            # ── Step 1: DISCOVERY ─────────────────────────────────────────────
            session.advance(MigrationStatus.DISCOVERY)
            disc_step = self._step_executor.execute_discovery(
                metadata.strategy_id, metadata.strategy_name, metadata_found=True
            )
            session.add_step(disc_step)
            session.save_checkpoint()

            # ── Step 2: VALIDATION ────────────────────────────────────────────
            session.advance(MigrationStatus.VALIDATION)
            val_report = self._validator.validate_metadata(metadata)
            session.validation_report = val_report

            val_step = self._step_executor.execute_validation(
                metadata.strategy_id, metadata.strategy_name,
                validation_passed=val_report.is_migration_approved,
                error_count=val_report.error_count,
                warning_count=val_report.warning_count,
            )
            session.add_step(val_step)

            if not val_report.is_migration_approved:
                session.mark_failed(
                    f"Validation blocked: {val_report.error_count} errors"
                )
                self._stats.record_status(MigrationStatus.FAILED)
                return session

            # ── Step 3: PREPARATION ───────────────────────────────────────────
            session.advance(MigrationStatus.PREPARATION)
            adapter  = self._adapter_factory.create(metadata)
            session.adapter = adapter

            # Validate adapter
            adapter_check = self._validator.validate_adapter(adapter)
            if not adapter_check.is_valid:
                session.mark_failed(
                    f"Adapter validation failed: {'; '.join(adapter_check.issues)}"
                )
                self._stats.record_status(MigrationStatus.FAILED)
                return session

            prep_step = self._step_executor.execute_preparation(
                metadata.strategy_id, metadata.strategy_name,
                adapter_id=adapter.strategy_id,
                adaptation_mode=adapter.adaptation_mode.value,
            )
            session.add_step(prep_step)
            session.save_checkpoint()

            # ── Step 4: MIGRATION ─────────────────────────────────────────────
            session.advance(MigrationStatus.MIGRATING)
            self._adapter_registry.register(adapter)

            mig_step = self._step_executor.execute_migration(
                metadata.strategy_id, metadata.strategy_name,
                registered=True, registry_name="AdapterRegistry",
            )
            session.add_step(mig_step)

            # ── Step 5: VERIFICATION ──────────────────────────────────────────
            session.advance(MigrationStatus.VERIFICATION)
            behavior_report = self._beh_validator.validate(
                metadata, adapter, test_cases or []
            )
            equiv_ok   = behavior_report.is_equivalent
            fail_count = behavior_report.failed

            ver_step = self._step_executor.execute_verification(
                metadata.strategy_id, metadata.strategy_name,
                equivalence_passed=equiv_ok,
                test_count=behavior_report.test_case_count,
                fail_count=fail_count,
            )
            session.add_step(ver_step)

            if self._config.require_behavior_equivalence and not equiv_ok and test_cases:
                session.mark_failed(
                    f"Behavior equivalence check failed ({fail_count} failures)"
                )
                self._stats.record_status(MigrationStatus.FAILED)
                return session

            # ── Step 6: APPROVAL ──────────────────────────────────────────────
            auto_approve = (
                self._config.auto_approve
                and val_report.warning_count <= self._config.max_warning_count
                and equiv_ok
            )
            if auto_approve:
                session.advance(MigrationStatus.COMPLETED, note="auto-approved")
            else:
                session.advance(MigrationStatus.APPROVAL_PENDING, note="awaiting approval")

            app_step = self._step_executor.execute_approval(
                metadata.strategy_id, metadata.strategy_name,
                auto_approved=auto_approve,
            )
            session.add_step(app_step)

            final_status = (
                MigrationStatus.COMPLETED
                if auto_approve
                else MigrationStatus.APPROVAL_PENDING
            )
            self._stats.record_status(final_status)
            self._stats.record_duration((time.monotonic() - start) * 1000)

            self._audit.record_event(
                strategy_id=metadata.strategy_id,
                strategy_name=metadata.strategy_name,
                event_type="migration_completed",
                before_state={"status": MigrationStatus.MIGRATING.value},
                after_state={"status": final_status.value},
                session_id=session.session_id,
            )

        except Exception as exc:
            session.mark_failed(f"Unexpected error: {exc}")
            self._stats.record_status(MigrationStatus.FAILED)

        return session

    def rollback(
        self,
        strategy_name: str,
        reason: RollbackReason = RollbackReason.MANUAL_REQUEST,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(strategy_name)
        if not session or not session.has_checkpoint():
            return False
        success = session.rollback(reason=reason)
        if success:
            self._adapter_registry.remove(session.strategy_id)
            self._audit.record_event(
                strategy_id=session.strategy_id,
                strategy_name=strategy_name,
                event_type="rollback",
                after_state={"reason": reason.value},
                session_id=session.session_id,
            )
        return success

    def get_session(self, strategy_name: str) -> Optional[MigrationSession]:
        with self._lock:
            return self._sessions.get(strategy_name)

    def get_report(self, strategy_name: str) -> Optional[MigrationReport]:
        session = self.get_session(strategy_name)
        if not session:
            return None
        return build_migration_report(
            strategy_id=session.strategy_id,
            strategy_name=strategy_name,
            migration_status=session.status,
            validation_report=session.validation_report,
            step_results=session.step_results,
        )

    def stats(self) -> MigrationStatistics:
        return self._stats

    def audit(self) -> MigrationAudit:
        return self._audit

    def adapter_registry(self) -> AdapterRegistry:
        return self._adapter_registry
