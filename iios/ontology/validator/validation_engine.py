"""
iios/ontology/validator/validation_engine.py
=============================================
Master orchestrator for the Ontology Validation & Constraint Engine.

This is the primary public API surface.  Callers should only need to
import from this module (or from the package __init__.py).

Responsibilities:
  - Bootstrap built-in constraints on first use
  - Expose validate_type / validate_ontology / validate_all_ontologies
  - Enforce validation policies (mode → exception gating)
  - Maintain per-target validation history
  - Provide incremental / batch / background validation
  - Record stats and health status
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from typing import Any, Optional

from ..compiler.compiler_manager import get_compiler_manager
from ..ontology_constants import BUILTIN_ONTOLOGY_NAMES
from ..registry.ontology_registry_manager import OntologyRegistryManager, get_registry_manager
from ..runtime.runtime_object import OntologyDocument, OntologyTypeDef
from .constraint_engine import ConstraintEngine, get_constraint_engine
from .constraint_manager import ConstraintManager, get_constraint_manager
from .constraint_registry import ConstraintDef, ConstraintRegistry, get_constraint_registry
from .ontology_validator import OntologyValidator, get_ontology_validator
from .validation_constants import (
    MAX_BATCH_SIZE,
    MAX_HISTORY_PER_TARGET,
    MAX_PARALLEL_VALIDATORS,
    SYSTEM_VALIDATOR_ACTOR,
    VALIDATOR_VERSION,
    ConstraintType,
    ValidationMode,
    ValidationPhase,
    ValidationScope,
    ValidationSeverity,
)
from .validation_exceptions import (
    ConstraintViolationError,
    ValidationEngineError,
    ValidationNotInitializedError,
    ValidationTimeoutError,
)
from .validation_report import ValidationHistory, ValidationReport
from .validation_result import ValidationResult

__all__ = [
    "ValidationEngine",
    "get_validation_engine",
    "reset_validation_engine",
]

_LOG = logging.getLogger("iios.ontology.validator.engine")


class ValidationEngine:
    """
    Production-grade semantic validation orchestrator.

    Thread-safe.  All methods are safe to call concurrently.

    Bootstrap order:
      1. Instantiate (singletons are lazy-initialized).
      2. Call ``initialize()`` (or let it auto-initialise on first use).
      3. Call any ``validate_*`` method.

    Policy enforcement:
      - STRICT:       ERROR + WARNING both raise ConstraintViolationError
      - STANDARD:     ERROR raises; WARNING recorded only
      - PERMISSIVE:   Only CRITICAL raises
      - WARNING_ONLY: Never raises — all findings reported only
    """

    def __init__(
        self,
        registry:   Optional[OntologyRegistryManager] = None,
        validator:  Optional[OntologyValidator]        = None,
        engine:     Optional[ConstraintEngine]         = None,
        manager:    Optional[ConstraintManager]        = None,
        creg:       Optional[ConstraintRegistry]       = None,
    ) -> None:
        self._registry   = registry  or get_registry_manager()
        self._validator  = validator or get_ontology_validator()
        self._engine     = engine    or get_constraint_engine()
        self._manager    = manager   or get_constraint_manager()
        self._creg       = creg      or get_constraint_registry()
        self._history    = ValidationHistory(max_per_target=MAX_HISTORY_PER_TARGET)
        self._lock       = threading.RLock()
        self._initialized = False
        self._total_runs  = 0
        self._total_errors = 0

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Ensure built-in constraints are loaded and the compiler is warm.

        Idempotent — safe to call multiple times.
        """
        with self._lock:
            if self._initialized:
                return
            if not self._manager.is_initialized:
                self._manager.register_builtin_constraints()
            self._initialized = True
            _LOG.info("ValidationEngine initialized (v%s)", VALIDATOR_VERSION)

    def _ensure_init(self) -> None:
        if not self._initialized:
            self.initialize()

    # ── Single type validation ────────────────────────────────────────────────

    def validate_type(
        self,
        typedef:   OntologyTypeDef,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.ON_DEMAND,
        raise_on_failure: bool = False,
    ) -> ValidationReport:
        """
        Validate a single OntologyTypeDef.

        Args:
            typedef:         The type to validate.
            all_types:       Additional types visible during validation.
            mode:            Policy strictness level.
            phase:           Lifecycle phase.
            raise_on_failure: If True, raises ConstraintViolationError when
                             the report has errors (respecting mode).
        """
        self._ensure_init()
        if all_types is None:
            all_types = {t.uri: t for t in self._registry.list_all_types()}
        report = self._validator.validate_type_def(typedef, all_types, mode=mode, phase=phase)
        self._record(report)
        if raise_on_failure:
            self._maybe_raise(report, mode)
        return report

    # ── Single ontology validation ────────────────────────────────────────────

    def validate_ontology(
        self,
        name:  str,
        mode:  ValidationMode  = ValidationMode.STANDARD,
        phase: ValidationPhase = ValidationPhase.POST_COMPILE,
    ) -> ValidationReport:
        """
        Validate a single compiled ontology by name.

        The ontology must already be compiled (loaded into the registry).
        """
        self._ensure_init()
        compiled = self._registry.get_compiled(name)
        if compiled is None:
            report = ValidationReport(
                target_id   = name,
                target_type = "CompiledOntology",
                phase       = phase,
            )
            report.add(ValidationResult.fail(
                "engine.ontology_not_found",
                f"Ontology {name!r} is not compiled — run compile_builtins() first",
                severity=ValidationSeverity.ERROR,
            ))
            report.finalise()
            self._record(report)
            return report

        all_types = {t.uri: t for t in self._registry.list_all_types()}
        report    = self._validator.validate_compiled_ontology(compiled, all_types, mode=mode, phase=phase)
        # Also namespace consistency
        ns_report = self._validator.validate_namespace_consistency(compiled)
        report.merge(ns_report)
        report.finalise()
        self._record(report)
        return report

    # ── All builtins ──────────────────────────────────────────────────────────

    def validate_all_ontologies(
        self,
        mode:     ValidationMode = ValidationMode.STANDARD,
        parallel: bool           = False,
    ) -> dict[str, ValidationReport]:
        """
        Validate every compiled ontology in the registry.

        Returns:
            Mapping of ontology_name → ValidationReport.
        """
        self._ensure_init()
        names = list(self._registry.compiled_names())
        if not names:
            return {}

        if parallel and len(names) > 2:
            reports: dict[str, ValidationReport] = {}
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(MAX_PARALLEL_VALIDATORS, len(names))
            ) as pool:
                future_to_name = {pool.submit(self.validate_ontology, n, mode): n for n in names}
                for fut in concurrent.futures.as_completed(future_to_name):
                    n = future_to_name[fut]
                    try:
                        reports[n] = fut.result()
                    except Exception as exc:
                        _LOG.exception("Validation of %r raised: %s", n, exc)
                        r = ValidationReport(target_id=n, target_type="CompiledOntology")
                        r.add(ValidationResult.fail("engine.internal_error", str(exc),
                                                    severity=ValidationSeverity.CRITICAL))
                        r.finalise()
                        reports[n] = r
            return reports
        else:
            return {n: self.validate_ontology(n, mode=mode) for n in names}

    # ── Full registry validation ──────────────────────────────────────────────

    def validate_all(
        self,
        mode: ValidationMode = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """
        Run a complete global validation pass across the entire live registry.

        This is the heaviest operation — intended for scheduled / background use.
        """
        self._ensure_init()
        report = self._validator.validate_all(self._registry, mode=mode)
        self._record(report)
        return report

    # ── Referential integrity ─────────────────────────────────────────────────

    def validate_referential_integrity(
        self,
        mode: ValidationMode = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """
        Validate cross-references across all known types and relationships.
        """
        self._ensure_init()
        all_types = {t.uri: t for t in self._registry.list_all_types()}
        all_rels  = {r.uri: r for r in self._registry.list_relationships()}
        report    = self._validator.validate_cross_references(all_types, all_rels, mode=mode)
        self._record(report)
        return report

    # ── Hierarchy validation ──────────────────────────────────────────────────

    def validate_hierarchy(
        self,
        mode: ValidationMode = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """Validate the global inheritance hierarchy."""
        self._ensure_init()
        all_types = {t.uri: t for t in self._registry.list_all_types()}
        report    = self._validator.validate_hierarchy(all_types, mode=mode)
        self._record(report)
        return report

    # ── Runtime object ────────────────────────────────────────────────────────

    def validate_runtime_object(
        self,
        obj:              dict[str, Any],
        type_uri:         str,
        mode:             ValidationMode  = ValidationMode.STANDARD,
        phase:            ValidationPhase = ValidationPhase.RUNTIME,
        raise_on_failure: bool            = False,
    ) -> ValidationReport:
        """
        Validate a live runtime object against its declared ontology type.

        Args:
            obj:      The runtime object as a dict of field→value.
            type_uri: The ontology type URI the object claims to be.
        """
        self._ensure_init()
        all_types = {t.uri: t for t in self._registry.list_all_types()}
        report    = self._validator.validate_runtime_object(obj, type_uri, all_types, mode=mode, phase=phase)
        self._record(report)
        if raise_on_failure:
            self._maybe_raise(report, mode)
        return report

    # ── Pre-registration ──────────────────────────────────────────────────────

    def validate_pre_registration(
        self,
        typedef:          OntologyTypeDef,
        raise_on_failure: bool           = True,
        mode:             ValidationMode = ValidationMode.STRICT,
    ) -> ValidationReport:
        """
        Gate-check before a type is registered in the ontology.

        By default this is STRICT and raises on failure.
        """
        return self.validate_type(
            typedef,
            mode             = mode,
            phase            = ValidationPhase.PRE_REGISTRATION,
            raise_on_failure = raise_on_failure,
        )

    # ── Batch validation ──────────────────────────────────────────────────────

    def validate_batch(
        self,
        typedefs: list[OntologyTypeDef],
        mode:     ValidationMode = ValidationMode.STANDARD,
        parallel: bool           = False,
    ) -> list[ValidationReport]:
        """
        Validate a list of OntologyTypeDef objects.

        Args:
            typedefs: The types to validate (max MAX_BATCH_SIZE).
            parallel: Run validations in parallel for speed.
        """
        self._ensure_init()
        if len(typedefs) > MAX_BATCH_SIZE:
            raise ValidationEngineError(
                f"Batch size {len(typedefs)} exceeds MAX_BATCH_SIZE={MAX_BATCH_SIZE}"
            )
        all_types = {t.uri: t for t in self._registry.list_all_types()}

        if parallel and len(typedefs) > 4:
            reports: list[Optional[ValidationReport]] = [None] * len(typedefs)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(MAX_PARALLEL_VALIDATORS, len(typedefs))
            ) as pool:
                future_to_idx = {
                    pool.submit(self.validate_type, td, all_types, mode): i
                    for i, td in enumerate(typedefs)
                }
                for fut in concurrent.futures.as_completed(future_to_idx):
                    idx = future_to_idx[fut]
                    try:
                        reports[idx] = fut.result()
                    except Exception as exc:
                        r = ValidationReport(target_id=typedefs[idx].uri, target_type="OntologyTypeDef")
                        r.add(ValidationResult.fail("engine.batch_error", str(exc),
                                                    severity=ValidationSeverity.CRITICAL))
                        r.finalise()
                        reports[idx] = r
            return [r for r in reports if r is not None]
        else:
            return [self.validate_type(td, all_types, mode=mode) for td in typedefs]

    # ── Incremental validation ────────────────────────────────────────────────

    def validate_incremental(
        self,
        changed_names: list[str],
        mode:          ValidationMode = ValidationMode.STANDARD,
    ) -> dict[str, ValidationReport]:
        """
        Validate only ontologies that have changed (name list from IncrementalLoader).
        """
        self._ensure_init()
        return {n: self.validate_ontology(n, mode=mode) for n in changed_names}

    # ── Convenience helpers ───────────────────────────────────────────────────

    def is_valid(
        self,
        typedef: OntologyTypeDef,
        mode:    ValidationMode = ValidationMode.STANDARD,
    ) -> bool:
        """Return True if the type passes validation without errors."""
        return self.validate_type(typedef, mode=mode).passed

    def is_ontology_valid(self, name: str) -> bool:
        """Return True if the named ontology passes validation."""
        return self.validate_ontology(name).passed

    # ── History ───────────────────────────────────────────────────────────────

    def get_history(
        self,
        target_id: str,
        limit:     Optional[int] = None,
    ) -> list[ValidationReport]:
        return self._history.get(target_id, limit=limit)

    def last_report(self, target_id: str) -> Optional[ValidationReport]:
        return self._history.last(target_id)

    # ── Custom constraints ────────────────────────────────────────────────────

    def register_constraint(
        self,
        rule:            Any,
        name:            str,
        constraint_type: ConstraintType    = ConstraintType.CUSTOM,
        scope:           ValidationScope   = ValidationScope.TYPE,
        severity:        ValidationSeverity = ValidationSeverity.ERROR,
        constraint_id:   Optional[str]     = None,
        description:     str               = "",
    ) -> str:
        """Register a custom constraint rule and return its ID."""
        return self._manager.register_custom(
            rule            = rule,
            name            = name,
            constraint_type = constraint_type,
            scope           = scope,
            severity        = severity,
            constraint_id   = constraint_id,
            description     = description,
        )

    def disable_constraint(self, constraint_id: str) -> None:
        self._manager.disable(constraint_id)

    def enable_constraint(self, constraint_id: str) -> None:
        self._manager.enable(constraint_id)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _record(self, report: ValidationReport) -> None:
        with self._lock:
            self._total_runs  += 1
            self._total_errors += report.error_count + report.critical_count
        if report.target_id:
            self._history.record(report)

    def _maybe_raise(self, report: ValidationReport, mode: ValidationMode) -> None:
        """Raise ConstraintViolationError if the mode demands it."""
        if mode == ValidationMode.WARNING_ONLY:
            return
        threshold = {
            ValidationMode.STRICT:     ValidationSeverity.WARNING,
            ValidationMode.STANDARD:   ValidationSeverity.ERROR,
            ValidationMode.PERMISSIVE: ValidationSeverity.CRITICAL,
            ValidationMode.SCHEMA_ONLY: ValidationSeverity.ERROR,
            ValidationMode.RUNTIME_ONLY: ValidationSeverity.ERROR,
        }.get(mode, ValidationSeverity.ERROR)

        blocking = report.at_or_above(threshold)
        blocking = [r for r in blocking if not r.passed]  # Only actual failures
        if blocking:
            worst = blocking[0]
            raise ConstraintViolationError(
                constraint_id = worst.constraint_id,
                target        = report.target_id,
                message       = worst.message,
            )

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "initialized":   self._initialized,
                "version":       VALIDATOR_VERSION,
                "total_runs":    self._total_runs,
                "total_errors":  self._total_errors,
                "history":       self._history.stats(),
                "constraints":   self._creg.stats(),
            }

    def health(self) -> dict[str, Any]:
        constraints = self._creg.stats()
        status = "healthy" if self._initialized and constraints["enabled"] > 0 else "degraded"
        return {
            "status":      status,
            "initialized": self._initialized,
            "constraints": constraints["enabled"],
            "total_runs":  self._total_runs,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_lock:   threading.Lock              = threading.Lock()
_engine: Optional[ValidationEngine] = None


def get_validation_engine() -> ValidationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = ValidationEngine()
    return _engine


def reset_validation_engine() -> None:
    global _engine
    with _lock:
        _engine = None
