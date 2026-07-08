"""
iios/ontology/reasoning/inference/inference_registry.py
========================================================
Registry of inference rules with built-in rules for the IIOS
ontology structure.

Built-in rules cover:
  1. Inheritance propagation   — explicit property inheritance facts
  2. Subtype transitivity      — transitive subtype relationships
  3. Symmetric relationship    — inverse relationship inference
  4. Type consistency          — broken parent references
  5. Namespace consistency     — namespace URI registered
  6. Reference validity        — REF properties pointing to unknown types
  7. Abstract type check       — abstract types with no children (warning)
  8. Orphan type check         — types whose parent does not exist
  9. Relationship endpoint check — broken source/target URIs

Singleton: get_inference_registry() / reset_inference_registry()
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from ..reasoning_constants import (
    RuleType,
    IssueSeverity,
    IssueType,
    CONFIDENCE_CERTAIN,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    PRED_INHERITS_PROPERTY,
    PRED_HAS_OWN_PROPERTY,
    PRED_TRANSITIVE_SUBTYPE,
    PRED_INVERSE_RELATED,
    RULE_INHERITANCE_PROPAGATION,
    RULE_SUBTYPE_TRANSITIVITY,
    RULE_SYMMETRIC_RELATIONSHIP,
    RULE_TYPE_CONSISTENCY,
    RULE_NAMESPACE_CONSISTENCY,
    RULE_REFERENCE_VALIDITY,
    RULE_ABSTRACT_TYPE_CHECK,
    RULE_ORPHAN_TYPE_CHECK,
    RULE_REL_ENDPOINT_CHECK,
    MAX_RULES,
)
from ..reasoning_exceptions import DuplicateRuleError, UnknownRuleError
from ..reasoning_result     import InferredFact, ConsistencyIssue, FactStore
from .inference_rule        import InferenceRule

__all__ = [
    "InferenceRegistry",
    "get_inference_registry",
    "reset_inference_registry",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Built-in rule implementations
#  (module-level functions — no closures, deterministic behaviour)
# ══════════════════════════════════════════════════════════════════════════════

def _inheritance_condition(facts: FactStore, mgr: Any) -> bool:
    return mgr.stats()["total_types"] > 0


def _inheritance_action(facts: FactStore, mgr: Any) -> list:
    new_items: list = []
    for td in mgr.list_all_types():
        if td.parent_uri is None:
            continue
        # Own properties
        for prop_name in td.properties:
            f = InferredFact(
                subject_uri  = td.uri,
                predicate    = PRED_HAS_OWN_PROPERTY,
                object_value = prop_name,
                confidence   = CONFIDENCE_CERTAIN,
                rule_ids     = [RULE_INHERITANCE_PROPAGATION],
                inferred     = False,
            )
            new_items.append(f)
        # Inherited properties (from all_properties_of which merges ancestry)
        merged = mgr.all_properties_of(td.uri)
        for prop_name, prop in merged.items():
            if prop_name not in td.properties:
                f = InferredFact(
                    subject_uri  = td.uri,
                    predicate    = PRED_INHERITS_PROPERTY,
                    object_value = prop_name,
                    confidence   = CONFIDENCE_HIGH,
                    rule_ids     = [RULE_INHERITANCE_PROPAGATION],
                    inferred     = True,
                )
                new_items.append(f)
    return new_items


def _subtype_transitivity_action(facts: FactStore, mgr: Any) -> list:
    new_items: list = []
    for td in mgr.list_all_types():
        ancestors = mgr.ancestors_of(td.uri)
        for anc_uri in ancestors:
            if anc_uri == td.uri:
                continue
            f = InferredFact(
                subject_uri  = td.uri,
                predicate    = PRED_TRANSITIVE_SUBTYPE,
                object_value = anc_uri,
                confidence   = CONFIDENCE_CERTAIN,
                rule_ids     = [RULE_SUBTYPE_TRANSITIVITY],
                inferred     = True,
            )
            new_items.append(f)
    return new_items


def _symmetric_rel_action(facts: FactStore, mgr: Any) -> list:
    new_items: list = []
    for rel in mgr.list_relationships():
        if rel.inverse_uri and rel.source_type_uri and rel.target_type_uri:
            # Forward inference: source knows it is inversely related to target
            f = InferredFact(
                subject_uri  = rel.target_type_uri,
                predicate    = PRED_INVERSE_RELATED,
                object_value = rel.source_type_uri,
                confidence   = CONFIDENCE_HIGH,
                rule_ids     = [RULE_SYMMETRIC_RELATIONSHIP],
                inferred     = True,
                metadata     = {"via_relationship": rel.uri},
            )
            new_items.append(f)
    return new_items


def _type_consistency_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    for td in mgr.list_all_types():
        if td.parent_uri and not mgr.has_type(td.parent_uri):
            issues.append(ConsistencyIssue(
                issue_type    = IssueType.BROKEN_PARENT_REF,
                severity      = IssueSeverity.ERROR,
                description   = (
                    f"Type {td.uri!r} declares parent {td.parent_uri!r} "
                    f"which is not registered."
                ),
                affected_uris = [td.uri, td.parent_uri],
                rule_id       = RULE_TYPE_CONSISTENCY,
                fix_suggestion = f"Register {td.parent_uri!r} or remove the parent reference.",
            ))
    return issues


def _namespace_consistency_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    registered_ns = {ns.uri for ns in mgr.list_namespaces()}
    seen_ns: set[str] = set()
    for td in mgr.list_all_types():
        ns_uri = td.namespace_uri
        if ns_uri and ns_uri not in registered_ns and ns_uri not in seen_ns:
            seen_ns.add(ns_uri)
            issues.append(ConsistencyIssue(
                issue_type    = IssueType.NAMESPACE_NOT_FOUND,
                severity      = IssueSeverity.WARNING,
                description   = f"Namespace {ns_uri!r} used by types but not registered.",
                affected_uris = [td.uri],
                rule_id       = RULE_NAMESPACE_CONSISTENCY,
                fix_suggestion = f"Register namespace {ns_uri!r} in the ontology.",
            ))
    return issues


def _reference_validity_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    from iios.ontology.runtime.runtime_object import DataType
    for td in mgr.list_all_types():
        for prop_name, prop in td.properties.items():
            if prop.data_type == DataType.REF and prop.ref_uri:
                if not mgr.has_type(prop.ref_uri):
                    issues.append(ConsistencyIssue(
                        issue_type    = IssueType.BROKEN_PROPERTY_REF,
                        severity      = IssueSeverity.ERROR,
                        description   = (
                            f"Property {prop_name!r} on {td.uri!r} references "
                            f"type {prop.ref_uri!r} which does not exist."
                        ),
                        affected_uris = [td.uri, prop.ref_uri],
                        rule_id       = RULE_REFERENCE_VALIDITY,
                        fix_suggestion = f"Register type {prop.ref_uri!r} or update the property.",
                    ))
    return issues


def _abstract_type_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    for td in mgr.list_all_types():
        if td.abstract and not mgr.children_of(td.uri):
            issues.append(ConsistencyIssue(
                issue_type    = IssueType.ABSTRACT_NO_CHILDREN,
                severity      = IssueSeverity.WARNING,
                description   = (
                    f"Abstract type {td.uri!r} has no registered subtypes. "
                    f"It cannot be instantiated."
                ),
                affected_uris = [td.uri],
                rule_id       = RULE_ABSTRACT_TYPE_CHECK,
                fix_suggestion = "Add concrete subtypes or remove the abstract flag.",
            ))
    return issues


def _orphan_type_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    for td in mgr.list_all_types():
        if td.parent_uri and not mgr.has_type(td.parent_uri):
            issues.append(ConsistencyIssue(
                issue_type    = IssueType.ORPHAN_TYPE,
                severity      = IssueSeverity.ERROR,
                description   = (
                    f"Type {td.uri!r} is an orphan: its parent {td.parent_uri!r} "
                    f"is not in the registry."
                ),
                affected_uris = [td.uri],
                rule_id       = RULE_ORPHAN_TYPE_CHECK,
                fix_suggestion = f"Register parent {td.parent_uri!r} or remove parent reference.",
            ))
    return issues


def _rel_endpoint_action(facts: FactStore, mgr: Any) -> list:
    issues: list = []
    for rel in mgr.list_relationships():
        for uri, role in [
            (rel.source_type_uri, "source"),
            (rel.target_type_uri, "target"),
        ]:
            if uri and not mgr.has_type(uri):
                issues.append(ConsistencyIssue(
                    issue_type    = IssueType.RELATIONSHIP_BROKEN,
                    severity      = IssueSeverity.ERROR,
                    description   = (
                        f"Relationship {rel.uri!r} has an unregistered {role} type: {uri!r}."
                    ),
                    affected_uris = [rel.uri, uri],
                    rule_id       = RULE_REL_ENDPOINT_CHECK,
                    fix_suggestion = f"Register type {uri!r} or update the relationship.",
                ))
    return issues


# ══════════════════════════════════════════════════════════════════════════════
#  Registry
# ══════════════════════════════════════════════════════════════════════════════

class InferenceRegistry:
    """
    Thread-safe registry of inference rules.

    Built-in rules are registered automatically on construction.
    Custom rules can be added at any time via register().
    """

    def __init__(self) -> None:
        self._rules: dict[str, InferenceRule] = {}
        self._lock   = threading.RLock()
        self._register_builtins()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        rule:      InferenceRule,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if rule.rule_id in self._rules and not overwrite:
                raise DuplicateRuleError(rule.rule_id)
            if len(self._rules) >= MAX_RULES and rule.rule_id not in self._rules:
                raise DuplicateRuleError(
                    f"Registry full ({MAX_RULES} rules)"
                )
            self._rules[rule.rule_id] = rule

    def unregister(self, rule_id: str) -> bool:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            if rule.builtin:
                raise DuplicateRuleError(
                    f"Cannot unregister built-in rule {rule_id!r}"
                )
            del self._rules[rule_id]
            return True

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, rule_id: str) -> InferenceRule:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                raise UnknownRuleError(rule_id)
            return rule

    def has(self, rule_id: str) -> bool:
        with self._lock:
            return rule_id in self._rules

    def all_rules(self) -> list[InferenceRule]:
        with self._lock:
            return sorted(self._rules.values(), key=lambda r: r.priority)

    def enabled_rules(self) -> list[InferenceRule]:
        with self._lock:
            return sorted(
                (r for r in self._rules.values() if r.enabled),
                key=lambda r: r.priority,
            )

    def rules_by_type(self, rule_type: RuleType) -> list[InferenceRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.rule_type == rule_type]

    def rules_by_tag(self, tag: str) -> list[InferenceRule]:
        with self._lock:
            return [r for r in self._rules.values() if tag in r.tags]

    def enable(self, rule_id: str) -> None:
        with self._lock:
            self.get(rule_id).enabled = True

    def disable(self, rule_id: str) -> None:
        with self._lock:
            self.get(rule_id).enabled = False

    def stats(self) -> dict:
        with self._lock:
            total    = len(self._rules)
            enabled  = sum(1 for r in self._rules.values() if r.enabled)
            builtins = sum(1 for r in self._rules.values() if r.builtin)
            return {
                "total":    total,
                "enabled":  enabled,
                "disabled": total - enabled,
                "builtins": builtins,
                "custom":   total - builtins,
            }

    # ── Built-in registration ─────────────────────────────────────────────────

    def _register_builtins(self) -> None:
        self._add(InferenceRule(
            rule_id     = RULE_INHERITANCE_PROPAGATION,
            name        = "Inheritance Propagation",
            description = "Emit inherits_property facts for all inherited properties.",
            rule_type   = RuleType.IMPLICATION,
            priority    = 10,
            confidence  = CONFIDENCE_HIGH,
            condition   = _inheritance_condition,
            action      = _inheritance_action,
            builtin     = True,
            tags        = ["inheritance", "property"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_SUBTYPE_TRANSITIVITY,
            name        = "Subtype Transitivity",
            description = "Emit transitive_subtype_of facts for all ancestor chains.",
            rule_type   = RuleType.DEDUCTION,
            priority    = 20,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: True,
            action      = _subtype_transitivity_action,
            builtin     = True,
            tags        = ["inheritance", "transitivity"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_SYMMETRIC_RELATIONSHIP,
            name        = "Symmetric Relationship",
            description = "Emit inverse_related_to facts for relationships with inverse_uri.",
            rule_type   = RuleType.IMPLICATION,
            priority    = 30,
            confidence  = CONFIDENCE_HIGH,
            condition   = lambda f, m: len(m.list_relationships()) > 0,
            action      = _symmetric_rel_action,
            builtin     = True,
            tags        = ["relationship", "symmetry"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_TYPE_CONSISTENCY,
            name        = "Type Consistency",
            description = "Detect types with unregistered parent URIs.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 50,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: True,
            action      = _type_consistency_action,
            builtin     = True,
            tags        = ["consistency", "constraint"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_NAMESPACE_CONSISTENCY,
            name        = "Namespace Consistency",
            description = "Detect types referencing unregistered namespace URIs.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 51,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: True,
            action      = _namespace_consistency_action,
            builtin     = True,
            tags        = ["consistency", "namespace"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_REFERENCE_VALIDITY,
            name        = "Reference Validity",
            description = "Detect REF properties pointing to unregistered types.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 52,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: True,
            action      = _reference_validity_action,
            builtin     = True,
            tags        = ["consistency", "reference"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_ABSTRACT_TYPE_CHECK,
            name        = "Abstract Type Check",
            description = "Warn about abstract types with no subtypes.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 60,
            confidence  = CONFIDENCE_HIGH,
            condition   = lambda f, m: True,
            action      = _abstract_type_action,
            builtin     = True,
            tags        = ["consistency", "abstract"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_ORPHAN_TYPE_CHECK,
            name        = "Orphan Type Check",
            description = "Detect types whose declared parent is missing.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 53,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: True,
            action      = _orphan_type_action,
            builtin     = True,
            tags        = ["consistency", "orphan"],
        ))
        self._add(InferenceRule(
            rule_id     = RULE_REL_ENDPOINT_CHECK,
            name        = "Relationship Endpoint Check",
            description = "Detect relationships with unregistered source/target types.",
            rule_type   = RuleType.CONSTRAINT,
            priority    = 54,
            confidence  = CONFIDENCE_CERTAIN,
            condition   = lambda f, m: len(m.list_relationships()) > 0,
            action      = _rel_endpoint_action,
            builtin     = True,
            tags        = ["consistency", "relationship"],
        ))

    def _add(self, rule: InferenceRule) -> None:
        """Internal add without lock (called from __init__)."""
        self._rules[rule.rule_id] = rule


# ── Singleton ─────────────────────────────────────────────────────────────────

_reg_lock = threading.Lock()
_reg_inst: Optional[InferenceRegistry] = None


def get_inference_registry() -> InferenceRegistry:
    global _reg_inst
    if _reg_inst is None:
        with _reg_lock:
            if _reg_inst is None:
                _reg_inst = InferenceRegistry()
    return _reg_inst


def reset_inference_registry() -> None:
    global _reg_inst
    with _reg_lock:
        _reg_inst = None
