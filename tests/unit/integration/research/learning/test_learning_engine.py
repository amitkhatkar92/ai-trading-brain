"""test_learning_engine.py — Comprehensive tests for the AI Learning Framework."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Optional

import pytest

from iios.integration.research.learning import (
    get_learning_engine,
    reset_learning_engine,
    LearningEngine,
    LearningConfiguration,
    TrainingResult,
    Experiment,
    DatasetRecord,
    TrainingDataset,
    ValidationDataset,
    TestDataset as HeldOutDataset,
    FeatureDefinition,
    FeaturePipeline,
    BaseModel,
    ModelMetadata,
    TrainingJob,
    MetricsEngine,
    EvaluationReport,
    DeploymentRecord,
    DriftDetector,
    DriftResult,
)
from iios.integration.research.learning.learning_constants import (
    JobStatus,
    LearningEngineStatus,
    ModelStatus,
    LearningType,
    ModelTask,
    DataSplitStrategy,
    FeatureType,
    DeploymentStatus,
    DeploymentStrategy,
    DriftType,
    AlertSeverity,
    ValidationStatus,
    ExperimentStatus,
    LEARNING_ENGINE_VERSION,
    DEFAULT_TRAIN_SPLIT,
    DEFAULT_VAL_SPLIT,
    DEFAULT_TEST_SPLIT,
    PSI_DRIFT_THRESHOLD,
    MIN_DATASET_SIZE,
)
from iios.integration.research.learning.learning_exceptions import (
    LearningError,
    EngineNotRunningError,
    EngineAlreadyRunningError,
    JobNotFoundError,
    JobStateError,
    DatasetNotFoundError,
    InsufficientDataError,
    ModelNotFoundError,
    TrainingError,
    FeatureNotFoundError,
    FeaturePipelineError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


class MockModel:
    """Minimal implementation of the BaseModel Protocol for testing."""

    def __init__(
        self,
        model_id:      str          = "mock-model-001",
        name:          str          = "MockModel",
        version:       str          = "1.0.0",
        model_task:    ModelTask    = ModelTask.REGRESSION,
        learning_type: LearningType = LearningType.SUPERVISED,
        fail:          bool         = False,
        async_fit:     bool         = False,
    ) -> None:
        self.model_id      = model_id
        self.name          = name
        self.version       = version
        self.model_task    = model_task
        self.learning_type = learning_type
        self._fitted       = False
        self._fail         = fail
        self._async_fit    = async_fit
        self.fit_call_count = 0

    def fit(self, dataset: Any, config: Any) -> dict[str, float]:
        if self._fail:
            raise RuntimeError("Intentional fit failure")
        self._fitted = True
        self.fit_call_count += 1
        return {"train_loss": 0.05, "val_loss": 0.08, "accuracy": 0.92}

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        return {"prediction": 1.0, "confidence": 0.9}

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"prediction": 1.0} for _ in records]

    def evaluate(self, dataset: Any) -> dict[str, float]:
        return {"accuracy": 0.91, "val_loss": 0.09}

    def save(self, path: str) -> None:
        pass

    def load(self, path: str) -> None:
        pass

    def is_fitted(self) -> bool:
        return self._fitted

    def get_profile(self) -> Any:
        from iios.integration.research.learning.models.model_profile import ModelProfile
        return ModelProfile.create(self.model_id, self.version)

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "name": self.name, "version": self.version}


class AsyncMockModel(MockModel):
    """Mock model with async fit and predict_batch."""

    async def fit(self, dataset: Any, config: Any) -> dict[str, float]:  # type: ignore[override]
        await asyncio.sleep(0)
        self._fitted = True
        self.fit_call_count += 1
        return {"train_loss": 0.03, "val_loss": 0.07}


def _make_records(n: int = 30, with_labels: bool = True) -> list[DatasetRecord]:
    import random
    rng = random.Random(42)
    records = []
    for i in range(n):
        features = {"x1": rng.uniform(0, 1), "x2": rng.uniform(0, 1), "x3": float(i)}
        label    = rng.choice([0, 1]) if with_labels else None
        records.append(DatasetRecord.create(features=features, label=label))
    return records


def _make_dataset(n: int = 30, name: str = "test_ds") -> TrainingDataset:
    return TrainingDataset.create(name, _make_records(n), label_name="y")


def _fresh_engine() -> LearningEngine:
    reset_learning_engine()
    engine = get_learning_engine()
    _run(engine.start())
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_string(self):
        assert LEARNING_ENGINE_VERSION == "1.0.0"

    def test_splits_sum_to_one(self):
        assert abs(DEFAULT_TRAIN_SPLIT + DEFAULT_VAL_SPLIT + DEFAULT_TEST_SPLIT - 1.0) < 1e-6

    def test_psi_threshold(self):
        assert PSI_DRIFT_THRESHOLD == 0.20

    def test_min_dataset_size(self):
        assert MIN_DATASET_SIZE == 10

    def test_all_job_statuses(self):
        assert len(JobStatus) == 7

    def test_all_model_tasks(self):
        assert len(ModelTask) >= 6

    def test_all_learning_types(self):
        assert len(LearningType) >= 5

    def test_all_deployment_strategies(self):
        assert len(DeploymentStrategy) >= 4

    def test_enum_values_lowercase(self):
        for status in JobStatus:
            assert status.value == status.value.lower()
        for task in ModelTask:
            assert task.value == task.value.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_exception_code(self):
        e = LearningError("oops")
        assert e.code == "ML-000"

    def test_repr_contains_code_and_message(self):
        e = EngineNotRunningError("not started")
        r = repr(e)
        assert "ML-001" in r
        assert "not started" in r

    def test_exception_hierarchy(self):
        assert issubclass(EngineNotRunningError, LearningError)
        assert issubclass(JobNotFoundError, LearningError)
        assert issubclass(TrainingError, LearningError)

    def test_all_ml_codes_unique(self):
        from iios.integration.research.learning import learning_exceptions as lex
        import inspect
        codes = [
            cls.code
            for _, cls in inspect.getmembers(lex, inspect.isclass)
            if issubclass(cls, LearningError) and cls is not LearningError
        ]
        assert len(codes) == len(set(codes)), "Duplicate exception codes found"

    def test_job_not_found_code(self):
        assert JobNotFoundError.code == "ML-010"

    def test_dataset_not_found_code(self):
        assert DatasetNotFoundError.code == "ML-021"

    def test_training_error_code(self):
        assert TrainingError.code == "ML-050"


# ─────────────────────────────────────────────────────────────────────────────
# 3. LearningConfiguration
# ─────────────────────────────────────────────────────────────────────────────

class TestLearningConfiguration:
    def test_default_values(self):
        cfg = LearningConfiguration()
        assert abs(cfg.train_split - 0.70) < 1e-6
        assert cfg.max_epochs == 1000
        assert cfg.batch_size == 32

    def test_validate_passes(self):
        cfg = LearningConfiguration()
        errors = cfg.validate()
        assert errors == []

    def test_validate_bad_splits(self):
        cfg = LearningConfiguration(train_split=0.8, val_split=0.1, test_split=0.05)
        errors = cfg.validate()
        assert any("sum" in e.lower() for e in errors)

    def test_validate_bad_epochs(self):
        cfg = LearningConfiguration(max_epochs=0)
        errors = cfg.validate()
        assert any("epoch" in e.lower() for e in errors)

    def test_validate_bad_lr(self):
        cfg = LearningConfiguration(learning_rate=-0.1)
        errors = cfg.validate()
        assert any("learning_rate" in e.lower() for e in errors)

    def test_to_dict_keys(self):
        cfg = LearningConfiguration()
        d = cfg.to_dict()
        assert "train_split" in d
        assert "max_epochs" in d
        assert "hyperparameters" in d

    def test_hyperparameters_dict(self):
        cfg = LearningConfiguration(hyperparameters={"n_estimators": 100})
        assert cfg.hyperparameters["n_estimators"] == 100

    def test_split_strategy_roundtrip(self):
        cfg = LearningConfiguration(split_strategy=DataSplitStrategy.TIME_SERIES)
        d = cfg.to_dict()
        assert d["split_strategy"] == "time_series"


# ─────────────────────────────────────────────────────────────────────────────
# 4. DatasetRecord & TrainingDataset
# ─────────────────────────────────────────────────────────────────────────────

class TestDataset:
    def test_record_create(self):
        rec = DatasetRecord.create({"x": 1.0}, label=0)
        assert rec.row_id.startswith("row_")
        assert rec.features["x"] == 1.0
        assert rec.label == 0

    def test_record_to_dict(self):
        rec = DatasetRecord.create({"x": 1.0})
        d = rec.to_dict()
        assert "row_id" in d
        assert "features" in d

    def test_dataset_create(self):
        ds = _make_dataset(20)
        assert len(ds) == 20
        assert ds.name == "test_ds"

    def test_dataset_iteration(self):
        ds = _make_dataset(10)
        count = sum(1 for _ in ds)
        assert count == 10

    def test_split_train_val_test(self):
        ds = _make_dataset(100)
        train, val, test = ds.split_train_val_test()
        assert len(train) + len(val) + len(test) == 100
        assert len(train) > len(val)

    def test_split_returns_correct_types(self):
        ds = _make_dataset(100)
        train, val, test = ds.split_train_val_test()
        assert isinstance(train, TrainingDataset)
        assert isinstance(val, ValidationDataset)
        assert isinstance(test, HeldOutDataset)

    def test_split_too_small_raises(self):
        ds = _make_dataset(5)  # below MIN_DATASET_SIZE=10
        with pytest.raises(InsufficientDataError):
            ds.split_train_val_test()

    def test_time_series_split(self):
        ds = _make_dataset(50)
        folds = ds.split_time_series(n_folds=5)
        assert len(folds) == 5
        for train, val in folds:
            assert len(train) > 0
            assert len(val) > 0

    def test_stats_computed(self):
        ds = _make_dataset(30)
        stats = ds.stats()
        assert stats.total_records == 30
        assert stats.feature_count > 0

    def test_record_dicts(self):
        ds = _make_dataset(5)
        dicts = ds.record_dicts()
        assert len(dicts) == 5
        assert "x1" in dicts[0]

    def test_dataset_to_dict(self):
        ds = _make_dataset(10)
        d = ds.to_dict()
        assert d["record_count"] == 10


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dataset Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetRegistry:
    def test_register_and_get(self):
        from iios.integration.research.learning.datasets.dataset_registry import DatasetRegistry
        reg = DatasetRegistry()
        ds  = _make_dataset(20)
        reg.register(ds)
        result = reg.get(ds.dataset_id)
        assert result.dataset_id == ds.dataset_id

    def test_get_missing_raises(self):
        from iios.integration.research.learning.datasets.dataset_registry import DatasetRegistry
        reg = DatasetRegistry()
        with pytest.raises(DatasetNotFoundError):
            reg.get("no-such-id")

    def test_count(self):
        from iios.integration.research.learning.datasets.dataset_registry import DatasetRegistry
        reg = DatasetRegistry()
        reg.register(_make_dataset(10, "ds1"))
        reg.register(_make_dataset(10, "ds2"))
        assert reg.count() == 2

    def test_version_created_on_register(self):
        from iios.integration.research.learning.datasets.dataset_registry import DatasetRegistry
        reg = DatasetRegistry()
        ds  = _make_dataset(10)
        ver = reg.register(ds)
        assert ver.version == ds.version

    def test_capacity_enforced(self):
        from iios.integration.research.learning.datasets.dataset_registry import DatasetRegistry
        from iios.integration.research.learning.learning_exceptions import DatasetError
        reg = DatasetRegistry(max_datasets=2)
        reg.register(_make_dataset(10, "a"))
        reg.register(_make_dataset(10, "b"))
        with pytest.raises(DatasetError):
            reg.register(_make_dataset(10, "c"))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Feature layer
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureDefinition:
    def test_create(self):
        f = FeatureDefinition.create("price", FeatureType.NUMERIC, min_value=0.0)
        assert f.name == "price"
        assert f.feature_type == FeatureType.NUMERIC

    def test_validate_in_range(self):
        f = FeatureDefinition.create("x", FeatureType.NUMERIC, min_value=0.0, max_value=1.0)
        assert f.validate_value(0.5) == []

    def test_validate_below_min(self):
        f = FeatureDefinition.create("x", FeatureType.NUMERIC, min_value=0.0)
        errors = f.validate_value(-1.0)
        assert errors

    def test_validate_wrong_type(self):
        f = FeatureDefinition.create("x", FeatureType.BOOLEAN)
        errors = f.validate_value("yes")
        assert errors

    def test_validate_categorical_ok(self):
        f = FeatureDefinition.create("color", FeatureType.CATEGORICAL, allowed_vals=["red", "blue"])
        assert f.validate_value("red") == []

    def test_validate_categorical_fail(self):
        f = FeatureDefinition.create("color", FeatureType.CATEGORICAL, allowed_vals=["red", "blue"])
        errors = f.validate_value("green")
        assert errors

    def test_required_none_fails(self):
        f = FeatureDefinition.create("x", FeatureType.NUMERIC, required=True)
        errors = f.validate_value(None)
        assert errors

    def test_optional_none_ok(self):
        f = FeatureDefinition.create("x", FeatureType.NUMERIC, required=False)
        assert f.validate_value(None) == []

    def test_to_dict(self):
        f = FeatureDefinition.create("vol", FeatureType.NUMERIC)
        d = f.to_dict()
        assert d["name"] == "vol"


class TestFeaturePipeline:
    def _make_pass_through_transformer(self):
        """A transformer that simply passes records through."""
        class PassThrough:
            transformer_id = "pt_001"
            name = "pass_through"
            _fitted = False
            def fit(self, records): self._fitted = True
            def transform(self, record): return dict(record)
            def is_fitted(self): return self._fitted
            def to_dict(self): return {"name": self.name}
        return PassThrough()

    def test_add_step(self):
        pipe = FeaturePipeline()
        pipe.add_step(self._make_pass_through_transformer())
        assert pipe.step_count() == 1

    def test_fit_and_transform(self):
        pipe = FeaturePipeline()
        pipe.add_step(self._make_pass_through_transformer())
        records = [{"x": 1.0}, {"x": 2.0}]
        pipe.fit(records)
        result = pipe.transform({"x": 3.0})
        assert result["x"] == 3.0

    def test_transform_before_fit_raises(self):
        pipe = FeaturePipeline()
        pipe.add_step(self._make_pass_through_transformer())
        with pytest.raises(FeaturePipelineError):
            pipe.transform({"x": 1.0})

    def test_transform_batch(self):
        pipe = FeaturePipeline()
        pipe.add_step(self._make_pass_through_transformer())
        records = [{"x": float(i)} for i in range(5)]
        pipe.fit(records)
        results = pipe.transform_batch(records)
        assert len(results) == 5

    def test_pipeline_to_dict(self):
        pipe = FeaturePipeline(name="test_pipe")
        pipe.add_step(self._make_pass_through_transformer())
        d = pipe.to_dict()
        assert d["name"] == "test_pipe"
        assert d["step_count"] == 1


class TestFeatureTransformerProtocol:
    def test_protocol_is_runtime_checkable(self):
        from iios.integration.research.learning.features.feature_transformer import FeatureTransformerProtocol
        class GoodTransformer:
            transformer_id = "g1"
            name = "good"
            def transform(self, record): return record
            def fit(self, records): pass
            def is_fitted(self): return True
            def to_dict(self): return {}
        assert isinstance(GoodTransformer(), FeatureTransformerProtocol)

    def test_non_conforming_not_instance(self):
        from iios.integration.research.learning.features.feature_transformer import FeatureTransformerProtocol
        class Bad:
            pass
        assert not isinstance(Bad(), FeatureTransformerProtocol)


class TestFeatureEngine:
    def test_define_and_get_feature(self):
        from iios.integration.research.learning.features.feature_engine import FeatureEngine
        eng = FeatureEngine()
        feat = FeatureDefinition.create("rsi", FeatureType.NUMERIC)
        eng.define_feature(feat)
        result = eng.get_feature("rsi")
        assert result.name == "rsi"

    def test_get_missing_feature_raises(self):
        from iios.integration.research.learning.features.feature_engine import FeatureEngine
        eng = FeatureEngine()
        with pytest.raises(FeatureNotFoundError):
            eng.get_feature("ghost")

    def test_stats(self):
        from iios.integration.research.learning.features.feature_engine import FeatureEngine
        eng = FeatureEngine()
        d = eng.stats()
        assert "features_registered" in d


# ─────────────────────────────────────────────────────────────────────────────
# 7. Model layer
# ─────────────────────────────────────────────────────────────────────────────

class TestBaseModelProtocol:
    def test_mock_model_satisfies_protocol(self):
        assert isinstance(MockModel(), BaseModel)

    def test_non_model_fails_protocol(self):
        class Dummy:
            pass
        assert not isinstance(Dummy(), BaseModel)


class TestModelMetadata:
    def test_create(self):
        meta = ModelMetadata.create("Forecaster", ModelTask.FORECASTING, LearningType.SUPERVISED)
        assert meta.name == "Forecaster"
        assert meta.status == ModelStatus.DRAFT

    def test_mark_trained(self):
        meta = ModelMetadata.create("M1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        meta.mark_trained("job-123", {"accuracy": 0.9})
        assert meta.status == ModelStatus.TRAINED
        assert meta.metrics["accuracy"] == 0.9

    def test_mark_deployed(self):
        meta = ModelMetadata.create("M1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        meta.mark_deployed()
        assert meta.status == ModelStatus.DEPLOYED
        assert meta.deployed_at is not None

    def test_to_dict(self):
        meta = ModelMetadata.create("M1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        d = meta.to_dict()
        assert d["name"] == "M1"
        assert d["status"] == "draft"


class TestModelRegistry:
    def test_register_and_get(self):
        from iios.integration.research.learning.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        meta = ModelMetadata.create("M1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        reg.register(meta)
        result = reg.get(meta.model_id)
        assert result.name == "M1"

    def test_get_missing_raises(self):
        from iios.integration.research.learning.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        with pytest.raises(ModelNotFoundError):
            reg.get("no-such-model")

    def test_by_task_filter(self):
        from iios.integration.research.learning.models.model_registry import ModelRegistry
        reg = ModelRegistry()
        reg.register(ModelMetadata.create("A", ModelTask.REGRESSION, LearningType.SUPERVISED))
        reg.register(ModelMetadata.create("B", ModelTask.CLASSIFICATION, LearningType.SUPERVISED))
        reg.register(ModelMetadata.create("C", ModelTask.REGRESSION, LearningType.SUPERVISED))
        reg_models = reg.by_task(ModelTask.REGRESSION)
        assert len(reg_models) == 2

    def test_capacity(self):
        from iios.integration.research.learning.models.model_registry import ModelRegistry
        from iios.integration.research.learning.learning_exceptions import ModelError
        reg = ModelRegistry(max_models=2)
        reg.register(ModelMetadata.create("A", ModelTask.REGRESSION, LearningType.SUPERVISED))
        reg.register(ModelMetadata.create("B", ModelTask.REGRESSION, LearningType.SUPERVISED))
        with pytest.raises(ModelError):
            reg.register(ModelMetadata.create("C", ModelTask.REGRESSION, LearningType.SUPERVISED))


# ─────────────────────────────────────────────────────────────────────────────
# 8. TrainingJob
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingJob:
    def test_create(self):
        cfg = LearningConfiguration()
        job = TrainingJob.create("mdl1", "ds1", cfg)
        assert job.status == JobStatus.PENDING
        assert job.job_id.startswith("job_")

    def test_start_transition(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        job.start()
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_complete_transition(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        job.start()
        job.complete("result-001")
        assert job.status == JobStatus.COMPLETED
        assert job.result_id == "result-001"

    def test_fail_transition(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        job.start()
        job.fail("boom")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "boom"

    def test_cancel_from_queued(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        job.cancel()
        assert job.status == JobStatus.CANCELLED

    def test_invalid_transition_raises(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        # Cannot complete from PENDING
        with pytest.raises(JobStateError):
            job.complete("r1")

    def test_is_terminal(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        assert not job.is_terminal()
        job.status = JobStatus.QUEUED
        job.start()
        job.complete("r")
        assert job.is_terminal()

    def test_elapsed_sec(self):
        job = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        job.start()
        time.sleep(0.01)
        elapsed = job.elapsed_sec()
        assert elapsed >= 0.01

    def test_to_dict(self):
        job = TrainingJob.create("m", "d", LearningConfiguration(), tags=["v2"])
        d = job.to_dict()
        assert d["status"] == "pending"
        assert d["tags"] == ["v2"]


# ─────────────────────────────────────────────────────────────────────────────
# 9. TrainingEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingEngine:
    def test_run_sync_model(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        model  = MockModel()
        job    = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        ds     = _make_dataset(20)
        result = _run(engine.run_job(job, model, ds))
        assert isinstance(result, TrainingResult)
        assert result.is_success

    def test_run_async_model(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        model  = AsyncMockModel()
        job    = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        ds     = _make_dataset(20)
        result = _run(engine.run_job(job, model, ds))
        assert result.is_success

    def test_run_failing_model_raises(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        model  = MockModel(fail=True)
        job    = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        ds     = _make_dataset(20)
        with pytest.raises(TrainingError):
            _run(engine.run_job(job, model, ds))
        assert job.status == JobStatus.FAILED

    def test_job_status_becomes_completed(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        model  = MockModel()
        job    = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        _run(engine.run_job(job, model, _make_dataset(20)))
        assert job.status == JobStatus.COMPLETED

    def test_result_contains_metrics(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        model  = MockModel()
        job    = TrainingJob.create("m", "d", LearningConfiguration())
        job.status = JobStatus.QUEUED
        result = _run(engine.run_job(job, model, _make_dataset(20)))
        assert result.has_metric("train_loss")
        assert result.get_metric("accuracy") == pytest.approx(0.92)

    def test_engine_stats(self):
        from iios.integration.research.learning.training.training_engine import TrainingEngine
        engine = TrainingEngine()
        d = engine.stats()
        assert "total_run" in d


# ─────────────────────────────────────────────────────────────────────────────
# 10. Training Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingScheduler:
    def test_enqueue_and_pop(self):
        from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
        sched = TrainingScheduler()
        job   = TrainingJob.create("m", "d", LearningConfiguration())
        sched.enqueue(job, priority=3)
        popped = sched.pop_next()
        assert popped is not None
        assert popped.job_id == job.job_id

    def test_priority_ordering(self):
        from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
        sched = TrainingScheduler()
        job1 = TrainingJob.create("m", "d", LearningConfiguration())
        job2 = TrainingJob.create("m", "d", LearningConfiguration())
        sched.enqueue(job1, priority=5)
        sched.enqueue(job2, priority=1)  # higher priority
        first = sched.pop_next()
        assert first.job_id == job2.job_id

    def test_duplicate_enqueue_raises(self):
        from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
        from iios.integration.research.learning.learning_exceptions import JobAlreadyExistsError
        sched = TrainingScheduler()
        job   = TrainingJob.create("m", "d", LearningConfiguration())
        sched.enqueue(job)
        with pytest.raises(JobAlreadyExistsError):
            sched.enqueue(job)

    def test_pop_empty_returns_none(self):
        from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
        sched = TrainingScheduler()
        assert sched.pop_next() is None

    def test_stats(self):
        from iios.integration.research.learning.training.training_scheduler import TrainingScheduler
        sched = TrainingScheduler()
        job = TrainingJob.create("m", "d", LearningConfiguration())
        sched.enqueue(job)
        d = sched.stats()
        assert d["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 11. Checkpoint Manager
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckpointManager:
    def test_add_and_latest(self):
        from iios.integration.research.learning.training.checkpoint_manager import (
            CheckpointManager, Checkpoint
        )
        mgr  = CheckpointManager()
        ckpt = Checkpoint.create("job-1", epoch=1, metrics={"val_loss": 0.1})
        mgr.add(ckpt)
        latest = mgr.latest("job-1")
        assert latest is not None
        assert latest.epoch == 1

    def test_best_by_metric(self):
        from iios.integration.research.learning.training.checkpoint_manager import (
            CheckpointManager, Checkpoint
        )
        mgr = CheckpointManager()
        for i in range(3):
            mgr.add(Checkpoint.create("j1", epoch=i, metrics={"val_loss": 0.1 * (3 - i)}))
        best = mgr.best("j1", "val_loss", higher_is_better=False)
        assert best is not None
        assert best.epoch == 2  # lowest val_loss

    def test_count(self):
        from iios.integration.research.learning.training.checkpoint_manager import (
            CheckpointManager, Checkpoint
        )
        mgr = CheckpointManager()
        for i in range(5):
            mgr.add(Checkpoint.create("j1", epoch=i, metrics={}))
        assert mgr.count("j1") == 5


# ─────────────────────────────────────────────────────────────────────────────
# 12. Hyperparameter Manager
# ─────────────────────────────────────────────────────────────────────────────

class TestHyperparameterManager:
    def test_defaults(self):
        from iios.integration.research.learning.training.hyperparameter_manager import (
            HyperparameterManager, HyperparameterSpec
        )
        mgr = HyperparameterManager()
        mgr.register_spec(HyperparameterSpec.float("lr", 1e-4, 1e-2, default=1e-3))
        d = mgr.defaults()
        assert d["lr"] == pytest.approx(1e-3)

    def test_random_sample_in_range(self):
        from iios.integration.research.learning.training.hyperparameter_manager import (
            HyperparameterManager, HyperparameterSpec
        )
        mgr = HyperparameterManager(seed=0)
        mgr.register_spec(HyperparameterSpec.float("x", 0.0, 1.0, default=0.5))
        s = mgr.sample_random()
        assert 0.0 <= s["x"] <= 1.0

    def test_integer_sample(self):
        from iios.integration.research.learning.training.hyperparameter_manager import (
            HyperparameterManager, HyperparameterSpec
        )
        mgr = HyperparameterManager(seed=7)
        mgr.register_spec(HyperparameterSpec.integer("k", 2, 10, default=5))
        for _ in range(10):
            s = mgr.sample_random()
            assert 2 <= s["k"] <= 10

    def test_categorical_sample(self):
        from iios.integration.research.learning.training.hyperparameter_manager import (
            HyperparameterManager, HyperparameterSpec
        )
        mgr = HyperparameterManager(seed=1)
        mgr.register_spec(HyperparameterSpec.categorical("activation", ["relu", "tanh"], "relu"))
        for _ in range(5):
            s = mgr.sample_random()
            assert s["activation"] in ("relu", "tanh")


# ─────────────────────────────────────────────────────────────────────────────
# 13. MetricsEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricsEngine:
    def setup_method(self):
        self.eng = MetricsEngine()

    def test_classification_accuracy(self):
        m = self.eng.compute_classification([0, 1, 1, 0], [0, 1, 0, 0])
        assert m["accuracy"] == pytest.approx(0.75)

    def test_classification_perfect(self):
        m = self.eng.compute_classification([0, 1, 1], [0, 1, 1])
        assert m["accuracy"] == pytest.approx(1.0)
        assert m["f1_macro"] == pytest.approx(1.0)

    def test_regression_mae(self):
        m = self.eng.compute_regression([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert m["mae"] == pytest.approx(0.0)
        assert m["r_squared"] == pytest.approx(1.0)

    def test_regression_r2(self):
        m = self.eng.compute_regression([1.0, 2.0, 3.0, 4.0], [1.1, 2.1, 3.1, 4.1])
        assert m["r_squared"] > 0.99

    def test_forecasting_directional_accuracy(self):
        actuals = [1.0, 2.0, 3.0, 2.5]
        preds   = [1.1, 2.1, 2.9, 2.4]
        m = self.eng.compute_forecasting(actuals, preds)
        assert "directional_accuracy" in m

    def test_ranking_spearman(self):
        actuals = [1.0, 2.0, 3.0, 4.0]
        scores  = [1.1, 2.2, 3.3, 4.4]
        m = self.eng.compute_ranking(actuals, scores)
        assert m["spearman_rho"] == pytest.approx(1.0)

    def test_compute_router_classification(self):
        m = self.eng.compute(ModelTask.CLASSIFICATION, [0, 1], [0, 1])
        assert "accuracy" in m

    def test_compute_router_regression(self):
        m = self.eng.compute(ModelTask.REGRESSION, [1.0, 2.0], [1.0, 2.0])
        assert "mae" in m

    def test_mismatched_lengths_raises(self):
        from iios.integration.research.learning.learning_exceptions import MetricsError
        with pytest.raises(MetricsError):
            self.eng.compute_classification([0, 1], [0])


# ─────────────────────────────────────────────────────────────────────────────
# 14. EvaluationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationEngine:
    def test_evaluate_with_model_evaluate_method(self):
        from iios.integration.research.learning.evaluation.evaluation_engine import EvaluationEngine
        eng    = EvaluationEngine()
        model  = MockModel()
        ds     = _make_dataset(20)
        report = _run(eng.evaluate(model, ds, ModelTask.CLASSIFICATION))
        assert isinstance(report, EvaluationReport)
        assert report.status in (ValidationStatus.PASSED, ValidationStatus.FAILED)

    def test_evaluate_via_predict_batch(self):
        from iios.integration.research.learning.evaluation.evaluation_engine import EvaluationEngine
        class PredictOnlyModel(MockModel):
            def evaluate(self, dataset): raise NotImplementedError  # type: ignore
        eng    = EvaluationEngine()
        model  = PredictOnlyModel()
        ds     = _make_dataset(20)
        # no evaluate() → fallback to predict_batch
        report = _run(eng.evaluate(model, ds, ModelTask.REGRESSION))
        assert isinstance(report, EvaluationReport)

    def test_report_has_model_id(self):
        from iios.integration.research.learning.evaluation.evaluation_engine import EvaluationEngine
        eng    = EvaluationEngine()
        model  = MockModel(model_id="eval-model")
        ds     = _make_dataset(20)
        report = _run(eng.evaluate(model, ds, ModelTask.CLASSIFICATION))
        assert report.model_id == "eval-model"


class TestEvaluationReport:
    def test_create(self):
        r = EvaluationReport.create(
            model_id="m1", model_version="1.0", dataset_id="ds1",
            model_task=ModelTask.REGRESSION,
            metrics={"mae": 0.1}, evaluation_sec=0.5,
        )
        assert r.has_metric("mae")
        assert r.get_metric("mae") == pytest.approx(0.1)

    def test_get_metric_default(self):
        r = EvaluationReport.create("m", "1", "ds", ModelTask.REGRESSION, {}, 0.1)
        assert r.get_metric("missing", default=99.0) == pytest.approx(99.0)

    def test_to_dict(self):
        r = EvaluationReport.create("m", "1", "ds", ModelTask.REGRESSION, {"r2": 0.9}, 0.2)
        d = r.to_dict()
        assert d["metrics"]["r2"] == pytest.approx(0.9)


class TestModelComparator:
    def test_compare_picks_best_lower(self):
        from iios.integration.research.learning.evaluation.model_comparator import ModelComparator
        mc = ModelComparator()
        r1 = EvaluationReport.create("m1", "1", "ds", ModelTask.REGRESSION, {"mae": 0.2}, 0.1)
        r2 = EvaluationReport.create("m2", "1", "ds", ModelTask.REGRESSION, {"mae": 0.1}, 0.1)
        result = mc.compare([r1, r2], "mae", higher_is_better=False)
        assert result.winner_model_id == "m2"

    def test_compare_picks_best_higher(self):
        from iios.integration.research.learning.evaluation.model_comparator import ModelComparator
        mc = ModelComparator()
        r1 = EvaluationReport.create("m1", "1", "ds", ModelTask.CLASSIFICATION, {"accuracy": 0.9}, 0.1)
        r2 = EvaluationReport.create("m2", "1", "ds", ModelTask.CLASSIFICATION, {"accuracy": 0.85}, 0.1)
        result = mc.compare([r1, r2], "accuracy", higher_is_better=True)
        assert result.winner_model_id == "m1"


class TestCrossValidator:
    def test_k_fold_count(self):
        from iios.integration.research.learning.evaluation.cross_validation import CrossValidator
        cv = CrossValidator(n_folds=5)
        splits = cv.k_fold_splits(50)
        assert len(splits) == 5

    def test_k_fold_no_overlap(self):
        from iios.integration.research.learning.evaluation.cross_validation import CrossValidator
        cv = CrossValidator(n_folds=3)
        splits = cv.k_fold_splits(30)
        for train_idx, val_idx in splits:
            assert len(set(train_idx) & set(val_idx)) == 0

    def test_walk_forward_expanding(self):
        from iios.integration.research.learning.evaluation.cross_validation import CrossValidator
        cv = CrossValidator(n_folds=4)
        splits = cv.walk_forward_splits(40)
        for i in range(1, len(splits)):
            assert len(splits[i][0]) > len(splits[i - 1][0])


# ─────────────────────────────────────────────────────────────────────────────
# 15. Deployment layer
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentEngine:
    def test_deploy_direct(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng = DeploymentEngine()
        rec = eng.deploy("m1", "1.0")
        assert rec.status == DeploymentStatus.CHAMPION

    def test_champion_is_retrievable(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng = DeploymentEngine()
        eng.deploy("m1", "1.0")
        champ = eng.champion("m1")
        assert champ is not None

    def test_new_deploy_retires_old(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng  = DeploymentEngine()
        rec1 = eng.deploy("m1", "1.0")
        rec2 = eng.deploy("m1", "2.0")
        assert rec1.status == DeploymentStatus.RETIRED
        assert rec2.status == DeploymentStatus.CHAMPION

    def test_rollback(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng  = DeploymentEngine()
        eng.deploy("m1", "1.0")
        eng.deploy("m1", "2.0")
        restored = eng.rollback("m1", reason="regression")
        assert restored is not None
        assert restored.model_version == "1.0"

    def test_shadow_deploy_status(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng = DeploymentEngine()
        rec = eng.deploy("m1", "1.0", strategy=DeploymentStrategy.SHADOW)
        assert rec.status == DeploymentStatus.SHADOW

    def test_stats(self):
        from iios.integration.research.learning.deployment.deployment_engine import DeploymentEngine
        eng = DeploymentEngine()
        d   = eng.stats()
        assert "total_deployed" in d


class TestDeploymentPolicy:
    def test_default_policy(self):
        from iios.integration.research.learning.deployment.deployment_policy import DeploymentPolicy
        p = DeploymentPolicy.default()
        assert p.strategy == DeploymentStrategy.DIRECT

    def test_promotion_eligible_pass(self):
        from iios.integration.research.learning.deployment.deployment_policy import DeploymentPolicy
        p = DeploymentPolicy.default()
        p.min_metric_thresholds = {"accuracy": 0.8}
        ok, reasons = p.check_promotion_eligible({"accuracy": 0.9})
        assert ok
        assert reasons == []

    def test_promotion_eligible_fail(self):
        from iios.integration.research.learning.deployment.deployment_policy import DeploymentPolicy
        p = DeploymentPolicy.default()
        p.min_metric_thresholds = {"accuracy": 0.8}
        ok, reasons = p.check_promotion_eligible({"accuracy": 0.7})
        assert not ok
        assert len(reasons) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 16. Drift detection
# ─────────────────────────────────────────────────────────────────────────────

class TestDriftDetector:
    def test_no_drift_on_identical_data(self):
        det = DriftDetector()
        data = [{"x": float(i)} for i in range(50)]
        result = det.check_data_drift("m1", data, data)
        assert not result.is_drifted

    def test_drift_detected_on_shifted_data(self):
        det  = DriftDetector(psi_threshold=0.10)
        base = [{"x": float(i)} for i in range(50)]
        curr = [{"x": float(i) + 100.0} for i in range(50)]
        result = det.check_data_drift("m1", base, curr)
        assert result.is_drifted
        assert result.drift_type == DriftType.DATA_DRIFT

    def test_performance_drift_no_change(self):
        det    = DriftDetector()
        base   = {"accuracy": 0.9, "val_loss": 0.1}
        result = det.check_performance_drift("m1", base, base)
        assert not result.is_drifted

    def test_performance_drift_detected(self):
        det    = DriftDetector(psi_threshold=0.10)
        base   = {"accuracy": 0.9}
        curr   = {"accuracy": 0.5}  # big drop
        result = det.check_performance_drift("m1", base, curr)
        assert result.is_drifted

    def test_psi_identical(self):
        det  = DriftDetector()
        vals = [float(i) for i in range(100)]
        psi  = det.psi(vals, vals)
        assert psi == pytest.approx(0.0, abs=1e-6)

    def test_psi_high_for_shifted(self):
        det  = DriftDetector()
        base = [float(i) for i in range(100)]
        curr = [float(i) + 200 for i in range(100)]
        psi  = det.psi(base, curr)
        assert psi > 0.20

    def test_mean_shift_zero(self):
        det  = DriftDetector()
        vals = [float(i) for i in range(50)]
        score = det.mean_shift_score(vals, vals)
        assert score == pytest.approx(0.0)

    def test_mean_shift_large(self):
        det  = DriftDetector()
        base = [1.0] * 50
        curr = [100.0] * 50
        score = det.mean_shift_score(base, curr)
        assert score > 2.0

    def test_result_to_dict(self):
        det  = DriftDetector()
        data = [{"x": 1.0}]
        r    = det.check_data_drift("m1", data, data)
        d    = r.to_dict()
        assert "drift_score" in d

    def test_stats_counts(self):
        det  = DriftDetector()
        data = [{"x": float(i)} for i in range(20)]
        det.check_data_drift("m1", data, data)
        s = det.stats()
        assert s["checks_run"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 17. Alert Manager
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertManager:
    def test_raise_alert(self):
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        mgr   = AlertManager()
        alert = mgr.raise_alert(AlertSeverity.WARNING, "drift", "test drift")
        assert not alert.resolved
        assert alert.severity == AlertSeverity.WARNING

    def test_resolve_alert(self):
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        mgr   = AlertManager()
        alert = mgr.raise_alert(AlertSeverity.INFO, "test", "hello")
        mgr.resolve(alert.alert_id)
        assert alert.resolved

    def test_open_alerts_filter(self):
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        mgr = AlertManager()
        a1  = mgr.raise_alert(AlertSeverity.INFO, "cat", "m1")
        a2  = mgr.raise_alert(AlertSeverity.CRITICAL, "cat", "m2")
        mgr.resolve(a1.alert_id)
        open_ = mgr.open_alerts()
        assert len(open_) == 1
        assert open_[0].alert_id == a2.alert_id

    def test_handler_called(self):
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        received = []
        mgr = AlertManager()
        mgr.register_handler(lambda a: received.append(a.alert_id))
        mgr.raise_alert(AlertSeverity.WARNING, "test", "fired")
        assert len(received) == 1

    def test_stats(self):
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        mgr = AlertManager()
        mgr.raise_alert(AlertSeverity.INFO, "c", "m")
        s = mgr.stats()
        assert s["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 18. Experiment Tracker
# ─────────────────────────────────────────────────────────────────────────────

class TestExperimentTracker:
    def test_create_experiment(self):
        from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker
        tracker = ExperimentTracker()
        exp = tracker.create_experiment("EXP1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        assert exp.name == "EXP1"
        assert exp.status == ExperimentStatus.ACTIVE

    def test_add_job(self):
        from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker
        tracker = ExperimentTracker()
        exp = tracker.create_experiment("EXP2", ModelTask.REGRESSION, LearningType.SUPERVISED)
        tracker.add_job(exp.experiment_id, "job-001")
        assert "job-001" in tracker.get(exp.experiment_id).job_ids

    def test_update_best(self):
        from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker
        tracker = ExperimentTracker()
        exp = tracker.create_experiment("EXP3", ModelTask.REGRESSION, LearningType.SUPERVISED,
                                        best_metric_name="val_loss", higher_is_better=False)
        tracker.update_best(exp.experiment_id, "job-1", 0.5)
        tracker.update_best(exp.experiment_id, "job-2", 0.3)
        updated = tracker.get(exp.experiment_id)
        assert updated.best_job_id == "job-2"
        assert updated.best_metric_value == pytest.approx(0.3)

    def test_complete_experiment(self):
        from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker
        tracker = ExperimentTracker()
        exp = tracker.create_experiment("EXP4", ModelTask.CLASSIFICATION, LearningType.SUPERVISED)
        tracker.complete(exp.experiment_id)
        assert tracker.get(exp.experiment_id).status == ExperimentStatus.COMPLETED

    def test_get_missing_raises(self):
        from iios.integration.research.learning.experiments.experiment_tracker import ExperimentTracker
        from iios.integration.research.learning.learning_exceptions import ExperimentNotFoundError
        tracker = ExperimentTracker()
        with pytest.raises(ExperimentNotFoundError):
            tracker.get("no-such-exp")


# ─────────────────────────────────────────────────────────────────────────────
# 19. LearningEngine (singleton facade)
# ─────────────────────────────────────────────────────────────────────────────

class TestLearningEngineLifecycle:
    def setup_method(self):
        reset_learning_engine()

    def test_get_engine_returns_same_instance(self):
        e1 = get_learning_engine()
        e2 = get_learning_engine()
        assert e1 is e2

    def test_start_sets_running(self):
        engine = get_learning_engine()
        _run(engine.start())
        assert engine.is_running()
        assert engine.status() == LearningEngineStatus.RUNNING

    def test_double_start_raises(self):
        engine = get_learning_engine()
        _run(engine.start())
        with pytest.raises(EngineAlreadyRunningError):
            _run(engine.start())

    def test_stop_sets_stopped(self):
        engine = get_learning_engine()
        _run(engine.start())
        _run(engine.stop())
        assert engine.status() == LearningEngineStatus.STOPPED

    def test_uptime_increases(self):
        engine = get_learning_engine()
        _run(engine.start())
        t0 = engine.uptime_sec()
        time.sleep(0.02)
        t1 = engine.uptime_sec()
        assert t1 > t0

    def test_reset_clears_singleton(self):
        e1 = get_learning_engine()
        reset_learning_engine()
        e2 = get_learning_engine()
        assert e1 is not e2

    def test_auto_start(self):
        reset_learning_engine()
        engine = get_learning_engine(auto_start=True)
        assert engine.is_running()


class TestLearningEngineOperations:
    def setup_method(self):
        self.engine = _fresh_engine()

    def teardown_method(self):
        if self.engine.is_running():
            _run(self.engine.stop())
        reset_learning_engine()

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def test_create_job(self):
        cfg = LearningConfiguration()
        job = self.engine.create_job("m1", "ds1", cfg)
        assert isinstance(job, TrainingJob)
        assert job.status == JobStatus.QUEUED

    def test_get_job_after_create(self):
        cfg = LearningConfiguration()
        job = self.engine.create_job("m1", "ds1", cfg)
        found = self.engine.get_job(job.job_id)
        assert found.job_id == job.job_id

    def test_get_missing_job_raises(self):
        with pytest.raises(JobNotFoundError):
            self.engine.get_job("no-such-job")

    def test_list_jobs_by_status(self):
        cfg = LearningConfiguration()
        self.engine.create_job("m1", "ds1", cfg)
        queued = self.engine.list_jobs(status=JobStatus.QUEUED)
        assert len(queued) == 1

    def test_cancel_job(self):
        cfg = LearningConfiguration()
        job = self.engine.create_job("m1", "ds1", cfg)
        self.engine.cancel_job(job.job_id)
        assert job.status == JobStatus.CANCELLED

    def test_run_job_end_to_end(self):
        model = MockModel()
        ds    = _make_dataset(30)
        self.engine.register_dataset(ds)
        cfg = LearningConfiguration()
        job = self.engine.create_job(model.model_id, ds.dataset_id, cfg)
        result = _run(self.engine.run_job(job.job_id, model, ds))
        assert result.is_success
        assert job.status == JobStatus.COMPLETED

    def test_run_failing_job_raises_training_error(self):
        model = MockModel(fail=True)
        ds    = _make_dataset(20)
        cfg   = LearningConfiguration()
        job   = self.engine.create_job(model.model_id, ds.dataset_id, cfg)
        with pytest.raises(TrainingError):
            _run(self.engine.run_job(job.job_id, model, ds))

    # ── Models ────────────────────────────────────────────────────────────────

    def test_register_and_get_model(self):
        meta = ModelMetadata.create("Reg1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        self.engine.register_model(meta)
        found = self.engine.get_model(meta.model_id)
        assert found.name == "Reg1"

    def test_get_missing_model_raises(self):
        with pytest.raises(ModelNotFoundError):
            self.engine.get_model("nope")

    def test_list_models_by_task(self):
        self.engine.register_model(
            ModelMetadata.create("R", ModelTask.REGRESSION, LearningType.SUPERVISED)
        )
        self.engine.register_model(
            ModelMetadata.create("C", ModelTask.CLASSIFICATION, LearningType.SUPERVISED)
        )
        regs = self.engine.list_models(task=ModelTask.REGRESSION)
        assert len(regs) == 1

    def test_model_marked_trained_after_job(self):
        model = MockModel(model_id="m-trained")
        meta  = ModelMetadata.create("Trained", ModelTask.REGRESSION, LearningType.SUPERVISED,
                                     model_id="m-trained")
        self.engine.register_model(meta)
        ds  = _make_dataset(20)
        cfg = LearningConfiguration()
        job = self.engine.create_job("m-trained", ds.dataset_id, cfg)
        _run(self.engine.run_job(job.job_id, model, ds))
        updated = self.engine.get_model("m-trained")
        assert updated.status == ModelStatus.TRAINED

    # ── Datasets ──────────────────────────────────────────────────────────────

    def test_register_and_get_dataset(self):
        ds = _make_dataset(20)
        self.engine.register_dataset(ds)
        found = self.engine.get_dataset(ds.dataset_id)
        assert found.dataset_id == ds.dataset_id

    def test_get_missing_dataset_raises(self):
        with pytest.raises(DatasetNotFoundError):
            self.engine.get_dataset("no-such-ds")

    # ── Experiments ───────────────────────────────────────────────────────────

    def test_create_and_get_experiment(self):
        exp = self.engine.create_experiment("Exp1", ModelTask.REGRESSION, LearningType.SUPERVISED)
        found = self.engine.get_experiment(exp.experiment_id)
        assert found.name == "Exp1"

    def test_job_linked_to_experiment(self):
        exp = self.engine.create_experiment("E2", ModelTask.REGRESSION, LearningType.SUPERVISED)
        cfg = LearningConfiguration()
        job = self.engine.create_job("m1", "ds1", cfg, experiment_id=exp.experiment_id)
        found_exp = self.engine.get_experiment(exp.experiment_id)
        assert job.job_id in found_exp.job_ids

    # ── Deployment ────────────────────────────────────────────────────────────

    def test_deploy_model(self):
        rec = self.engine.deploy_model("m1", "1.0")
        assert isinstance(rec, DeploymentRecord)
        assert rec.status == DeploymentStatus.CHAMPION

    def test_deploy_updates_model_status(self):
        meta = ModelMetadata.create("Dep", ModelTask.REGRESSION, LearningType.SUPERVISED,
                                    model_id="dep-1")
        self.engine.register_model(meta)
        self.engine.deploy_model("dep-1", "1.0")
        updated = self.engine.get_model("dep-1")
        assert updated.status == ModelStatus.DEPLOYED

    def test_rollback_model(self):
        self.engine.deploy_model("m1", "1.0")
        self.engine.deploy_model("m1", "2.0")
        restored = self.engine.rollback_model("m1", reason="test rollback")
        assert restored is not None
        assert restored.model_version == "1.0"

    # ── Evaluation ────────────────────────────────────────────────────────────

    def test_evaluate_via_engine(self):
        model = MockModel()
        ds    = _make_dataset(20)
        report = _run(self.engine.evaluate(
            model.model_id, model.version, ds, model, ModelTask.CLASSIFICATION
        ))
        assert isinstance(report, EvaluationReport)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def test_stats_structure(self):
        s = self.engine.stats()
        assert "status" in s
        assert "jobs" in s
        assert "models" in s
        assert "datasets" in s
        assert "experiments" in s
        assert "deployments" in s

    def test_stats_uptime(self):
        time.sleep(0.01)
        s = self.engine.stats()
        assert s["uptime_sec"] >= 0.01

    # ── Guard: operations require running engine ───────────────────────────────

    def test_create_job_requires_running(self):
        _run(self.engine.stop())
        with pytest.raises(EngineNotRunningError):
            self.engine.create_job("m", "d", LearningConfiguration())

    def test_register_model_requires_running(self):
        _run(self.engine.stop())
        meta = ModelMetadata.create("X", ModelTask.REGRESSION, LearningType.SUPERVISED)
        with pytest.raises(EngineNotRunningError):
            self.engine.register_model(meta)


# ─────────────────────────────────────────────────────────────────────────────
# 20. Feature Store
# ─────────────────────────────────────────────────────────────────────────────

class TestFeatureStore:
    def test_put_and_get(self):
        from iios.integration.research.learning.features.feature_store import FeatureStore
        store = FeatureStore()
        store.put("entity-1", {"rsi": 70.0, "vol": 1.5})
        result = store.get("entity-1")
        assert result["rsi"] == 70.0

    def test_get_missing_raises(self):
        from iios.integration.research.learning.features.feature_store import FeatureStore
        store = FeatureStore()
        with pytest.raises(FeatureNotFoundError):
            store.get("ghost")

    def test_put_batch(self):
        from iios.integration.research.learning.features.feature_store import FeatureStore
        store = FeatureStore()
        store.put_batch({"e1": {"x": 1.0}, "e2": {"x": 2.0}})
        assert store.count() == 2

    def test_ttl_eviction(self):
        from iios.integration.research.learning.features.feature_store import FeatureStore
        store = FeatureStore()
        store.put("e1", {"x": 1.0}, ttl_sec=0.01)
        time.sleep(0.05)
        assert not store.has("e1")

    def test_delete(self):
        from iios.integration.research.learning.features.feature_store import FeatureStore
        store = FeatureStore()
        store.put("e1", {"x": 1.0})
        store.delete("e1")
        assert not store.has("e1")


# ─────────────────────────────────────────────────────────────────────────────
# 21. LearningHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestLearningHistory:
    def test_append_and_count(self):
        from iios.integration.research.learning.core.learning_history import (
            LearningHistory, LearningHistoryEntry
        )
        history = LearningHistory()
        entry   = LearningHistoryEntry.create("job", "j1", "created")
        history.append(entry)
        assert history.count() == 1

    def test_query_by_entity_id(self):
        from iios.integration.research.learning.core.learning_history import (
            LearningHistory, LearningHistoryEntry
        )
        history = LearningHistory()
        history.append(LearningHistoryEntry.create("job", "j1", "created"))
        history.append(LearningHistoryEntry.create("job", "j2", "created"))
        results = history.query(entity_id="j1")
        assert len(results) == 1

    def test_query_by_event_type(self):
        from iios.integration.research.learning.core.learning_history import (
            LearningHistory, LearningHistoryEntry
        )
        history = LearningHistory()
        history.append(LearningHistoryEntry.create("job", "j1", "created"))
        history.append(LearningHistoryEntry.create("job", "j1", "completed"))
        results = history.query(event_type="completed")
        assert len(results) == 1

    def test_max_entries_respected(self):
        from iios.integration.research.learning.core.learning_history import (
            LearningHistory, LearningHistoryEntry
        )
        history = LearningHistory(max_entries=5)
        for i in range(10):
            history.append(LearningHistoryEntry.create("job", f"j{i}", "created"))
        assert history.count() == 5

    def test_latest(self):
        from iios.integration.research.learning.core.learning_history import (
            LearningHistory, LearningHistoryEntry
        )
        history = LearningHistory()
        for i in range(10):
            history.append(LearningHistoryEntry.create("job", f"j{i}", "e"))
        latest = history.latest(3)
        assert len(latest) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 22. Learning context
# ─────────────────────────────────────────────────────────────────────────────

class TestLearningContext:
    def test_set_and_get(self):
        from iios.integration.research.learning.learning_context import (
            set_context, get_context, clear_context
        )
        set_context("train_run", job_id="j1", model_id="m1")
        ctx = get_context()
        assert ctx is not None
        assert ctx.operation == "train_run"
        assert ctx.job_id == "j1"
        clear_context()
        assert get_context() is None

    def test_scope_contextmanager(self):
        from iios.integration.research.learning.learning_context import scope, get_context
        with scope("eval", model_id="m2") as ctx:
            assert ctx is not None
            assert ctx.model_id == "m2"
            in_scope_ctx = get_context()
            assert in_scope_ctx is not None
        assert get_context() is None

    def test_elapsed_ms(self):
        from iios.integration.research.learning.learning_context import set_context, get_context, clear_context
        set_context("op")
        time.sleep(0.01)
        ctx = get_context()
        assert ctx.elapsed_ms() >= 10.0
        clear_context()


# ─────────────────────────────────────────────────────────────────────────────
# 23. ModelVersion / ModelArtifact
# ─────────────────────────────────────────────────────────────────────────────

class TestModelVersion:
    def test_create(self):
        from iios.integration.research.learning.models.model_version import ModelVersion
        v = ModelVersion.create("m1", "1.0")
        assert v.model_id == "m1"
        assert not v.is_champion

    def test_promote(self):
        from iios.integration.research.learning.models.model_version import ModelVersion
        v = ModelVersion.create("m1", "1.0")
        v.promote()
        assert v.is_champion

    def test_to_dict(self):
        from iios.integration.research.learning.models.model_version import ModelVersion
        v = ModelVersion.create("m1", "1.0", metrics={"acc": 0.9})
        d = v.to_dict()
        assert d["version"] == "1.0"
        assert d["metrics"]["acc"] == 0.9


class TestModelArtifact:
    def test_create(self):
        from iios.integration.research.learning.models.model_artifact import ModelArtifact
        art = ModelArtifact.create("m1", "1.0", "/tmp/model.pkl")
        assert art.storage_path == "/tmp/model.pkl"

    def test_to_dict(self):
        from iios.integration.research.learning.models.model_artifact import ModelArtifact
        art = ModelArtifact.create("m1", "1.0", "/tmp/m.pkl", format="pkl")
        d = art.to_dict()
        assert d["format"] == "pkl"


# ─────────────────────────────────────────────────────────────────────────────
# 24. ModelProfile
# ─────────────────────────────────────────────────────────────────────────────

class TestModelProfile:
    def test_create(self):
        from iios.integration.research.learning.models.model_profile import ModelProfile
        p = ModelProfile.create("m1", "1.0")
        assert p.total_predictions == 0

    def test_to_dict(self):
        from iios.integration.research.learning.models.model_profile import ModelProfile
        p = ModelProfile.create("m1", "1.0", baseline_metrics={"accuracy": 0.9})
        d = p.to_dict()
        assert d["baseline_metrics"]["accuracy"] == 0.9


# ─────────────────────────────────────────────────────────────────────────────
# 25. ModelMonitor
# ─────────────────────────────────────────────────────────────────────────────

class TestModelMonitor:
    def test_record_batch_updates_profile(self):
        from iios.integration.research.learning.monitoring.model_monitor import ModelMonitor
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        alerts  = AlertManager()
        monitor = ModelMonitor(alerts)
        monitor.register("m1", "1.0")
        monitor.record_batch("m1", n_predictions=10, latency_ms=50.0)
        profile = monitor.get_profile("m1")
        assert profile.total_predictions == 10

    def test_high_error_rate_raises_alert(self):
        from iios.integration.research.learning.monitoring.model_monitor import ModelMonitor
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        alerts  = AlertManager()
        monitor = ModelMonitor(alerts, error_rate_limit=0.01)
        monitor.register("m2", "1.0")
        monitor.record_batch("m2", n_predictions=5, latency_ms=10.0, n_errors=5)
        open_ = alerts.open_alerts(severity=AlertSeverity.CRITICAL)
        assert len(open_) >= 1

    def test_stats(self):
        from iios.integration.research.learning.monitoring.model_monitor import ModelMonitor
        from iios.integration.research.learning.drift.alert_manager import AlertManager
        monitor = ModelMonitor(AlertManager())
        d = monitor.stats()
        assert "models_monitored" in d


# ─────────────────────────────────────────────────────────────────────────────
# 26. DatasetStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetStatistics:
    def test_compute_basic(self):
        from iios.integration.research.learning.datasets.dataset_statistics import DatasetStatistics
        records = [{"x": float(i), "label": i % 2} for i in range(20)]
        stats   = DatasetStatistics.compute(records, ["x"], "label")
        assert stats.total_records == 20
        assert "x" in stats.feature_means

    def test_empty_dataset(self):
        from iios.integration.research.learning.datasets.dataset_statistics import DatasetStatistics
        stats = DatasetStatistics.compute([], ["x"], "label")
        assert stats.total_records == 0

    def test_to_dict(self):
        from iios.integration.research.learning.datasets.dataset_statistics import DatasetStatistics
        records = [{"x": 1.0}]
        stats   = DatasetStatistics.compute(records, ["x"], None)
        d = stats.to_dict()
        assert "total_records" in d


# ─────────────────────────────────────────────────────────────────────────────
# 27. TrainingResult
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingResult:
    def test_create(self):
        r = TrainingResult.create(
            job_id="j1", model_id="m1", model_version="1.0",
            metrics={"accuracy": 0.9}, training_sec=1.5,
        )
        assert r.is_success
        assert r.has_metric("accuracy")

    def test_get_metric_default(self):
        r = TrainingResult.create("j", "m", "v", {}, 0.1)
        assert r.get_metric("missing", default=42.0) == pytest.approx(42.0)

    def test_to_dict(self):
        r = TrainingResult.create("j", "m", "v", {"mae": 0.05}, 0.8)
        d = r.to_dict()
        assert d["metrics"]["mae"] == pytest.approx(0.05)
        assert d["is_success"]


# ─────────────────────────────────────────────────────────────────────────────
# 28. Integration: full train → evaluate → deploy cycle
# ─────────────────────────────────────────────────────────────────────────────

class TestFullCycle:
    def setup_method(self):
        self.engine = _fresh_engine()

    def teardown_method(self):
        if self.engine.is_running():
            _run(self.engine.stop())
        reset_learning_engine()

    def test_train_evaluate_deploy(self):
        model = MockModel(model_id="full-cycle-model")
        meta  = ModelMetadata.create(
            "FullCycleModel", ModelTask.REGRESSION, LearningType.SUPERVISED,
            model_id="full-cycle-model"
        )
        self.engine.register_model(meta)

        ds  = _make_dataset(60)
        self.engine.register_dataset(ds)

        cfg = LearningConfiguration(max_epochs=5)
        job = self.engine.create_job("full-cycle-model", ds.dataset_id, cfg)
        result = _run(self.engine.run_job(job.job_id, model, ds))
        assert result.is_success

        report = _run(self.engine.evaluate(
            "full-cycle-model", "1.0.0", ds, model, ModelTask.REGRESSION
        ))
        assert isinstance(report, EvaluationReport)

        rec = self.engine.deploy_model("full-cycle-model", "1.0.0",
                                        metrics=report.metrics)
        assert rec.status == DeploymentStatus.CHAMPION

        updated = self.engine.get_model("full-cycle-model")
        assert updated.status == ModelStatus.DEPLOYED

    def test_experiment_tracking_full(self):
        exp = self.engine.create_experiment(
            "Full Exp", ModelTask.REGRESSION, LearningType.SUPERVISED,
            best_metric_name="val_loss", higher_is_better=False,
        )
        model = MockModel()
        ds    = _make_dataset(30)

        cfg = LearningConfiguration()
        job = self.engine.create_job(
            model.model_id, ds.dataset_id, cfg,
            experiment_id=exp.experiment_id,
        )
        result = _run(self.engine.run_job(job.job_id, model, ds))
        assert result.is_success

        updated_exp = self.engine.get_experiment(exp.experiment_id)
        assert job.job_id in updated_exp.job_ids

    def test_drift_detection_integration(self):
        baseline = [{"x": float(i), "y": float(i) * 2} for i in range(50)]
        shifted  = [{"x": float(i) + 1000, "y": float(i) * 2} for i in range(50)]

        detector = self.engine.drift_detector
        result   = detector.check_data_drift("integration-model", baseline, shifted)
        assert result.is_drifted

    def test_stats_after_cycle(self):
        model = MockModel()
        ds    = _make_dataset(30)
        cfg   = LearningConfiguration()
        job   = self.engine.create_job(model.model_id, ds.dataset_id, cfg)
        _run(self.engine.run_job(job.job_id, model, ds))
        self.engine.deploy_model(model.model_id, model.version)

        s = self.engine.stats()
        assert s["performance"]["total_jobs"] >= 1
        assert s["performance"]["total_deploys"] >= 1
