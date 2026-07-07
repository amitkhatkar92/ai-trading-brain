"""
iios/ontology/validator/ontology_validator.py
=============================================
Core semantic validator for ontology objects.

Runs constraint checks via the ConstraintEngine and adds semantic
checks that operate across multiple objects (hierarchy analysis,
cross-reference validation, namespace consistency).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ..ontology_constants import MAX_INHERITANCE_DEPTH
from ..registry.ontology_registry_manager import OntologyRegistryManager
from ..runtime.runtime_object import (
    CompiledOntology,
    OntologyDocument,
    OntologyNamespace,
    OntologyRelationshipDef,
    OntologyTypeDef,
)
from .constraint_engine import ConstraintEngine, get_constraint_engine
from .constraint_manager import ConstraintManager, get_constraint_manager
from .validation_constants import (
    BUILTIN_HIER_PREFIX,
    BUILTIN_REF_PREFIX,
    MAX_INHERITANCE_CHECK_DEPTH,
    ValidationMode,
    ValidationPhase,
    ValidationScope,
    ValidationSeverity,
)
from .validation_report import ValidationReport
from .validation_result import ValidationResult

__all__ = [
    "OntologyValidator",
    "get_ontology_validator",
    "reset_ontology_validator",
]

_LOG = logging.getLogger("iios.ontology.validator")


class OntologyValidator:
    """
    Semantic validator for ontology definitions.

    Responsibilities:
      - Validate individual OntologyTypeDef / Namespace / Relationship / Document
      - Validate compiled ontologies (full structural check)
      - Validate the global hierarchy for cycles and depth violations
      - Validate cross-references across the registry
      - Validate runtime object compliance
    """

    def __init__(
        self,
        engine:  Optional[ConstraintEngine]  = None,
        manager: Optional[ConstraintManager] = None,
    ) -> None:
        self._engine  = engine  or get_constraint_engine()
        self._manager = manager or get_constraint_manager()
        # Ensure built-in constraints are loaded
        if not self._manager.is_initialized:
            self._manager.register_builtin_constraints()

    # ── Type definition ───────────────────────────────────────────────────────

    def validate_type_def(
        self,
        typedef:   OntologyTypeDef,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.ON_DEMAND,
    ) -> ValidationReport:
        """Validate a single OntologyTypeDef."""
        report   = ValidationReport(
            target_id   = typedef.uri,
            target_type = "OntologyTypeDef",
            phase       = phase,
        )
        types    = all_types or {}
        report.add_all(self._engine.check_type_def(typedef, types))
        report.add_all(self._engine.check_property(typedef, types))
        report.finalise()
        return report

    # ── Namespace ─────────────────────────────────────────────────────────────

    def validate_namespace(
        self,
        namespace: OntologyNamespace,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.ON_DEMAND,
    ) -> ValidationReport:
        """Validate an OntologyNamespace."""
        report = ValidationReport(
            target_id   = namespace.uri,
            target_type = "OntologyNamespace",
            phase       = phase,
        )
        report.add_all(self._engine.check_namespace(namespace, all_types or {}))
        report.finalise()
        return report

    # ── Relationship ──────────────────────────────────────────────────────────

    def validate_relationship_def(
        self,
        rel:       OntologyRelationshipDef,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.ON_DEMAND,
    ) -> ValidationReport:
        """Validate an OntologyRelationshipDef."""
        report = ValidationReport(
            target_id   = rel.uri,
            target_type = "OntologyRelationshipDef",
            phase       = phase,
        )
        report.add_all(self._engine.check_relationship_def(rel, all_types or {}))
        report.finalise()
        return report

    # ── Document ──────────────────────────────────────────────────────────────

    def validate_document(
        self,
        doc:       OntologyDocument,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.PRE_COMPILE,
    ) -> ValidationReport:
        """Validate an OntologyDocument (pre-compile)."""
        report = ValidationReport(
            target_id   = doc.name,
            target_type = "OntologyDocument",
            phase       = phase,
        )
        # Namespace
        if doc.namespace:
            ns_report = self.validate_namespace(doc.namespace, all_types)
            report.merge(ns_report)
        # Each type in the document
        types = all_types or {}
        for typedef in doc.types.values():
            report.add_all(self._engine.check_type_def(typedef, types))
            report.add_all(self._engine.check_property(typedef, types))
        # Each relationship in the document
        for rel in doc.relationships.values():
            report.add_all(self._engine.check_relationship_def(rel, types))
        # Document-level constraints
        report.add_all(self._engine.check_document(doc, types))
        report.finalise()
        return report

    # ── Compiled ontology ─────────────────────────────────────────────────────

    def validate_compiled_ontology(
        self,
        compiled:  CompiledOntology,
        all_types: Optional[dict[str, OntologyTypeDef]] = None,
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.POST_COMPILE,
    ) -> ValidationReport:
        """Validate a CompiledOntology (post-compile)."""
        report = ValidationReport(
            target_id   = compiled.name,
            target_type = "CompiledOntology",
            phase       = phase,
        )
        types = {**compiled.types, **(all_types or {})}
        report.add_all(self._engine.check_compiled_ontology(compiled, types))
        report.finalise()
        return report

    # ── Hierarchy (global) ────────────────────────────────────────────────────

    def validate_hierarchy(
        self,
        all_types: dict[str, OntologyTypeDef],
        mode:      ValidationMode  = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """
        Validate the full inheritance hierarchy across all known types.

        Checks:
          - No circular inheritance
          - Max depth not exceeded
        """
        report = ValidationReport(
            target_id   = "global.hierarchy",
            target_type = "GlobalHierarchy",
            phase       = ValidationPhase.BATCH,
        )
        report.add_all(self._engine.check_hierarchy(all_types))
        report.finalise()
        return report

    # ── Cross-references ──────────────────────────────────────────────────────

    def validate_cross_references(
        self,
        all_types:         dict[str, OntologyTypeDef],
        all_relationships: Optional[dict[str, OntologyRelationshipDef]] = None,
        mode:              ValidationMode = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """Validate all cross-object references (parent URIs, ref_uris, endpoints)."""
        report = ValidationReport(
            target_id   = "global.references",
            target_type = "CrossReferences",
            phase       = ValidationPhase.BATCH,
        )
        report.add_all(self._engine.check_references(all_types, all_relationships or {}))
        report.finalise()
        return report

    # ── Full registry validation ──────────────────────────────────────────────

    def validate_all(
        self,
        registry: OntologyRegistryManager,
        mode:     ValidationMode = ValidationMode.STANDARD,
    ) -> ValidationReport:
        """
        Run a complete validation pass against the live registry.

        This is the heaviest operation — use for batch / background runs.
        """
        report = ValidationReport(
            target_id   = "global",
            target_type = "GlobalRegistry",
            phase       = ValidationPhase.BATCH,
        )
        all_types = {t.uri: t for t in registry.list_all_types()}

        # 1. Type + property checks
        for typedef in all_types.values():
            report.add_all(self._engine.check_type_def(typedef, all_types))
            report.add_all(self._engine.check_property(typedef, all_types))

        # 2. Relationship checks
        all_rels = {r.uri: r for r in registry.list_relationships()}
        for rel in all_rels.values():
            report.add_all(self._engine.check_relationship_def(rel, all_types))

        # 3. Namespace checks
        all_ns = {ns.uri: ns for ns in registry.list_namespaces()}
        for ns in all_ns.values():
            report.add_all(self._engine.check_namespace(ns, all_types))

        # 4. Hierarchy
        report.merge(self.validate_hierarchy(all_types, mode=mode))

        # 5. Cross-references
        report.merge(self.validate_cross_references(all_types, all_rels, mode=mode))

        report.finalise()
        _LOG.info(
            "Full registry validation complete: %s errors, %s warnings, %s criticals (%.1f ms)",
            report.error_count, report.warning_count, report.critical_count, report.duration_ms,
        )
        return report

    # ── Runtime object ────────────────────────────────────────────────────────

    def validate_runtime_object(
        self,
        obj:       dict[str, Any],
        type_uri:  str,
        all_types: dict[str, OntologyTypeDef],
        mode:      ValidationMode  = ValidationMode.STANDARD,
        phase:     ValidationPhase = ValidationPhase.RUNTIME,
    ) -> ValidationReport:
        """Validate a live runtime object against its declared ontology type."""
        report = ValidationReport(
            target_id   = type_uri,
            target_type = "RuntimeObject",
            phase       = phase,
        )
        report.add_all(self._engine.check_runtime_object(obj, type_uri, all_types))
        report.finalise()
        return report

    # ── Namespace consistency ─────────────────────────────────────────────────

    def validate_namespace_consistency(
        self,
        compiled: CompiledOntology,
    ) -> ValidationReport:
        """
        Verify that every type URI in *compiled* starts with the namespace URI.
        """
        report = ValidationReport(
            target_id   = compiled.name,
            target_type = "NamespaceConsistency",
            phase       = ValidationPhase.POST_COMPILE,
        )
        ns_uri = compiled.namespace_uri or ""
        for typedef in compiled.types.values():
            if ns_uri and not typedef.uri.startswith(ns_uri):
                report.add(ValidationResult.fail(
                    f"{BUILTIN_REF_PREFIX}.ns_consistency",
                    f"Type {typedef.uri!r} not within namespace {ns_uri!r}",
                    scope=ValidationScope.NAMESPACE,
                    severity=ValidationSeverity.ERROR,
                    target_uri=typedef.uri,
                ))
            else:
                report.add(ValidationResult.ok(
                    f"{BUILTIN_REF_PREFIX}.ns_consistency",
                    ValidationScope.NAMESPACE,
                    target_uri=typedef.uri,
                ))
        report.finalise()
        return report


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading

_lock:     threading.Lock               = threading.Lock()
_validator: Optional[OntologyValidator] = None


def get_ontology_validator() -> OntologyValidator:
    global _validator
    if _validator is None:
        with _lock:
            if _validator is None:
                _validator = OntologyValidator()
    return _validator


def reset_ontology_validator() -> None:
    global _validator
    with _lock:
        _validator = None
