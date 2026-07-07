"""
iios/ontology/validator/constraint_manager.py
==============================================
Manages the lifecycle of constraints: loads built-in rules, supports
custom rule registration, and provides policy-level helpers.

All built-in IIOS constraints are registered here under stable IDs
with the ``builtin.*`` prefix.  Callers may add their own constraints
under any other prefix.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from ..ontology_constants import MAX_INHERITANCE_DEPTH, DataType
from ..runtime.runtime_object import (
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)
from .constraint_registry import (
    ConstraintDef,
    ConstraintRegistry,
    get_constraint_registry,
)
from .validation_constants import (
    BUILTIN_HIER_PREFIX,
    BUILTIN_NS_PREFIX,
    BUILTIN_PROP_PREFIX,
    BUILTIN_REF_PREFIX,
    BUILTIN_REL_PREFIX,
    BUILTIN_TYPE_PREFIX,
    MAX_INHERITANCE_CHECK_DEPTH,
    ConstraintType,
    ValidationScope,
    ValidationSeverity,
)
from .validation_result import ValidationResult

__all__ = [
    "ConstraintManager",
    "get_constraint_manager",
    "reset_constraint_manager",
]

_LOG = logging.getLogger("iios.ontology.validator.constraint_manager")


# ══════════════════════════════════════════════════════════════════════════════
# Built-in constraint rule functions
# ══════════════════════════════════════════════════════════════════════════════

# ── Type-level rules ──────────────────────────────────────────────────────────

def _type_has_uri(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.has_uri"
    if not typedef.uri or not typedef.uri.strip():
        return [ValidationResult.critical(cid, f"Type has empty URI", scope=ValidationScope.TYPE,
                                          target_uri=typedef.uri)]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_has_name(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.has_name"
    if not typedef.name or not typedef.name.strip():
        return [ValidationResult.critical(cid, f"Type has empty name", scope=ValidationScope.TYPE,
                                          target_uri=typedef.uri)]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_has_namespace(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.has_namespace"
    if not typedef.namespace_uri or not typedef.namespace_uri.strip():
        return [ValidationResult.critical(cid, f"Type {typedef.uri!r} has empty namespace_uri",
                                          scope=ValidationScope.TYPE, target_uri=typedef.uri)]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_uri_matches_namespace(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.uri_matches_namespace"
    if typedef.uri and typedef.namespace_uri and not typedef.uri.startswith(typedef.namespace_uri):
        return [ValidationResult.fail(
            cid,
            f"Type URI {typedef.uri!r} does not start with namespace {typedef.namespace_uri!r}",
            scope=ValidationScope.TYPE,
            severity=ValidationSeverity.ERROR,
            target_uri=typedef.uri,
            fix_suggestion="Ensure type URI begins with namespace_uri + '.'",
        )]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_no_self_inheritance(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.no_self_inheritance"
    if typedef.parent_uri and typedef.parent_uri == typedef.uri:
        return [ValidationResult.critical(cid, f"Type {typedef.uri!r} inherits from itself",
                                          scope=ValidationScope.TYPE, target_uri=typedef.uri)]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_parent_exists(typedef: OntologyTypeDef, all_types: dict[str, Any]) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.parent_exists"
    if not typedef.parent_uri:
        return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]
    # all_types may be the raw dict or a wrapped {"types": ..., "relationships": ...}
    types_map: dict[str, OntologyTypeDef] = (
        all_types.get("types", all_types) if isinstance(all_types, dict) and "types" in all_types
        else all_types
    )
    if typedef.parent_uri not in types_map:
        return [ValidationResult.fail(
            cid,
            f"Type {typedef.uri!r} references unknown parent {typedef.parent_uri!r}",
            scope=ValidationScope.TYPE,
            severity=ValidationSeverity.WARNING,
            target_uri=typedef.uri,
            path="parent_uri",
            fix_suggestion="Ensure the parent ontology is compiled before this one",
        )]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=typedef.uri)]


def _type_uri_well_formed(typedef: OntologyTypeDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_TYPE_PREFIX}.uri_well_formed"
    uri = typedef.uri
    if not uri:
        return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=uri)]
    if " " in uri:
        return [ValidationResult.fail(cid, f"URI {uri!r} contains whitespace",
                                      scope=ValidationScope.TYPE, severity=ValidationSeverity.ERROR,
                                      target_uri=uri, fix_suggestion="Remove spaces from the URI")]
    if not all(part.isidentifier() or part == "" for part in uri.split(".")):
        return [ValidationResult.warn(cid, f"URI {uri!r} contains non-identifier segments",
                                      scope=ValidationScope.TYPE, target_uri=uri)]
    return [ValidationResult.ok(cid, ValidationScope.TYPE, target_uri=uri)]


# ── Property-level rules ──────────────────────────────────────────────────────

def _prop_has_name(prop: OntologyProperty, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_PROP_PREFIX}.has_name"
    if not prop.name or not prop.name.strip():
        return [ValidationResult.critical(cid, "Property has empty name", scope=ValidationScope.PROPERTY)]
    return [ValidationResult.ok(cid, ValidationScope.PROPERTY)]


def _prop_ref_uri_if_ref_type(prop: OntologyProperty, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_PROP_PREFIX}.ref_uri_if_ref_type"
    if prop.data_type == DataType.REF and not prop.ref_uri:
        return [ValidationResult.fail(
            cid,
            f"Property {prop.name!r} has data_type=REF but ref_uri is empty",
            scope=ValidationScope.PROPERTY,
            severity=ValidationSeverity.ERROR,
            path=f"properties.{prop.name}.ref_uri",
            fix_suggestion="Set ref_uri to the target type URI",
        )]
    return [ValidationResult.ok(cid, ValidationScope.PROPERTY)]


def _prop_ref_uri_exists(prop: OntologyProperty, all_types: dict[str, Any]) -> list[ValidationResult]:
    cid = f"{BUILTIN_PROP_PREFIX}.ref_uri_exists"
    if prop.data_type != DataType.REF or not prop.ref_uri:
        return [ValidationResult.ok(cid, ValidationScope.PROPERTY)]
    types_map: dict[str, Any] = (
        all_types.get("types", all_types) if isinstance(all_types, dict) and "types" in all_types
        else all_types
    )
    if prop.ref_uri not in types_map:
        return [ValidationResult.fail(
            cid,
            f"Property {prop.name!r} ref_uri {prop.ref_uri!r} not found",
            scope=ValidationScope.PROPERTY,
            severity=ValidationSeverity.WARNING,
            path=f"properties.{prop.name}.ref_uri",
            fix_suggestion="Ensure the referenced type is compiled first",
        )]
    return [ValidationResult.ok(cid, ValidationScope.PROPERTY)]


def _prop_name_is_identifier(prop: OntologyProperty, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_PROP_PREFIX}.name_is_identifier"
    if prop.name and not prop.name.isidentifier():
        return [ValidationResult.warn(
            cid,
            f"Property name {prop.name!r} is not a valid Python identifier",
            scope=ValidationScope.PROPERTY,
        )]
    return [ValidationResult.ok(cid, ValidationScope.PROPERTY)]


# ── Relationship-level rules ──────────────────────────────────────────────────

def _rel_has_uri(rel: OntologyRelationshipDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_REL_PREFIX}.has_uri"
    if not rel.uri or not rel.uri.strip():
        return [ValidationResult.critical(cid, "Relationship has empty URI", scope=ValidationScope.RELATIONSHIP)]
    return [ValidationResult.ok(cid, ValidationScope.RELATIONSHIP, target_uri=rel.uri)]


def _rel_source_exists(rel: OntologyRelationshipDef, all_types: dict[str, Any]) -> list[ValidationResult]:
    cid = f"{BUILTIN_REL_PREFIX}.source_exists"
    types_map: dict[str, Any] = (
        all_types.get("types", all_types) if isinstance(all_types, dict) and "types" in all_types
        else all_types
    )
    if rel.source_type_uri not in types_map:
        return [ValidationResult.fail(
            cid,
            f"Relationship {rel.uri!r} source {rel.source_type_uri!r} not found",
            scope=ValidationScope.RELATIONSHIP,
            severity=ValidationSeverity.WARNING,
            target_uri=rel.uri,
            path="source_type_uri",
        )]
    return [ValidationResult.ok(cid, ValidationScope.RELATIONSHIP, target_uri=rel.uri)]


def _rel_target_exists(rel: OntologyRelationshipDef, all_types: dict[str, Any]) -> list[ValidationResult]:
    cid = f"{BUILTIN_REL_PREFIX}.target_exists"
    types_map: dict[str, Any] = (
        all_types.get("types", all_types) if isinstance(all_types, dict) and "types" in all_types
        else all_types
    )
    if rel.target_type_uri not in types_map:
        return [ValidationResult.fail(
            cid,
            f"Relationship {rel.uri!r} target {rel.target_type_uri!r} not found",
            scope=ValidationScope.RELATIONSHIP,
            severity=ValidationSeverity.WARNING,
            target_uri=rel.uri,
            path="target_type_uri",
        )]
    return [ValidationResult.ok(cid, ValidationScope.RELATIONSHIP, target_uri=rel.uri)]


def _rel_has_name(rel: OntologyRelationshipDef, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_REL_PREFIX}.has_name"
    if not rel.name or not rel.name.strip():
        return [ValidationResult.critical(cid, "Relationship has empty name",
                                          scope=ValidationScope.RELATIONSHIP, target_uri=rel.uri)]
    return [ValidationResult.ok(cid, ValidationScope.RELATIONSHIP, target_uri=rel.uri)]


# ── Namespace-level rules ─────────────────────────────────────────────────────

def _ns_has_uri(ns: OntologyNamespace, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_NS_PREFIX}.has_uri"
    if not ns.uri or not ns.uri.strip():
        return [ValidationResult.critical(cid, "Namespace has empty URI", scope=ValidationScope.NAMESPACE)]
    return [ValidationResult.ok(cid, ValidationScope.NAMESPACE)]


def _ns_has_name(ns: OntologyNamespace, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_NS_PREFIX}.has_name"
    if not ns.name or not ns.name.strip():
        return [ValidationResult.critical(cid, "Namespace has empty name", scope=ValidationScope.NAMESPACE)]
    return [ValidationResult.ok(cid, ValidationScope.NAMESPACE)]


def _ns_has_prefix(ns: OntologyNamespace, _: Any) -> list[ValidationResult]:
    cid = f"{BUILTIN_NS_PREFIX}.has_prefix"
    if not ns.prefix or not ns.prefix.strip():
        return [ValidationResult.warn(cid, f"Namespace {ns.uri!r} has no prefix set",
                                      scope=ValidationScope.NAMESPACE,
                                      fix_suggestion="Set a short prefix for usability")]
    return [ValidationResult.ok(cid, ValidationScope.NAMESPACE)]


# ── Hierarchy-level rules ─────────────────────────────────────────────────────

def _hier_max_depth(all_types: dict[str, OntologyTypeDef], _: Any) -> list[ValidationResult]:
    cid  = f"{BUILTIN_HIER_PREFIX}.max_depth"
    results: list[ValidationResult] = []
    for uri, typedef in all_types.items():
        depth = 0
        current: Optional[str] = typedef.parent_uri
        visited: set[str] = {uri}
        while current and depth <= MAX_INHERITANCE_CHECK_DEPTH:
            if current in visited:
                break  # Cycle — handled by _hier_no_cycle
            visited.add(current)
            depth += 1
            parent = all_types.get(current)
            current = parent.parent_uri if parent else None
        if depth > MAX_INHERITANCE_DEPTH:
            results.append(ValidationResult.fail(
                cid,
                f"Type {uri!r} has inheritance depth {depth} > {MAX_INHERITANCE_DEPTH}",
                scope=ValidationScope.HIERARCHY,
                severity=ValidationSeverity.ERROR,
                target_uri=uri,
                fix_suggestion=f"Flatten the hierarchy — max depth is {MAX_INHERITANCE_DEPTH}",
            ))
        else:
            results.append(ValidationResult.ok(cid, ValidationScope.HIERARCHY, target_uri=uri))
    return results


def _hier_no_cycle(all_types: dict[str, OntologyTypeDef], _: Any) -> list[ValidationResult]:
    cid     = f"{BUILTIN_HIER_PREFIX}.no_cycle"
    results: list[ValidationResult] = []
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {uri: WHITE for uri in all_types}

    def _dfs(uri: str, path: list[str]) -> Optional[list[str]]:
        color[uri] = GREY
        path.append(uri)
        parent_uri = all_types[uri].parent_uri
        if parent_uri and parent_uri in all_types:
            c = color.get(parent_uri, WHITE)
            if c == GREY:
                return path + [parent_uri]
            if c == WHITE:
                sub = _dfs(parent_uri, path[:])
                if sub:
                    return sub
        color[uri] = BLACK
        return None

    reported: set[frozenset[str]] = set()
    for uri in list(all_types):
        if color[uri] == WHITE:
            cycle = _dfs(uri, [])
            if cycle:
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    results.append(ValidationResult.critical(
                        cid,
                        f"Circular inheritance: {' → '.join(cycle)}",
                        scope=ValidationScope.HIERARCHY,
                        details={"chain": cycle},
                        target_uri=cycle[0],
                    ))

    if not results:
        results.append(ValidationResult.ok(cid, ValidationScope.HIERARCHY))
    return results


# ── Reference-level rules ─────────────────────────────────────────────────────

def _ref_parent_uri_exists(typedef: OntologyTypeDef, combined: dict[str, Any]) -> list[ValidationResult]:
    cid        = f"{BUILTIN_REF_PREFIX}.parent_uri_exists"
    types_map  = combined.get("types", combined) if isinstance(combined, dict) and "types" in combined else combined
    if not typedef.parent_uri:
        return [ValidationResult.ok(cid, ValidationScope.REFERENCE, target_uri=typedef.uri)]
    if typedef.parent_uri not in types_map:
        return [ValidationResult.fail(
            cid,
            f"parent_uri {typedef.parent_uri!r} of type {typedef.uri!r} not found",
            scope=ValidationScope.REFERENCE,
            severity=ValidationSeverity.WARNING,
            target_uri=typedef.uri,
            path="parent_uri",
        )]
    return [ValidationResult.ok(cid, ValidationScope.REFERENCE, target_uri=typedef.uri)]


def _ref_property_ref_uris_exist(typedef: OntologyTypeDef, combined: dict[str, Any]) -> list[ValidationResult]:
    cid       = f"{BUILTIN_REF_PREFIX}.property_ref_uris"
    types_map = combined.get("types", combined) if isinstance(combined, dict) and "types" in combined else combined
    results: list[ValidationResult] = []
    for prop in typedef.properties.values():
        if prop.data_type == DataType.REF and prop.ref_uri and prop.ref_uri not in types_map:
            results.append(ValidationResult.fail(
                cid,
                f"Property {prop.name!r}.ref_uri {prop.ref_uri!r} not found",
                scope=ValidationScope.REFERENCE,
                severity=ValidationSeverity.WARNING,
                target_uri=typedef.uri,
                path=f"properties.{prop.name}.ref_uri",
            ))
    if not results:
        results.append(ValidationResult.ok(cid, ValidationScope.REFERENCE, target_uri=typedef.uri))
    return results


# ── Runtime object rules ──────────────────────────────────────────────────────

def _runtime_required_props(target: dict[str, Any], all_types: dict[str, Any]) -> list[ValidationResult]:
    cid      = f"{BUILTIN_TYPE_PREFIX}.runtime.required_props"
    obj      = target.get("obj", {})
    type_uri = target.get("type_uri", "")
    results: list[ValidationResult] = []
    typedef: Optional[OntologyTypeDef] = all_types.get(type_uri)  # type: ignore[assignment]
    if typedef is None:
        results.append(ValidationResult.warn(
            cid,
            f"Cannot validate runtime object: type {type_uri!r} not found",
            scope=ValidationScope.RUNTIME_OBJ,
        ))
        return results
    for name, prop in typedef.properties.items():
        if prop.required and name not in obj:
            results.append(ValidationResult.fail(
                cid,
                f"Required property {name!r} missing on runtime object of type {type_uri!r}",
                scope=ValidationScope.RUNTIME_OBJ,
                severity=ValidationSeverity.ERROR,
                path=name,
                target_uri=type_uri,
                fix_suggestion=f"Set {name!r} before persisting the object",
            ))
    if not results:
        results.append(ValidationResult.ok(cid, ValidationScope.RUNTIME_OBJ, target_uri=type_uri))
    return results


def _runtime_type_known(target: dict[str, Any], all_types: dict[str, Any]) -> list[ValidationResult]:
    cid      = f"{BUILTIN_TYPE_PREFIX}.runtime.type_known"
    type_uri = target.get("type_uri", "")
    if type_uri not in all_types:
        return [ValidationResult.fail(
            cid,
            f"Runtime object claims unknown type {type_uri!r}",
            scope=ValidationScope.RUNTIME_OBJ,
            severity=ValidationSeverity.ERROR,
            target_uri=type_uri,
        )]
    return [ValidationResult.ok(cid, ValidationScope.RUNTIME_OBJ, target_uri=type_uri)]


# ══════════════════════════════════════════════════════════════════════════════
# ConstraintManager
# ══════════════════════════════════════════════════════════════════════════════

class ConstraintManager:
    """
    Manages the constraint lifecycle:
      - Loads all built-in IIOS constraints into the registry
      - Accepts custom constraint registration
      - Provides policy-level enable/disable helpers
    """

    def __init__(self, registry: Optional[ConstraintRegistry] = None) -> None:
        self._registry   = registry or get_constraint_registry()
        self._initialized = False
        self._lock        = threading.RLock()

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def register_builtin_constraints(self) -> int:
        """
        Register all IIOS built-in constraints.

        Returns:
            Number of constraints registered.
        """
        with self._lock:
            if self._initialized:
                return len(self._registry.all_ids())
            rules = self._builtin_rules()
            registered = 0
            for (cid, name, ctype, scope, severity, rule, description) in rules:
                try:
                    self._registry.register(
                        constraint_id   = cid,
                        name            = name,
                        constraint_type = ctype,
                        scope           = scope,
                        severity        = severity,
                        rule            = rule,
                        description     = description,
                        overwrite       = False,
                    )
                    registered += 1
                except Exception as exc:
                    _LOG.warning("Failed to register builtin constraint %r: %s", cid, exc)
            self._initialized = True
            _LOG.info("Registered %d built-in constraints", registered)
            return registered

    @staticmethod
    def _builtin_rules() -> list[tuple]:
        """Return (cid, name, ctype, scope, severity, rule, description) tuples."""
        S = ValidationSeverity
        T = ConstraintType
        Sc = ValidationScope
        return [
            # ── Type ─────────────────────────────────────────────────────────
            (f"{BUILTIN_TYPE_PREFIX}.has_uri",              "Type has URI",
             T.REQUIRED_FIELD, Sc.TYPE,  S.CRITICAL, _type_has_uri,
             "Every OntologyTypeDef must have a non-empty URI"),
            (f"{BUILTIN_TYPE_PREFIX}.has_name",             "Type has name",
             T.REQUIRED_FIELD, Sc.TYPE,  S.CRITICAL, _type_has_name,
             "Every OntologyTypeDef must have a non-empty name"),
            (f"{BUILTIN_TYPE_PREFIX}.has_namespace",        "Type has namespace",
             T.REQUIRED_FIELD, Sc.TYPE,  S.CRITICAL, _type_has_namespace,
             "Every OntologyTypeDef must have a non-empty namespace_uri"),
            (f"{BUILTIN_TYPE_PREFIX}.uri_matches_namespace","URI matches namespace",
             T.URI_FORMAT,     Sc.TYPE,  S.ERROR,    _type_uri_matches_namespace,
             "Type URI must start with namespace_uri"),
            (f"{BUILTIN_TYPE_PREFIX}.no_self_inheritance",  "No self-inheritance",
             T.CIRCULAR,       Sc.TYPE,  S.CRITICAL, _type_no_self_inheritance,
             "A type must not declare itself as its own parent"),
            (f"{BUILTIN_TYPE_PREFIX}.parent_exists",        "Parent exists",
             T.REFERENCE,      Sc.TYPE,  S.WARNING,  _type_parent_exists,
             "If parent_uri is set it must be in the visible type universe"),
            (f"{BUILTIN_TYPE_PREFIX}.uri_well_formed",      "URI well-formed",
             T.URI_FORMAT,     Sc.TYPE,  S.WARNING,  _type_uri_well_formed,
             "Type URI should contain only dotted identifier segments"),
            # ── Property ─────────────────────────────────────────────────────
            (f"{BUILTIN_PROP_PREFIX}.has_name",             "Property has name",
             T.REQUIRED_FIELD, Sc.PROPERTY, S.CRITICAL, _prop_has_name,
             "Every property must have a non-empty name"),
            (f"{BUILTIN_PROP_PREFIX}.ref_uri_if_ref_type",  "REF type needs ref_uri",
             T.REFERENCE,      Sc.PROPERTY, S.ERROR,   _prop_ref_uri_if_ref_type,
             "Properties with DataType.REF must set ref_uri"),
            (f"{BUILTIN_PROP_PREFIX}.ref_uri_exists",       "REF uri exists",
             T.REFERENCE,      Sc.PROPERTY, S.WARNING, _prop_ref_uri_exists,
             "ref_uri on a property must point to a known type"),
            (f"{BUILTIN_PROP_PREFIX}.name_is_identifier",   "Prop name is identifier",
             T.URI_FORMAT,     Sc.PROPERTY, S.WARNING, _prop_name_is_identifier,
             "Property names should be valid Python identifiers"),
            # ── Relationship ─────────────────────────────────────────────────
            (f"{BUILTIN_REL_PREFIX}.has_uri",               "Relationship has URI",
             T.REQUIRED_FIELD, Sc.RELATIONSHIP, S.CRITICAL, _rel_has_uri,
             "Every relationship must have a non-empty URI"),
            (f"{BUILTIN_REL_PREFIX}.has_name",              "Relationship has name",
             T.REQUIRED_FIELD, Sc.RELATIONSHIP, S.CRITICAL, _rel_has_name,
             "Every relationship must have a non-empty name"),
            (f"{BUILTIN_REL_PREFIX}.source_exists",         "Relationship source exists",
             T.REFERENCE,      Sc.RELATIONSHIP, S.WARNING, _rel_source_exists,
             "Relationship source_type_uri must point to a known type"),
            (f"{BUILTIN_REL_PREFIX}.target_exists",         "Relationship target exists",
             T.REFERENCE,      Sc.RELATIONSHIP, S.WARNING, _rel_target_exists,
             "Relationship target_type_uri must point to a known type"),
            # ── Namespace ────────────────────────────────────────────────────
            (f"{BUILTIN_NS_PREFIX}.has_uri",                "Namespace has URI",
             T.REQUIRED_FIELD, Sc.NAMESPACE, S.CRITICAL, _ns_has_uri,
             "Every namespace must have a non-empty URI"),
            (f"{BUILTIN_NS_PREFIX}.has_name",               "Namespace has name",
             T.REQUIRED_FIELD, Sc.NAMESPACE, S.CRITICAL, _ns_has_name,
             "Every namespace must have a non-empty name"),
            (f"{BUILTIN_NS_PREFIX}.has_prefix",             "Namespace has prefix",
             T.REQUIRED_FIELD, Sc.NAMESPACE, S.WARNING,  _ns_has_prefix,
             "Namespaces should define a short prefix"),
            # ── Hierarchy ────────────────────────────────────────────────────
            (f"{BUILTIN_HIER_PREFIX}.max_depth",            "Max inheritance depth",
             T.INHERITANCE,    Sc.HIERARCHY, S.ERROR,    _hier_max_depth,
             f"Inheritance depth must not exceed {MAX_INHERITANCE_DEPTH}"),
            (f"{BUILTIN_HIER_PREFIX}.no_cycle",             "No circular inheritance",
             T.CIRCULAR,       Sc.HIERARCHY, S.CRITICAL, _hier_no_cycle,
             "No type may appear in its own inheritance chain"),
            # ── Reference ────────────────────────────────────────────────────
            (f"{BUILTIN_REF_PREFIX}.parent_uri_exists",     "parent_uri reference",
             T.REFERENCE,      Sc.REFERENCE, S.WARNING,  _ref_parent_uri_exists,
             "All parent_uri references must be resolvable"),
            (f"{BUILTIN_REF_PREFIX}.property_ref_uris",     "Property ref_uri references",
             T.REFERENCE,      Sc.REFERENCE, S.WARNING,  _ref_property_ref_uris_exist,
             "All property ref_uri values must point to known types"),
            # ── Runtime object ────────────────────────────────────────────────
            (f"{BUILTIN_TYPE_PREFIX}.runtime.type_known",   "Runtime type known",
             T.TYPE_CHECK,     Sc.RUNTIME_OBJ, S.ERROR, _runtime_type_known,
             "Runtime objects must claim a type known to the ontology"),
            (f"{BUILTIN_TYPE_PREFIX}.runtime.required_props", "Runtime required props",
             T.REQUIRED_FIELD, Sc.RUNTIME_OBJ, S.ERROR, _runtime_required_props,
             "All required properties must be present on runtime objects"),
        ]

    # ── Custom constraint registration ────────────────────────────────────────

    def register_custom(
        self,
        rule:            Callable,
        name:            str,
        constraint_type: ConstraintType    = ConstraintType.CUSTOM,
        scope:           ValidationScope   = ValidationScope.TYPE,
        severity:        ValidationSeverity = ValidationSeverity.ERROR,
        constraint_id:   Optional[str]     = None,
        description:     str               = "",
        tags:            Optional[list[str]] = None,
        overwrite:       bool              = False,
    ) -> str:
        """
        Register a custom constraint rule.

        Returns:
            The assigned constraint_id.
        """
        import uuid as _uuid
        cid = constraint_id or f"custom.{name.lower().replace(' ', '_')}.{_uuid.uuid4().hex[:8]}"
        self._registry.register(
            constraint_id   = cid,
            name            = name,
            constraint_type = constraint_type,
            scope           = scope,
            severity        = severity,
            rule            = rule,
            description     = description,
            tags            = list(tags or []),
            overwrite       = overwrite,
        )
        return cid

    def unregister(self, constraint_id: str) -> None:
        self._registry.unregister(constraint_id)

    def enable(self, constraint_id: str) -> None:
        self._registry.enable(constraint_id)

    def disable(self, constraint_id: str) -> None:
        self._registry.disable(constraint_id)

    def list_constraints(
        self,
        scope:           Optional[ValidationScope]  = None,
        constraint_type: Optional[ConstraintType]   = None,
        enabled_only:    bool                       = False,
    ) -> list[ConstraintDef]:
        """Return constraints filtered by optional scope / type."""
        if scope is not None:
            return self._registry.get_by_scope(scope, enabled_only=enabled_only)
        if constraint_type is not None:
            return self._registry.get_by_type(constraint_type, enabled_only=enabled_only)
        if enabled_only:
            return self._registry.all_enabled()
        with self._registry._lock:
            return list(self._registry._constraints.values())

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def stats(self) -> dict[str, Any]:
        return {
            "initialized":   self._initialized,
            "constraints":   self._registry.stats(),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading as _threading

_mlock:   _threading.Lock              = _threading.Lock()
_manager: Optional[ConstraintManager] = None


def get_constraint_manager() -> ConstraintManager:
    global _manager
    if _manager is None:
        with _mlock:
            if _manager is None:
                _manager = ConstraintManager()
    return _manager


def reset_constraint_manager() -> None:
    global _manager
    with _mlock:
        _manager = None
