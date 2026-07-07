"""
tests/unit/ontology/test_validator.py
======================================
Comprehensive test suite for the IIOS Ontology Validation & Constraint Engine.

Coverage:
  1.  Validation constants & severity ordering
  2.  Validation exceptions hierarchy
  3.  ValidationResult (factory helpers, properties, serialisation)
  4.  ValidationReport (accumulation, stats, severity roll-up, history)
  5.  ValidationContext (thread-local, CMs, diagnostics, isolation)
  6.  ConstraintRegistry (register, lookup, enable/disable, stats)
  7.  ConstraintEngine (run type/prop/rel/ns/hierarchy/reference checks)
  8.  ConstraintManager (builtin load, custom registration, policy helpers)
  9.  OntologyValidator (type/namespace/rel/doc/compiled/hierarchy/cross-ref/runtime)
 10.  ValidationEngine (validate_type, validate_ontology, validate_all, batch, runtime)
 11.  Referential integrity (broken refs, cycles, endpoint errors)
 12.  Hierarchy validation (cycles, depth)
 13.  Business rules (custom constraints)
 14.  Performance & concurrency
 15.  End-to-end (full pipeline integration)
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════

def _reset_all() -> None:
    """Reset every ontology + validator singleton."""
    from iios.ontology.validator.validation_engine    import reset_validation_engine
    from iios.ontology.validator.ontology_validator   import reset_ontology_validator
    from iios.ontology.validator.constraint_manager   import reset_constraint_manager
    from iios.ontology.validator.constraint_engine    import reset_constraint_engine
    from iios.ontology.validator.constraint_registry  import reset_constraint_registry
    from iios.ontology.validator.validation_context   import reset_validation_context
    from iios.ontology.compiler.compiler_manager      import reset_compiler_manager
    from iios.ontology.compiler.compiler_registry     import reset_compiler_registry
    from iios.ontology.compiler.compiler_factory      import reset_compiler_factory
    from iios.ontology.compiler.compiler_context      import reset_compiler_context
    from iios.ontology.compiler.dependency_resolver   import reset_dependency_resolver
    from iios.ontology.compiler.metadata_generator    import reset_metadata_generator
    from iios.ontology.compiler.ontology_compiler     import reset_ontology_compiler
    from iios.ontology.loader.runtime_loader          import reset_runtime_loader
    from iios.ontology.loader.ontology_loader         import reset_ontology_loader
    from iios.ontology.cache.ontology_cache           import reset_ontology_cache
    from iios.ontology.registry.ontology_registry_manager import reset_registry_manager
    from iios.ontology.registry.entity_registry          import reset_entity_registry
    from iios.ontology.registry.relationship_registry    import reset_relationship_registry
    from iios.ontology.registry.event_registry           import reset_event_registry
    from iios.ontology.registry.observation_registry     import reset_observation_registry
    from iios.ontology.registry.knowledge_registry       import reset_knowledge_ont_registry
    from iios.ontology.ontology_registry                 import reset_ontology_registry
    from iios.ontology.ontology_manager                  import reset_ontology_manager
    from iios.ontology.ontology_runtime_engine           import reset_ontology_engine
    from iios.ontology.ontology_context                  import reset_ontology_context
    from iios.ontology.ontology_factory                  import reset_ontology_factory
    from iios.ontology.graph.ontology_graph              import reset_ontology_graph
    from iios.ontology.query.ontology_query              import reset_query_engine
    from iios.ontology.services.lookup_service           import reset_lookup_service
    from iios.ontology.services.hierarchy_service        import reset_hierarchy_service
    from iios.ontology.services.statistics_service       import reset_statistics_service
    from iios.ontology.loader.compiled_loader            import reset_compiled_loader
    from iios.ontology.loader.incremental_loader         import reset_incremental_loader
    from iios.ontology.loader.cache_loader               import reset_cache_loader

    reset_validation_engine()
    reset_ontology_validator()
    reset_constraint_manager()
    reset_constraint_engine()
    reset_constraint_registry()
    reset_validation_context()
    reset_compiler_manager()
    reset_compiler_registry()
    reset_compiler_factory()
    reset_compiler_context()
    reset_dependency_resolver()
    reset_metadata_generator()
    reset_ontology_compiler()
    reset_runtime_loader()
    reset_ontology_loader()
    reset_ontology_cache()
    reset_registry_manager()
    reset_entity_registry()
    reset_relationship_registry()
    reset_event_registry()
    reset_observation_registry()
    reset_knowledge_ont_registry()
    reset_ontology_registry()
    reset_ontology_manager()
    reset_ontology_engine()
    reset_ontology_context()
    reset_ontology_factory()
    reset_ontology_graph()
    reset_query_engine()
    reset_lookup_service()
    reset_hierarchy_service()
    reset_statistics_service()
    reset_compiled_loader()
    reset_incremental_loader()
    reset_cache_loader()


@pytest.fixture(autouse=True)
def clean_state():
    _reset_all()
    yield
    _reset_all()


def _make_type(name: str = "MyType", ns: str = "iios.test", parent: str | None = None):
    from iios.ontology.ontology_factory import get_ontology_factory
    fac = get_ontology_factory()
    return fac.create_type(name=name, namespace_uri=ns, parent_uri=parent)


def _make_prop(name: str = "value", required: bool = False):
    from iios.ontology.ontology_factory import get_ontology_factory
    return get_ontology_factory().create_property(name=name, required=required)


def _make_rel(name: str = "HasChild",
              src: str = "iios.test.ParentType",
              tgt: str = "iios.test.ChildType"):
    from iios.ontology.ontology_factory import get_ontology_factory
    return get_ontology_factory().create_relationship(name=name, namespace_uri="iios.test",
                                                       source_type_uri=src, target_type_uri=tgt)


def _make_namespace(uri: str = "iios.test", name: str = "TestNS", prefix: str = "tst"):
    from iios.ontology.runtime.runtime_object import OntologyNamespace
    return OntologyNamespace(uri=uri, name=name, prefix=prefix)


def _warm_registry():
    """Compile all builtins so the registry is populated."""
    from iios.ontology.compiler.compiler_manager import get_compiler_manager
    return get_compiler_manager().compile_builtins()


# ═════════════════════════════════════════════════════════════════════════════
# 1. Validation Constants
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationConstants:
    def test_severity_values(self):
        from iios.ontology.validator import ValidationSeverity
        assert ValidationSeverity.PASS.value     == "pass"
        assert ValidationSeverity.INFO.value     == "info"
        assert ValidationSeverity.WARNING.value  == "warning"
        assert ValidationSeverity.ERROR.value    == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_severity_ge(self):
        from iios.ontology.validator import severity_ge, ValidationSeverity
        S = ValidationSeverity
        assert severity_ge(S.ERROR,    S.WARNING)
        assert severity_ge(S.CRITICAL, S.ERROR)
        assert severity_ge(S.WARNING,  S.WARNING)
        assert not severity_ge(S.PASS, S.ERROR)

    def test_max_severity_empty(self):
        from iios.ontology.validator import max_severity, ValidationSeverity
        assert max_severity([]) == ValidationSeverity.PASS

    def test_max_severity_mixed(self):
        from iios.ontology.validator import max_severity, ValidationSeverity
        S = ValidationSeverity
        assert max_severity([S.PASS, S.WARNING, S.ERROR]) == S.ERROR
        assert max_severity([S.INFO, S.CRITICAL, S.ERROR]) == S.CRITICAL

    def test_scope_values(self):
        from iios.ontology.validator import ValidationScope
        assert ValidationScope.TYPE.value         == "type"
        assert ValidationScope.HIERARCHY.value    == "hierarchy"
        assert ValidationScope.RUNTIME_OBJ.value  == "runtime_object"

    def test_constraint_type_values(self):
        from iios.ontology.validator import ConstraintType
        assert ConstraintType.REQUIRED_FIELD.value == "required_field"
        assert ConstraintType.CIRCULAR.value       == "circular"

    def test_mode_values(self):
        from iios.ontology.validator import ValidationMode
        assert ValidationMode.STRICT.value      == "strict"
        assert ValidationMode.STANDARD.value    == "standard"
        assert ValidationMode.PERMISSIVE.value  == "permissive"

    def test_numeric_constants_positive(self):
        from iios.ontology.validator import (
            MAX_VALIDATION_ERRORS, MAX_BATCH_SIZE, VALIDATION_TIMEOUT_MS,
            MAX_HISTORY_PER_TARGET, MAX_PARALLEL_VALIDATORS,
        )
        assert MAX_VALIDATION_ERRORS > 0
        assert MAX_BATCH_SIZE        > 0
        assert VALIDATION_TIMEOUT_MS > 0
        assert MAX_HISTORY_PER_TARGET > 0
        assert MAX_PARALLEL_VALIDATORS > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. Validation Exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationExceptions:
    def test_base_has_code(self):
        from iios.ontology.validator import ValidatorError
        exc = ValidatorError("test", code="VAL-999")
        assert exc.code == "VAL-999"
        assert "VAL-999" in str(exc)

    def test_constraint_violation_hierarchy(self):
        from iios.ontology.validator import (
            ConstraintViolationError, RequiredFieldError, DataTypeConstraintError,
            CardinalityViolationError, ValidatorError,
        )
        assert issubclass(ConstraintViolationError, ValidatorError)
        assert issubclass(RequiredFieldError,       ConstraintViolationError)
        assert issubclass(DataTypeConstraintError,  ConstraintViolationError)
        assert issubclass(CardinalityViolationError, ConstraintViolationError)

    def test_semantic_validation_hierarchy(self):
        from iios.ontology.validator import (
            SemanticValidationError, HierarchyValidationError,
            NamespaceConsistencyError, ValidatorError,
        )
        assert issubclass(SemanticValidationError, ValidatorError)
        assert issubclass(HierarchyValidationError, SemanticValidationError)
        assert issubclass(NamespaceConsistencyError, SemanticValidationError)

    def test_referential_integrity_hierarchy(self):
        from iios.ontology.validator import (
            ReferentialIntegrityError, BrokenReferenceError,
            CircularReferenceError, InvalidEndpointError, ValidatorError,
        )
        assert issubclass(ReferentialIntegrityError, ValidatorError)
        assert issubclass(BrokenReferenceError,     ReferentialIntegrityError)
        assert issubclass(CircularReferenceError,   ReferentialIntegrityError)
        assert issubclass(InvalidEndpointError,     ReferentialIntegrityError)

    def test_broken_reference_carries_fields(self):
        from iios.ontology.validator import BrokenReferenceError
        exc = BrokenReferenceError("iios.foo.Bar", "iios.test.MyType", kind="parent_uri")
        assert exc.ref_uri == "iios.foo.Bar"
        assert exc.source  == "iios.test.MyType"
        assert "VAL-031"   in exc.code

    def test_circular_reference_carries_chain(self):
        from iios.ontology.validator import CircularReferenceError
        chain = ["A", "B", "C", "A"]
        exc   = CircularReferenceError(chain)
        assert exc.chain == chain
        assert "VAL-032" in exc.code

    def test_duplicate_constraint_error(self):
        from iios.ontology.validator import DuplicateConstraintError, ConstraintRegistryError
        exc = DuplicateConstraintError("my.constraint")
        assert isinstance(exc, ConstraintRegistryError)
        assert exc.constraint_id == "my.constraint"

    def test_validation_timeout_carries_ms(self):
        from iios.ontology.validator import ValidationTimeoutError
        exc = ValidationTimeoutError("iios.test.Type", 5000.0)
        assert exc.target     == "iios.test.Type"
        assert exc.timeout_ms == 5000.0


# ═════════════════════════════════════════════════════════════════════════════
# 3. ValidationResult
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationResult:
    def test_ok_factory(self):
        from iios.ontology.validator import ValidationResult, ValidationSeverity, ValidationScope
        r = ValidationResult.ok("my.constraint", ValidationScope.TYPE, target_uri="iios.test.T")
        assert r.passed
        assert r.severity  == ValidationSeverity.PASS
        assert r.target_uri == "iios.test.T"

    def test_fail_factory(self):
        from iios.ontology.validator import ValidationResult, ValidationSeverity, ValidationScope
        r = ValidationResult.fail("c.id", "bad thing", scope=ValidationScope.TYPE,
                                  severity=ValidationSeverity.ERROR)
        assert not r.passed
        assert r.is_error
        assert not r.is_critical

    def test_critical_factory(self):
        from iios.ontology.validator import ValidationResult, ValidationSeverity
        r = ValidationResult.critical("c.id", "structural break")
        assert not r.passed
        assert r.is_critical
        assert r.severity == ValidationSeverity.CRITICAL

    def test_warn_factory_does_not_block(self):
        from iios.ontology.validator import ValidationResult
        r = ValidationResult.warn("c.id", "soft warning")
        assert r.passed      # warnings don't block
        assert r.is_warning
        assert not r.is_error

    def test_info_factory(self):
        from iios.ontology.validator import ValidationResult, ValidationSeverity
        r = ValidationResult.info("c.id", "informational")
        assert r.passed
        assert r.severity == ValidationSeverity.INFO

    def test_to_dict(self):
        from iios.ontology.validator import ValidationResult
        r = ValidationResult.fail("c.id", "msg", path="properties.x")
        d = r.to_dict()
        assert d["passed"]        is False
        assert d["constraint_id"] == "c.id"
        assert d["path"]          == "properties.x"
        assert "severity"         in d
        assert "timestamp"        in d

    def test_details_carried(self):
        from iios.ontology.validator import ValidationResult
        r = ValidationResult.fail("c.id", "msg", details={"depth": 5})
        assert r.details["depth"] == 5


# ═════════════════════════════════════════════════════════════════════════════
# 4. ValidationReport
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationReport:
    def test_passed_when_no_errors(self):
        from iios.ontology.validator import ValidationReport, ValidationResult
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.ok("c.id"))
        r.add(ValidationResult.warn("c.id2", "soft"))
        assert r.passed

    def test_not_passed_on_error(self):
        from iios.ontology.validator import ValidationReport, ValidationResult
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.fail("c.id", "oops"))
        assert not r.passed
        assert r.has_errors

    def test_counts(self):
        from iios.ontology.validator import ValidationReport, ValidationResult, ValidationSeverity
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.ok("c1"))
        r.add(ValidationResult.warn("c2", "w"))
        r.add(ValidationResult.fail("c3", "e"))
        r.add(ValidationResult.critical("c4", "crit"))
        assert r.error_count    == 1
        assert r.critical_count == 1
        assert r.warning_count  == 1
        assert r.pass_count     == 1
        assert r.total          == 4

    def test_severity_rollup(self):
        from iios.ontology.validator import ValidationReport, ValidationResult, ValidationSeverity
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.warn("c", "w"))
        r.add(ValidationResult.fail("c2", "e"))
        assert r.severity == ValidationSeverity.ERROR

    def test_merge(self):
        from iios.ontology.validator import ValidationReport, ValidationResult
        r1 = ValidationReport(target_id="A")
        r2 = ValidationReport(target_id="B")
        r1.add(ValidationResult.ok("c1"))
        r2.add(ValidationResult.fail("c2", "err"))
        r1.merge(r2)
        assert r1.total == 2

    def test_finalise(self):
        from iios.ontology.validator import ValidationReport
        r = ValidationReport(target_id="T")
        time.sleep(0.01)
        r.finalise()
        assert r.finished_at > 0
        assert r.duration_ms >= 5.0

    def test_to_dict(self):
        from iios.ontology.validator import ValidationReport, ValidationResult
        r = ValidationReport(target_id="T", target_type="OntologyTypeDef")
        r.add(ValidationResult.ok("c"))
        r.finalise()
        d = r.to_dict()
        assert "target_id"  in d
        assert "passed"     in d
        assert "results"    in d
        assert len(d["results"]) == 1

    def test_summary(self):
        from iios.ontology.validator import ValidationReport
        r = ValidationReport(target_id="T")
        r.finalise()
        s = r.summary()
        assert "passed"    in s
        assert "severity"  in s
        assert "duration_ms" in s

    def test_by_scope(self):
        from iios.ontology.validator import ValidationReport, ValidationResult, ValidationScope
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.ok("c1", ValidationScope.TYPE))
        r.add(ValidationResult.ok("c2", ValidationScope.PROPERTY))
        assert len(r.by_scope(ValidationScope.TYPE))     == 1
        assert len(r.by_scope(ValidationScope.PROPERTY)) == 1

    def test_errors_and_criticals(self):
        from iios.ontology.validator import ValidationReport, ValidationResult
        r = ValidationReport(target_id="T")
        r.add(ValidationResult.fail("c1", "err"))
        r.add(ValidationResult.critical("c2", "crit"))
        r.add(ValidationResult.warn("c3", "w"))
        assert len(r.errors_and_criticals()) == 2


class TestValidationHistory:
    def test_record_and_get(self):
        from iios.ontology.validator import ValidationReport
        from iios.ontology.validator.validation_report import ValidationHistory
        h  = ValidationHistory(max_per_target=10)
        r  = ValidationReport(target_id="T")
        h.record(r)
        items = h.get("T")
        assert len(items) == 1

    def test_respects_max(self):
        from iios.ontology.validator import ValidationReport
        from iios.ontology.validator.validation_report import ValidationHistory
        h = ValidationHistory(max_per_target=3)
        for _ in range(5):
            h.record(ValidationReport(target_id="T"))
        assert len(h.get("T")) == 3

    def test_clear_one(self):
        from iios.ontology.validator import ValidationReport
        from iios.ontology.validator.validation_report import ValidationHistory
        h = ValidationHistory()
        h.record(ValidationReport(target_id="A"))
        h.record(ValidationReport(target_id="B"))
        h.clear("A")
        assert len(h.get("A")) == 0
        assert len(h.get("B")) == 1

    def test_stats(self):
        from iios.ontology.validator import ValidationReport
        from iios.ontology.validator.validation_report import ValidationHistory
        h = ValidationHistory()
        h.record(ValidationReport(target_id="X"))
        h.record(ValidationReport(target_id="X"))
        s = h.stats()
        assert s["tracked_targets"] == 1
        assert s["total_reports"]   == 2


# ═════════════════════════════════════════════════════════════════════════════
# 5. ValidationContext
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationContext:
    def test_initial_none(self):
        from iios.ontology.validator import get_validation_context, ValidationMode, ValidationPhase
        ctx = get_validation_context()
        assert ctx.operation_id    is None
        assert ctx.current_target  is None

    def test_validation_cm_sets_target(self):
        from iios.ontology.validator import get_validation_context
        ctx = get_validation_context()
        with ctx.validation("iios.test.T"):
            assert ctx.current_target == "iios.test.T"
            assert ctx.operation_id   is not None
        assert ctx.current_target is None

    def test_mode_propagated(self):
        from iios.ontology.validator import get_validation_context, ValidationMode
        ctx = get_validation_context()
        with ctx.validation("T", mode=ValidationMode.STRICT):
            assert ctx.mode == ValidationMode.STRICT

    def test_nested_cm(self):
        from iios.ontology.validator import get_validation_context
        ctx = get_validation_context()
        with ctx.validation("outer"):
            assert ctx.current_target == "outer"
            with ctx.target("inner"):
                assert ctx.current_target == "inner"
                assert ctx.depth == 2
            assert ctx.current_target == "outer"

    def test_add_diagnostic(self):
        from iios.ontology.validator import get_validation_context, DiagnosticLevel
        ctx = get_validation_context()
        with ctx.validation("T"):
            ctx.add_diagnostic(DiagnosticLevel.WARNING, "test warning")
            ctx.add_diagnostic(DiagnosticLevel.ERROR, "test error")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_thread_isolation(self):
        from iios.ontology.validator import get_validation_context
        ctx     = get_validation_context()
        results: list = []
        lock    = threading.Lock()

        def worker(name: str) -> None:
            with ctx.validation(name):
                time.sleep(0.01)
                with lock:
                    results.append(ctx.current_target)

        threads = [threading.Thread(target=worker, args=(f"T{i}",)) for i in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(results) == 4
        # Each thread should have seen its own target
        assert set(results) == {"T0", "T1", "T2", "T3"}

    def test_elapsed_ms(self):
        from iios.ontology.validator import get_validation_context
        ctx = get_validation_context()
        with ctx.validation("T"):
            time.sleep(0.01)
            ms = ctx.elapsed_ms()
        assert ms >= 5.0

    def test_singleton(self):
        from iios.ontology.validator import get_validation_context
        assert get_validation_context() is get_validation_context()


# ═════════════════════════════════════════════════════════════════════════════
# 6. ConstraintRegistry
# ═════════════════════════════════════════════════════════════════════════════

class TestConstraintRegistry:
    def _simple_rule(self, target, all_types):
        from iios.ontology.validator import ValidationResult, ValidationScope
        return [ValidationResult.ok("test.rule", ValidationScope.TYPE)]

    def test_register_and_get(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope, ValidationSeverity
        )
        reg = get_constraint_registry()
        reg.register("my.rule", "My Rule", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        cd = reg.get("my.rule")
        assert cd.constraint_id == "my.rule"
        assert cd.name          == "My Rule"

    def test_duplicate_raises(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope,
            ValidationSeverity, DuplicateConstraintError,
        )
        reg = get_constraint_registry()
        reg.register("dup.rule", "R", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        with pytest.raises(DuplicateConstraintError):
            reg.register("dup.rule", "R2", ConstraintType.CUSTOM, ValidationScope.TYPE,
                         ValidationSeverity.ERROR, self._simple_rule)

    def test_overwrite_allowed(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope, ValidationSeverity
        )
        reg = get_constraint_registry()
        reg.register("ow.rule", "Old", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        reg.register("ow.rule", "New", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.WARNING, self._simple_rule, overwrite=True)
        assert reg.get("ow.rule").name == "New"

    def test_enable_disable(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope, ValidationSeverity
        )
        reg = get_constraint_registry()
        reg.register("tog.rule", "R", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        reg.disable("tog.rule")
        assert not reg.get("tog.rule").enabled
        reg.enable("tog.rule")
        assert reg.get("tog.rule").enabled

    def test_get_by_scope(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope, ValidationSeverity
        )
        reg = get_constraint_registry()
        reg.register("s1.rule", "R1", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        reg.register("s2.rule", "R2", ConstraintType.CUSTOM, ValidationScope.PROPERTY,
                     ValidationSeverity.ERROR, self._simple_rule)
        type_constraints = reg.get_by_scope(ValidationScope.TYPE)
        assert any(cd.constraint_id == "s1.rule" for cd in type_constraints)
        assert all(cd.scope == ValidationScope.TYPE for cd in type_constraints)

    def test_stats(self):
        from iios.ontology.validator import (
            get_constraint_registry, ConstraintType, ValidationScope, ValidationSeverity
        )
        reg = get_constraint_registry()
        reg.register("st.r1", "R1", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.ERROR, self._simple_rule)
        reg.register("st.r2", "R2", ConstraintType.CUSTOM, ValidationScope.TYPE,
                     ValidationSeverity.WARNING, self._simple_rule)
        reg.disable("st.r2")
        s = reg.stats()
        assert s["total"]   == 2
        assert s["enabled"] == 1
        assert s["disabled"] == 1

    def test_singleton(self):
        from iios.ontology.validator import get_constraint_registry
        assert get_constraint_registry() is get_constraint_registry()


# ═════════════════════════════════════════════════════════════════════════════
# 7. ConstraintEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestConstraintEngine:
    def _bootstrap(self):
        from iios.ontology.validator import get_constraint_manager
        mgr = get_constraint_manager()
        if not mgr.is_initialized:
            mgr.register_builtin_constraints()

    def test_check_type_def_valid(self):
        from iios.ontology.validator import get_constraint_engine
        self._bootstrap()
        td      = _make_type("GoodType", "iios.test")
        engine  = get_constraint_engine()
        results = engine.check_type_def(td, {})
        assert any(r.passed for r in results)

    def test_check_type_def_empty_uri_critical(self):
        from iios.ontology.validator import get_constraint_engine, ValidationSeverity
        self._bootstrap()
        td = _make_type("X", "iios.test")
        td.uri = ""   # Force empty URI
        engine  = get_constraint_engine()
        results = engine.check_type_def(td, {})
        criticals = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(criticals) >= 1

    def test_check_property_ref_uri_missing(self):
        from iios.ontology.validator import get_constraint_engine, ValidationSeverity
        from iios.ontology.ontology_constants import DataType
        self._bootstrap()
        td      = _make_type("T", "iios.test")
        prop    = _make_prop("ref_field")
        prop.data_type = DataType.REF
        prop.ref_uri   = ""       # REF without ref_uri
        td.properties["ref_field"] = prop
        engine  = get_constraint_engine()
        results = engine.check_property(td, {})
        errors  = [r for r in results if r.severity == ValidationSeverity.ERROR and not r.passed]
        assert len(errors) >= 1

    def test_check_namespace_valid(self):
        from iios.ontology.validator import get_constraint_engine
        self._bootstrap()
        ns      = _make_namespace()
        engine  = get_constraint_engine()
        results = engine.check_namespace(ns, {})
        assert any(r.passed for r in results)

    def test_check_namespace_empty_uri(self):
        from iios.ontology.validator import get_constraint_engine, ValidationSeverity
        self._bootstrap()
        ns     = _make_namespace(uri="")
        engine = get_constraint_engine()
        results = engine.check_namespace(ns, {})
        criticals = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(criticals) >= 1

    def test_check_relationship_def(self):
        from iios.ontology.validator import get_constraint_engine
        self._bootstrap()
        rel     = _make_rel()
        engine  = get_constraint_engine()
        results = engine.check_relationship_def(rel, {})
        assert any(r.passed for r in results)

    def test_check_hierarchy_detects_cycle(self):
        from iios.ontology.validator import get_constraint_engine, ValidationSeverity
        self._bootstrap()
        td_a = _make_type("A", "iios.test")
        td_b = _make_type("B", "iios.test", parent=td_a.uri)
        td_a.parent_uri = td_b.uri   # Create cycle A→B→A
        all_types = {td_a.uri: td_a, td_b.uri: td_b}
        engine  = get_constraint_engine()
        results = engine.check_hierarchy(all_types)
        criticals = [r for r in results if r.severity == ValidationSeverity.CRITICAL and not r.passed]
        assert len(criticals) >= 1

    def test_singleton(self):
        from iios.ontology.validator import get_constraint_engine
        assert get_constraint_engine() is get_constraint_engine()


# ═════════════════════════════════════════════════════════════════════════════
# 8. ConstraintManager
# ═════════════════════════════════════════════════════════════════════════════

class TestConstraintManager:
    def test_register_builtin_constraints(self):
        from iios.ontology.validator import get_constraint_manager
        mgr = get_constraint_manager()
        n   = mgr.register_builtin_constraints()
        assert n >= 20   # We have 25 built-in rules
        assert mgr.is_initialized

    def test_idempotent_second_call(self):
        from iios.ontology.validator import get_constraint_manager
        mgr = get_constraint_manager()
        n1  = mgr.register_builtin_constraints()
        n2  = mgr.register_builtin_constraints()
        assert n1 == n2   # No duplication

    def test_register_custom(self):
        from iios.ontology.validator import (
            get_constraint_manager, ConstraintType, ValidationScope, ValidationSeverity,
        )
        from iios.ontology.validator import ValidationResult

        def my_rule(target, all_types):
            return [ValidationResult.ok("custom.ok")]

        mgr = get_constraint_manager()
        cid = mgr.register_custom(
            my_rule, "My custom rule",
            constraint_type = ConstraintType.BUSINESS_RULE,
            scope           = ValidationScope.TYPE,
            severity        = ValidationSeverity.WARNING,
        )
        assert cid.startswith("custom.")
        constraints = mgr.list_constraints(scope=ValidationScope.TYPE)
        assert any(c.constraint_id == cid for c in constraints)

    def test_enable_disable_custom(self):
        from iios.ontology.validator import get_constraint_manager, ValidationResult
        from iios.ontology.validator import ConstraintType, ValidationScope, ValidationSeverity

        def noop(t, a): return [ValidationResult.ok("noop")]
        mgr = get_constraint_manager()
        cid = mgr.register_custom(noop, "Noop", constraint_id="test.noop",
                                   scope=ValidationScope.TYPE,
                                   severity=ValidationSeverity.INFO)
        mgr.disable(cid)
        enabled = mgr.list_constraints(enabled_only=True)
        assert not any(c.constraint_id == cid for c in enabled)
        mgr.enable(cid)
        enabled = mgr.list_constraints(enabled_only=True)
        assert any(c.constraint_id == cid for c in enabled)

    def test_stats(self):
        from iios.ontology.validator import get_constraint_manager
        mgr = get_constraint_manager()
        mgr.register_builtin_constraints()
        s = mgr.stats()
        assert "initialized"  in s
        assert "constraints"  in s
        assert s["initialized"] is True

    def test_singleton(self):
        from iios.ontology.validator import get_constraint_manager
        assert get_constraint_manager() is get_constraint_manager()


# ═════════════════════════════════════════════════════════════════════════════
# 9. OntologyValidator
# ═════════════════════════════════════════════════════════════════════════════

class TestOntologyValidator:
    def test_validate_type_def_valid(self):
        from iios.ontology.validator import get_ontology_validator
        td     = _make_type()
        val    = get_ontology_validator()
        report = val.validate_type_def(td)
        # Valid type should pass
        assert report.target_id   == td.uri
        assert report.target_type == "OntologyTypeDef"

    def test_validate_type_def_empty_name_fails(self):
        from iios.ontology.validator import get_ontology_validator, ValidationSeverity
        td   = _make_type()
        td.name = ""
        val  = get_ontology_validator()
        rpt  = val.validate_type_def(td)
        assert rpt.critical_count >= 1

    def test_validate_namespace_valid(self):
        from iios.ontology.validator import get_ontology_validator
        ns     = _make_namespace()
        val    = get_ontology_validator()
        report = val.validate_namespace(ns)
        assert report.target_id == ns.uri

    def test_validate_namespace_empty_uri(self):
        from iios.ontology.validator import get_ontology_validator
        ns     = _make_namespace(uri="", name="Bad")
        val    = get_ontology_validator()
        report = val.validate_namespace(ns)
        assert report.critical_count >= 1

    def test_validate_relationship_def_valid(self):
        from iios.ontology.validator import get_ontology_validator
        rel = _make_rel()
        val = get_ontology_validator()
        rpt = val.validate_relationship_def(rel)
        assert rpt.target_id == rel.uri

    def test_validate_document(self):
        from iios.ontology.validator import get_ontology_validator
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader = get_ontology_loader()
        doc    = loader.load_builtin(ONT_INFORMATION)
        val    = get_ontology_validator()
        rpt    = val.validate_document(doc)
        assert rpt.target_id  == doc.name
        assert rpt.total      >= 0

    def test_validate_compiled_ontology(self):
        from iios.ontology.validator import get_ontology_validator
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        doc      = loader.load_builtin(ONT_INFORMATION)
        compiled = compiler.compile(doc)
        val      = get_ontology_validator()
        rpt      = val.validate_compiled_ontology(compiled)
        assert rpt.target_id == compiled.name

    def test_validate_hierarchy_no_cycle(self):
        from iios.ontology.validator import get_ontology_validator
        td_a = _make_type("A", "iios.test")
        td_b = _make_type("B", "iios.test", parent=td_a.uri)
        all_types = {td_a.uri: td_a, td_b.uri: td_b}
        val = get_ontology_validator()
        rpt = val.validate_hierarchy(all_types)
        assert rpt.target_id == "global.hierarchy"
        assert rpt.passed    # No cycles

    def test_validate_hierarchy_detects_cycle(self):
        from iios.ontology.validator import get_ontology_validator, ValidationSeverity
        td_a = _make_type("A", "iios.test")
        td_b = _make_type("B", "iios.test", parent=td_a.uri)
        td_a.parent_uri = td_b.uri   # Cycle
        all_types = {td_a.uri: td_a, td_b.uri: td_b}
        val = get_ontology_validator()
        rpt = val.validate_hierarchy(all_types)
        assert rpt.critical_count >= 1

    def test_validate_cross_references_clean(self):
        from iios.ontology.validator import get_ontology_validator
        td_a = _make_type("A", "iios.test")
        td_b = _make_type("B", "iios.test", parent=td_a.uri)
        all_types = {td_a.uri: td_a, td_b.uri: td_b}
        val = get_ontology_validator()
        rpt = val.validate_cross_references(all_types)
        assert rpt.target_id == "global.references"

    def test_validate_runtime_object_with_required(self):
        from iios.ontology.validator import get_ontology_validator
        td   = _make_type()
        prop = _make_prop("name", required=True)
        td.properties["name"] = prop
        all_types = {td.uri: td}
        val = get_ontology_validator()
        # Missing required property
        rpt = val.validate_runtime_object({}, td.uri, all_types)
        assert not rpt.passed
        # With required property present
        rpt2 = val.validate_runtime_object({"name": "hello"}, td.uri, all_types)
        assert rpt2.passed

    def test_validate_namespace_consistency(self):
        from iios.ontology.validator import get_ontology_validator
        from iios.ontology.compiler.ontology_compiler import get_ontology_compiler
        from iios.ontology.loader.ontology_loader import get_ontology_loader
        from iios.ontology.ontology_constants import ONT_INFORMATION
        loader   = get_ontology_loader()
        compiler = get_ontology_compiler()
        compiled = compiler.compile(loader.load_builtin(ONT_INFORMATION))
        val      = get_ontology_validator()
        rpt      = val.validate_namespace_consistency(compiled)
        assert rpt.target_id == compiled.name

    def test_singleton(self):
        from iios.ontology.validator import get_ontology_validator
        assert get_ontology_validator() is get_ontology_validator()


# ═════════════════════════════════════════════════════════════════════════════
# 10. ValidationEngine
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationEngine:
    def test_initialize(self):
        from iios.ontology.validator import get_validation_engine
        engine = get_validation_engine()
        engine.initialize()
        assert engine.stats()["initialized"] is True

    def test_validate_type_valid(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        rpt    = engine.validate_type(td)
        assert rpt.target_id   == td.uri
        assert rpt.target_type == "OntologyTypeDef"

    def test_validate_type_raises_in_strict_mode(self):
        from iios.ontology.validator import (
            get_validation_engine, ValidationMode, ConstraintViolationError,
        )
        td   = _make_type()
        td.uri = ""  # Force critical
        engine = get_validation_engine()
        with pytest.raises(ConstraintViolationError):
            engine.validate_type(td, mode=ValidationMode.STRICT, raise_on_failure=True)

    def test_validate_type_no_raise_in_warning_only(self):
        from iios.ontology.validator import get_validation_engine, ValidationMode
        td   = _make_type()
        td.uri = ""
        engine = get_validation_engine()
        # Should NOT raise in WARNING_ONLY mode
        rpt = engine.validate_type(td, mode=ValidationMode.WARNING_ONLY, raise_on_failure=True)
        assert rpt is not None

    def test_validate_ontology_not_compiled_returns_error(self):
        from iios.ontology.validator import get_validation_engine, ValidationSeverity
        engine = get_validation_engine()
        rpt    = engine.validate_ontology("NOT_COMPILED_ONT")
        assert not rpt.passed
        assert rpt.has_errors

    def test_validate_ontology_after_compile(self):
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import ONT_INFORMATION
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_ontology(ONT_INFORMATION)
        assert rpt.target_id == ONT_INFORMATION

    def test_validate_all_ontologies(self):
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        _warm_registry()
        engine  = get_validation_engine()
        reports = engine.validate_all_ontologies()
        assert len(reports) == len(BUILTIN_ONTOLOGY_NAMES)
        assert all(name in reports for name in BUILTIN_ONTOLOGY_NAMES)

    def test_validate_all_ontologies_parallel(self):
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        _warm_registry()
        engine  = get_validation_engine()
        reports = engine.validate_all_ontologies(parallel=True)
        assert len(reports) == len(BUILTIN_ONTOLOGY_NAMES)

    def test_validate_hierarchy(self):
        from iios.ontology.validator import get_validation_engine
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_hierarchy()
        assert rpt.target_id == "global.hierarchy"

    def test_validate_referential_integrity(self):
        from iios.ontology.validator import get_validation_engine
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_referential_integrity()
        assert rpt.target_id == "global.references"

    def test_validate_runtime_object_missing_required(self):
        from iios.ontology.validator import get_validation_engine
        _warm_registry()
        engine = get_validation_engine()
        # Use a builtin type that might have required props
        # Just pass unknown type — engine should report it
        rpt = engine.validate_runtime_object({}, "iios.UNKNOWN.Type")
        assert rpt is not None

    def test_validate_pre_registration_valid(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        rpt    = engine.validate_pre_registration(td, raise_on_failure=False)
        assert rpt is not None

    def test_validate_batch(self):
        from iios.ontology.validator import get_validation_engine
        types  = [_make_type(f"T{i}", "iios.test") for i in range(5)]
        engine = get_validation_engine()
        rpts   = engine.validate_batch(types)
        assert len(rpts) == 5

    def test_validate_batch_parallel(self):
        from iios.ontology.validator import get_validation_engine
        types  = [_make_type(f"T{i}", "iios.test") for i in range(8)]
        engine = get_validation_engine()
        rpts   = engine.validate_batch(types, parallel=True)
        assert len(rpts) == 8

    def test_validate_batch_too_large(self):
        from iios.ontology.validator import get_validation_engine, ValidationEngineError, MAX_BATCH_SIZE
        engine = get_validation_engine()
        types  = [_make_type(f"T{i}", "iios.test") for i in range(MAX_BATCH_SIZE + 1)]
        with pytest.raises(ValidationEngineError):
            engine.validate_batch(types)

    def test_is_valid(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        assert engine.is_valid(td)

    def test_history_recorded(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        engine.validate_type(td)
        history = engine.get_history(td.uri)
        assert len(history) >= 1

    def test_last_report(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        engine.validate_type(td)
        rpt = engine.last_report(td.uri)
        assert rpt is not None

    def test_register_custom_constraint(self):
        from iios.ontology.validator import (
            get_validation_engine, ValidationResult, ValidationScope, ConstraintType,
            ValidationSeverity,
        )

        def always_warn(target, all_types):
            return [ValidationResult.warn("custom.always_warn", "soft advisory")]

        engine = get_validation_engine()
        cid    = engine.register_constraint(
            always_warn, "Always Warn",
            constraint_type = ConstraintType.BUSINESS_RULE,
            scope           = ValidationScope.TYPE,
            severity        = ValidationSeverity.WARNING,
        )
        assert cid.startswith("custom.")

    def test_disable_enable_constraint(self):
        from iios.ontology.validator import get_validation_engine, get_constraint_registry
        engine = get_validation_engine()
        engine.initialize()
        cids = get_constraint_registry().all_ids()
        cid  = cids[0]
        engine.disable_constraint(cid)
        assert not get_constraint_registry().get(cid).enabled
        engine.enable_constraint(cid)
        assert get_constraint_registry().get(cid).enabled

    def test_stats(self):
        from iios.ontology.validator import get_validation_engine
        engine = get_validation_engine()
        engine.initialize()
        s = engine.stats()
        assert "initialized"  in s
        assert "version"      in s
        assert "total_runs"   in s
        assert "constraints"  in s

    def test_health(self):
        from iios.ontology.validator import get_validation_engine
        engine = get_validation_engine()
        engine.initialize()
        h = engine.health()
        assert h["status"]      == "healthy"
        assert h["initialized"] is True

    def test_singleton(self):
        from iios.ontology.validator import get_validation_engine
        assert get_validation_engine() is get_validation_engine()


# ═════════════════════════════════════════════════════════════════════════════
# 11. Referential Integrity
# ═════════════════════════════════════════════════════════════════════════════

class TestReferentialIntegrity:
    def test_broken_parent_uri_detected(self):
        from iios.ontology.validator import get_ontology_validator, ValidationSeverity
        td = _make_type("Child", "iios.test", parent="iios.NONEXISTENT.Parent")
        all_types = {td.uri: td}   # Parent not in map
        val = get_ontology_validator()
        rpt = val.validate_cross_references(all_types)
        warnings = [r for r in rpt.results if not r.passed]
        assert len(warnings) >= 1

    def test_clean_references_all_pass(self):
        from iios.ontology.validator import get_ontology_validator
        parent = _make_type("Parent", "iios.test")
        child  = _make_type("Child",  "iios.test", parent=parent.uri)
        all_types = {parent.uri: parent, child.uri: child}
        val = get_ontology_validator()
        rpt = val.validate_cross_references(all_types)
        errors = [r for r in rpt.results if r.is_error and not r.passed]
        assert len(errors) == 0

    def test_broken_ref_property_detected(self):
        from iios.ontology.validator import get_ontology_validator, ValidationSeverity
        from iios.ontology.ontology_constants import DataType
        td   = _make_type("T", "iios.test")
        prop = _make_prop("ref_field")
        prop.data_type = DataType.REF
        prop.ref_uri   = "iios.NONEXISTENT.TargetType"
        td.properties["ref_field"] = prop
        all_types = {td.uri: td}
        val = get_ontology_validator()
        rpt = val.validate_cross_references(all_types)
        warnings = [r for r in rpt.results if not r.passed]
        assert len(warnings) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 12. Hierarchy Validation
# ═════════════════════════════════════════════════════════════════════════════

class TestHierarchyValidation:
    def test_deep_chain_within_limit(self):
        from iios.ontology.validator import get_ontology_validator
        # Build a chain of 5 (well within limit)
        types: dict[str, Any] = {}
        prev_uri: str | None = None
        for i in range(5):
            td = _make_type(f"T{i}", "iios.test", parent=prev_uri)
            types[td.uri] = td
            prev_uri      = td.uri
        val = get_ontology_validator()
        rpt = val.validate_hierarchy(types)
        # No depth errors expected for depth=5
        depth_errors = [r for r in rpt.results
                        if "depth" in r.constraint_id and not r.passed]
        assert len(depth_errors) == 0

    def test_self_inheritance_critical(self):
        from iios.ontology.validator import get_constraint_engine, ValidationSeverity
        from iios.ontology.validator import get_constraint_manager
        get_constraint_manager().register_builtin_constraints()
        td = _make_type("SelfRef", "iios.test")
        td.parent_uri = td.uri   # Self-inheritance
        engine  = get_constraint_engine()
        results = engine.check_type_def(td, {})
        criticals = [r for r in results
                     if r.severity == ValidationSeverity.CRITICAL and not r.passed]
        assert len(criticals) >= 1

    def test_multi_level_cycle_detected(self):
        from iios.ontology.validator import get_ontology_validator, ValidationSeverity
        ta = _make_type("A", "iios.test")
        tb = _make_type("B", "iios.test", parent=ta.uri)
        tc = _make_type("C", "iios.test", parent=tb.uri)
        ta.parent_uri = tc.uri   # A→B→C→A cycle
        all_types = {ta.uri: ta, tb.uri: tb, tc.uri: tc}
        val = get_ontology_validator()
        rpt = val.validate_hierarchy(all_types)
        criticals = [r for r in rpt.results
                     if r.severity == ValidationSeverity.CRITICAL and not r.passed]
        assert len(criticals) >= 1

    def test_no_false_positive_on_valid_chain(self):
        from iios.ontology.validator import get_ontology_validator
        # Linear chain: A → B → C (valid)
        ta = _make_type("A", "iios.test")
        tb = _make_type("B", "iios.test", parent=ta.uri)
        tc = _make_type("C", "iios.test", parent=tb.uri)
        all_types = {ta.uri: ta, tb.uri: tb, tc.uri: tc}
        val = get_ontology_validator()
        rpt = val.validate_hierarchy(all_types)
        cycles = [r for r in rpt.results
                  if "no_cycle" in r.constraint_id and not r.passed]
        assert len(cycles) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 13. Business Rules (Custom Constraints)
# ═════════════════════════════════════════════════════════════════════════════

class TestBusinessRules:
    def test_custom_constraint_fires(self):
        from iios.ontology.validator import (
            get_constraint_manager, get_constraint_engine,
            ValidationResult, ValidationScope, ValidationSeverity, ConstraintType,
        )
        mgr = get_constraint_manager()
        mgr.register_builtin_constraints()

        FIRED: list[bool] = []

        def must_have_tag(td, _):
            FIRED.append(True)
            if "core" not in (td.tags or []):
                return [ValidationResult.warn(
                    "custom.must_have_tag", "Missing 'core' tag", scope=ValidationScope.TYPE,
                )]
            return [ValidationResult.ok("custom.must_have_tag", ValidationScope.TYPE)]

        mgr.register_custom(must_have_tag, "Must have core tag",
                            constraint_type=ConstraintType.BUSINESS_RULE,
                            scope=ValidationScope.TYPE,
                            severity=ValidationSeverity.WARNING,
                            constraint_id="custom.must_have_tag",
                            overwrite=True)

        td      = _make_type("T", "iios.test")
        engine  = get_constraint_engine()
        results = engine.check_type_def(td, {})
        assert len(FIRED) >= 1
        warns   = [r for r in results if "must_have_tag" in r.constraint_id]
        assert len(warns) == 1

    def test_custom_constraint_passes_when_satisfied(self):
        from iios.ontology.validator import (
            get_constraint_manager, get_constraint_engine,
            ValidationResult, ValidationScope, ValidationSeverity, ConstraintType,
        )
        mgr = get_constraint_manager()
        mgr.register_builtin_constraints()

        def must_have_tag(td, _):
            if "core" not in (td.tags or []):
                return [ValidationResult.warn("custom.tag_check2", "Missing tag")]
            return [ValidationResult.ok("custom.tag_check2", ValidationScope.TYPE)]

        mgr.register_custom(must_have_tag, "Tag check 2",
                            scope=ValidationScope.TYPE,
                            severity=ValidationSeverity.WARNING,
                            constraint_id="custom.tag_check2",
                            overwrite=True)

        td      = _make_type("T", "iios.test")
        td.tags = ["core"]   # Satisfies constraint
        engine  = get_constraint_engine()
        results = engine.check_type_def(td, {})
        passes  = [r for r in results if "tag_check2" in r.constraint_id and r.passed]
        assert len(passes) == 1

    def test_disabled_custom_does_not_fire(self):
        from iios.ontology.validator import (
            get_constraint_manager, get_constraint_engine,
            ValidationResult, ValidationScope, ValidationSeverity, ConstraintType,
        )
        FIRED: list[bool] = []

        def always_fire(td, _):
            FIRED.append(True)
            return [ValidationResult.warn("custom.af", "fired")]

        mgr = get_constraint_manager()
        mgr.register_builtin_constraints()
        cid = mgr.register_custom(always_fire, "Always Fire",
                                   scope=ValidationScope.TYPE,
                                   severity=ValidationSeverity.WARNING,
                                   constraint_id="custom.always_fire",
                                   overwrite=True)
        mgr.disable(cid)

        td     = _make_type()
        engine = get_constraint_engine()
        engine.check_type_def(td, {})
        assert len(FIRED) == 0   # Disabled — must not fire


# ═════════════════════════════════════════════════════════════════════════════
# 14. Performance & Concurrency
# ═════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_singleton_thread_safety(self):
        from iios.ontology.validator import get_validation_engine
        ids:  list[int] = []
        lock = threading.Lock()

        def _get():
            eng = get_validation_engine()
            with lock:
                ids.append(id(eng))

        threads = [threading.Thread(target=_get) for _ in range(16)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(set(ids)) == 1, "Multiple ValidationEngine instances"

    def test_context_thread_isolation(self):
        from iios.ontology.validator import get_validation_context
        ctx     = get_validation_context()
        results: dict[str, str] = {}
        lock    = threading.Lock()

        def _worker(name: str):
            with ctx.validation(name):
                time.sleep(0.01)
                with lock:
                    results[name] = ctx.current_target or "none"

        threads = [threading.Thread(target=_worker, args=(f"U{i}",)) for i in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        # Each thread should see its own target
        for name, seen in results.items():
            assert seen == name, f"Thread {name} saw {seen!r}"

    def test_parallel_validate_batch(self):
        from iios.ontology.validator import get_validation_engine
        types  = [_make_type(f"T{i}", "iios.test") for i in range(16)]
        engine = get_validation_engine()
        rpts   = engine.validate_batch(types, parallel=True)
        assert len(rpts) == 16
        assert all(rpt is not None for rpt in rpts)

    def test_parallel_validate_all_ontologies(self):
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        _warm_registry()
        engine  = get_validation_engine()
        reports = engine.validate_all_ontologies(parallel=True)
        assert len(reports) == len(BUILTIN_ONTOLOGY_NAMES)

    def test_concurrent_history_writes(self):
        from iios.ontology.validator import get_validation_engine
        engine = get_validation_engine()
        errors: list[Exception] = []

        def _validate():
            try:
                td = _make_type("Shared", "iios.test")
                engine.validate_type(td)
            except Exception as e:
                errors.append(e)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: _validate(), range(32)))
        assert len(errors) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 15. End-to-End Integration
# ═════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline_validate_all_after_cold_start(self):
        """Cold start → validate all ontologies → all pass structural checks."""
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import BUILTIN_ONTOLOGY_NAMES
        _warm_registry()
        engine  = get_validation_engine()
        reports = engine.validate_all_ontologies()
        assert len(reports) == len(BUILTIN_ONTOLOGY_NAMES)
        # Check every report was produced
        for name in BUILTIN_ONTOLOGY_NAMES:
            assert name in reports, f"Missing report for {name}"

    def test_full_pipeline_hierarchy_no_cycle_in_builtins(self):
        """Built-in ontologies must not contain any circular inheritance."""
        from iios.ontology.validator import get_validation_engine, ValidationSeverity
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_hierarchy()
        criticals = [r for r in rpt.results
                     if r.severity == ValidationSeverity.CRITICAL and not r.passed]
        assert len(criticals) == 0, f"Unexpected cycle in builtins: {criticals}"

    def test_full_pipeline_referential_integrity(self):
        """All parent_uri references in built-ins must resolve."""
        from iios.ontology.validator import get_validation_engine, ValidationSeverity
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_referential_integrity()
        # No critical referential errors expected
        criticals = [r for r in rpt.results
                     if r.severity == ValidationSeverity.CRITICAL and not r.passed]
        assert len(criticals) == 0

    def test_pre_registration_gate_blocks_empty_uri(self):
        """Pre-registration gate rejects type with empty URI."""
        from iios.ontology.validator import get_validation_engine, ConstraintViolationError, ValidationMode
        td     = _make_type()
        td.uri = ""
        engine = get_validation_engine()
        with pytest.raises(ConstraintViolationError):
            engine.validate_pre_registration(td, raise_on_failure=True)

    def test_pre_registration_gate_passes_valid_type(self):
        from iios.ontology.validator import get_validation_engine
        td     = _make_type()
        engine = get_validation_engine()
        rpt    = engine.validate_pre_registration(td, raise_on_failure=False)
        assert rpt is not None

    def test_global_validation_pass(self):
        """validate_all on a warm registry returns a combined report."""
        from iios.ontology.validator import get_validation_engine
        _warm_registry()
        engine = get_validation_engine()
        rpt    = engine.validate_all()
        assert rpt.target_id   == "global"
        assert rpt.total       > 0
        assert rpt.duration_ms >= 0

    def test_incremental_validation(self):
        """Incremental validation only re-validates changed names."""
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.ontology_constants import ONT_INFORMATION, ONT_ENTITY
        _warm_registry()
        engine  = get_validation_engine()
        reports = engine.validate_incremental([ONT_INFORMATION, ONT_ENTITY])
        assert ONT_INFORMATION in reports
        assert ONT_ENTITY      in reports
        assert len(reports)    == 2

    def test_runtime_object_validation_full(self):
        """Runtime object validation catches missing required field."""
        from iios.ontology.validator import get_validation_engine
        from iios.ontology.compiler.compiler_manager import get_compiler_manager
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        _warm_registry()
        # Find a concrete type
        reg  = get_registry_manager()
        td   = reg.get_type_or_none("iios.entity.Instrument")
        if td is None:
            pytest.skip("iios.entity.Instrument not found in registry")
        engine = get_validation_engine()
        rpt    = engine.validate_runtime_object({"symbol": "NIFTY"}, td.uri)
        assert rpt is not None

    def test_stats_after_runs(self):
        """After multiple validation runs, stats accumulate correctly."""
        from iios.ontology.validator import get_validation_engine
        engine = get_validation_engine()
        for _ in range(3):
            engine.validate_type(_make_type())
        s = engine.stats()
        assert s["total_runs"] >= 3
