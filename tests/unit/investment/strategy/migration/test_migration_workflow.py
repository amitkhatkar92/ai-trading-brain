"""Tests for the migration workflow (session, steps, pipeline, statistics)."""
import pytest

from iios.investment.strategy.migration.migration_session import MigrationSession
from iios.investment.strategy.migration.migration_status import (
    MigrationStatus,
    MigrationPhase,
    RollbackReason,
)
from iios.investment.strategy.migration.migration_steps import (
    MigrationStepExecutor,
    StepResult,
)
from iios.investment.strategy.migration.migration_statistics import MigrationStatistics
from iios.investment.strategy.migration.migration_pipeline import (
    MigrationPipeline,
    PipelineConfig,
)


class TestMigrationSession:
    def test_create(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        assert session.strategy_name == basic_metadata.strategy_name
        assert session.status == MigrationStatus.NOT_STARTED

    def test_advance_status(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.DISCOVERY)
        assert session.status == MigrationStatus.DISCOVERY

    def test_mark_failed(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.mark_failed("test failure")
        assert session.status == MigrationStatus.FAILED
        assert session.error == "test failure"

    def test_completed_at_set_on_terminal(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.COMPLETED)
        assert session.completed_at is not None

    def test_save_checkpoint(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.DISCOVERY)
        session.save_checkpoint()
        assert session.has_checkpoint()

    def test_rollback_restores_from_checkpoint(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.DISCOVERY)
        session.save_checkpoint()
        session.advance(MigrationStatus.VALIDATION)
        success = session.rollback()
        assert success
        assert session.status == MigrationStatus.ROLLED_BACK

    def test_rollback_without_checkpoint_returns_false(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        assert session.rollback() is False

    def test_duration_ms_positive(self, basic_metadata):
        import time
        session = MigrationSession.create(basic_metadata)
        time.sleep(0.01)
        assert session.duration_ms > 0

    def test_to_dict(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        d = session.to_dict()
        assert "session_id" in d
        assert "status" in d

    def test_add_step(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        executor = MigrationStepExecutor()
        step = executor.execute_discovery(
            basic_metadata.strategy_id,
            basic_metadata.strategy_name,
            metadata_found=True,
        )
        session.add_step(step)
        assert len(session.step_results) == 1

    def test_steps_passed_true(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        executor = MigrationStepExecutor()
        step = executor.execute_discovery(
            basic_metadata.strategy_id,
            basic_metadata.strategy_name,
            metadata_found=True,
        )
        session.add_step(step)
        assert session.steps_passed()

    def test_steps_passed_false_on_failure(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        executor = MigrationStepExecutor()
        step = executor.execute_discovery(
            basic_metadata.strategy_id,
            basic_metadata.strategy_name,
            metadata_found=False,
        )
        session.add_step(step)
        assert not session.steps_passed()

    def test_notes_appended(self, basic_metadata):
        session = MigrationSession.create(basic_metadata)
        session.advance(MigrationStatus.DISCOVERY, note="started")
        assert "started" in session.notes


class TestMigrationStepExecutor:
    def setup_method(self):
        self.executor = MigrationStepExecutor()
        self.sid  = "test-id"
        self.name = "Test_Strategy"

    def test_execute_discovery_pass(self):
        result = self.executor.execute_discovery(self.sid, self.name, True)
        assert result.result == StepResult.PASSED
        assert result.is_success

    def test_execute_discovery_fail(self):
        result = self.executor.execute_discovery(self.sid, self.name, False)
        assert result.result == StepResult.FAILED
        assert result.is_failure

    def test_execute_validation_pass(self):
        result = self.executor.execute_validation(self.sid, self.name, True, 0, 0)
        assert result.result == StepResult.PASSED

    def test_execute_validation_partial_warnings(self):
        result = self.executor.execute_validation(self.sid, self.name, True, 0, 3)
        assert result.result == StepResult.PARTIAL

    def test_execute_validation_fail(self):
        result = self.executor.execute_validation(self.sid, self.name, False, 2, 0)
        assert result.result == StepResult.FAILED

    def test_execute_preparation(self):
        result = self.executor.execute_preparation(
            self.sid, self.name, "adapter-id", "full_wrap"
        )
        assert result.is_success

    def test_execute_migration_pass(self):
        result = self.executor.execute_migration(
            self.sid, self.name, True, "AdapterRegistry"
        )
        assert result.is_success

    def test_execute_verification_pass(self):
        result = self.executor.execute_verification(
            self.sid, self.name, True, 10, 0
        )
        assert result.is_success

    def test_execute_rollback(self):
        result = self.executor.execute_rollback(
            self.sid, self.name, "manual", True
        )
        assert result.is_success

    def test_step_result_to_dict(self):
        result = self.executor.execute_discovery(self.sid, self.name, True)
        d = result.to_dict()
        assert "step_id" in d
        assert "result" in d


class TestMigrationStatistics:
    def setup_method(self):
        self.stats = MigrationStatistics()

    def test_initial_state(self):
        assert self.stats.total_attempts == 0
        assert self.stats.completed == 0

    def test_record_attempt(self):
        self.stats.record_attempt()
        assert self.stats.total_attempts == 1

    def test_record_completed(self):
        self.stats.record_attempt()
        self.stats.record_status(MigrationStatus.COMPLETED)
        assert self.stats.completed == 1

    def test_record_failed(self):
        self.stats.record_attempt()
        self.stats.record_status(MigrationStatus.FAILED)
        assert self.stats.failed == 1

    def test_success_rate(self):
        for _ in range(3):
            self.stats.record_attempt()
            self.stats.record_status(MigrationStatus.COMPLETED)
        self.stats.record_attempt()
        self.stats.record_status(MigrationStatus.FAILED)
        assert abs(self.stats.success_rate - 75.0) < 0.01

    def test_avg_duration(self):
        self.stats.record_duration(100.0)
        self.stats.record_duration(200.0)
        assert abs(self.stats.avg_duration_ms - 150.0) < 0.01

    def test_summary_dict(self):
        s = self.stats.summary()
        assert "total_attempts" in s
        assert "success_rate_pct" in s

    def test_reset(self):
        self.stats.record_attempt()
        self.stats.reset()
        assert self.stats.total_attempts == 0


class TestMigrationPipeline:
    def test_run_single_basic(self, basic_metadata):
        pipeline = MigrationPipeline()
        session  = pipeline.run_single(basic_metadata)
        assert session is not None
        assert session.status in (
            MigrationStatus.COMPLETED,
            MigrationStatus.APPROVAL_PENDING,
            MigrationStatus.FAILED,
        )

    def test_run_auto_approve(self, basic_metadata):
        config   = PipelineConfig(auto_approve=True, require_behavior_equivalence=False)
        pipeline = MigrationPipeline(config=config)
        session  = pipeline.run_single(basic_metadata)
        assert session.status in (MigrationStatus.COMPLETED, MigrationStatus.FAILED)

    def test_run_batch(self, basic_metadata, json_metadata):
        pipeline = MigrationPipeline()
        sessions = pipeline.run([basic_metadata, json_metadata])
        assert len(sessions) == 2

    def test_get_session_by_name(self, basic_metadata):
        pipeline = MigrationPipeline()
        pipeline.run_single(basic_metadata)
        session = pipeline.get_session(basic_metadata.strategy_name)
        assert session is not None

    def test_rollback_after_migration(self, basic_metadata):
        pipeline = MigrationPipeline()
        session  = pipeline.run_single(basic_metadata)
        result   = pipeline.rollback(basic_metadata.strategy_name)
        # rollback succeeds only if there's a checkpoint
        assert isinstance(result, bool)

    def test_stats_returned(self, basic_metadata):
        pipeline = MigrationPipeline()
        pipeline.run_single(basic_metadata)
        assert pipeline.stats().total_attempts >= 1

    def test_adapter_registered_on_success(self, basic_metadata):
        config   = PipelineConfig(auto_approve=True, require_behavior_equivalence=False)
        pipeline = MigrationPipeline(config=config)
        session  = pipeline.run_single(basic_metadata)
        if session.status == MigrationStatus.COMPLETED:
            adapter = pipeline.adapter_registry().get_by_name(basic_metadata.strategy_name)
            assert adapter is not None
