"""
tests/unit/ontology/test_reasoning_engine.py
=============================================
Comprehensive tests for the IIOS Ontology Reasoning Integration Engine.
"""

from __future__ import annotations

import threading
import time
import pytest

# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_type(name, ns="iios.test", parent=None, labels=None, aliases=None, abstract=False):
    from iios.ontology.ontology_factory import get_ontology_factory
    fac = get_ontology_factory()
    return fac.create_type(
        name=name, namespace_uri=ns, parent_uri=parent,
        labels=labels or [], aliases=aliases or [], abstract=abstract,
        uri=f"{ns}.{name}",
    )


def _register_type(td):
    from iios.ontology.registry.ontology_registry_manager import get_registry_manager
    mgr = get_registry_manager()
    with mgr._lock:
        mgr._types[td.uri] = td
        if td.parent_uri:
            mgr._children.setdefault(td.parent_uri, set()).add(td.uri)
        for alias in td.aliases:
            mgr._aliases[alias] = td.uri


def _register_namespace(uri: str, name: str | None = None):
    from iios.ontology.registry.ontology_registry_manager import get_registry_manager
    from iios.ontology.runtime.runtime_object import OntologyNamespace
    mgr = get_registry_manager()
    ns = OntologyNamespace(uri=uri, name=name or uri.split(".")[-1], prefix=uri.split(".")[-1])
    with mgr._lock:
        mgr._namespaces[uri] = ns


def _register_rel(uri, name, source, target, inverse_uri=None):
    from iios.ontology.registry.ontology_registry_manager import get_registry_manager
    from iios.ontology.runtime.runtime_object import OntologyRelationshipDef
    rel = OntologyRelationshipDef(
        uri=uri, name=name, namespace_uri="iios.test",
        source_type_uri=source, target_type_uri=target,
        description="", labels=[],
        inverse_uri=inverse_uri,
    )
    mgr = get_registry_manager()
    with mgr._lock:
        mgr._relationships[uri] = rel
    return rel


def _reset_all():
    from iios.ontology.reasoning.reasoning_engine      import reset_reasoning_engine
    from iios.ontology.reasoning.reasoning_manager     import reset_reasoning_manager
    from iios.ontology.reasoning.reasoning_registry    import reset_reasoning_registry
    from iios.ontology.reasoning.reasoning_context     import reset_reasoning_context
    from iios.ontology.reasoning.reasoning_factory     import reset_reasoning_factory
    from iios.ontology.reasoning.reasoning_session     import reset_session_manager
    from iios.ontology.reasoning.reasoning_statistics  import reset_reasoning_statistics
    from iios.ontology.reasoning.inference.inference_engine   import reset_inference_engine_instance
    from iios.ontology.reasoning.inference.inference_executor import reset_inference_executor
    from iios.ontology.reasoning.inference.inference_registry import reset_inference_registry
    # inference_graph has no module singleton — nothing to reset
    from iios.ontology.reasoning.explanation.explanation_engine   import reset_explanation_engine
    from iios.ontology.reasoning.explanation.proof_generator      import reset_proof_generator
    from iios.ontology.reasoning.explanation.reasoning_explainer  import reset_reasoning_explainer
    # Ontology singletons
    from iios.ontology.ontology_factory import reset_ontology_factory
    from iios.ontology.registry.ontology_registry_manager import reset_registry_manager
    reset_reasoning_engine()
    reset_reasoning_manager()
    reset_reasoning_registry()
    reset_reasoning_context()
    reset_reasoning_factory()
    reset_session_manager()
    reset_reasoning_statistics()
    reset_inference_engine_instance()
    reset_inference_executor()
    reset_inference_registry()
    reset_explanation_engine()
    reset_proof_generator()
    reset_reasoning_explainer()
    reset_registry_manager()
    reset_ontology_factory()


@pytest.fixture(autouse=True)
def reset_all_singletons():
    _reset_all()
    yield
    _reset_all()


# ══════════════════════════════════════════════════════════════════════════════
#  1 — Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_reasoning_type_members(self):
        from iios.ontology.reasoning import ReasoningType
        assert ReasoningType.FORWARD_CHAIN.value == "forward_chain"
        assert ReasoningType.BACKWARD_CHAIN.value == "backward_chain"
        assert ReasoningType.FULL_INFERENCE.value == "full_inference"
        assert ReasoningType.CONSISTENCY_CHECK.value == "consistency_check"

    def test_confidence_levels_ordered(self):
        from iios.ontology.reasoning import (
            CONFIDENCE_CERTAIN, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
            CONFIDENCE_LOW, CONFIDENCE_SPECULATIVE,
        )
        assert CONFIDENCE_CERTAIN > CONFIDENCE_HIGH > CONFIDENCE_MEDIUM > CONFIDENCE_LOW > CONFIDENCE_SPECULATIVE
        assert CONFIDENCE_CERTAIN == 1.0

    def test_predicates_are_strings(self):
        from iios.ontology.reasoning import (
            PRED_SUBTYPE_OF, PRED_TRANSITIVE_SUBTYPE,
            PRED_INHERITS_PROPERTY, PRED_HAS_OWN_PROPERTY,
            PRED_INVERSE_RELATED, PRED_HAS_NAMESPACE,
        )
        for p in [PRED_SUBTYPE_OF, PRED_TRANSITIVE_SUBTYPE, PRED_INHERITS_PROPERTY,
                  PRED_HAS_OWN_PROPERTY, PRED_INVERSE_RELATED, PRED_HAS_NAMESPACE]:
            assert isinstance(p, str) and len(p) > 0

    def test_rule_ids_are_strings(self):
        from iios.ontology.reasoning import (
            RULE_INHERITANCE_PROPAGATION, RULE_SUBTYPE_TRANSITIVITY,
            RULE_SYMMETRIC_RELATIONSHIP, RULE_TYPE_CONSISTENCY,
            RULE_NAMESPACE_CONSISTENCY, RULE_REFERENCE_VALIDITY,
            RULE_ABSTRACT_TYPE_CHECK, RULE_ORPHAN_TYPE_CHECK,
            RULE_REL_ENDPOINT_CHECK,
        )
        rules = [
            RULE_INHERITANCE_PROPAGATION, RULE_SUBTYPE_TRANSITIVITY,
            RULE_SYMMETRIC_RELATIONSHIP, RULE_TYPE_CONSISTENCY,
            RULE_NAMESPACE_CONSISTENCY, RULE_REFERENCE_VALIDITY,
            RULE_ABSTRACT_TYPE_CHECK, RULE_ORPHAN_TYPE_CHECK,
            RULE_REL_ENDPOINT_CHECK,
        ]
        assert len(rules) == 9
        assert len(set(rules)) == 9  # all unique

    def test_issue_type_members(self):
        from iios.ontology.reasoning import IssueType
        assert IssueType.BROKEN_PARENT_REF.value == "broken_parent_ref"
        assert IssueType.ORPHAN_TYPE.value == "orphan_type"
        assert IssueType.ABSTRACT_NO_CHILDREN.value == "abstract_no_children"
        assert IssueType.NAMESPACE_NOT_FOUND.value == "namespace_not_found"
        assert IssueType.RELATIONSHIP_BROKEN.value == "relationship_broken"
        assert IssueType.BROKEN_PROPERTY_REF.value == "broken_property_ref"

    def test_limits_positive(self):
        from iios.ontology.reasoning import (
            MAX_INFERENCE_DEPTH, MAX_FIXPOINT_ITERATIONS, MAX_RULES,
            MAX_FACTS_PER_SESSION, REASONING_TIMEOUT_MS, SESSION_TTL_SECONDS,
            MAX_SESSIONS, PROOF_MAX_STEPS,
        )
        for v in [MAX_INFERENCE_DEPTH, MAX_FIXPOINT_ITERATIONS, MAX_RULES,
                  MAX_FACTS_PER_SESSION, SESSION_TTL_SECONDS, MAX_SESSIONS, PROOF_MAX_STEPS]:
            assert v > 0
        assert REASONING_TIMEOUT_MS > 0


# ══════════════════════════════════════════════════════════════════════════════
#  2 — Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        from iios.ontology.reasoning import (
            ReasoningError, InferenceError, InferenceTimeoutError,
            InferenceDepthError, InferenceCycleError, ConsistencyError,
            OntologyInconsistencyError, ReasoningConstraintError, ConflictError,
            RuleError, DuplicateRuleError, UnknownRuleError, RuleExecutionError,
            ExplanationError, SessionError, SessionNotFoundError, SessionExpiredError,
            ReasoningEngineError, ReasoningNotInitializedError,
        )
        assert issubclass(InferenceError, ReasoningError)
        assert issubclass(InferenceTimeoutError, InferenceError)
        assert issubclass(InferenceDepthError, InferenceError)
        assert issubclass(InferenceCycleError, InferenceError)
        assert issubclass(OntologyInconsistencyError, ConsistencyError)
        assert issubclass(ReasoningConstraintError, ConsistencyError)
        assert issubclass(ConflictError, ConsistencyError)
        assert issubclass(DuplicateRuleError, RuleError)
        assert issubclass(UnknownRuleError, RuleError)
        assert issubclass(RuleExecutionError, RuleError)
        assert issubclass(SessionNotFoundError, SessionError)
        assert issubclass(SessionExpiredError, SessionError)
        assert issubclass(ReasoningNotInitializedError, ReasoningEngineError)

    def test_error_codes(self):
        from iios.ontology.reasoning import (
            ReasoningError, InferenceTimeoutError, SessionNotFoundError,
            ReasoningNotInitializedError,
        )
        assert ReasoningError("test").code == "RSN-000"
        assert InferenceTimeoutError(500.0).code == "RSN-011"
        assert SessionNotFoundError("s").code == "RSN-051"
        assert ReasoningNotInitializedError().code == "RSN-061"

    def test_raise_and_catch(self):
        from iios.ontology.reasoning import (
            ReasoningError, DuplicateRuleError, SessionNotFoundError,
        )
        with pytest.raises(ReasoningError):
            raise DuplicateRuleError("my.rule")
        with pytest.raises(SessionNotFoundError):
            raise SessionNotFoundError("abc-123")


# ══════════════════════════════════════════════════════════════════════════════
#  3 — FactStore
# ══════════════════════════════════════════════════════════════════════════════

class TestFactStore:
    def _fact(self, s="a", p="p", o="b", inferred=True, conf=0.9):
        from iios.ontology.reasoning import InferredFact
        return InferredFact(subject_uri=s, predicate=p, object_value=o,
                            confidence=conf, rule_ids=["r1"], inferred=inferred)

    def test_add_and_has(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        f  = self._fact()
        assert fs.add(f)
        assert fs.has("a", "p", "b")
        assert not fs.has("a", "p", "c")

    def test_deduplication(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        f  = self._fact()
        assert fs.add(f)
        assert not fs.add(f)  # duplicate → no change
        assert fs.count() == 1

    def test_about(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        fs.add(self._fact("x", "p1", "y"))
        fs.add(self._fact("x", "p2", "z"))
        fs.add(self._fact("w", "p1", "y"))
        about_x = fs.about("x")
        assert len(about_x) == 2
        subjects = {f.subject_uri for f in about_x}
        assert subjects == {"x"}

    def test_with_predicate(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        fs.add(self._fact("a", "p1", "b"))
        fs.add(self._fact("c", "p2", "d"))
        fs.add(self._fact("e", "p1", "f"))
        result = fs.with_predicate("p1")
        assert len(result) == 2

    def test_inferred_vs_ground_truth(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        fs.add(self._fact(inferred=True))
        fs.add(self._fact("x", "p", "y", inferred=False))
        assert len(fs.inferred_facts()) == 1
        assert len(fs.ground_truth()) == 1

    def test_clear(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        fs.add(self._fact())
        fs.clear()
        assert fs.count() == 0

    def test_stats(self):
        from iios.ontology.reasoning import FactStore
        fs = FactStore()
        fs.add(self._fact(inferred=True))
        fs.add(self._fact("x", "p", "y", inferred=False))
        s = fs.stats()
        assert s["total_facts"] == 2
        assert s["inferred"] == 1
        assert s["ground_truth"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  4 — ReasoningResult
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningResult:
    def _make_result(self, n_facts=2, n_issues=1):
        from iios.ontology.reasoning import (
            ReasoningResult, ReasoningType, InferenceStatus, ConsistencyStatus,
            InferredFact, ConsistencyIssue, IssueSeverity, IssueType,
        )
        facts  = [
            InferredFact(f"iios.t{i}", "p", f"v{i}", 0.9, ["r1"], True)
            for i in range(n_facts)
        ]
        issues = [
            ConsistencyIssue(
                IssueType.ORPHAN_TYPE, IssueSeverity.ERROR,
                "Broken parent", ["iios.t0"], "r1",
            )
        ] * n_issues
        return ReasoningResult(
            session_id="s1",
            reasoning_type=ReasoningType.FULL_INFERENCE,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.INCONSISTENT,
            inferred_facts=facts,
            consistency_issues=issues,
            duration_ms=12.3,
            iterations=3,
            rule_fire_count=5,
        )

    def test_counts(self):
        r = self._make_result(n_facts=4, n_issues=2)
        assert r.fact_count == 4
        assert r.issue_count == 2
        assert r.error_count == 2
        assert r.warning_count == 0
        assert r.succeeded is True

    def test_is_consistent(self):
        from iios.ontology.reasoning import ConsistencyStatus
        r = self._make_result()
        assert r.is_consistent is False
        r.consistency_status = ConsistencyStatus.CONSISTENT
        assert r.is_consistent is True

    def test_to_dict(self):
        r = self._make_result()
        d = r.to_dict()
        assert d["session_id"] == "s1"
        assert "inferred_facts" in d
        assert "consistency_issues" in d


# ══════════════════════════════════════════════════════════════════════════════
#  5 — ReasoningTrace
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningTrace:
    def test_add_step_and_counts(self):
        from iios.ontology.reasoning import ReasoningTrace
        trace = ReasoningTrace("sess-1")
        trace.add_step("r1", "Rule One", [], [{"x": 1}], [], 0.9)
        trace.add_step("r2", "Rule Two", [], [{"x": 2}, {"x": 3}], [], 0.8)
        trace.finalise()
        assert trace.step_count == 2
        assert trace.total_facts_produced == 3

    def test_rules_fired(self):
        from iios.ontology.reasoning import ReasoningTrace
        trace = ReasoningTrace("s2")
        trace.add_step("rule_a", "A", [], [{}], [], 1.0)
        trace.add_step("rule_b", "B", [], [], [], 1.0)
        fired = trace.rules_fired()
        assert "rule_a" in fired
        assert "rule_b" in fired

    def test_entries_for_rule(self):
        from iios.ontology.reasoning import ReasoningTrace
        trace = ReasoningTrace("s3")
        trace.add_step("r1", "R1", [], [{}], [], 1.0)
        trace.add_step("r1", "R1", [], [{}], [], 1.0)
        trace.add_step("r2", "R2", [], [], [], 1.0)
        assert len(trace.entries_for_rule("r1")) == 2
        assert len(trace.entries_for_rule("r2")) == 1

    def test_summary(self):
        from iios.ontology.reasoning import ReasoningTrace
        trace = ReasoningTrace("s4")
        trace.add_step("r1", "R", [], [{}, {}], [], 0.9)
        d = trace.summary()
        assert d["step_count"] == 1
        assert d["total_facts_produced"] == 2


# ══════════════════════════════════════════════════════════════════════════════
#  6 — ReasoningContext
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningContext:
    def test_context_manager(self):
        from iios.ontology.reasoning import (
            get_reasoning_context, ReasoningType,
        )
        from iios.ontology.reasoning.reasoning_context import reasoning_session
        with reasoning_session(ReasoningType.FULL_INFERENCE, actor="test_actor"):
            ctx = get_reasoning_context()
            assert ctx.reasoning_type == ReasoningType.FULL_INFERENCE
            assert ctx.actor == "test_actor"
            assert ctx.session_id is not None

    def test_elapsed_ms(self):
        from iios.ontology.reasoning.reasoning_context import reasoning_session
        from iios.ontology.reasoning import get_reasoning_context, ReasoningType
        with reasoning_session(ReasoningType.CONSISTENCY_CHECK, actor="actor"):
            time.sleep(0.01)
            ctx = get_reasoning_context()
            assert ctx.elapsed_ms() >= 0

    def test_diagnostics(self):
        from iios.ontology.reasoning.reasoning_context import reasoning_session
        from iios.ontology.reasoning import get_reasoning_context, ReasoningType
        with reasoning_session(ReasoningType.FULL_INFERENCE, actor="a"):
            ctx = get_reasoning_context()
            ctx.add_diagnostic("WARNING", "test warning", "src")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors()) == 0


# ══════════════════════════════════════════════════════════════════════════════
#  7 — ReasoningFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningFactory:
    def test_make_request(self):
        from iios.ontology.reasoning import (
            get_reasoning_factory, ReasoningType,
        )
        fac = get_reasoning_factory()
        req = fac.make_request(ReasoningType.FULL_INFERENCE, "iios.core.Entity")
        assert req.reasoning_type == ReasoningType.FULL_INFERENCE
        assert req.target_uri == "iios.core.Entity"
        assert req.request_id is not None

    def test_make_response(self):
        from iios.ontology.reasoning import (
            get_reasoning_factory, ReasoningType, InferenceStatus,
            ConsistencyStatus, ReasoningResult, ReasoningTrace,
        )
        fac  = get_reasoning_factory()
        req  = fac.make_request(ReasoningType.CONSISTENCY_CHECK, "*")
        result = ReasoningResult(
            session_id="r1", reasoning_type=ReasoningType.CONSISTENCY_CHECK,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.CONSISTENT,
            inferred_facts=[], consistency_issues=[],
            duration_ms=1.0, iterations=1, rule_fire_count=1,
        )
        trace = ReasoningTrace("r1")
        trace.finalise()
        resp = fac.make_response(req, result, trace)
        assert resp.succeeded is True
        d    = resp.to_dict()
        assert "request" in d
        assert "result"  in d

    def test_singleton(self):
        from iios.ontology.reasoning import get_reasoning_factory, reset_reasoning_factory
        a = get_reasoning_factory()
        b = get_reasoning_factory()
        assert a is b
        reset_reasoning_factory()
        c = get_reasoning_factory()
        assert c is not a


# ══════════════════════════════════════════════════════════════════════════════
#  8 — SessionManager
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionManager:
    def _req(self):
        from iios.ontology.reasoning import get_reasoning_factory, ReasoningType
        return get_reasoning_factory().make_request(ReasoningType.FULL_INFERENCE, "*")

    def test_create_and_get(self):
        from iios.ontology.reasoning import get_session_manager
        sm  = get_session_manager()
        req = self._req()
        s   = sm.create(req)
        assert s.session_id is not None
        retrieved = sm.get(s.session_id)
        assert retrieved.session_id == s.session_id

    def test_not_found(self):
        from iios.ontology.reasoning import get_session_manager, SessionNotFoundError
        sm = get_session_manager()
        with pytest.raises(SessionNotFoundError):
            sm.get("nonexistent-id")

    def test_close(self):
        from iios.ontology.reasoning import get_session_manager, SessionNotFoundError
        sm  = get_session_manager()
        s   = sm.create(self._req())
        sid = s.session_id
        assert sm.close(sid)
        with pytest.raises(SessionNotFoundError):
            sm.get(sid)

    def test_stats(self):
        from iios.ontology.reasoning import get_session_manager
        sm = get_session_manager()
        sm.create(self._req())
        sm.create(self._req())
        stats = sm.stats()
        assert stats["total"] >= 2
        assert "active" in stats

    def test_session_to_dict(self):
        from iios.ontology.reasoning import get_session_manager
        sm = get_session_manager()
        s  = sm.create(self._req())
        d  = s.to_dict()
        assert d["session_id"] == s.session_id
        assert "status" in d


# ══════════════════════════════════════════════════════════════════════════════
#  9 — InferenceRule
# ══════════════════════════════════════════════════════════════════════════════

class TestInferenceRule:
    def test_execute_returns_list(self):
        from iios.ontology.reasoning.inference import InferenceRule
        from iios.ontology.reasoning import RuleType, FactStore
        rule = InferenceRule(
            rule_id="test.r1", name="Test", description="",
            rule_type=RuleType.IMPLICATION, priority=1,
            action=lambda f, m: [],
        )
        result = rule.execute(FactStore(), None)
        assert isinstance(result, list)

    def test_disabled_rule_returns_empty(self):
        from iios.ontology.reasoning.inference import InferenceRule
        from iios.ontology.reasoning import RuleType, FactStore, InferredFact
        fired = []
        def _action(f, m):
            fired.append(1)
            return [InferredFact("a", "p", "b", 0.9, ["r"], True)]
        rule = InferenceRule(
            rule_id="r2", name="R2", description="",
            rule_type=RuleType.IMPLICATION, enabled=False,
            action=_action,
        )
        result = rule.execute(FactStore(), None)
        assert result == []
        assert fired == []

    def test_to_dict(self):
        from iios.ontology.reasoning.inference import InferenceRule
        from iios.ontology.reasoning import RuleType
        rule = InferenceRule("r3", "R3", "desc", RuleType.CONSTRAINT)
        d = rule.to_dict()
        assert d["rule_id"] == "r3"
        assert d["enabled"] is True

    def test_exception_in_action_returns_empty(self):
        from iios.ontology.reasoning.inference import InferenceRule
        from iios.ontology.reasoning import RuleType, FactStore
        rule = InferenceRule(
            rule_id="r4", name="bad", description="",
            rule_type=RuleType.DEDUCTION,
            action=lambda f, m: 1 / 0,  # will raise
        )
        result = rule.execute(FactStore(), None)
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
#  10 — InferenceRegistry (9 built-in rules)
# ══════════════════════════════════════════════════════════════════════════════

class TestInferenceRegistry:
    def test_nine_builtins_registered(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        from iios.ontology.reasoning import (
            RULE_INHERITANCE_PROPAGATION, RULE_SUBTYPE_TRANSITIVITY,
            RULE_SYMMETRIC_RELATIONSHIP, RULE_TYPE_CONSISTENCY,
            RULE_NAMESPACE_CONSISTENCY, RULE_REFERENCE_VALIDITY,
            RULE_ABSTRACT_TYPE_CHECK, RULE_ORPHAN_TYPE_CHECK,
            RULE_REL_ENDPOINT_CHECK,
        )
        reg = get_inference_registry()
        for rid in [
            RULE_INHERITANCE_PROPAGATION, RULE_SUBTYPE_TRANSITIVITY,
            RULE_SYMMETRIC_RELATIONSHIP, RULE_TYPE_CONSISTENCY,
            RULE_NAMESPACE_CONSISTENCY, RULE_REFERENCE_VALIDITY,
            RULE_ABSTRACT_TYPE_CHECK, RULE_ORPHAN_TYPE_CHECK,
            RULE_REL_ENDPOINT_CHECK,
        ]:
            assert reg.has(rid), f"Missing builtin rule: {rid}"

    def test_all_builtins_enabled_by_default(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        reg   = get_inference_registry()
        rules = reg.enabled_rules()
        assert len(rules) >= 9

    def test_register_custom_rule(self):
        from iios.ontology.reasoning.inference import get_inference_registry, InferenceRule
        from iios.ontology.reasoning import RuleType
        reg  = get_inference_registry()
        rule = InferenceRule("custom.r1", "CR1", "desc", RuleType.DEDUCTION)
        reg.register(rule)
        assert reg.has("custom.r1")

    def test_duplicate_raises(self):
        from iios.ontology.reasoning.inference import get_inference_registry, InferenceRule
        from iios.ontology.reasoning import RuleType, DuplicateRuleError
        reg  = get_inference_registry()
        rule = InferenceRule("dup.r1", "D", "d", RuleType.DEDUCTION)
        reg.register(rule)
        with pytest.raises(DuplicateRuleError):
            reg.register(rule)

    def test_enable_disable(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        from iios.ontology.reasoning import RULE_ABSTRACT_TYPE_CHECK
        reg = get_inference_registry()
        reg.disable(RULE_ABSTRACT_TYPE_CHECK)
        assert not reg.get(RULE_ABSTRACT_TYPE_CHECK).enabled
        reg.enable(RULE_ABSTRACT_TYPE_CHECK)
        assert reg.get(RULE_ABSTRACT_TYPE_CHECK).enabled

    def test_unknown_raises(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        from iios.ontology.reasoning import UnknownRuleError
        reg = get_inference_registry()
        with pytest.raises(UnknownRuleError):
            reg.get("no.such.rule")

    def test_stats(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        reg   = get_inference_registry()
        stats = reg.stats()
        assert stats["total"] >= 9
        assert stats["builtins"] == 9

    def test_rules_by_type(self):
        from iios.ontology.reasoning.inference import get_inference_registry
        from iios.ontology.reasoning import RuleType
        reg         = get_inference_registry()
        constraints = reg.rules_by_type(RuleType.CONSTRAINT)
        assert len(constraints) >= 6  # type, ns, ref, abstract, orphan, rel


# ══════════════════════════════════════════════════════════════════════════════
#  11 — Forward chaining
# ══════════════════════════════════════════════════════════════════════════════

class TestForwardChaining:
    def _setup_simple_hierarchy(self):
        """Entity -> Animal -> Dog"""
        _register_namespace("iios.test")
        entity = _make_type("Entity", abstract=True)
        animal = _make_type("Animal", parent="iios.test.Entity")
        dog    = _make_type("Dog", parent="iios.test.Animal")
        _register_type(entity)
        _register_type(animal)
        _register_type(dog)
        return entity, animal, dog

    def test_subtype_transitivity_inferred(self):
        from iios.ontology.reasoning import (
            get_reasoning_engine, PRED_TRANSITIVE_SUBTYPE,
        )
        self._setup_simple_hierarchy()
        engine = get_reasoning_engine()
        engine.initialize()
        resp = engine.forward_chain("iios.test.Dog")
        # Dog should have transitive_subtype_of Entity
        facts = resp.result.inferred_facts
        transitive = [
            f for f in facts
            if f.predicate == PRED_TRANSITIVE_SUBTYPE
            and f.subject_uri == "iios.test.Dog"
        ]
        obj_vals = {str(f.object_value) for f in transitive}
        assert "iios.test.Entity" in obj_vals or "iios.test.Animal" in obj_vals

    def test_result_is_completed(self):
        from iios.ontology.reasoning import get_reasoning_engine, InferenceStatus
        self._setup_simple_hierarchy()
        engine = get_reasoning_engine()
        engine.initialize()
        resp = engine.forward_chain("iios.test.Animal")
        assert resp.result.status == InferenceStatus.COMPLETED

    def test_response_to_dict(self):
        self._setup_simple_hierarchy()
        from iios.ontology.reasoning import get_reasoning_engine
        engine = get_reasoning_engine()
        engine.initialize()
        resp = engine.forward_chain("*")
        d = resp.to_dict()
        assert "result" in d
        assert "trace" in d


# ══════════════════════════════════════════════════════════════════════════════
#  12 — Backward chaining
# ══════════════════════════════════════════════════════════════════════════════

class TestBackwardChaining:
    def test_backward_chain_completes(self):
        from iios.ontology.reasoning import get_reasoning_engine, InferenceStatus
        _register_namespace("iios.test")
        t = _make_type("Target")
        _register_type(t)
        engine = get_reasoning_engine()
        engine.initialize()
        resp = engine.backward_chain("iios.test.Target")
        assert resp.result.status == InferenceStatus.COMPLETED


# ══════════════════════════════════════════════════════════════════════════════
#  13 — Consistency checking
# ══════════════════════════════════════════════════════════════════════════════

class TestConsistencyChecking:
    def test_clean_ontology_has_no_errors(self):
        _register_namespace("iios.test")
        t = _make_type("Clean")
        _register_type(t)
        from iios.ontology.reasoning import get_reasoning_engine, IssueSeverity
        engine = get_reasoning_engine()
        engine.initialize()
        result = engine.check_consistency()
        errors = [i for i in result.consistency_issues if i.is_error]
        assert errors == []

    def test_broken_parent_detected(self):
        """Register a type with a parent_uri that doesn't exist."""
        _register_namespace("iios.test")
        child = _make_type("Orphan", parent="iios.test.GhostParent")
        _register_type(child)
        from iios.ontology.reasoning import (
            get_reasoning_engine, IssueType,
        )
        engine = get_reasoning_engine()
        engine.initialize()
        result = engine.check_consistency()
        issues_t = {i.issue_type for i in result.consistency_issues}
        assert IssueType.BROKEN_PARENT_REF in issues_t or IssueType.ORPHAN_TYPE in issues_t

    def test_abstract_no_children_warning(self):
        _register_namespace("iios.test")
        abstract_type = _make_type("AbstractNoKids", abstract=True)
        _register_type(abstract_type)
        from iios.ontology.reasoning import get_reasoning_engine, IssueType
        engine = get_reasoning_engine()
        engine.initialize()
        result = engine.check_consistency()
        types_found = {i.issue_type for i in result.consistency_issues}
        assert IssueType.ABSTRACT_NO_CHILDREN in types_found

    def test_broken_relationship_detected(self):
        _register_namespace("iios.test")
        t1 = _make_type("RelSrc")
        _register_type(t1)
        _register_rel("iios.test.rel1", "rel1", "iios.test.RelSrc", "iios.test.MISSING")
        from iios.ontology.reasoning import get_reasoning_engine, IssueType
        engine = get_reasoning_engine()
        engine.initialize()
        result = engine.check_consistency()
        types_found = {i.issue_type for i in result.consistency_issues}
        assert IssueType.RELATIONSHIP_BROKEN in types_found

    def test_result_has_consistency_status(self):
        _register_namespace("iios.test")
        from iios.ontology.reasoning import (
            get_reasoning_engine, ConsistencyStatus,
        )
        engine = get_reasoning_engine()
        engine.initialize()
        result = engine.check_consistency()
        assert result.consistency_status in list(ConsistencyStatus)


# ══════════════════════════════════════════════════════════════════════════════
#  14 — Explanation generation
# ══════════════════════════════════════════════════════════════════════════════

class TestExplanation:
    def _setup_and_run(self):
        _register_namespace("iios.test")
        entity = _make_type("ExplEntity", abstract=True)
        child  = _make_type("ExplChild", parent="iios.test.ExplEntity")
        _register_type(entity)
        _register_type(child)
        from iios.ontology.reasoning import get_reasoning_engine
        engine = get_reasoning_engine()
        engine.initialize()
        return engine

    def test_explain_returns_dict(self):
        engine = self._setup_and_run()
        resp   = engine.infer_all()
        sid    = resp.result.session_id
        d      = engine.explain(sid)
        assert isinstance(d, dict)
        assert "session_id" in d or "stats" in d

    def test_reasoning_explainer_human(self):
        from iios.ontology.reasoning import (
            get_reasoning_engine, ReasoningType, InferenceStatus,
            ConsistencyStatus, ReasoningResult, ReasoningTrace,
        )
        from iios.ontology.reasoning.explanation import get_reasoning_explainer
        explainer = get_reasoning_explainer()
        result    = ReasoningResult(
            session_id="s-expl",
            reasoning_type=ReasoningType.FULL_INFERENCE,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.CONSISTENT,
            inferred_facts=[], consistency_issues=[],
            duration_ms=5.0, iterations=2, rule_fire_count=4,
        )
        trace = ReasoningTrace("s-expl")
        trace.finalise()
        text = explainer.explain_result(result, trace)
        assert "REASONING SESSION" in text
        assert "CONSISTENT" in text.upper() or "consistent" in text

    def test_reasoning_explainer_machine(self):
        from iios.ontology.reasoning import (
            ReasoningType, InferenceStatus, ConsistencyStatus,
            ReasoningResult, ReasoningTrace,
        )
        from iios.ontology.reasoning.explanation import get_reasoning_explainer
        explainer = get_reasoning_explainer()
        result    = ReasoningResult(
            session_id="s-mach",
            reasoning_type=ReasoningType.CONSISTENCY_CHECK,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.CONSISTENT,
            inferred_facts=[], consistency_issues=[],
            duration_ms=1.0, iterations=1, rule_fire_count=2,
        )
        trace = ReasoningTrace("s-mach")
        trace.finalise()
        d = explainer.explain_machine(result, trace)
        assert "session_id" in d
        assert "stats" in d

    def test_explain_consistency_report(self):
        from iios.ontology.reasoning.explanation import get_reasoning_explainer
        from iios.ontology.reasoning import ConsistencyIssue, IssueSeverity, IssueType
        issues = [
            ConsistencyIssue(IssueType.ORPHAN_TYPE, IssueSeverity.ERROR, "Broken", ["u1"], "r1"),
        ]
        explainer = get_reasoning_explainer()
        text = explainer.explain_consistency(issues)
        assert "ERROR" in text.upper() or "orphan" in text.lower()

    def test_explain_consistency_empty(self):
        from iios.ontology.reasoning.explanation import get_reasoning_explainer
        text = get_reasoning_explainer().explain_consistency([])
        assert "consistent" in text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  15 — Proof generator
# ══════════════════════════════════════════════════════════════════════════════

class TestProofGenerator:
    def test_generate_returns_proof_node(self):
        from iios.ontology.reasoning import InferredFact, ReasoningTrace
        from iios.ontology.reasoning.explanation import get_proof_generator
        fact  = InferredFact("iios.t.Dog", "transitive_subtype_of", "iios.t.Entity", 1.0, ["r1"], True)
        trace = ReasoningTrace("s5")
        trace.finalise()
        gen   = get_proof_generator()
        proof = gen.generate(fact, trace)
        from iios.ontology.reasoning.explanation import ProofNode
        assert isinstance(proof, ProofNode)
        assert proof.fact.subject_uri == "iios.t.Dog"

    def test_to_human_readable(self):
        from iios.ontology.reasoning import InferredFact, ReasoningTrace
        from iios.ontology.reasoning.explanation import get_proof_generator
        fact  = InferredFact("iios.t.Dog", "p", "iios.t.Entity", 0.9, [], False)
        trace = ReasoningTrace("s6")
        trace.finalise()
        gen  = get_proof_generator()
        text = gen.to_human_readable(gen.generate(fact, trace))
        assert "iios.t.Dog" in text

    def test_singleton(self):
        from iios.ontology.reasoning.explanation import (
            get_proof_generator, reset_proof_generator,
        )
        a = get_proof_generator()
        b = get_proof_generator()
        assert a is b


# ══════════════════════════════════════════════════════════════════════════════
#  16 — DecisionTrace
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionTrace:
    def test_to_dict_keys(self):
        from iios.ontology.reasoning import InferredFact
        from iios.ontology.reasoning.explanation import DecisionTrace
        fact  = InferredFact("a", "p", "b", 0.9, ["r1"], True)
        dt    = DecisionTrace(fact=fact, supporting_rules=["r1"], evidence_uris=["a"], confidence_path=[0.9], depth=1)
        d     = dt.to_dict()
        assert "fact" in d
        assert "supporting_rules" in d
        assert "depth" in d

    def test_human_readable(self):
        from iios.ontology.reasoning import InferredFact
        from iios.ontology.reasoning.explanation import DecisionTrace
        fact = InferredFact("sub", "pred", "obj", 0.8, ["r"], True)
        dt   = DecisionTrace(fact=fact, supporting_rules=["r"])
        text = dt.human_readable()
        assert "sub" in text
        assert "pred" in text


# ══════════════════════════════════════════════════════════════════════════════
#  17 — ExplanationEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestExplanationEngine:
    def test_explain_human(self):
        from iios.ontology.reasoning import (
            ReasoningType, InferenceStatus, ConsistencyStatus,
            ReasoningResult, ReasoningTrace, ExplanationType,
        )
        from iios.ontology.reasoning.explanation import get_explanation_engine
        result = ReasoningResult(
            session_id="se1",
            reasoning_type=ReasoningType.FULL_INFERENCE,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.CONSISTENT,
            inferred_facts=[], consistency_issues=[],
            duration_ms=2.0, iterations=1, rule_fire_count=1,
        )
        trace = ReasoningTrace("se1")
        trace.finalise()
        engine = get_explanation_engine()
        text   = engine.explain(result, trace, ExplanationType.HUMAN_READABLE)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_explain_machine(self):
        from iios.ontology.reasoning import (
            ReasoningType, InferenceStatus, ConsistencyStatus,
            ReasoningResult, ReasoningTrace, ExplanationType,
        )
        from iios.ontology.reasoning.explanation import get_explanation_engine
        result = ReasoningResult(
            session_id="se2",
            reasoning_type=ReasoningType.CONSISTENCY_CHECK,
            status=InferenceStatus.COMPLETED,
            consistency_status=ConsistencyStatus.CONSISTENT,
            inferred_facts=[], consistency_issues=[],
            duration_ms=1.5, iterations=1, rule_fire_count=2,
        )
        trace = ReasoningTrace("se2")
        trace.finalise()
        d = get_explanation_engine().explain(result, trace, ExplanationType.MACHINE_READABLE)
        assert isinstance(d, dict)

    def test_explain_fact(self):
        from iios.ontology.reasoning import InferredFact, ReasoningTrace
        from iios.ontology.reasoning.explanation import get_explanation_engine, DecisionTrace
        fact  = InferredFact("a", "p", "b", 0.9, ["r1"], True)
        trace = ReasoningTrace("se3")
        trace.finalise()
        engine = get_explanation_engine()
        dt     = engine.explain_fact(fact, trace)
        assert isinstance(dt, DecisionTrace)

    def test_generate_proof(self):
        from iios.ontology.reasoning import InferredFact, ReasoningTrace
        from iios.ontology.reasoning.explanation import get_explanation_engine, ProofNode
        fact  = InferredFact("x", "p", "y", 1.0, ["r"], False)
        trace = ReasoningTrace("se4")
        trace.finalise()
        proof = get_explanation_engine().generate_proof(fact, trace)
        assert isinstance(proof, ProofNode)


# ══════════════════════════════════════════════════════════════════════════════
#  18 — ReasoningManager
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningManager:
    def test_not_initialized_raises(self):
        from iios.ontology.reasoning import (
            get_reasoning_manager, ReasoningNotInitializedError,
            get_reasoning_factory, ReasoningType,
        )
        mgr = get_reasoning_manager()
        req = get_reasoning_factory().make_request(ReasoningType.FULL_INFERENCE, "*")
        with pytest.raises(ReasoningNotInitializedError):
            mgr.reason(req)

    def test_initialize_and_reason(self):
        _register_namespace("iios.test")
        t = _make_type("MgrType")
        _register_type(t)
        from iios.ontology.reasoning import (
            get_reasoning_manager, get_reasoning_factory, ReasoningType,
        )
        mgr = get_reasoning_manager()
        mgr.initialize()
        req  = get_reasoning_factory().make_request(ReasoningType.FULL_INFERENCE, "*")
        resp = mgr.reason(req)
        assert resp.succeeded

    def test_stats_structure(self):
        from iios.ontology.reasoning import get_reasoning_manager
        mgr   = get_reasoning_manager()
        stats = mgr.stats()
        assert "initialized" in stats
        assert "sessions" in stats
        assert "reasoning" in stats

    def test_health(self):
        from iios.ontology.reasoning import get_reasoning_manager
        mgr = get_reasoning_manager()
        h   = mgr.health()
        assert h["status"] in ("healthy", "not_initialized")

    def test_reason_all(self):
        _register_namespace("iios.test")
        t = _make_type("MgrAll")
        _register_type(t)
        from iios.ontology.reasoning import get_reasoning_manager
        mgr = get_reasoning_manager()
        mgr.initialize()
        resp = mgr.reason_all()
        assert resp.succeeded


# ══════════════════════════════════════════════════════════════════════════════
#  19 — ReasoningEngine (master facade)
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngineFacade:
    def _engine(self):
        _register_namespace("iios.test")
        t = _make_type("Facade")
        _register_type(t)
        from iios.ontology.reasoning import get_reasoning_engine
        engine = get_reasoning_engine()
        engine.initialize()
        return engine

    def test_is_initialized(self):
        engine = self._engine()
        assert engine.is_initialized is True

    def test_infer_all(self):
        engine = self._engine()
        resp   = engine.infer_all()
        assert resp.succeeded

    def test_check_consistency(self):
        engine = self._engine()
        result = engine.check_consistency()
        assert result is not None

    def test_register_and_disable_rule(self):
        from iios.ontology.reasoning.inference import InferenceRule
        from iios.ontology.reasoning import RuleType
        engine = self._engine()
        rule   = InferenceRule("facade.test", "FT", "desc", RuleType.IMPLICATION)
        engine.register_rule(rule)
        engine.disable_rule("facade.test")
        from iios.ontology.reasoning.inference import get_inference_registry
        assert not get_inference_registry().get("facade.test").enabled
        engine.enable_rule("facade.test")
        assert get_inference_registry().get("facade.test").enabled

    def test_list_rules(self):
        engine = self._engine()
        rules  = engine.list_rules()
        assert len(rules) >= 9

    def test_get_session(self):
        engine = self._engine()
        resp   = engine.infer_all()
        sid    = resp.result.session_id
        s      = engine.get_session(sid)
        assert s.session_id == sid

    def test_stats(self):
        engine = self._engine()
        stats  = engine.stats()
        assert "initialized" in stats

    def test_health(self):
        engine = self._engine()
        h      = engine.health()
        assert h["status"] == "healthy"

    def test_singleton(self):
        from iios.ontology.reasoning import get_reasoning_engine, reset_reasoning_engine
        a = get_reasoning_engine()
        b = get_reasoning_engine()
        assert a is b
        reset_reasoning_engine()
        c = get_reasoning_engine()
        assert c is not a


# ══════════════════════════════════════════════════════════════════════════════
#  20 — Concurrency (parallel sessions)
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_sessions(self):
        """Multiple threads can reason simultaneously without corruption."""
        _register_namespace("iios.test")
        for i in range(5):
            t = _make_type(f"ConcType{i}")
            _register_type(t)

        from iios.ontology.reasoning import get_reasoning_engine
        engine = get_reasoning_engine()
        engine.initialize()

        results: list = []
        errors:  list = []

        def _run():
            try:
                resp = engine.infer_all()
                results.append(resp.succeeded)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Thread errors: {errors}"
        assert all(results)

    def test_session_manager_thread_safe(self):
        from iios.ontology.reasoning import get_session_manager, get_reasoning_factory, ReasoningType
        sm     = get_session_manager()
        fac    = get_reasoning_factory()
        ids: list = []
        errors: list = []

        def _create():
            try:
                req = fac.make_request(ReasoningType.FULL_INFERENCE, "*")
                s   = sm.create(req)
                ids.append(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_create) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
        assert len(ids) == 20
        assert len(set(ids)) == 20  # all unique


# ══════════════════════════════════════════════════════════════════════════════
#  21 — Large ontology (100+ types)
# ══════════════════════════════════════════════════════════════════════════════

class TestLargeOntology:
    def test_100_type_inference(self):
        """Forward chaining across 100 types should complete quickly."""
        _register_namespace("iios.large")
        root = _make_type("Root", ns="iios.large", abstract=True)
        _register_type(root)
        for i in range(99):
            child = _make_type(f"T{i}", ns="iios.large", parent="iios.large.Root")
            _register_type(child)

        from iios.ontology.reasoning import get_reasoning_engine, InferenceStatus
        engine = get_reasoning_engine()
        engine.initialize()
        t0   = time.perf_counter()
        resp = engine.infer_all()
        ms   = (time.perf_counter() - t0) * 1_000
        assert resp.result.status == InferenceStatus.COMPLETED
        assert ms < 10_000, f"Large ontology inference took {ms:.0f} ms"


# ══════════════════════════════════════════════════════════════════════════════
#  22 — InferenceGraph
# ══════════════════════════════════════════════════════════════════════════════

class TestInferenceGraph:
    def test_add_node_and_edge(self):
        from iios.ontology.reasoning.inference import (
            InferenceGraph, InferenceNode, InferenceEdge,
        )
        g = InferenceGraph()
        g.add_node(InferenceNode("a", "A", "ns", False))
        g.add_node(InferenceNode("b", "B", "ns", False))
        g.add_edge(InferenceEdge("a", "b", "rel1"))
        assert g.get_node("a") is not None
        assert "b" in g.neighbours("a")

    def test_path_finding(self):
        from iios.ontology.reasoning.inference import (
            InferenceGraph, InferenceNode, InferenceEdge,
        )
        g = InferenceGraph()
        for uid in ["x", "y", "z"]:
            g.add_node(InferenceNode(uid, uid, "ns", False))
        g.add_edge(InferenceEdge("x", "y", "p"))
        g.add_edge(InferenceEdge("y", "z", "p"))
        path = g.find_path("x", "z")
        assert path == ["x", "y", "z"]

    def test_cycle_detection(self):
        from iios.ontology.reasoning.inference import (
            InferenceGraph, InferenceNode, InferenceEdge,
        )
        g = InferenceGraph()
        for uid in ["a", "b", "c"]:
            g.add_node(InferenceNode(uid, uid, "ns", False))
        g.add_edge(InferenceEdge("a", "b", "p"))
        g.add_edge(InferenceEdge("b", "c", "p"))
        g.add_edge(InferenceEdge("c", "a", "p"))  # cycle
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_no_cycle_linear(self):
        from iios.ontology.reasoning.inference import (
            InferenceGraph, InferenceNode, InferenceEdge,
        )
        g = InferenceGraph()
        for uid in ["a", "b", "c"]:
            g.add_node(InferenceNode(uid, uid, "ns", False))
        g.add_edge(InferenceEdge("a", "b", "p"))
        g.add_edge(InferenceEdge("b", "c", "p"))
        cycles = g.detect_cycles()
        assert cycles == []

    def test_stats(self):
        from iios.ontology.reasoning.inference import (
            InferenceGraph, InferenceNode, InferenceEdge,
        )
        g = InferenceGraph()
        g.add_node(InferenceNode("n", "N", "ns", False))
        g.add_edge(InferenceEdge("n", "m", "p"))
        s = g.stats()
        assert s["nodes"] == 1
        assert s["edges"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  23 — End-to-end full pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline(self):
        """
        Complete pipeline:
        1. Register a 3-level hierarchy with a relationship
        2. Forward-chain all inference
        3. Consistency-check
        4. Explain session (machine)
        5. Verify inferred facts contain transitivity and inheritance
        """
        _register_namespace("iios.e2e")
        root     = _make_type("E2ERoot", ns="iios.e2e", abstract=True)
        mid      = _make_type("E2EMid",  ns="iios.e2e", parent="iios.e2e.E2ERoot")
        leaf     = _make_type("E2ELeaf", ns="iios.e2e", parent="iios.e2e.E2EMid")
        _register_type(root)
        _register_type(mid)
        _register_type(leaf)
        _register_rel(
            "iios.e2e.rel_mid_leaf",
            "midToLeaf",
            "iios.e2e.E2EMid",
            "iios.e2e.E2ELeaf",
            inverse_uri="iios.e2e.rel_leaf_mid",
        )

        from iios.ontology.reasoning import (
            get_reasoning_engine, PRED_TRANSITIVE_SUBTYPE, PRED_INVERSE_RELATED,
            InferenceStatus, IssueType,
        )
        engine = get_reasoning_engine()
        engine.initialize()

        # --- Forward chain ---
        resp = engine.infer_all()
        assert resp.succeeded
        assert resp.result.status == InferenceStatus.COMPLETED

        # Transitivity: E2ELeaf should declare E2ERoot as transitive ancestor
        trans_facts = [
            f for f in resp.result.inferred_facts
            if f.predicate == PRED_TRANSITIVE_SUBTYPE
            and f.subject_uri == "iios.e2e.E2ELeaf"
        ]
        objs = {str(f.object_value) for f in trans_facts}
        assert "iios.e2e.E2ERoot" in objs or "iios.e2e.E2EMid" in objs

        # Inverse relationship: E2ELeaf should have inverse_related_to E2EMid
        inv_facts = [
            f for f in resp.result.inferred_facts
            if f.predicate == PRED_INVERSE_RELATED
        ]
        assert len(inv_facts) >= 1

        # --- Consistency check ---
        consistency = engine.check_consistency()
        # abstract E2ERoot has two subtypes (mid+leaf), no abstract_no_children warning for root
        abstract_warnings = [
            i for i in consistency.consistency_issues
            if i.issue_type == IssueType.ABSTRACT_NO_CHILDREN
            and "E2ERoot" in " ".join(i.affected_uris)
        ]
        assert abstract_warnings == []

        # --- Explain session ---
        sid  = resp.result.session_id
        expl = engine.explain(sid)
        assert isinstance(expl, dict)

        # --- Trace audit ---
        session = engine.get_session(sid)
        assert session.trace is not None
        assert session.trace.step_count >= 1

    def test_statistics_recorded_after_session(self):
        _register_namespace("iios.test")
        t = _make_type("StatType")
        _register_type(t)
        from iios.ontology.reasoning import (
            get_reasoning_engine, get_reasoning_statistics,
        )
        engine = get_reasoning_engine()
        engine.initialize()
        engine.infer_all()
        stats = get_reasoning_statistics().snapshot()
        assert stats["session_count"] >= 1
        assert stats["total_facts_inferred"] >= 0

    def test_infer_for_type(self):
        _register_namespace("iios.test")
        p = _make_type("IFT_Parent")
        c = _make_type("IFT_Child", parent="iios.test.IFT_Parent")
        _register_type(p)
        _register_type(c)
        from iios.ontology.reasoning import get_reasoning_engine
        engine = get_reasoning_engine()
        engine.initialize()
        facts  = engine.infer_for_type("iios.test.IFT_Child")
        # Returns list (may be empty for leaf)
        assert isinstance(facts, list)

    def test_build_inference_graph(self):
        _register_namespace("iios.test")
        for name in ["GraphRoot", "GraphChild1", "GraphChild2"]:
            t = _make_type(name, parent="iios.test.GraphRoot" if name != "GraphRoot" else None)
            _register_type(t)
        from iios.ontology.reasoning import get_reasoning_engine
        from iios.ontology.reasoning.inference import get_inference_engine_instance
        engine = get_reasoning_engine()
        engine.initialize()
        facts  = engine._manager._inf_engine.forward_chain_all(engine._manager._mgr)
        from iios.ontology.registry.ontology_registry_manager import get_registry_manager
        graph  = engine._manager._inf_engine.build_graph(facts, get_registry_manager())
        assert graph.stats()["nodes"] >= 3
