"""tests/unit/integration/research/test_research_engine.py

Comprehensive test suite for iios/integration/research/

Run with:
    python -m pytest tests/unit/integration/research/ -q

Async tests use _run() -- no pytest-asyncio required.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import Any

import pytest

# ── Async helper ──────────────────────────────────────────────────────────────
def _run(coro): return asyncio.run(coro)

# ── Imports ───────────────────────────────────────────────────────────────────
from iios.integration.research.research_constants import (
    CheckpointStatus,
    DatasetSourceType,
    ExperimentPriority,
    ExperimentStatus,
    ResearchDatasetStatus,
    ResearchEngineStatus,
    ResearchEventType,
    ResearchProjectStatus,
    ResearchSessionStatus,
    WorkflowStatus,
    RESEARCH_ENGINE_VERSION,
    RESEARCH_ERROR_PREFIX,
    DEFAULT_MAX_PROJECTS,
    DEFAULT_MAX_EXPERIMENTS,
    DEFAULT_MAX_DATASETS,
    DEFAULT_EXPERIMENT_TIMEOUT_SEC,
)
from iios.integration.research.research_exceptions import (
    CheckpointError,
    DatasetLineageError,
    ExperimentAlreadyRunningError,
    ExperimentNotRunningError,
    ExperimentStateError,
    ResearchDatasetAlreadyExistsError,
    ResearchDatasetCapacityError,
    ResearchDatasetNotFoundError,
    ResearchEngineAlreadyRunningError,
    ResearchEngineInitializationError,
    ResearchEngineNotRunningError,
    ResearchError,
    ResearchExperimentAlreadyExistsError,
    ResearchExperimentCapacityError,
    ResearchExperimentNotFoundError,
    ResearchProjectAlreadyExistsError,
    ResearchProjectCapacityError,
    ResearchProjectNotFoundError,
    ResearchRegistryFullError,
    TrackingSessionNotFoundError,
    WorkflowError,
    WorkflowStepNotFoundError,
    WorkflowValidationError,
)
from iios.integration.research.core.research_metadata   import ResearchMetadata
from iios.integration.research.core.research_project    import ResearchProject
from iios.integration.research.core.research_experiment import ResearchExperiment
from iios.integration.research.core.research_dataset    import ResearchDataset, DatasetSnapshot
from iios.integration.research.core.research_session    import ResearchSession
from iios.integration.research.core.research_result     import ResearchResult
from iios.integration.research.core.research_statistics import ResearchStatistics
from iios.integration.research.core.research_history    import ResearchHistory, ResearchHistoryEntry
from iios.integration.research.experiments.experiment_lifecycle import ExperimentLifecycle
from iios.integration.research.experiments.experiment_runner    import ExperimentRunner
from iios.integration.research.projects.project_manager  import ProjectManager
from iios.integration.research.registry.experiment_registry import ExperimentRegistry
from iios.integration.research.workflow.research_workflow import ResearchWorkflow, WorkflowStep
from iios.integration.research.datasets.dataset_manager  import DatasetManager
from iios.integration.research.tracking.execution_tracker import ExecutionTracker, ExecutionCheckpoint
from iios.integration.research.monitoring.research_monitor import ResearchMonitor
from iios.integration.research.research_context          import ResearchContext
from iios.integration.research.research_registry         import ResearchRegistry
from iios.integration.research.research_factory          import ResearchFactory
from iios.integration.research.research_manager          import ResearchManager
from iios.integration.research.research_engine           import (
    ResearchEngine,
    get_research_engine,
    reset_research_engine,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_project(name: str = "Test Project") -> ResearchProject:
    return ResearchProject(
        name        = name,
        description = "A test research project",
        objective   = "Validate something",
        hypothesis  = "X causes Y",
        owner       = "tester",
    )


def _make_experiment(project_id: str = "", name: str = "Test Exp") -> ResearchExperiment:
    return ResearchExperiment(
        project_id  = project_id,
        name        = name,
        description = "A test experiment",
        hypothesis  = "X causes Y",
    )


def _make_dataset(name: str = "Test DS") -> ResearchDataset:
    return ResearchDataset(
        name        = name,
        description = "Test dataset",
        source_type = DatasetSourceType.CUSTOM,
    )


def _trivial_fn(exp: ResearchExperiment) -> dict[str, Any]:
    return {"accuracy": 0.95, "loss": 0.05}


async def _async_fn(exp: ResearchExperiment) -> dict[str, Any]:
    await asyncio.sleep(0)
    return {"value": 42}


def _failing_fn(exp: ResearchExperiment) -> dict[str, Any]:
    raise ValueError("Experiment failed intentionally")


def _make_manager() -> ResearchManager:
    return ResearchManager(
        registry     = ResearchFactory.create_registry(),
        proj_mgr     = ResearchFactory.create_project_manager(),
        exp_registry = ResearchFactory.create_experiment_registry(),
        lifecycle    = ResearchFactory.create_experiment_lifecycle(),
        runner       = ResearchFactory.create_experiment_runner(),
        dataset_mgr  = ResearchFactory.create_dataset_manager(),
        tracker      = ResearchFactory.create_execution_tracker(),
        monitor      = ResearchFactory.create_research_monitor(),
        history      = ResearchFactory.create_research_history(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(RESEARCH_ENGINE_VERSION, str)

    def test_error_prefix(self):
        assert RESEARCH_ERROR_PREFIX == "QR"

    def test_experiment_status_values(self):
        assert ExperimentStatus.DRAFT.value      == "draft"
        assert ExperimentStatus.RUNNING.value    == "running"
        assert ExperimentStatus.COMPLETED.value  == "completed"

    def test_project_status_values(self):
        assert ResearchProjectStatus.DRAFT.value    == "draft"
        assert ResearchProjectStatus.ACTIVE.value   == "active"
        assert ResearchProjectStatus.ARCHIVED.value == "archived"

    def test_engine_status_values(self):
        assert ResearchEngineStatus.STOPPED.value  == "stopped"
        assert ResearchEngineStatus.RUNNING.value  == "running"

    def test_workflow_status_values(self):
        assert WorkflowStatus.PENDING.value   == "pending"
        assert WorkflowStatus.COMPLETED.value == "completed"

    def test_default_max_projects(self):
        assert DEFAULT_MAX_PROJECTS > 0

    def test_experiment_priority_values(self):
        assert ExperimentPriority.NORMAL.value == "normal"
        assert ExperimentPriority.HIGH.value   == "high"


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_root_exception_code(self):
        e = ResearchError("msg")
        assert e.code == "QR-000"

    def test_engine_not_running_code(self):
        e = ResearchEngineNotRunningError("x")
        assert "QR-001" in repr(e)

    def test_engine_already_running_code(self):
        e = ResearchEngineAlreadyRunningError("x")
        assert "QR-002" in repr(e)

    def test_project_not_found_code(self):
        e = ResearchProjectNotFoundError("x")
        assert "QR-010" in repr(e)

    def test_project_already_exists_code(self):
        e = ResearchProjectAlreadyExistsError("x")
        assert "QR-011" in repr(e)

    def test_experiment_not_found_code(self):
        e = ResearchExperimentNotFoundError("x")
        assert "QR-020" in repr(e)

    def test_experiment_state_error_code(self):
        e = ExperimentStateError("x")
        assert "QR-023" in repr(e)

    def test_dataset_not_found_code(self):
        e = ResearchDatasetNotFoundError("x")
        assert "QR-030" in repr(e)

    def test_workflow_step_not_found(self):
        e = WorkflowStepNotFoundError("x")
        assert "QR-053" in repr(e)

    def test_registry_full_code(self):
        e = ResearchRegistryFullError("x")
        assert "QR-061" in repr(e)

    def test_tracking_session_not_found(self):
        e = TrackingSessionNotFoundError("x")
        assert "QR-072" in repr(e)

    def test_checkpoint_error_code(self):
        e = CheckpointError("x")
        assert "QR-071" in repr(e)


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchMetadata:
    def test_defaults(self):
        m = ResearchMetadata()
        assert m.version  == "1.0.0"
        assert m.tags     == []
        assert m.labels   == {}

    def test_add_tag(self):
        m = ResearchMetadata()
        m.add_tag("alpha")
        assert "alpha" in m.tags

    def test_remove_tag(self):
        m = ResearchMetadata()
        m.add_tag("beta")
        m.remove_tag("beta")
        assert "beta" not in m.tags

    def test_set_label(self):
        m = ResearchMetadata()
        m.set_label("env", "prod")
        assert m.labels["env"] == "prod"

    def test_to_dict(self):
        m = ResearchMetadata(owner="alice")
        d = m.to_dict()
        assert d["owner"] == "alice"


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchProject
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchProject:
    def test_defaults(self):
        p = _make_project()
        assert p.project_id != ""
        assert p.status == ResearchProjectStatus.DRAFT

    def test_add_experiment(self):
        p = _make_project()
        p.add_experiment("exp-1")
        assert "exp-1" in p.experiment_ids

    def test_add_experiment_idempotent(self):
        p = _make_project()
        p.add_experiment("exp-1")
        p.add_experiment("exp-1")
        assert p.experiment_ids.count("exp-1") == 1

    def test_remove_experiment(self):
        p = _make_project()
        p.add_experiment("exp-1")
        p.remove_experiment("exp-1")
        assert "exp-1" not in p.experiment_ids

    def test_experiment_count(self):
        p = _make_project()
        p.add_experiment("exp-1")
        p.add_experiment("exp-2")
        assert p.experiment_count() == 2

    def test_touch_updates_timestamp(self):
        p = _make_project()
        before = p.updated_at
        time.sleep(0.01)
        p.touch()
        assert p.updated_at >= before

    def test_is_active_false_for_draft(self):
        p = _make_project()
        assert p.is_active() is False

    def test_to_dict(self):
        p = _make_project()
        d = p.to_dict()
        assert "project_id" in d
        assert "status" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchExperiment
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchExperiment:
    def test_defaults(self):
        e = _make_experiment()
        assert e.status   == ExperimentStatus.DRAFT
        assert e.priority == ExperimentPriority.NORMAL
        assert e.version  == "1.0.0"

    def test_unique_ids(self):
        a = _make_experiment()
        b = _make_experiment()
        assert a.experiment_id != b.experiment_id

    def test_is_terminal_false_for_draft(self):
        e = _make_experiment()
        assert e.is_terminal() is False

    def test_is_terminal_true_for_completed(self):
        e = _make_experiment()
        e.status = ExperimentStatus.COMPLETED
        assert e.is_terminal() is True

    def test_is_active_false_for_draft(self):
        e = _make_experiment()
        assert e.is_active() is False

    def test_elapsed_sec_zero_when_not_started(self):
        e = _make_experiment()
        assert e.elapsed_sec() == 0.0

    def test_to_dict_contains_status(self):
        e = _make_experiment()
        d = e.to_dict()
        assert d["status"] == "draft"

    def test_touch_updates_timestamp(self):
        e = _make_experiment()
        before = e.updated_at
        time.sleep(0.01)
        e.touch()
        assert e.updated_at >= before


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchDataset
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchDataset:
    def test_defaults(self):
        ds = _make_dataset()
        assert ds.version == "1.0.0"
        assert ds.status  == ResearchDatasetStatus.PENDING

    def test_create_snapshot(self):
        ds = _make_dataset()
        snap = ds.create_snapshot("initial")
        assert snap.snapshot_id != ""
        assert len(ds.snapshots) == 1

    def test_bump_version(self):
        ds = _make_dataset()
        ds.bump_version()
        assert ds.version == "1.0.1"

    def test_lineage_depth_zero(self):
        ds = _make_dataset()
        assert ds.lineage_depth() == 0

    def test_to_dict(self):
        ds = _make_dataset()
        d  = ds.to_dict()
        assert "dataset_id" in d
        assert "version" in d

    def test_parent_ids_default_empty(self):
        ds = _make_dataset()
        assert ds.parent_ids == []


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchSession
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchSession:
    def test_defaults(self):
        s = ResearchSession(experiment_id="e-1", project_id="p-1")
        assert s.status == ResearchSessionStatus.IDLE

    def test_start(self):
        s = ResearchSession()
        s.start()
        assert s.status    == ResearchSessionStatus.ACTIVE
        assert s.started_at is not None

    def test_end_success(self):
        s = ResearchSession()
        s.start()
        s.end()
        assert s.status   == ResearchSessionStatus.COMPLETED
        assert s.ended_at is not None

    def test_end_failed(self):
        s = ResearchSession()
        s.start()
        s.end(failed=True)
        assert s.status == ResearchSessionStatus.FAILED

    def test_duration_positive_after_end(self):
        s = ResearchSession()
        s.start()
        time.sleep(0.01)
        s.end()
        assert s.duration_sec() > 0

    def test_progress_zero_when_no_steps(self):
        s = ResearchSession()
        assert s.progress() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchResult
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchResult:
    def test_defaults(self):
        r = ResearchResult(experiment_id="e-1", project_id="p-1")
        assert r.is_success is False
        assert r.metrics    == {}

    def test_has_metric(self):
        r = ResearchResult(metrics={"acc": 0.9})
        assert r.has_metric("acc") is True
        assert r.has_metric("loss") is False

    def test_get_metric(self):
        r = ResearchResult(metrics={"k": 42})
        assert r.get_metric("k")       == 42
        assert r.get_metric("x", -1)   == -1

    def test_add_artifact(self):
        r = ResearchResult()
        r.add_artifact("/path/to/file.pkl")
        assert "/path/to/file.pkl" in r.artifacts

    def test_to_dict(self):
        r = ResearchResult(experiment_id="e-1")
        d = r.to_dict()
        assert "result_id"     in d
        assert "experiment_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchStatistics:
    def test_compute_empty(self):
        s = ResearchStatistics.compute([], [], [], [])
        assert s.total_projects    == 0
        assert s.total_experiments == 0

    def test_compute_counts(self):
        p = _make_project()
        p.status = ResearchProjectStatus.ACTIVE
        e1 = _make_experiment(); e1.status = ExperimentStatus.COMPLETED; e1.duration_sec = 10.0
        e2 = _make_experiment(); e2.status = ExperimentStatus.FAILED;    e2.duration_sec = 5.0
        s  = ResearchStatistics.compute([p], [e1, e2], [], [])
        assert s.total_projects        == 1
        assert s.active_projects       == 1
        assert s.completed_experiments == 1
        assert s.failed_experiments    == 1

    def test_success_rate(self):
        e1 = _make_experiment(); e1.status = ExperimentStatus.COMPLETED
        e2 = _make_experiment(); e2.status = ExperimentStatus.FAILED
        s  = ResearchStatistics.compute([], [e1, e2], [], [])
        assert s.success_rate == pytest.approx(0.5)

    def test_to_dict(self):
        s = ResearchStatistics.compute([], [], [], [])
        d = s.to_dict()
        assert "total_projects"    in d
        assert "success_rate"      in d


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchHistory:
    def _entry(self, entity_id: str = "e-1") -> ResearchHistoryEntry:
        return ResearchHistoryEntry(
            entity_type = "experiment",
            entity_id   = entity_id,
            event_type  = ResearchEventType.EXPERIMENT_STARTED,
        )

    def test_append_and_count(self):
        h = ResearchHistory()
        h.append(self._entry())
        assert h.count() == 1

    def test_query_by_entity_id(self):
        h = ResearchHistory()
        h.append(self._entry("A"))
        h.append(self._entry("B"))
        results = h.query(entity_id="A")
        assert len(results) == 1
        assert results[0].entity_id == "A"

    def test_query_by_event_type(self):
        h = ResearchHistory()
        h.append(self._entry())
        results = h.query(event_type=ResearchEventType.EXPERIMENT_STARTED)
        assert len(results) == 1

    def test_clear(self):
        h = ResearchHistory()
        h.append(self._entry())
        h.clear()
        assert h.count() == 0

    def test_latest(self):
        h = ResearchHistory()
        for i in range(5):
            h.append(self._entry(f"e-{i}"))
        latest = h.latest(3)
        assert len(latest) == 3

    def test_max_entries_cap(self):
        h = ResearchHistory(max_entries=3)
        for i in range(5):
            h.append(self._entry(f"e-{i}"))
        assert h.count() == 3


# ─────────────────────────────────────────────────────────────────────────────
# TestExperimentLifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentLifecycle:
    def _lc(self) -> ExperimentLifecycle:
        return ExperimentLifecycle()

    def test_draft_to_configured(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.DRAFT, ExperimentStatus.CONFIGURED)

    def test_draft_to_running_invalid(self):
        lc = self._lc()
        assert not lc.is_valid_transition(ExperimentStatus.DRAFT, ExperimentStatus.RUNNING)

    def test_running_to_completed(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED)

    def test_running_to_failed(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.RUNNING, ExperimentStatus.FAILED)

    def test_running_to_paused(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.RUNNING, ExperimentStatus.PAUSED)

    def test_paused_to_running(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.PAUSED, ExperimentStatus.RUNNING)

    def test_completed_to_archived(self):
        lc = self._lc()
        assert lc.is_valid_transition(ExperimentStatus.COMPLETED, ExperimentStatus.ARCHIVED)

    def test_archived_is_terminal(self):
        lc = self._lc()
        for s in ExperimentStatus:
            assert not lc.is_valid_transition(ExperimentStatus.ARCHIVED, s)

    def test_transition_changes_status(self):
        lc  = self._lc()
        exp = _make_experiment()
        lc.configure(exp)
        assert exp.status == ExperimentStatus.CONFIGURED

    def test_invalid_transition_raises(self):
        lc  = self._lc()
        exp = _make_experiment()
        exp.status = ExperimentStatus.ARCHIVED
        with pytest.raises(ExperimentStateError):
            lc.configure(exp)


# ─────────────────────────────────────────────────────────────────────────────
# TestExperimentRunner
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentRunner:
    def test_run_sync_fn_returns_result(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        result = _run(runner.run(exp, _trivial_fn))
        assert isinstance(result, ResearchResult)

    def test_run_async_fn_returns_result(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        result = _run(runner.run(exp, _async_fn))
        assert result.is_success is True

    def test_run_sets_metrics(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        result = _run(runner.run(exp, _trivial_fn))
        assert result.metrics.get("accuracy") == pytest.approx(0.95)

    def test_run_success_status(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        _run(runner.run(exp, _trivial_fn))
        assert exp.status == ExperimentStatus.COMPLETED

    def test_run_failure_status(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        result = _run(runner.run(exp, _failing_fn))
        assert exp.status    == ExperimentStatus.FAILED
        assert result.is_success is False

    def test_run_failure_captures_error(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        result = _run(runner.run(exp, _failing_fn))
        assert "failed intentionally" in result.error

    def test_run_sets_started_at(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        _run(runner.run(exp, _trivial_fn))
        assert exp.started_at is not None

    def test_stats_updated_after_run(self):
        runner = ExperimentRunner()
        exp    = _make_experiment()
        _run(runner.run(exp, _trivial_fn))
        assert runner.stats()["runs"] == 1
        assert runner.stats()["successes"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# TestProjectManager
# ─────────────────────────────────────────────────────────────────────────────

class TestProjectManager:
    def test_create_and_get(self):
        mgr = ProjectManager()
        p   = _make_project()
        mgr.create(p)
        assert mgr.get(p.project_id).project_id == p.project_id

    def test_create_duplicate_raises(self):
        mgr = ProjectManager()
        p   = _make_project()
        mgr.create(p)
        with pytest.raises(ResearchProjectAlreadyExistsError):
            mgr.create(p)

    def test_delete(self):
        mgr = ProjectManager()
        p   = _make_project()
        mgr.create(p)
        mgr.delete(p.project_id)
        with pytest.raises(ResearchProjectNotFoundError):
            mgr.get(p.project_id)

    def test_capacity_enforced(self):
        mgr = ProjectManager(max_projects=2)
        mgr.create(_make_project("A"))
        mgr.create(_make_project("B"))
        with pytest.raises(ResearchProjectCapacityError):
            mgr.create(_make_project("C"))

    def test_activate(self):
        mgr = ProjectManager()
        p   = _make_project()
        mgr.create(p)
        mgr.activate(p.project_id)
        assert mgr.get(p.project_id).status == ResearchProjectStatus.ACTIVE

    def test_archive(self):
        mgr = ProjectManager()
        p   = _make_project()
        mgr.create(p)
        mgr.archive(p.project_id)
        assert mgr.get(p.project_id).status == ResearchProjectStatus.ARCHIVED

    def test_clone(self):
        mgr = ProjectManager()
        p   = _make_project("Original")
        mgr.create(p)
        cloned = mgr.clone(p.project_id, new_name="Cloned")
        assert cloned.project_id != p.project_id
        assert cloned.name == "Cloned"
        assert cloned.objective == p.objective

    def test_stats(self):
        mgr = ProjectManager()
        s   = mgr.stats()
        assert "total" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestExperimentRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentRegistry:
    def test_register_and_get(self):
        reg = ExperimentRegistry()
        exp = _make_experiment()
        reg.register(exp)
        assert reg.get(exp.experiment_id).experiment_id == exp.experiment_id

    def test_register_duplicate_raises(self):
        reg = ExperimentRegistry()
        exp = _make_experiment()
        reg.register(exp)
        with pytest.raises(ResearchExperimentAlreadyExistsError):
            reg.register(exp)

    def test_remove(self):
        reg = ExperimentRegistry()
        exp = _make_experiment()
        reg.register(exp)
        reg.remove(exp.experiment_id)
        with pytest.raises(ResearchExperimentNotFoundError):
            reg.get(exp.experiment_id)

    def test_find_by_status(self):
        reg = ExperimentRegistry()
        e1  = _make_experiment()
        e2  = _make_experiment()
        e2.status = ExperimentStatus.COMPLETED
        reg.register(e1)
        reg.register(e2)
        hits = reg.find_by_status(ExperimentStatus.DRAFT)
        assert len(hits) == 1

    def test_find_by_project(self):
        reg = ExperimentRegistry()
        e1  = _make_experiment(project_id="p-1")
        e2  = _make_experiment(project_id="p-2")
        reg.register(e1)
        reg.register(e2)
        assert len(reg.find_by_project("p-1")) == 1

    def test_capacity_enforced(self):
        reg = ExperimentRegistry(max_experiments=1)
        reg.register(_make_experiment())
        with pytest.raises(ResearchExperimentCapacityError):
            reg.register(_make_experiment())

    def test_count(self):
        reg = ExperimentRegistry()
        reg.register(_make_experiment())
        reg.register(_make_experiment())
        assert reg.count() == 2

    def test_stats(self):
        reg = ExperimentRegistry()
        s   = reg.stats()
        assert "total" in s
        assert "by_status" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchWorkflow
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchWorkflow:
    def test_add_step(self):
        wf   = ResearchWorkflow(project_id="p-1", name="WF")
        step = WorkflowStep(name="s1", experiment_id="e-1")
        wf.add_step(step)
        assert wf.step_count() == 1

    def test_add_step_with_dependency(self):
        wf = ResearchWorkflow()
        s1 = WorkflowStep(name="s1", experiment_id="e-1")
        wf.add_step(s1)
        s2 = WorkflowStep(name="s2", experiment_id="e-2", depends_on=[s1.step_id])
        wf.add_step(s2)
        assert wf.step_count() == 2

    def test_add_step_missing_dep_raises(self):
        wf = ResearchWorkflow()
        s  = WorkflowStep(name="s1", depends_on=["nonexistent-step-id"])
        with pytest.raises(WorkflowValidationError):
            wf.add_step(s)

    def test_next_runnable_no_deps(self):
        wf   = ResearchWorkflow()
        step = WorkflowStep(name="s1", experiment_id="e-1")
        wf.add_step(step)
        runnable = wf.next_runnable_steps()
        assert step in runnable

    def test_next_runnable_with_deps(self):
        wf = ResearchWorkflow()
        s1 = WorkflowStep(name="s1", experiment_id="e-1")
        wf.add_step(s1)
        s2 = WorkflowStep(name="s2", experiment_id="e-2", depends_on=[s1.step_id])
        wf.add_step(s2)
        # s2 not runnable until s1 completes
        assert s2 not in wf.next_runnable_steps()
        s1.status = "completed"
        assert s2 in wf.next_runnable_steps()

    def test_is_complete(self):
        wf   = ResearchWorkflow()
        step = WorkflowStep(name="s1", experiment_id="e-1")
        wf.add_step(step)
        assert not wf.is_complete()
        step.status = "completed"
        assert wf.is_complete()

    def test_execute_runs_all_steps(self):
        wf = ResearchWorkflow(project_id="p-1", name="WF")
        e1 = _make_experiment(name="E1")
        e2 = _make_experiment(name="E2")
        s1 = WorkflowStep(name="s1", experiment_id=e1.experiment_id)
        wf.add_step(s1)
        s2 = WorkflowStep(name="s2", experiment_id=e2.experiment_id, depends_on=[s1.step_id])
        wf.add_step(s2)
        experiments = {e1.experiment_id: e1, e2.experiment_id: e2}

        async def _runner(exp):
            runner = ExperimentRunner()
            return await runner.run(exp, _trivial_fn)

        results = _run(wf.execute(experiments, _runner))
        assert len(results) == 2
        assert wf.status == WorkflowStatus.COMPLETED

    def test_to_dict(self):
        wf = ResearchWorkflow(name="WF")
        d  = wf.to_dict()
        assert "workflow_id" in d
        assert "steps" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestDatasetManager
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetManager:
    def test_register_and_get(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        assert mgr.get(ds.dataset_id).dataset_id == ds.dataset_id

    def test_register_duplicate_raises(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        with pytest.raises(ResearchDatasetAlreadyExistsError):
            mgr.register(ds)

    def test_remove(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        mgr.remove(ds.dataset_id)
        with pytest.raises(ResearchDatasetNotFoundError):
            mgr.get(ds.dataset_id)

    def test_new_version_creates_child(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        child = mgr.new_version(ds.dataset_id, changes="Added features")
        assert child.parent_ids[-1]  == ds.dataset_id
        assert child.version         == "1.0.1"
        assert child.dataset_id      != ds.dataset_id

    def test_snapshot(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        snap = mgr.snapshot(ds.dataset_id, "baseline")
        assert snap.snapshot_id != ""

    def test_lineage(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        child = mgr.new_version(ds.dataset_id)
        chain = mgr.lineage(child.dataset_id)
        assert len(chain) == 1
        assert chain[0].dataset_id == ds.dataset_id

    def test_activate_changes_status(self):
        mgr = DatasetManager()
        ds  = _make_dataset()
        mgr.register(ds)
        mgr.activate(ds.dataset_id)
        assert mgr.get(ds.dataset_id).status == ResearchDatasetStatus.ACTIVE

    def test_capacity_enforced(self):
        mgr = DatasetManager(max_datasets=1)
        mgr.register(_make_dataset("A"))
        with pytest.raises(ResearchDatasetCapacityError):
            mgr.register(_make_dataset("B"))


# ─────────────────────────────────────────────────────────────────────────────
# TestExecutionTracker
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionTracker:
    def test_start_tracking(self):
        tracker = ExecutionTracker()
        tracker.start_tracking("s-1", total_steps=10)
        assert tracker.stats()["sessions_tracked"] == 1

    def test_update_progress(self):
        tracker = ExecutionTracker()
        tracker.start_tracking("s-1", total_steps=10)
        tracker.update_progress("s-1", step=5)
        prog = tracker.get_progress("s-1")
        assert prog["step"] == 5

    def test_save_checkpoint(self):
        tracker = ExecutionTracker()
        tracker.start_tracking("s-1")
        ckpt = tracker.save_checkpoint("s-1", {"w": [1, 2, 3]})
        assert ckpt.checkpoint_id != ""
        assert ckpt.data["w"]      == [1, 2, 3]

    def test_restore_checkpoint(self):
        tracker = ExecutionTracker()
        tracker.start_tracking("s-1")
        tracker.save_checkpoint("s-1", {"step": 5})
        ckpt = tracker.restore_checkpoint("s-1")
        assert ckpt is not None
        assert ckpt.status == CheckpointStatus.RESTORED

    def test_restore_none_when_no_checkpoints(self):
        tracker = ExecutionTracker()
        tracker.start_tracking("s-1")
        assert tracker.restore_checkpoint("s-1") is None

    def test_session_not_tracked_raises(self):
        tracker = ExecutionTracker()
        with pytest.raises(TrackingSessionNotFoundError):
            tracker.get_progress("unknown-session")


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchMonitor
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchMonitor:
    def test_record_start_increments_running(self):
        mon = ResearchMonitor()
        mon.record_start("e-1")
        assert mon.running_count() == 1

    def test_record_end_decrements_running(self):
        mon = ResearchMonitor()
        mon.record_start("e-1")
        mon.record_end("e-1", "completed")
        assert mon.running_count() == 0

    def test_success_rate(self):
        mon = ResearchMonitor()
        mon.record_start("e-1")
        mon.record_end("e-1", "completed")
        mon.record_start("e-2")
        mon.record_end("e-2", "failed")
        assert mon.success_rate() == pytest.approx(0.5)

    def test_alerts_when_exceeded_timeout(self):
        mon = ResearchMonitor(timeout_sec=0.0)
        mon.record_start("e-slow")
        time.sleep(0.01)
        alerts = mon.alerts()
        assert any("e-slow" in a for a in alerts)

    def test_no_alerts_when_within_timeout(self):
        mon = ResearchMonitor(timeout_sec=3_600.0)
        mon.record_start("e-fast")
        assert mon.alerts() == []

    def test_health_dict(self):
        mon = ResearchMonitor()
        h   = mon.health()
        assert "running"    in h
        assert "completed"  in h
        assert "success_rate" in h


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchContext
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchContext:
    def test_set_and_get(self):
        ResearchContext.set(operation="run", experiment_id="e-1")
        s = ResearchContext.get()
        assert s.operation     == "run"
        assert s.experiment_id == "e-1"
        ResearchContext.clear()

    def test_clear_resets(self):
        ResearchContext.set(operation="x")
        ResearchContext.clear()
        assert ResearchContext.get().operation == ""

    def test_scope(self):
        with ResearchContext.scope("query", project_id="p-1") as s:
            assert s.operation  == "query"
            assert s.project_id == "p-1"
        assert ResearchContext.get().operation == ""

    def test_elapsed_ms_positive(self):
        ResearchContext.set(operation="t")
        time.sleep(0.01)
        assert ResearchContext.get().elapsed_ms() > 0
        ResearchContext.clear()

    def test_thread_isolation(self):
        results: dict[str, str] = {}
        def _set(label: str):
            ResearchContext.set(operation=label)
            time.sleep(0.02)
            results[label] = ResearchContext.get().operation
        t1 = threading.Thread(target=_set, args=("A",))
        t2 = threading.Thread(target=_set, args=("B",))
        t1.start(); t2.start()
        t1.join();  t2.join()
        assert results["A"] == "A"
        assert results["B"] == "B"

    def test_nested_scope_clears_after(self):
        with ResearchContext.scope("outer"):
            with ResearchContext.scope("inner"):
                assert ResearchContext.get().operation == "inner"
        assert ResearchContext.get().operation == ""


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchRegistry:
    def test_register_and_get(self):
        reg = ResearchRegistry()
        p   = _make_project()
        reg.register(p)
        assert reg.get(p.project_id).project_id == p.project_id

    def test_duplicate_raises(self):
        reg = ResearchRegistry()
        p   = _make_project()
        reg.register(p)
        with pytest.raises(ResearchProjectAlreadyExistsError):
            reg.register(p)

    def test_unregister(self):
        reg = ResearchRegistry()
        p   = _make_project()
        reg.register(p)
        reg.unregister(p.project_id)
        with pytest.raises(ResearchProjectNotFoundError):
            reg.get(p.project_id)

    def test_capacity(self):
        reg = ResearchRegistry(max_projects=1)
        reg.register(_make_project("A"))
        with pytest.raises(ResearchRegistryFullError):
            reg.register(_make_project("B"))

    def test_find_by_status(self):
        reg = ResearchRegistry()
        p   = _make_project()
        p.status = ResearchProjectStatus.ACTIVE
        reg.register(p)
        hits = reg.find_by_status(ResearchProjectStatus.ACTIVE)
        assert len(hits) == 1

    def test_stats(self):
        reg = ResearchRegistry()
        s   = reg.stats()
        assert "total" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchFactory:
    def test_create_registry(self):
        r = ResearchFactory.create_registry()
        assert isinstance(r, ResearchRegistry)

    def test_create_project_manager(self):
        m = ResearchFactory.create_project_manager()
        assert isinstance(m, ProjectManager)

    def test_create_experiment_registry(self):
        r = ResearchFactory.create_experiment_registry()
        assert isinstance(r, ExperimentRegistry)

    def test_create_experiment_lifecycle(self):
        lc = ResearchFactory.create_experiment_lifecycle()
        assert isinstance(lc, ExperimentLifecycle)

    def test_create_experiment_runner(self):
        r = ResearchFactory.create_experiment_runner()
        assert isinstance(r, ExperimentRunner)

    def test_create_dataset_manager(self):
        d = ResearchFactory.create_dataset_manager()
        assert isinstance(d, DatasetManager)

    def test_create_workflow(self):
        wf = ResearchFactory.create_workflow(project_id="p-1", name="WF")
        assert isinstance(wf, ResearchWorkflow)
        assert wf.project_id == "p-1"

    def test_create_research_monitor(self):
        m = ResearchFactory.create_research_monitor()
        assert isinstance(m, ResearchMonitor)


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchManager
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchManager:
    def test_create_project(self):
        mgr = _make_manager()
        p   = _make_project()
        mgr.create_project(p)
        assert mgr.get_project(p.project_id).project_id == p.project_id

    def test_clone_project(self):
        mgr = _make_manager()
        p   = _make_project("Original")
        mgr.create_project(p)
        cloned = mgr.clone_project(p.project_id, new_name="Cloned")
        assert cloned.project_id != p.project_id
        assert cloned.name       == "Cloned"

    def test_archive_project(self):
        mgr = _make_manager()
        p   = _make_project()
        mgr.create_project(p)
        mgr.archive_project(p.project_id)
        assert mgr.get_project(p.project_id).status == ResearchProjectStatus.ARCHIVED

    def test_create_experiment(self):
        mgr = _make_manager()
        p   = _make_project()
        mgr.create_project(p)
        exp = _make_experiment(project_id=p.project_id)
        mgr.create_experiment(exp)
        assert mgr.get_experiment(exp.experiment_id).experiment_id == exp.experiment_id

    def test_run_experiment(self):
        mgr = _make_manager()
        p   = _make_project()
        mgr.create_project(p)
        exp = _make_experiment(project_id=p.project_id)
        mgr.create_experiment(exp)
        result = _run(mgr.run_experiment(exp.experiment_id, _trivial_fn))
        assert result.is_success is True

    def test_cancel_experiment(self):
        mgr = _make_manager()
        exp = _make_experiment()
        mgr.create_experiment(exp)
        # Must be in a cancellable state (QUEUED)
        mgr.queue_experiment(exp.experiment_id)
        mgr.cancel_experiment(exp.experiment_id)
        assert mgr.get_experiment(exp.experiment_id).status == ExperimentStatus.CANCELLED

    def test_compare_experiments(self):
        mgr = _make_manager()
        e1  = _make_experiment(name="E1")
        e2  = _make_experiment(name="E2")
        mgr.create_experiment(e1)
        mgr.create_experiment(e2)
        _run(mgr.run_experiment(e1.experiment_id, _trivial_fn))
        _run(mgr.run_experiment(e2.experiment_id, _trivial_fn))
        cmp = mgr.compare_experiments([e1.experiment_id, e2.experiment_id])
        assert e1.experiment_id in cmp["experiments"]
        assert e2.experiment_id in cmp["experiments"]

    def test_register_dataset(self):
        mgr = _make_manager()
        ds  = _make_dataset()
        mgr.register_dataset(ds)
        assert mgr.get_dataset(ds.dataset_id).dataset_id == ds.dataset_id

    def test_history_records_events(self):
        mgr = _make_manager()
        p   = _make_project()
        mgr.create_project(p)
        assert mgr._history.count() >= 1

    def test_stats(self):
        mgr = _make_manager()
        s   = mgr.stats()
        assert "total_projects" in s


# ─────────────────────────────────────────────────────────────────────────────
# TestResearchEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchEngine:
    def setup_method(self):
        reset_research_engine()

    def teardown_method(self):
        reset_research_engine()

    def _started(self) -> ResearchEngine:
        e = ResearchEngine()
        _run(e.start())
        return e

    def test_initial_status_stopped(self):
        e = ResearchEngine()
        assert e.status() == ResearchEngineStatus.STOPPED

    def test_start(self):
        e = self._started()
        assert e.is_running() is True

    def test_stop(self):
        e = self._started()
        _run(e.stop())
        assert e.is_running() is False

    def test_double_start_raises(self):
        e = self._started()
        with pytest.raises(ResearchEngineAlreadyRunningError):
            _run(e.start())

    def test_op_before_start_raises(self):
        e = ResearchEngine()
        with pytest.raises(ResearchEngineNotRunningError):
            e.create_project(_make_project())

    def test_create_and_get_project(self):
        e = self._started()
        p = _make_project()
        e.create_project(p)
        assert e.get_project(p.project_id).project_id == p.project_id

    def test_create_and_run_experiment(self):
        e   = self._started()
        p   = _make_project()
        e.create_project(p)
        exp = _make_experiment(project_id=p.project_id)
        e.create_experiment(exp)
        result = _run(e.run_experiment(exp.experiment_id, _trivial_fn))
        assert result.is_success is True

    def test_register_dataset(self):
        e  = self._started()
        ds = _make_dataset()
        e.register_dataset(ds)
        assert e.get_dataset(ds.dataset_id).dataset_id == ds.dataset_id

    def test_uptime_positive(self):
        e = self._started()
        time.sleep(0.01)
        assert e.uptime_sec() > 0

    def test_stats(self):
        e = self._started()
        s = e.stats()
        assert "version" in s
        assert "status"  in s


# ─────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    def setup_method(self):
        reset_research_engine()

    def teardown_method(self):
        reset_research_engine()

    def test_same_instance(self):
        a = get_research_engine()
        b = get_research_engine()
        assert a is b

    def test_reset_clears(self):
        a = get_research_engine()
        reset_research_engine()
        b = get_research_engine()
        assert a is not b

    def test_not_running_by_default(self):
        e = get_research_engine()
        assert e.is_running() is False

    def test_auto_start(self):
        e = get_research_engine(auto_start=True)
        assert e.is_running() is True

    def test_thread_safety(self):
        instances: list = []
        def _get():
            instances.append(get_research_engine())
        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(i is instances[0] for i in instances)
