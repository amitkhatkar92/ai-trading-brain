"""
tests/unit/workflow/test_workflow_snapshot_m5.py
-------------------------------------------------
Comprehensive tests for C16 M5: Workflow Snapshot.

Coverage target: 95%+
"""
import threading
import uuid

import pytest

from iios.workflow.snapshot import (
    # Constants
    ExecutionStatus,
    GovernanceDecision,
    LifecycleState,
    SnapshotEventType,
    SnapshotStatus,
    WorkflowHealthStatus,
    # Exceptions
    WorkflowSnapshotBuildError,
    WorkflowSnapshotNotFoundError,
    WorkflowSnapshotRegistryError,
    WorkflowSnapshotValidationError,
    # Domain objects
    SnapshotValidationResult,
    WorkflowSnapshot,
    WorkflowSnapshotBundle,
    WorkflowSnapshotEvent,
    WorkflowSnapshotMetadata,
    WorkflowSnapshotStatisticsReport,
    # Services
    WorkflowSnapshotBuilder,
    WorkflowSnapshotCache,
    WorkflowSnapshotEventBus,
    WorkflowSnapshotFactory,
    WorkflowSnapshotHistory,
    WorkflowSnapshotRegistry,
    WorkflowSnapshotStatistics,
    WorkflowSnapshotStore,
    WorkflowSnapshotValidation,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _snap(
    workflow_id:  str              = "wf-test",
    workflow_name: str             = "Test Workflow",
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    governance_decision: GovernanceDecision = GovernanceDecision.APPROVED,
) -> WorkflowSnapshot:
    return WorkflowSnapshotBuilder().build(
        workflow_id         = workflow_id,
        workflow_name       = workflow_name,
        execution_status    = execution_status,
        governance_decision = governance_decision,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_snapshot_status_values(self):
        assert SnapshotStatus.PENDING.value   == "pending"
        assert SnapshotStatus.VALID.value     == "valid"
        assert SnapshotStatus.PUBLISHED.value == "published"

    def test_execution_status_values(self):
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value    == "failed"
        assert ExecutionStatus.RUNNING.value   == "running"

    def test_governance_decision_values(self):
        assert GovernanceDecision.APPROVED.value       == "approved"
        assert GovernanceDecision.REJECTED.value       == "rejected"
        assert GovernanceDecision.NOT_EVALUATED.value  == "not_evaluated"

    def test_health_status_values(self):
        assert WorkflowHealthStatus.HEALTHY.value  == "healthy"
        assert WorkflowHealthStatus.FAILED.value   == "failed"
        assert WorkflowHealthStatus.DEGRADED.value == "degraded"

    def test_lifecycle_state_values(self):
        assert LifecycleState.ACTIVE.value    == "active"
        assert LifecycleState.COMPLETED.value == "completed"

    def test_event_types(self):
        assert len(SnapshotEventType) == 8


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_inherits_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        from iios.workflow.snapshot import WorkflowSnapshotError
        assert issubclass(WorkflowSnapshotError, IIOSError)

    def test_not_found_contains_id(self):
        err = WorkflowSnapshotNotFoundError("snap-abc")
        assert "snap-abc" in str(err)
        assert err.snapshot_id == "snap-abc"

    def test_validation_error_has_issues(self):
        issues = ["field is empty", "progress out of range"]
        err = WorkflowSnapshotValidationError("bad snap", issues=issues)
        assert err.issues == issues

    def test_build_error(self):
        err = WorkflowSnapshotBuildError("workflow_id is required")
        assert "workflow_id" in str(err)

    def test_registry_error(self):
        err = WorkflowSnapshotRegistryError("at capacity")
        assert "WSS" in err.code

    def test_all_codes_have_wss_prefix(self):
        from iios.workflow.snapshot.exceptions import (
            WorkflowSnapshotBundleError,
            WorkflowSnapshotCacheError,
            WorkflowSnapshotSerializationError,
            WorkflowSnapshotStoreError,
            WorkflowSnapshotVersionError,
        )
        for cls in [
            WorkflowSnapshotNotFoundError,
            WorkflowSnapshotValidationError,
            WorkflowSnapshotBuildError,
            WorkflowSnapshotRegistryError,
            WorkflowSnapshotStoreError,
            WorkflowSnapshotCacheError,
            WorkflowSnapshotBundleError,
            WorkflowSnapshotVersionError,
            WorkflowSnapshotSerializationError,
        ]:
            assert "WSS" in cls.error_code, f"{cls} missing WSS prefix"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. WorkflowSnapshotMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotMetadata:
    def test_create_defaults(self):
        m = WorkflowSnapshotMetadata.create()
        assert m.metadata_id.startswith("wsmeta-")
        assert m.environment == "production"
        assert m.correlation_id     # auto-generated
        assert m.trace_id           # auto-generated
        assert m.snapshot_version   == "1.0"

    def test_custom_values(self):
        m = WorkflowSnapshotMetadata.create(
            environment    = "staging",
            correlation_id = "corr-123",
            trace_id       = "trace-abc",
        )
        assert m.environment    == "staging"
        assert m.correlation_id == "corr-123"
        assert m.trace_id       == "trace-abc"

    def test_source_components(self):
        m = WorkflowSnapshotMetadata.create(
            source_components = ["M1", "M2", "M3"]
        )
        assert list(m.source_components) == ["M1", "M2", "M3"]

    def test_to_dict(self):
        m = WorkflowSnapshotMetadata.create()
        d = m.to_dict()
        assert "metadata_id" in d
        assert "environment" in d
        assert "correlation_id" in d

    def test_frozen(self):
        m = WorkflowSnapshotMetadata.create()
        with pytest.raises((TypeError, AttributeError)):
            m.environment = "test"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WorkflowSnapshotBuilder
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotBuilder:
    def test_build_minimal(self):
        builder = WorkflowSnapshotBuilder()
        snap = builder.build(workflow_id="wf-1", workflow_name="W1")
        assert snap.snapshot_id.startswith("wsnap-")
        assert snap.workflow_id   == "wf-1"
        assert snap.workflow_name == "W1"

    def test_build_raises_missing_workflow_id(self):
        with pytest.raises(WorkflowSnapshotBuildError):
            WorkflowSnapshotBuilder().build(workflow_id="", workflow_name="W")

    def test_build_raises_missing_name(self):
        with pytest.raises(WorkflowSnapshotBuildError):
            WorkflowSnapshotBuilder().build(workflow_id="wf-1", workflow_name="")

    def test_health_computed_completed_approved(self):
        snap = _snap(
            execution_status    = ExecutionStatus.COMPLETED,
            governance_decision = GovernanceDecision.APPROVED,
        )
        assert snap.health_status == WorkflowHealthStatus.HEALTHY

    def test_health_computed_failed(self):
        snap = _snap(execution_status=ExecutionStatus.FAILED)
        assert snap.health_status == WorkflowHealthStatus.FAILED

    def test_health_computed_rejected(self):
        snap = _snap(
            execution_status    = ExecutionStatus.RUNNING,
            governance_decision = GovernanceDecision.REJECTED,
        )
        assert snap.health_status == WorkflowHealthStatus.FAILED

    def test_health_computed_running(self):
        snap = _snap(execution_status=ExecutionStatus.RUNNING)
        assert snap.health_status == WorkflowHealthStatus.HEALTHY

    def test_health_computed_blocked(self):
        snap = _snap(
            execution_status    = ExecutionStatus.RUNNING,
            governance_decision = GovernanceDecision.BLOCKED,
        )
        assert snap.health_status == WorkflowHealthStatus.FAILED

    def test_execution_progress_clamped(self):
        snap = WorkflowSnapshotBuilder().build(
            workflow_id        = "wf-1",
            workflow_name      = "W",
            execution_progress = 0.75,
        )
        assert snap.execution_progress == 0.75

    def test_all_fields_present(self):
        snap = _snap()
        d = snap.to_dict()
        for key in (
            "snapshot_id", "workflow_id", "workflow_name",
            "execution_status", "governance_decision", "lifecycle_state",
            "health_status", "snapshot_status", "snapshot_timestamp",
            "created_at", "updated_at", "metadata",
        ):
            assert key in d, f"Missing key: {key}"

    def test_custom_snapshot_id(self):
        snap = WorkflowSnapshotBuilder().build(
            workflow_id  = "wf-1",
            workflow_name = "W",
            snapshot_id  = "wsnap-custom",
        )
        assert snap.snapshot_id == "wsnap-custom"

    def test_metadata_attached(self):
        m    = WorkflowSnapshotMetadata.create(environment="staging")
        snap = WorkflowSnapshotBuilder().build(
            workflow_id   = "wf-1",
            workflow_name = "W",
            metadata      = m,
        )
        assert snap.metadata.environment == "staging"

    def test_frozen(self):
        snap = _snap()
        with pytest.raises((TypeError, AttributeError)):
            snap.workflow_id = "changed"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WorkflowSnapshot properties
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotProperties:
    def test_is_completed_true(self):
        assert _snap(execution_status=ExecutionStatus.COMPLETED).is_completed

    def test_is_completed_false(self):
        assert not _snap(execution_status=ExecutionStatus.RUNNING).is_completed

    def test_is_failed_true(self):
        assert _snap(execution_status=ExecutionStatus.FAILED).is_failed

    def test_is_failed_timed_out(self):
        assert _snap(execution_status=ExecutionStatus.TIMED_OUT).is_failed

    def test_is_governance_approved_approved(self):
        assert _snap(governance_decision=GovernanceDecision.APPROVED).is_governance_approved

    def test_is_governance_approved_with_conditions(self):
        assert _snap(
            governance_decision=GovernanceDecision.APPROVED_WITH_CONDITIONS
        ).is_governance_approved

    def test_is_governance_approved_false(self):
        assert not _snap(governance_decision=GovernanceDecision.REJECTED).is_governance_approved

    def test_is_published(self):
        snap = WorkflowSnapshotBuilder().build(
            workflow_id    = "wf-1",
            workflow_name  = "W",
            snapshot_status = SnapshotStatus.PUBLISHED,
        )
        assert snap.is_published

    def test_is_not_published(self):
        assert not _snap().is_published

    def test_is_healthy(self):
        snap = _snap(
            execution_status    = ExecutionStatus.COMPLETED,
            governance_decision = GovernanceDecision.APPROVED,
        )
        assert snap.is_healthy

    def test_to_dict_has_computed_flags(self):
        d = _snap().to_dict()
        assert "is_healthy"             in d
        assert "is_completed"           in d
        assert "is_failed"              in d
        assert "is_governance_approved" in d
        assert "is_published"           in d


# ═══════════════════════════════════════════════════════════════════════════════
# 6. WorkflowSnapshotValidation
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotValidation:
    def test_valid_snapshot_passes(self):
        val    = WorkflowSnapshotValidation()
        result = val.validate(_snap())
        assert result.valid
        assert len(result.issues) == 0

    def test_invalid_progress_out_of_range(self):
        import dataclasses
        snap = _snap()
        snap = dataclasses.replace(snap, execution_progress=1.5)
        val  = WorkflowSnapshotValidation()
        r    = val.validate(snap)
        assert not r.valid
        assert any("progress" in i for i in r.issues)

    def test_invalid_empty_workflow_id(self):
        import dataclasses
        snap = _snap()
        snap = dataclasses.replace(snap, workflow_id="")
        val  = WorkflowSnapshotValidation()
        r    = val.validate(snap)
        assert not r.valid

    def test_invalid_completed_steps_exceed_total(self):
        import dataclasses
        snap = _snap()
        snap = dataclasses.replace(snap, total_steps=5, completed_steps=10)
        val  = WorkflowSnapshotValidation()
        r    = val.validate(snap)
        assert not r.valid

    def test_validate_or_raise_raises(self):
        import dataclasses
        snap = _snap()
        snap = dataclasses.replace(snap, workflow_id="")
        val  = WorkflowSnapshotValidation()
        with pytest.raises(WorkflowSnapshotValidationError):
            val.validate_or_raise(snap)

    def test_validate_or_raise_passes(self):
        WorkflowSnapshotValidation().validate_or_raise(_snap())   # should not raise

    def test_result_to_dict(self):
        r = WorkflowSnapshotValidation().validate(_snap())
        d = r.to_dict()
        assert "valid" in d
        assert "issues" in d

    def test_negative_retry_count_invalid(self):
        import dataclasses
        snap = _snap()
        snap = dataclasses.replace(snap, retry_count=-1)
        val  = WorkflowSnapshotValidation()
        r    = val.validate(snap)
        assert not r.valid


# ═══════════════════════════════════════════════════════════════════════════════
# 7. WorkflowSnapshotRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotRegistry:
    def test_register_and_get(self):
        reg  = WorkflowSnapshotRegistry()
        snap = _snap()
        reg.register(snap)
        assert reg.get(snap.snapshot_id).snapshot_id == snap.snapshot_id

    def test_get_not_found(self):
        reg = WorkflowSnapshotRegistry()
        with pytest.raises(WorkflowSnapshotNotFoundError):
            reg.get("nonexistent")

    def test_get_or_none(self):
        reg = WorkflowSnapshotRegistry()
        assert reg.get_or_none("x") is None
        snap = _snap()
        reg.register(snap)
        assert reg.get_or_none(snap.snapshot_id) is not None

    def test_exists(self):
        reg  = WorkflowSnapshotRegistry()
        snap = _snap()
        assert not reg.exists(snap.snapshot_id)
        reg.register(snap)
        assert reg.exists(snap.snapshot_id)

    def test_get_by_workflow(self):
        reg  = WorkflowSnapshotRegistry()
        snap = _snap("wf-target")
        reg.register(snap)
        reg.register(_snap("wf-other"))
        results = reg.get_by_workflow("wf-target")
        assert len(results) == 1
        assert results[0].workflow_id == "wf-target"

    def test_latest_for_workflow(self):
        reg  = WorkflowSnapshotRegistry()
        s1   = _snap("wf-x")
        s2   = _snap("wf-x")
        reg.register(s1)
        reg.register(s2)
        latest = reg.latest_for_workflow("wf-x")
        assert latest is not None

    def test_latest_for_missing_workflow(self):
        reg = WorkflowSnapshotRegistry()
        assert reg.latest_for_workflow("ghost") is None

    def test_deregister(self):
        reg  = WorkflowSnapshotRegistry()
        snap = _snap()
        reg.register(snap)
        removed = reg.deregister(snap.snapshot_id)
        assert removed is True
        assert not reg.exists(snap.snapshot_id)

    def test_deregister_not_found(self):
        assert WorkflowSnapshotRegistry().deregister("ghost") is False

    def test_snapshot_count(self):
        reg = WorkflowSnapshotRegistry()
        assert reg.snapshot_count() == 0
        reg.register(_snap())
        assert reg.snapshot_count() == 1

    def test_capacity_limit(self):
        reg = WorkflowSnapshotRegistry(max_snapshots=2)
        reg.register(_snap("w1"))
        reg.register(_snap("w2"))
        with pytest.raises(WorkflowSnapshotRegistryError):
            reg.register(_snap("w3"))

    def test_clear(self):
        reg = WorkflowSnapshotRegistry()
        reg.register(_snap())
        n = reg.clear()
        assert n == 1
        assert reg.snapshot_count() == 0

    def test_all_snapshots(self):
        reg = WorkflowSnapshotRegistry()
        reg.register(_snap("w1"))
        reg.register(_snap("w2"))
        assert len(reg.all_snapshots()) == 2

    def test_thread_safety(self):
        reg    = WorkflowSnapshotRegistry(max_snapshots=200)
        errors = []

        def worker():
            try:
                reg.register(_snap(str(uuid.uuid4())))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ═══════════════════════════════════════════════════════════════════════════════
# 8. WorkflowSnapshotStore
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotStore:
    def test_save_and_get(self):
        store = WorkflowSnapshotStore()
        snap  = _snap()
        store.save(snap)
        assert store.get(snap.snapshot_id).snapshot_id == snap.snapshot_id

    def test_get_not_found(self):
        store = WorkflowSnapshotStore()
        with pytest.raises(WorkflowSnapshotNotFoundError):
            store.get("ghost")

    def test_get_or_none(self):
        store = WorkflowSnapshotStore()
        assert store.get_or_none("x") is None
        snap = _snap()
        store.save(snap)
        assert store.get_or_none(snap.snapshot_id) is not None

    def test_exists(self):
        store = WorkflowSnapshotStore()
        snap  = _snap()
        assert not store.exists(snap.snapshot_id)
        store.save(snap)
        assert store.exists(snap.snapshot_id)

    def test_delete(self):
        store = WorkflowSnapshotStore()
        snap  = _snap()
        store.save(snap)
        removed = store.delete(snap.snapshot_id)
        assert removed is True
        assert not store.exists(snap.snapshot_id)

    def test_delete_not_found(self):
        assert WorkflowSnapshotStore().delete("ghost") is False

    def test_get_by_workflow(self):
        store = WorkflowSnapshotStore()
        s1 = _snap("wf-target")
        s2 = _snap("wf-other")
        store.save(s1); store.save(s2)
        results = store.get_by_workflow("wf-target")
        assert len(results) == 1

    def test_recent(self):
        store = WorkflowSnapshotStore()
        for i in range(5):
            store.save(_snap(f"wf-{i}"))
        assert len(store.recent(3)) == 3

    def test_count(self):
        store = WorkflowSnapshotStore()
        assert store.count() == 0
        store.save(_snap())
        assert store.count() == 1

    def test_clear(self):
        store = WorkflowSnapshotStore()
        store.save(_snap())
        n = store.clear()
        assert n == 1
        assert store.count() == 0

    def test_bounded(self):
        store = WorkflowSnapshotStore(max_entries=3)
        for i in range(5):
            store.save(_snap(f"wf-{i}"))
        assert store.count() == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 9. WorkflowSnapshotCache
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotCache:
    def test_put_and_get(self):
        cache = WorkflowSnapshotCache()
        snap  = _snap()
        cache.put(snap)
        fetched = cache.get(snap.snapshot_id)
        assert fetched is not None
        assert fetched.snapshot_id == snap.snapshot_id

    def test_get_miss(self):
        cache = WorkflowSnapshotCache()
        assert cache.get("ghost") is None

    def test_contains(self):
        cache = WorkflowSnapshotCache()
        snap  = _snap()
        assert not cache.contains(snap.snapshot_id)
        cache.put(snap)
        assert cache.contains(snap.snapshot_id)

    def test_remove(self):
        cache = WorkflowSnapshotCache()
        snap  = _snap()
        cache.put(snap)
        removed = cache.remove(snap.snapshot_id)
        assert removed is True
        assert not cache.contains(snap.snapshot_id)

    def test_remove_not_found(self):
        assert WorkflowSnapshotCache().remove("ghost") is False

    def test_lru_eviction(self):
        cache = WorkflowSnapshotCache(capacity=2)
        s1 = _snap("w1"); s2 = _snap("w2"); s3 = _snap("w3")
        cache.put(s1); cache.put(s2); cache.put(s3)
        assert cache.size() == 2
        assert not cache.contains(s1.snapshot_id)

    def test_hit_rate(self):
        cache = WorkflowSnapshotCache()
        snap  = _snap()
        cache.put(snap)
        cache.get(snap.snapshot_id)   # hit
        cache.get("ghost")            # miss
        hr = cache.hit_rate()
        assert hr == 0.5

    def test_size(self):
        cache = WorkflowSnapshotCache(capacity=10)
        assert cache.size() == 0
        cache.put(_snap())
        assert cache.size() == 1

    def test_stats(self):
        cache = WorkflowSnapshotCache()
        d = cache.stats()
        assert "capacity" in d
        assert "hit_rate" in d

    def test_clear(self):
        cache = WorkflowSnapshotCache()
        cache.put(_snap())
        n = cache.clear()
        assert n == 1
        assert cache.size() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 10. WorkflowSnapshotHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotHistory:
    def test_record_and_get(self):
        hist = WorkflowSnapshotHistory()
        snap = _snap()
        hist.record(snap)
        fetched = hist.get(snap.snapshot_id)
        assert fetched is not None
        assert fetched.snapshot_id == snap.snapshot_id

    def test_get_not_found(self):
        assert WorkflowSnapshotHistory().get("ghost") is None

    def test_for_workflow(self):
        hist = WorkflowSnapshotHistory()
        s1 = _snap("wf-a"); s2 = _snap("wf-b")
        hist.record(s1); hist.record(s2)
        results = hist.for_workflow("wf-a")
        assert len(results) == 1

    def test_recent(self):
        hist = WorkflowSnapshotHistory()
        for i in range(5):
            hist.record(_snap(f"w{i}"))
        assert len(hist.recent(3)) == 3

    def test_count(self):
        hist = WorkflowSnapshotHistory()
        assert hist.count() == 0
        hist.record(_snap())
        assert hist.count() == 1

    def test_clear(self):
        hist = WorkflowSnapshotHistory()
        hist.record(_snap())
        n = hist.clear()
        assert n == 1
        assert hist.count() == 0

    def test_bounded(self):
        hist = WorkflowSnapshotHistory(max_entries=3)
        for i in range(5):
            hist.record(_snap(f"w{i}"))
        assert hist.count() == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 11. WorkflowSnapshotStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotStatistics:
    def test_initial_zeros(self):
        stats  = WorkflowSnapshotStatistics()
        report = stats.report()
        assert report.total_snapshots       == 0
        assert report.success_rate          == 0.0

    def test_record_completed(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 100.0)
        r = stats.report()
        assert r.total_snapshots       == 1
        assert r.successful_executions == 1
        assert r.success_rate          == 1.0

    def test_record_failed(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.FAILED, 50.0)
        r = stats.report()
        assert r.failed_executions == 1
        assert r.failure_rate      == 1.0

    def test_record_steps_retries(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 200.0, steps=5, retries=2, compensations=1)
        r = stats.report()
        assert r.total_steps      == 5
        assert r.total_retries    == 2
        assert r.total_compensations == 1

    def test_average_duration(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 100.0)
        stats.record_snapshot(ExecutionStatus.COMPLETED, 200.0)
        r = stats.report()
        assert r.average_duration_ms == 150.0

    def test_published_flag(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 10.0, published=True)
        stats.record_snapshot(ExecutionStatus.COMPLETED, 10.0, published=False)
        r = stats.report()
        assert r.published_snapshots == 1

    def test_superseded_flag(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 10.0, superseded=True)
        assert stats.report().superseded_snapshots == 1

    def test_invalid_flag(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.FAILED, 10.0, valid=False)
        assert stats.report().invalid_snapshots == 1

    def test_reset(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 10.0)
        stats.reset()
        assert stats.report().total_snapshots == 0

    def test_report_to_dict(self):
        r = WorkflowSnapshotStatistics().report()
        d = r.to_dict()
        assert "total_snapshots" in d
        assert "success_rate"    in d


# ═══════════════════════════════════════════════════════════════════════════════
# 12. WorkflowSnapshotEventBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotEventBus:
    def _evt(self, et=SnapshotEventType.SNAPSHOT_PUBLISHED):
        return WorkflowSnapshotEvent.create(et, "snap-1", "wf-1")

    def test_add_listener_and_emit(self):
        bus      = WorkflowSnapshotEventBus()
        received = []
        bus.add_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, received.append)
        bus.emit(self._evt())
        assert len(received) == 1

    def test_wrong_type_not_received(self):
        bus      = WorkflowSnapshotEventBus()
        received = []
        bus.add_listener(SnapshotEventType.SNAPSHOT_CREATED, received.append)
        bus.emit(self._evt(SnapshotEventType.SNAPSHOT_PUBLISHED))
        assert len(received) == 0

    def test_remove_listener(self):
        bus      = WorkflowSnapshotEventBus()
        listener = lambda e: None
        bus.add_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, listener)
        removed = bus.remove_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, listener)
        assert removed is True
        assert bus.listener_count(SnapshotEventType.SNAPSHOT_PUBLISHED) == 0

    def test_remove_not_found(self):
        bus = WorkflowSnapshotEventBus()
        assert bus.remove_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, lambda e: None) is False

    def test_listener_count_all(self):
        bus = WorkflowSnapshotEventBus()
        bus.add_listener(SnapshotEventType.SNAPSHOT_CREATED,   lambda e: None)
        bus.add_listener(SnapshotEventType.SNAPSHOT_PUBLISHED,  lambda e: None)
        assert bus.listener_count() == 2

    def test_listener_error_does_not_propagate(self):
        bus = WorkflowSnapshotEventBus()
        def bad(e): raise RuntimeError("boom")
        bus.add_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, bad)
        notified = bus.emit(self._evt())   # should not raise
        assert notified == 0

    def test_clear(self):
        bus = WorkflowSnapshotEventBus()
        bus.add_listener(SnapshotEventType.SNAPSHOT_PUBLISHED, lambda e: None)
        bus.clear()
        assert bus.listener_count() == 0

    def test_event_create(self):
        evt = WorkflowSnapshotEvent.create(
            SnapshotEventType.SNAPSHOT_PUBLISHED, "snap-1", "wf-1", {"k": "v"}
        )
        assert evt.event_id.startswith("wsevt-")
        assert evt.event_type  == SnapshotEventType.SNAPSHOT_PUBLISHED
        assert evt.snapshot_id == "snap-1"
        assert evt.workflow_id == "wf-1"
        d = evt.to_dict()
        assert "event_id" in d
        assert "event_type" in d

    def test_event_frozen(self):
        evt = WorkflowSnapshotEvent.create(SnapshotEventType.SNAPSHOT_CREATED)
        with pytest.raises((TypeError, AttributeError)):
            evt.snapshot_id = "changed"


# ═══════════════════════════════════════════════════════════════════════════════
# 13. WorkflowSnapshotBundle
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotBundle:
    def test_create(self):
        snaps = [_snap("w1"), _snap("w2")]
        bundle = WorkflowSnapshotBundle.create("Test Bundle", snaps)
        assert bundle.bundle_id.startswith("wbndl-")
        assert bundle.snapshot_count == 2

    def test_workflow_ids(self):
        s1 = _snap("w1"); s2 = _snap("w2")
        b  = WorkflowSnapshotBundle.create("B", [s1, s2])
        assert "w1" in b.workflow_ids
        assert "w2" in b.workflow_ids

    def test_snapshot_ids(self):
        s1 = _snap(); s2 = _snap()
        b  = WorkflowSnapshotBundle.create("B", [s1, s2])
        assert s1.snapshot_id in b.snapshot_ids
        assert s2.snapshot_id in b.snapshot_ids

    def test_get_snapshot(self):
        s1 = _snap()
        b  = WorkflowSnapshotBundle.create("B", [s1])
        fetched = b.get_snapshot(s1.snapshot_id)
        assert fetched is not None

    def test_get_snapshot_missing(self):
        b = WorkflowSnapshotBundle.create("B", [_snap()])
        assert b.get_snapshot("ghost") is None

    def test_get_by_workflow(self):
        s1 = _snap("wf-a"); s2 = _snap("wf-a"); s3 = _snap("wf-b")
        b  = WorkflowSnapshotBundle.create("B", [s1, s2, s3])
        results = b.get_by_workflow("wf-a")
        assert len(results) == 2

    def test_to_dict(self):
        b = WorkflowSnapshotBundle.create("B", [_snap()])
        d = b.to_dict()
        assert "bundle_id"      in d
        assert "snapshot_count" in d

    def test_frozen(self):
        b = WorkflowSnapshotBundle.create("B", [])
        with pytest.raises((TypeError, AttributeError)):
            b.bundle_name = "changed"


# ═══════════════════════════════════════════════════════════════════════════════
# 14. WorkflowSnapshotFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotFactory:
    def test_create_completed(self):
        snap = WorkflowSnapshotFactory.create_completed("wf-1", "W1")
        assert snap.is_completed
        assert snap.execution_status == ExecutionStatus.COMPLETED

    def test_create_failed(self):
        snap = WorkflowSnapshotFactory.create_failed("wf-2", "W2")
        assert snap.is_failed
        assert snap.execution_status == ExecutionStatus.FAILED

    def test_create_running(self):
        snap = WorkflowSnapshotFactory.create_running("wf-3", "W3")
        assert snap.execution_status == ExecutionStatus.RUNNING

    def test_create_completed_progress(self):
        snap = WorkflowSnapshotFactory.create_completed(
            "wf-1", "W", completed_steps=3, total_steps=5
        )
        assert abs(snap.execution_progress - 0.6) < 0.001

    def test_create_failed_with_note(self):
        snap = WorkflowSnapshotFactory.create_failed(
            "wf-1", "W", error_note="disk full"
        )
        assert any("disk full" in entry for entry in snap.audit_trail)

    def test_create_bundle(self):
        snaps  = [_snap("w1"), _snap("w2")]
        bundle = WorkflowSnapshotFactory.create_bundle("My Bundle", snaps)
        assert bundle.snapshot_count == 2

    def test_create_metadata(self):
        m = WorkflowSnapshotFactory.create_metadata(
            environment    = "staging",
            correlation_id = "corr-xyz",
        )
        assert m.environment    == "staging"
        assert m.correlation_id == "corr-xyz"


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Serialization
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_snapshot_to_dict_is_dict(self):
        d = _snap().to_dict()
        assert isinstance(d, dict)

    def test_all_string_enum_values(self):
        """Ensure all enum fields are serialized as strings."""
        d = _snap().to_dict()
        assert isinstance(d["execution_status"],    str)
        assert isinstance(d["governance_decision"], str)
        assert isinstance(d["lifecycle_state"],     str)
        assert isinstance(d["health_status"],       str)
        assert isinstance(d["snapshot_status"],     str)

    def test_round_trip_fields(self):
        """Fields must survive dict export intact."""
        snap = WorkflowSnapshotBuilder().build(
            workflow_id        = "wf-rt",
            workflow_name      = "RT",
            execution_progress = 0.75,
            retry_count        = 3,
            completed_steps    = 6,
            total_steps        = 8,
            audit_trail        = ["step-1 completed", "step-2 completed"],
        )
        d = snap.to_dict()
        assert d["workflow_id"]        == "wf-rt"
        assert d["execution_progress"] == 0.75
        assert d["retry_count"]        == 3
        assert d["completed_steps"]    == 6
        assert d["total_steps"]        == 8
        assert "step-1 completed" in d["audit_trail"]

    def test_metadata_to_dict_nested(self):
        d = _snap().to_dict()
        assert isinstance(d["metadata"], dict)
        assert "metadata_id" in d["metadata"]


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Regression & Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_snapshot_id_unique(self):
        ids = {_snap().snapshot_id for _ in range(50)}
        assert len(ids) == 50

    def test_registry_workflow_index_multi_snapshot(self):
        reg = WorkflowSnapshotRegistry()
        for i in range(5):
            reg.register(_snap("wf-shared"))
        results = reg.get_by_workflow("wf-shared")
        assert len(results) == 5

    def test_store_workflow_index(self):
        store = WorkflowSnapshotStore()
        for i in range(3):
            store.save(_snap("wf-shared"))
        results = store.get_by_workflow("wf-shared")
        assert len(results) == 3

    def test_full_pipeline(self):
        """Builder → Validate → Register → Store → Cache → History → Stats."""
        builder  = WorkflowSnapshotBuilder()
        val      = WorkflowSnapshotValidation()
        reg      = WorkflowSnapshotRegistry()
        store    = WorkflowSnapshotStore()
        cache    = WorkflowSnapshotCache()
        history  = WorkflowSnapshotHistory()
        stats    = WorkflowSnapshotStatistics()

        snap = builder.build(
            workflow_id        = "wf-pipeline",
            workflow_name      = "Pipeline Test",
            execution_status   = ExecutionStatus.COMPLETED,
            total_steps        = 3,
            completed_steps    = 3,
            execution_progress = 1.0,
        )
        val.validate_or_raise(snap)
        reg.register(snap)
        store.save(snap)
        cache.put(snap)
        history.record(snap)
        stats.record_snapshot(snap.execution_status, 200.0, steps=3)

        assert reg.exists(snap.snapshot_id)
        assert store.exists(snap.snapshot_id)
        assert cache.contains(snap.snapshot_id)
        assert history.get(snap.snapshot_id) is not None
        report = stats.report()
        assert report.total_snapshots == 1
        assert report.successful_executions == 1

    def test_concurrent_registry(self):
        reg    = WorkflowSnapshotRegistry(max_snapshots=500)
        errors = []

        def worker():
            try:
                reg.register(_snap(str(uuid.uuid4())))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert reg.snapshot_count() == 100

    def test_concurrent_cache(self):
        cache  = WorkflowSnapshotCache(capacity=50)
        errors = []

        def worker():
            try:
                snap = _snap(str(uuid.uuid4()))
                cache.put(snap)
                cache.get(snap.snapshot_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_health_mapping_complete(self):
        """All ExecutionStatus values produce a valid health status."""
        for status in ExecutionStatus:
            snap = _snap(execution_status=status)
            assert snap.health_status in WorkflowHealthStatus

    def test_governance_mapping_complete(self):
        """All GovernanceDecision values produce a valid snapshot."""
        for decision in GovernanceDecision:
            snap = _snap(governance_decision=decision)
            assert snap.governance_decision == decision

    def test_empty_bundle(self):
        b = WorkflowSnapshotBundle.create("Empty", [])
        assert b.snapshot_count == 0
        assert b.workflow_ids   == []

    def test_stats_mixed_results(self):
        stats = WorkflowSnapshotStatistics()
        stats.record_snapshot(ExecutionStatus.COMPLETED, 100.0)
        stats.record_snapshot(ExecutionStatus.COMPLETED, 200.0)
        stats.record_snapshot(ExecutionStatus.FAILED,    50.0)
        r = stats.report()
        assert r.total_snapshots       == 3
        assert r.successful_executions == 2
        assert r.failed_executions     == 1
        assert abs(r.success_rate - 2/3) < 0.01
        assert abs(r.failure_rate - 1/3) < 0.01
