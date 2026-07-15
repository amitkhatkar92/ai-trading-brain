"""Tests for iios.common.async_exec.execution_classifier"""
import asyncio
from iios.common.async_exec.execution_classifier import (
    ClassificationResult,
    ExecutionClassifier,
    WorkloadType,
    classify,
    classify_as,
    _IO_PREFIXES,
    _CPU_PREFIXES,
)


# ── Helpers ────────────────────────────────────────────────────────────────

async def sample_coroutine():
    return 42


def fetch_data(url):
    pass


def compute_risk(weights):
    pass


def calculate_sharpe(returns):
    pass


def get_quotes(symbols):
    pass


def do_something():
    pass


# ── WorkloadType ────────────────────────────────────────────────────────────

class TestWorkloadType:

    def test_values_are_strings(self):
        for wt in WorkloadType:
            assert isinstance(wt.value, str)

    def test_expected_members(self):
        names = {wt.name for wt in WorkloadType}
        assert names == {"NATIVE_ASYNC", "IO_BOUND", "CPU_BOUND", "MIXED", "SYNC_WRAPPER"}

    def test_str_enum_comparison(self):
        assert WorkloadType.IO_BOUND == "io_bound"
        assert WorkloadType.CPU_BOUND == "cpu_bound"


# ── ClassificationResult ────────────────────────────────────────────────────

class TestClassificationResult:

    def test_frozen(self):
        result = ClassificationResult(
            workload_type        = WorkloadType.IO_BOUND,
            confidence           = 0.9,
            reason               = "test",
            recommended_executor = "thread_pool",
            callable_name        = "my_fn",
        )
        try:
            result.confidence = 0.5  # type: ignore[misc]
            assert False, "Should have raised"
        except (AttributeError, TypeError):
            pass

    def test_default_callable_name(self):
        result = ClassificationResult(
            workload_type        = WorkloadType.NATIVE_ASYNC,
            confidence           = 1.0,
            reason               = "r",
            recommended_executor = "native",
        )
        assert result.callable_name == ""


# ── ExecutionClassifier ─────────────────────────────────────────────────────

class TestExecutionClassifier:

    def setup_method(self):
        self.clf = ExecutionClassifier()

    # ── Coroutine detection ──────────────────────────────────────────────────

    def test_classify_coroutine_function(self):
        result = self.clf.classify(sample_coroutine)
        assert result.workload_type == WorkloadType.NATIVE_ASYNC
        assert result.confidence == 1.0
        assert result.recommended_executor == "native"

    def test_classify_lambda_is_not_native_async(self):
        result = self.clf.classify(lambda: None)
        assert result.workload_type != WorkloadType.NATIVE_ASYNC

    # ── IO heuristics ────────────────────────────────────────────────────────

    def test_fetch_prefix_is_io_bound(self):
        result = self.clf.classify(fetch_data)
        assert result.workload_type == WorkloadType.IO_BOUND
        assert result.confidence >= 0.5

    def test_get_prefix_is_io_bound(self):
        result = self.clf.classify(get_quotes)
        assert result.workload_type == WorkloadType.IO_BOUND

    def test_io_bound_uses_thread_pool(self):
        result = self.clf.classify(fetch_data)
        assert result.recommended_executor == "thread_pool"

    # ── CPU heuristics ───────────────────────────────────────────────────────

    def test_compute_prefix_is_cpu_bound(self):
        result = self.clf.classify(compute_risk)
        assert result.workload_type == WorkloadType.CPU_BOUND
        assert result.recommended_executor == "process_pool"

    def test_calculate_prefix_is_cpu_bound(self):
        result = self.clf.classify(calculate_sharpe)
        assert result.workload_type == WorkloadType.CPU_BOUND

    # ── Default fallback ─────────────────────────────────────────────────────

    def test_unknown_function_defaults_to_io_bound(self):
        result = self.clf.classify(do_something)
        assert result.workload_type == WorkloadType.IO_BOUND
        assert result.confidence == 0.4

    # ── Explicit annotation ──────────────────────────────────────────────────

    def test_explicit_annotation_overrides_all(self):
        @classify_as(WorkloadType.CPU_BOUND)
        def fetch_from_network():   # would normally be IO_BOUND by name
            pass
        result = self.clf.classify(fetch_from_network)
        assert result.workload_type == WorkloadType.CPU_BOUND
        assert result.confidence == 1.0

    def test_explicit_annotation_on_coroutine(self):
        @classify_as(WorkloadType.IO_BOUND)
        async def native_but_marked_io():
            pass
        result = self.clf.classify(native_but_marked_io)
        # Annotation wins over iscoroutinefunction
        assert result.workload_type == WorkloadType.IO_BOUND
        assert result.confidence == 1.0

    # ── classify_method ──────────────────────────────────────────────────────

    def test_classify_method_by_name(self):
        class MyEngine:
            def fetch_quotes(self):
                pass
        engine = MyEngine()
        result = self.clf.classify_method(engine, "fetch_quotes")
        assert result.workload_type == WorkloadType.IO_BOUND

    # ── Name extraction ──────────────────────────────────────────────────────

    def test_callable_name_extracted(self):
        result = self.clf.classify(fetch_data)
        assert result.callable_name == "fetch_data"

    def test_lambda_name_does_not_crash(self):
        result = self.clf.classify(lambda: None)
        assert result.callable_name is not None


# ── Module-level classify() ──────────────────────────────────────────────────

class TestModuleLevelClassify:

    def test_classify_shortcut(self):
        result = classify(sample_coroutine)
        assert result.workload_type == WorkloadType.NATIVE_ASYNC

    def test_classify_shortcut_sync(self):
        result = classify(fetch_data)
        assert result.workload_type == WorkloadType.IO_BOUND


# ── classify_as decorator ────────────────────────────────────────────────────

class TestClassifyAsDecorator:

    def test_decorator_sets_attribute(self):
        @classify_as(WorkloadType.CPU_BOUND)
        def my_fn():
            pass
        from iios.common.async_exec.execution_classifier import _ANNOTATION_ATTR
        assert getattr(my_fn, _ANNOTATION_ATTR) == WorkloadType.CPU_BOUND

    def test_decorated_fn_still_callable(self):
        @classify_as(WorkloadType.SYNC_WRAPPER)
        def my_fn():
            return 99
        assert my_fn() == 99

    def test_all_workload_types_can_be_annotated(self):
        for wt in WorkloadType:
            @classify_as(wt)
            def fn():
                pass
            result = classify(fn)
            assert result.workload_type == wt


# ── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_partial_function(self):
        import functools
        fn = functools.partial(fetch_data, "http://example.com")
        result = classify(fn)
        # partial wraps fetch_data — name heuristic should still work
        assert result is not None

    def test_builtin_function(self):
        result = classify(len)
        # builtin — no io/cpu hints, defaults to IO_BOUND
        assert result.workload_type in (WorkloadType.IO_BOUND, WorkloadType.CPU_BOUND, WorkloadType.SYNC_WRAPPER)

    def test_class_instance_callable(self):
        class Callable:
            def __call__(self):
                return 1
        result = classify(Callable())
        assert result is not None

    def test_confidence_in_range(self):
        for fn in [sample_coroutine, fetch_data, compute_risk, do_something]:
            result = classify(fn)
            assert 0.0 <= result.confidence <= 1.0

    def test_reason_is_non_empty(self):
        for fn in [sample_coroutine, fetch_data, compute_risk, do_something]:
            result = classify(fn)
            assert result.reason
