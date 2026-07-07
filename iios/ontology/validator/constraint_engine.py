"""
iios/ontology/validator/constraint_engine.py
=============================================
Evaluates registered constraints against ontology objects.

The ConstraintEngine is the low-level runner: it retrieves all
applicable constraints from the ConstraintRegistry for a given scope
and runs them against the supplied target, accumulating ValidationResult
objects.  It does NOT raise — all findings go into the result list.

Thread-safe: the engine itself is stateless; all mutable state lives
in the registry and the caller-supplied objects.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Optional

from ..ontology_constants import MAX_INHERITANCE_DEPTH, DataType
from ..runtime.runtime_object import (
    CompiledOntology,
    OntologyDocument,
    OntologyNamespace,
    OntologyRelationshipDef,
    OntologyTypeDef,
)
from .constraint_registry import ConstraintDef, ConstraintRegistry, get_constraint_registry
from .validation_constants import (
    MAX_PARALLEL_VALIDATORS,
    ConstraintType,
    ValidationScope,
    ValidationSeverity,
)
from .validation_result import ValidationResult

__all__ = [
    "ConstraintEngine",
    "get_constraint_engine",
    "reset_constraint_engine",
]

_LOG = logging.getLogger("iios.ontology.validator.constraint_engine")


class ConstraintEngine:
    """
    Evaluates applicable constraints for an ontology target.

    All ``check_*`` methods return a flat ``list[ValidationResult]``.
    They never raise — exceptions inside individual constraint rules
    are caught and surfaced as ERROR results.
    """

    def __init__(self, registry: Optional[ConstraintRegistry] = None) -> None:
        self._registry = registry or get_constraint_registry()

    # ── Internal runner ───────────────────────────────────────────────────────

    def _run_constraints(
        self,
        constraints: list[ConstraintDef],
        target:      Any,
        all_types:   dict[str, Any],
        parallel:    bool = False,
    ) -> list[ValidationResult]:
        """
        Execute *constraints* against *target*.

        Args:
            parallel: If True, run in a thread pool (for large batches).
        """
        results: list[ValidationResult] = []

        if parallel and len(constraints) > 4:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(MAX_PARALLEL_VALIDATORS, len(constraints))
            ) as pool:
                futures = {pool.submit(self._safe_run, cd, target, all_types): cd for cd in constraints}
                for fut in concurrent.futures.as_completed(futures):
                    results.extend(fut.result())
        else:
            for cd in constraints:
                results.extend(self._safe_run(cd, target, all_types))

        return results

    def _safe_run(
        self,
        cd:        ConstraintDef,
        target:    Any,
        all_types: dict[str, Any],
    ) -> list[ValidationResult]:
        """Run one constraint, catching all exceptions."""
        try:
            return cd(target, all_types)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("Constraint %r raised unexpectedly: %s", cd.constraint_id, exc)
            return [
                ValidationResult.fail(
                    constraint_id = cd.constraint_id,
                    message       = f"Constraint raised {type(exc).__name__}: {exc}",
                    severity      = ValidationSeverity.ERROR,
                    scope         = cd.scope,
                )
            ]

    # ── Public check methods ─────────────────────────────────────────────────

    def check_type_def(
        self,
        typedef:   OntologyTypeDef,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run all TYPE-scope constraints against *typedef*."""
        constraints = self._registry.get_by_scope(ValidationScope.TYPE)
        return self._run_constraints(constraints, typedef, all_types)  # type: ignore[arg-type]

    def check_property(
        self,
        typedef:   OntologyTypeDef,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run PROPERTY-scope constraints against every property of *typedef*."""
        constraints = self._registry.get_by_scope(ValidationScope.PROPERTY)
        results: list[ValidationResult] = []
        for prop in typedef.properties.values():
            results.extend(self._run_constraints(constraints, prop, all_types))  # type: ignore[arg-type]
        return results

    def check_relationship_def(
        self,
        rel:       OntologyRelationshipDef,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run RELATIONSHIP-scope constraints against *rel*."""
        constraints = self._registry.get_by_scope(ValidationScope.RELATIONSHIP)
        return self._run_constraints(constraints, rel, all_types)  # type: ignore[arg-type]

    def check_namespace(
        self,
        namespace: OntologyNamespace,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run NAMESPACE-scope constraints against *namespace*."""
        constraints = self._registry.get_by_scope(ValidationScope.NAMESPACE)
        return self._run_constraints(constraints, namespace, all_types)  # type: ignore[arg-type]

    def check_document(
        self,
        doc:       OntologyDocument,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run DOCUMENT-scope constraints against *doc*."""
        constraints = self._registry.get_by_scope(ValidationScope.DOCUMENT)
        return self._run_constraints(constraints, doc, all_types)  # type: ignore[arg-type]

    def check_compiled_ontology(
        self,
        compiled:  CompiledOntology,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run COMPILED-scope constraints against *compiled*."""
        constraints = self._registry.get_by_scope(ValidationScope.COMPILED)
        results = self._run_constraints(constraints, compiled, all_types)  # type: ignore[arg-type]

        # Also validate every type and its properties
        for typedef in compiled.types.values():
            results.extend(self.check_type_def(typedef, all_types))
            results.extend(self.check_property(typedef, all_types))

        # Validate relationships
        for rel in compiled.relationships.values():
            results.extend(self.check_relationship_def(rel, all_types))

        return results

    def check_hierarchy(
        self,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run HIERARCHY-scope constraints against the full type set."""
        constraints = self._registry.get_by_scope(ValidationScope.HIERARCHY)
        return self._run_constraints(constraints, all_types, all_types, parallel=True)  # type: ignore[arg-type]

    def check_references(
        self,
        all_types:         dict[str, OntologyTypeDef],
        all_relationships: dict[str, OntologyRelationshipDef],
    ) -> list[ValidationResult]:
        """Run REFERENCE-scope constraints against each type."""
        constraints = self._registry.get_by_scope(ValidationScope.REFERENCE)
        results: list[ValidationResult] = []
        combined: dict[str, Any] = {
            "types":         all_types,
            "relationships": all_relationships,
        }
        for typedef in all_types.values():
            results.extend(self._run_constraints(constraints, typedef, combined))  # type: ignore[arg-type]
        return results

    def check_runtime_object(
        self,
        obj:       dict[str, Any],
        type_uri:  str,
        all_types: dict[str, OntologyTypeDef],
    ) -> list[ValidationResult]:
        """Run RUNTIME_OBJ-scope constraints against *obj*."""
        constraints = self._registry.get_by_scope(ValidationScope.RUNTIME_OBJ)
        target = {"obj": obj, "type_uri": type_uri}
        return self._run_constraints(constraints, target, all_types)  # type: ignore[arg-type]


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading

_lock:   threading.Lock              = threading.Lock()
_engine: Optional[ConstraintEngine] = None


def get_constraint_engine() -> ConstraintEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = ConstraintEngine()
    return _engine


def reset_constraint_engine() -> None:
    global _engine
    with _lock:
        _engine = None
