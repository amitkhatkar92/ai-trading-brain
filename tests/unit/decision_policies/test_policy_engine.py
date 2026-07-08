"""
tests/unit/decision_policies/test_policy_engine.py
===================================================
Comprehensive unit tests for the Decision Policy & Rule Engine.
Target: ≥ 90 tests across all layers.
"""
from __future__ import annotations

import asyncio
import threading
import uuid

import pytest

# ── Shared helpers ────────────────────────────────────────────────────────────

def _ctx(payload: dict | None = None, source_id: str = "test") -> "EvaluationContext":
    from iios.decision_policies import EvaluationContext
    return EvaluationContext(source_id=source_id, payload=payload or {})


def _pass_eval(ctx):
    from iios.decision_policies import RuleStatus
    return RuleStatus.PASS, "always pass"


def _fail_eval(ctx):
    from iios.decision_policies import RuleStatus
    return RuleStatus.FAIL, "always fail"


def _warn_eval(ctx):
    from iios.decision_policies import RuleStatus
    return RuleStatus.WARN, "always warn"


def _pass_validator(ctx):
    return True, "ok"


def _fail_validator(ctx):
    return False, "constraint violated"


def _pass_checker(ctx):
    return True, "compliant"


def _fail_checker(ctx):
    return False, "not compliant"


def _reset_all() -> None:
    from iios.decision_policies.decision_policy_engine import reset_decision_policy_engine
    from iios.decision_policies.policy_manager import reset_policy_manager
    from iios.decision_policies.registry.policy_registry import reset_policy_registry
    from iios.decision_policies.rules.rule_registry import reset_rule_registry
    from iios.decision_policies.constraints.constraint_registry import reset_constraint_registry
    from iios.decision_policies.policy_context import reset_policy_context

    reset_decision_policy_engine()
    reset_policy_manager()
    reset_policy_registry()
    reset_rule_registry()
    reset_constraint_registry()
    reset_policy_context()


@pytest.fixture(autouse=True)
def clean_singletons():
    _reset_all()
    yield
    _reset_all()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_rule_status_values(self):
        from iios.decision_policies import RuleStatus
        assert RuleStatus.PASS.value  == "pass"
        assert RuleStatus.FAIL.value  == "fail"
        assert RuleStatus.WARN.value  == "warn"
        assert RuleStatus.SKIP.value  == "skip"
        assert RuleStatus.ERROR.value == "error"

    def test_group_operator_values(self):
        from iios.decision_policies import GroupOperator
        assert GroupOperator.AND.value      == "and"
        assert GroupOperator.OR.value       == "or"
        assert GroupOperator.MAJORITY.value == "majority"

    def test_policy_verdict_values(self):
        from iios.decision_policies import PolicyVerdict
        assert PolicyVerdict.APPROVE.value  == "approve"
        assert PolicyVerdict.REJECT.value   == "reject"
        assert PolicyVerdict.ESCALATE.value == "escalate"

    def test_evaluation_mode_values(self):
        from iios.decision_policies import EvaluationMode
        assert EvaluationMode.STRICT.value  == "strict"
        assert EvaluationMode.LENIENT.value == "lenient"
        assert EvaluationMode.AUDIT.value   == "audit"

    def test_constraint_types_present(self):
        from iios.decision_policies import ConstraintType
        for v in ("hard", "soft", "risk", "portfolio", "capital", "liquidity", "time", "custom"):
            assert ConstraintType(v) is not None

    def test_version(self):
        from iios.decision_policies import POLICY_ENGINE_VERSION
        assert POLICY_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_exception(self):
        from iios.decision_policies import PolicyEngineError
        with pytest.raises(PolicyEngineError):
            raise PolicyEngineError("test", "PE-000")

    def test_policy_not_found(self):
        from iios.decision_policies import PolicyNotFoundError
        exc = PolicyNotFoundError("p1")
        assert "PE-011" in str(exc)
        assert "p1" in str(exc)

    def test_policy_already_exists(self):
        from iios.decision_policies import PolicyAlreadyExistsError
        exc = PolicyAlreadyExistsError("p1")
        assert "PE-012" in str(exc)

    def test_rule_not_found(self):
        from iios.decision_policies import RuleNotFoundError
        exc = RuleNotFoundError("r1")
        assert "PE-021" in str(exc)

    def test_rule_already_exists(self):
        from iios.decision_policies import RuleAlreadyExistsError
        exc = RuleAlreadyExistsError("r1")
        assert "PE-025" in str(exc)

    def test_circular_dependency(self):
        from iios.decision_policies import CircularRuleDependencyError
        exc = CircularRuleDependencyError("r_cycle")
        assert "PE-024" in str(exc)

    def test_constraint_not_found(self):
        from iios.decision_policies import ConstraintNotFoundError
        exc = ConstraintNotFoundError("c1")
        assert "PE-032" in str(exc)

    def test_constraint_already_exists(self):
        from iios.decision_policies import ConstraintAlreadyExistsError
        exc = ConstraintAlreadyExistsError("c1")
        assert "PE-033" in str(exc)

    def test_engine_not_initialized(self):
        from iios.decision_policies import EngineNotInitializedError
        exc = EngineNotInitializedError()
        assert "PE-071" in str(exc)

    def test_engine_already_running(self):
        from iios.decision_policies import EngineAlreadyRunningError
        exc = EngineAlreadyRunningError()
        assert "PE-072" in str(exc)

    def test_unauthorized_override(self):
        from iios.decision_policies import UnauthorizedOverrideError
        exc = UnauthorizedOverrideError("user1")
        assert "PE-082" in str(exc)

    def test_hierarchy(self):
        from iios.decision_policies import (
            PolicyEngineError,
            RuleNotFoundError,
            ConstraintViolationError,
            EngineNotInitializedError,
        )
        assert issubclass(RuleNotFoundError,          PolicyEngineError)
        assert issubclass(ConstraintViolationError,   PolicyEngineError)
        assert issubclass(EngineNotInitializedError,  PolicyEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EvaluationContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationContext:
    def test_defaults(self):
        from iios.decision_policies import EvaluationContext, EvaluationMode
        ctx = EvaluationContext()
        assert ctx.decision_type  == "generic"
        assert ctx.evaluation_mode == EvaluationMode.LENIENT

    def test_get_key(self):
        ctx = _ctx({"score": 0.9})
        assert ctx.get("score") == 0.9
        assert ctx.get("missing", 42) == 42

    def test_to_dict_keys(self):
        ctx = _ctx({"x": 1})
        d = ctx.to_dict()
        for k in ("context_id", "source_id", "evaluation_mode", "payload_keys"):
            assert k in d
        assert "x" in d["payload_keys"]

    def test_context_id_unique(self):
        from iios.decision_policies import EvaluationContext
        a = EvaluationContext()
        b = EvaluationContext()
        assert a.context_id != b.context_id

    def test_custom_payload(self):
        ctx = _ctx({"risk": 0.3, "confidence": 0.8})
        assert ctx.get("risk") == 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PolicyContextScope
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyContextScope:
    def test_evaluation_scope(self):
        from iios.decision_policies import evaluation_scope, EvaluationMode
        with evaluation_scope("src1", EvaluationMode.STRICT) as state:
            assert state.source_id == "src1"
            assert state.depth     == 1

    def test_stage_scope(self):
        from iios.decision_policies import evaluation_scope, policy_stage_scope
        with evaluation_scope("src1") as state:
            with policy_stage_scope("validate") as s2:
                assert s2.current_stage == "validate"
            assert state.current_stage == ""  # restored after exit

    def test_diagnostics(self):
        from iios.decision_policies import evaluation_scope, get_policy_context
        with evaluation_scope("src1"):
            ctx = get_policy_context()
            ctx.add_diagnostic("WARNING", "test warning", "stage1", "tester")
            assert len(ctx.warnings()) == 1
            assert ctx.errors() == []

    def test_singleton_within_scope(self):
        from iios.decision_policies import evaluation_scope, get_policy_context
        with evaluation_scope("src1"):
            assert get_policy_context() is get_policy_context()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. StaticRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaticRule:
    def test_pass(self):
        from iios.decision_policies import StaticRule, RuleStatus
        rule = StaticRule("r1", "R1", _pass_eval)
        r    = rule.evaluate(_ctx())
        assert r.passed
        assert r.status == RuleStatus.PASS

    def test_fail(self):
        from iios.decision_policies import StaticRule, RuleStatus
        rule = StaticRule("r2", "R2", _fail_eval)
        r    = rule.evaluate(_ctx())
        assert r.failed
        assert r.status == RuleStatus.FAIL

    def test_condition_skip(self):
        from iios.decision_policies import StaticRule, RuleStatus
        rule = StaticRule("r3", "R3", _fail_eval, condition=lambda ctx: False)
        r    = rule.evaluate(_ctx())
        assert r.status == RuleStatus.SKIP

    def test_condition_pass(self):
        from iios.decision_policies import StaticRule, RuleStatus
        rule = StaticRule("r4", "R4", _pass_eval, condition=lambda ctx: True)
        r    = rule.evaluate(_ctx())
        assert r.passed

    def test_exception_becomes_error(self):
        from iios.decision_policies import StaticRule, RuleStatus
        def boom(ctx):
            raise ValueError("oops")
        rule = StaticRule("r5", "R5", boom)
        r    = rule.evaluate(_ctx())
        assert r.status == RuleStatus.ERROR
        assert r.score  == 0.0

    def test_disabled_skips(self):
        from iios.decision_policies import StaticRule, RuleStatus
        rule = StaticRule("r6", "R6", _fail_eval, enabled=False)
        r    = rule.evaluate(_ctx())
        assert r.status == RuleStatus.SKIP

    def test_to_dict(self):
        from iios.decision_policies import StaticRule
        rule = StaticRule("r7", "R7", _pass_eval, tags=["t1"])
        d    = rule.to_dict()
        assert d["rule_id"] == "r7"
        assert d["tags"]    == ["t1"]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DynamicRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestDynamicRule:
    def test_evaluate(self):
        from iios.decision_policies import DynamicRule, RuleStatus
        rule = DynamicRule("d1", "D1", _pass_eval)
        r    = rule.evaluate(_ctx())
        assert r.passed

    def test_update_evaluator(self):
        from iios.decision_policies import DynamicRule, RuleStatus
        rule = DynamicRule("d2", "D2", _pass_eval)
        rule.update_evaluator(_fail_eval)
        r = rule.evaluate(_ctx())
        assert r.failed

    def test_rule_type(self):
        from iios.decision_policies import DynamicRule, RuleType
        rule = DynamicRule("d3", "D3", _pass_eval)
        assert rule.rule_type == RuleType.DYNAMIC


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ConditionalRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestConditionalRule:
    def test_condition_true_evaluates(self):
        from iios.decision_policies import ConditionalRule, StaticRule, RuleStatus
        inner = StaticRule("inner1", "Inner", _pass_eval)
        rule  = ConditionalRule("c1", "C1", lambda ctx: True, inner)
        r     = rule.evaluate(_ctx())
        assert r.passed

    def test_condition_false_skips(self):
        from iios.decision_policies import ConditionalRule, StaticRule, RuleStatus
        inner = StaticRule("inner2", "Inner", _fail_eval)
        rule  = ConditionalRule("c2", "C2", lambda ctx: False, inner)
        r     = rule.evaluate(_ctx())
        assert r.status == RuleStatus.SKIP

    def test_rule_type(self):
        from iios.decision_policies import ConditionalRule, StaticRule, RuleType
        inner = StaticRule("inner3", "Inner", _pass_eval)
        rule  = ConditionalRule("c3", "C3", lambda ctx: True, inner)
        assert rule.rule_type == RuleType.CONDITIONAL


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CompositeRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeRule:
    def _make(self, op: str, *evals) -> "CompositeRule":
        from iios.decision_policies import StaticRule, CompositeRule
        children = [StaticRule(f"child_{i}", f"Child{i}", ev) for i, ev in enumerate(evals)]
        return CompositeRule(f"comp_{op}", f"Comp-{op}", children, operator=op)

    def test_and_all_pass(self):
        rule = self._make("and", _pass_eval, _pass_eval)
        r    = rule.evaluate(_ctx())
        assert r.passed

    def test_and_one_fail(self):
        rule = self._make("and", _pass_eval, _fail_eval)
        r    = rule.evaluate(_ctx())
        assert r.failed

    def test_or_one_pass(self):
        rule = self._make("or", _fail_eval, _pass_eval)
        r    = rule.evaluate(_ctx())
        assert r.passed

    def test_or_all_fail(self):
        rule = self._make("or", _fail_eval, _fail_eval)
        r    = rule.evaluate(_ctx())
        assert r.failed

    def test_rule_type(self):
        from iios.decision_policies import RuleType
        rule = self._make("and", _pass_eval)
        assert rule.rule_type == RuleType.COMPOSITE

    def test_and_short_circuit(self):
        """With short_circuit=True, AND stops at first fail."""
        from iios.decision_policies import StaticRule, CompositeRule, RuleStatus
        called = []
        def last_eval(ctx):
            called.append(1)
            return RuleStatus.PASS, "last"
        children = [
            StaticRule("sc1", "SC1", _fail_eval),
            StaticRule("sc2", "SC2", last_eval),
        ]
        rule = CompositeRule("comp_sc", "SC", children, operator="and", short_circuit=True)
        r    = rule.evaluate(_ctx())
        assert r.failed
        assert called == []  # second rule was not called


# ═══════════════════════════════════════════════════════════════════════════════
# 9. PriorityRule
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriorityRule:
    def test_priority_override(self):
        from iios.decision_policies import StaticRule, PriorityRule
        inner = StaticRule("p1", "P1", _pass_eval, priority=100)
        rule  = PriorityRule(inner, priority=5)
        assert rule.priority == 5
        assert rule.rule_id  == "p1"

    def test_evaluate_delegates(self):
        from iios.decision_policies import StaticRule, PriorityRule
        inner = StaticRule("p2", "P2", _pass_eval)
        rule  = PriorityRule(inner, priority=1)
        r     = rule.evaluate(_ctx())
        assert r.passed


# ═══════════════════════════════════════════════════════════════════════════════
# 10. RuleGroup
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleGroup:
    def _rules(self, *evals):
        from iios.decision_policies import StaticRule
        return [StaticRule(f"gr_{i}", f"GR{i}", ev) for i, ev in enumerate(evals)]

    def test_and_all_pass(self):
        from iios.decision_policies import RuleGroup, GroupOperator, RuleStatus
        g = RuleGroup("g1", "G1", GroupOperator.AND, self._rules(_pass_eval, _pass_eval))
        r = g.evaluate(_ctx())
        assert r.status == RuleStatus.PASS

    def test_and_one_fail(self):
        from iios.decision_policies import RuleGroup, GroupOperator, RuleStatus
        g = RuleGroup("g2", "G2", GroupOperator.AND, self._rules(_pass_eval, _fail_eval))
        r = g.evaluate(_ctx())
        assert r.status == RuleStatus.FAIL

    def test_or_one_pass(self):
        from iios.decision_policies import RuleGroup, GroupOperator, RuleStatus
        g = RuleGroup("g3", "G3", GroupOperator.OR, self._rules(_fail_eval, _pass_eval))
        r = g.evaluate(_ctx())
        assert r.status == RuleStatus.PASS

    def test_majority(self):
        from iios.decision_policies import RuleGroup, GroupOperator, RuleStatus
        # 2 pass, 1 fail → majority passes
        g = RuleGroup("g4", "G4", GroupOperator.MAJORITY,
                      self._rules(_pass_eval, _pass_eval, _fail_eval))
        r = g.evaluate(_ctx())
        assert r.status == RuleStatus.PASS

    def test_add_remove_rule(self):
        from iios.decision_policies import RuleGroup, GroupOperator, StaticRule
        g    = RuleGroup("g5", "G5", GroupOperator.AND)
        rule = StaticRule("r_add", "RAdd", _pass_eval)
        g.add_rule(rule)
        assert g.rule_count() == 1
        g.remove_rule("r_add")
        assert g.rule_count() == 0

    def test_to_dict(self):
        from iios.decision_policies import RuleGroup, GroupOperator
        g = RuleGroup("g6", "G6", GroupOperator.AND)
        d = g.to_dict()
        assert d["group_id"] == "g6"

    def test_group_score(self):
        from iios.decision_policies import RuleGroup, GroupOperator
        g = RuleGroup("g7", "G7", GroupOperator.AND, self._rules(_pass_eval))
        r = g.evaluate(_ctx())
        assert 0.0 <= r.score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. RuleRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleRegistry:
    def test_register_and_get(self):
        from iios.decision_policies import StaticRule, get_rule_registry
        reg  = get_rule_registry()
        rule = StaticRule("rr1", "RR1", _pass_eval)
        reg.register_rule(rule)
        assert reg.get_rule("rr1") is rule

    def test_duplicate_raises(self):
        from iios.decision_policies import StaticRule, get_rule_registry, RuleAlreadyExistsError
        reg  = get_rule_registry()
        rule = StaticRule("rr2", "RR2", _pass_eval)
        reg.register_rule(rule)
        with pytest.raises(RuleAlreadyExistsError):
            reg.register_rule(rule)

    def test_not_found_raises(self):
        from iios.decision_policies import get_rule_registry, RuleNotFoundError
        with pytest.raises(RuleNotFoundError):
            get_rule_registry().get_rule("nonexistent")

    def test_has_rule(self):
        from iios.decision_policies import StaticRule, get_rule_registry
        reg  = get_rule_registry()
        rule = StaticRule("rr3", "RR3", _pass_eval)
        reg.register_rule(rule)
        assert reg.has_rule("rr3")
        assert not reg.has_rule("ghost")

    def test_remove_rule(self):
        from iios.decision_policies import StaticRule, get_rule_registry
        reg  = get_rule_registry()
        rule = StaticRule("rr4", "RR4", _pass_eval)
        reg.register_rule(rule)
        assert reg.remove_rule("rr4")
        assert not reg.has_rule("rr4")

    def test_rules_by_tag(self):
        from iios.decision_policies import StaticRule, get_rule_registry
        reg = get_rule_registry()
        reg.register_rule(StaticRule("t1", "T1", _pass_eval, tags=["safety"]))
        reg.register_rule(StaticRule("t2", "T2", _pass_eval, tags=["risk"]))
        assert len(reg.rules_by_tag("safety")) == 1

    def test_singleton(self):
        from iios.decision_policies import get_rule_registry
        assert get_rule_registry() is get_rule_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 12. RuleExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleExecutor:
    def test_execute_sequential(self):
        from iios.decision_policies import StaticRule, RuleExecutor
        ex    = RuleExecutor(parallel=False)
        rules = [StaticRule("ex1", "EX1", _pass_eval), StaticRule("ex2", "EX2", _fail_eval)]
        rs    = ex.execute(rules, _ctx())
        assert len(rs) == 2
        assert rs[0].passed
        assert rs[1].failed

    def test_execute_parallel(self):
        from iios.decision_policies import StaticRule, RuleExecutor
        ex    = RuleExecutor(parallel=True, max_workers=2)
        rules = [StaticRule(f"px{i}", f"PX{i}", _pass_eval) for i in range(4)]
        rs    = ex.execute(rules, _ctx())
        assert all(r.passed for r in rs)

    def test_dependency_missing_raises(self):
        from iios.decision_policies import StaticRule, RuleExecutor, RuleDependencyError
        ex   = RuleExecutor()
        rule = StaticRule("dep_r", "DepR", _pass_eval, dependencies=["missing_dep"])
        with pytest.raises(RuleDependencyError):
            ex.execute([rule], _ctx())

    def test_circular_dependency_raises(self):
        from iios.decision_policies import StaticRule, RuleExecutor, CircularRuleDependencyError
        ex = RuleExecutor()
        r1 = StaticRule("cyc1", "CYC1", _pass_eval, dependencies=["cyc2"])
        r2 = StaticRule("cyc2", "CYC2", _pass_eval, dependencies=["cyc1"])
        with pytest.raises(CircularRuleDependencyError):
            ex.execute([r1, r2], _ctx())


# ═══════════════════════════════════════════════════════════════════════════════
# 13. RuleEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleEngine:
    def test_evaluate_rules(self):
        from iios.decision_policies import StaticRule, RuleEngine
        eng   = RuleEngine()
        rules = [StaticRule("re1", "RE1", _pass_eval), StaticRule("re2", "RE2", _fail_eval)]
        rs    = eng.evaluate_rules(rules, _ctx())
        assert len(rs) == 2

    def test_evaluate_group(self):
        from iios.decision_policies import StaticRule, RuleGroup, RuleEngine, GroupOperator
        from iios.decision_policies import RuleStatus
        rule = StaticRule("eg1", "EG1", _pass_eval)
        g    = RuleGroup("grp1", "GRP1", GroupOperator.AND, [rule])
        eng  = RuleEngine()
        gr   = eng.evaluate_group(g, _ctx())
        assert gr.status == RuleStatus.PASS

    def test_summary(self):
        from iios.decision_policies import StaticRule, RuleEngine
        eng   = RuleEngine()
        rules = [StaticRule("sm1", "SM1", _pass_eval), StaticRule("sm2", "SM2", _fail_eval)]
        rs    = eng.evaluate_rules(rules, _ctx())
        s     = eng.summary(rs)
        assert s["total"]   == 2
        assert s["passed"]  == 1
        assert s["failed"]  == 1

    def test_evaluate_by_tags(self):
        from iios.decision_policies import StaticRule, RuleEngine, get_rule_registry
        reg = get_rule_registry()
        reg.register_rule(StaticRule("tag1", "TAG1", _pass_eval, tags=["alpha"]))
        eng = RuleEngine(registry=reg)
        rs  = eng.evaluate_by_tags(["alpha"], _ctx())
        assert len(rs) == 1
        assert rs[0].passed

    def test_evaluate_all_registered(self):
        from iios.decision_policies import StaticRule, RuleEngine, get_rule_registry
        reg = get_rule_registry()
        reg.register_rule(StaticRule("ar1", "AR1", _pass_eval))
        reg.register_rule(StaticRule("ar2", "AR2", _pass_eval))
        eng = RuleEngine(registry=reg)
        rs  = eng.evaluate_all_registered(_ctx())
        assert len(rs) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 14. StaticConstraint
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaticConstraint:
    def test_pass(self):
        from iios.decision_policies import StaticConstraint
        c = StaticConstraint("sc1", "SC1", _pass_validator)
        r = c.validate(_ctx())
        assert r.passed

    def test_fail(self):
        from iios.decision_policies import StaticConstraint
        c = StaticConstraint("sc2", "SC2", _fail_validator)
        r = c.validate(_ctx())
        assert r.violated
        assert r.blocks_decision  # default mandatory=True

    def test_soft_does_not_block(self):
        from iios.decision_policies import StaticConstraint
        c = StaticConstraint("sc3", "SC3", _fail_validator, mandatory=False)
        r = c.validate(_ctx())
        assert r.violated
        assert not r.blocks_decision

    def test_condition_skip(self):
        from iios.decision_policies import StaticConstraint
        c = StaticConstraint("sc4", "SC4", _fail_validator, condition=lambda ctx: False)
        r = c.validate(_ctx())
        assert r.passed  # skipped


# ═══════════════════════════════════════════════════════════════════════════════
# 15. BoundedConstraint
# ═══════════════════════════════════════════════════════════════════════════════

class TestBoundedConstraint:
    def test_within_bounds(self):
        from iios.decision_policies import BoundedConstraint
        c = BoundedConstraint("bc1", "BC1", "score", min_val=0.0, max_val=1.0)
        r = c.validate(_ctx({"score": 0.5}))
        assert r.passed

    def test_below_min(self):
        from iios.decision_policies import BoundedConstraint
        c = BoundedConstraint("bc2", "BC2", "score", min_val=0.5, max_val=1.0)
        r = c.validate(_ctx({"score": 0.3}))
        assert r.violated

    def test_above_max(self):
        from iios.decision_policies import BoundedConstraint
        c = BoundedConstraint("bc3", "BC3", "risk", min_val=0.0, max_val=0.5)
        r = c.validate(_ctx({"risk": 0.8}))
        assert r.violated

    def test_missing_key(self):
        from iios.decision_policies import BoundedConstraint
        c = BoundedConstraint("bc4", "BC4", "missing_key", min_val=0.0)
        r = c.validate(_ctx({}))
        assert r.violated


# ═══════════════════════════════════════════════════════════════════════════════
# 16. ThresholdConstraint
# ═══════════════════════════════════════════════════════════════════════════════

class TestThresholdConstraint:
    def test_above_threshold_pass(self):
        from iios.decision_policies import ThresholdConstraint
        c = ThresholdConstraint("tc1", "TC1", "score", 0.5, above=True)
        r = c.validate(_ctx({"score": 0.8}))
        assert r.passed

    def test_above_threshold_fail(self):
        from iios.decision_policies import ThresholdConstraint
        c = ThresholdConstraint("tc2", "TC2", "score", 0.5, above=True)
        r = c.validate(_ctx({"score": 0.3}))
        assert r.violated

    def test_below_threshold_pass(self):
        from iios.decision_policies import ThresholdConstraint
        c = ThresholdConstraint("tc3", "TC3", "risk", 0.5, above=False)
        r = c.validate(_ctx({"risk": 0.2}))
        assert r.passed


# ═══════════════════════════════════════════════════════════════════════════════
# 17. ConstraintResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintResult:
    def test_violated_property(self):
        from iios.decision_policies import ConstraintResult
        r = ConstraintResult("cr1", "CR1", passed=False, is_hard=True)
        assert r.violated
        assert r.blocks_decision

    def test_soft_no_block(self):
        from iios.decision_policies import ConstraintResult
        r = ConstraintResult("cr2", "CR2", passed=False, is_hard=False)
        assert r.violated
        assert not r.blocks_decision

    def test_to_dict(self):
        from iios.decision_policies import ConstraintResult
        d = ConstraintResult("cr3", "CR3").to_dict()
        for k in ("constraint_id", "passed", "is_hard", "blocks_decision"):
            assert k in d


# ═══════════════════════════════════════════════════════════════════════════════
# 18. ConstraintRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintRegistry:
    def test_register_and_get(self):
        from iios.decision_policies import StaticConstraint, get_constraint_registry
        reg = get_constraint_registry()
        c   = StaticConstraint("creg1", "CREG1", _pass_validator)
        reg.register(c)
        assert reg.get("creg1") is c

    def test_duplicate_raises(self):
        from iios.decision_policies import StaticConstraint, get_constraint_registry, ConstraintAlreadyExistsError
        reg = get_constraint_registry()
        c   = StaticConstraint("creg2", "CREG2", _pass_validator)
        reg.register(c)
        with pytest.raises(ConstraintAlreadyExistsError):
            reg.register(c)

    def test_not_found_raises(self):
        from iios.decision_policies import get_constraint_registry, ConstraintNotFoundError
        with pytest.raises(ConstraintNotFoundError):
            get_constraint_registry().get("ghost")

    def test_has_and_remove(self):
        from iios.decision_policies import StaticConstraint, get_constraint_registry
        reg = get_constraint_registry()
        c   = StaticConstraint("creg3", "CREG3", _pass_validator)
        reg.register(c)
        assert reg.has("creg3")
        reg.remove("creg3")
        assert not reg.has("creg3")

    def test_singleton(self):
        from iios.decision_policies import get_constraint_registry
        assert get_constraint_registry() is get_constraint_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ConstraintEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstraintEngine:
    def test_evaluate(self):
        from iios.decision_policies import StaticConstraint, ConstraintEngine
        eng = ConstraintEngine()
        cs  = [StaticConstraint("ce1", "CE1", _pass_validator)]
        rs  = eng.evaluate(cs, _ctx())
        assert len(rs) == 1
        assert rs[0].passed

    def test_summary_blocked(self):
        from iios.decision_policies import StaticConstraint, ConstraintEngine
        eng = ConstraintEngine()
        cs  = [StaticConstraint("ce2", "CE2", _fail_validator, mandatory=True)]
        rs  = eng.evaluate(cs, _ctx())
        s   = eng.summary(rs)
        assert s["blocked"]
        assert s["hard_violations"] == 1

    def test_has_hard_violations(self):
        from iios.decision_policies import StaticConstraint, ConstraintEngine
        eng = ConstraintEngine()
        cs  = [StaticConstraint("ce3", "CE3", _fail_validator, mandatory=True)]
        rs  = eng.evaluate(cs, _ctx())
        assert eng.has_hard_violations(rs)

    def test_soft_no_block(self):
        from iios.decision_policies import StaticConstraint, ConstraintEngine
        eng = ConstraintEngine()
        cs  = [StaticConstraint("ce4", "CE4", _fail_validator, mandatory=False)]
        rs  = eng.evaluate(cs, _ctx())
        assert not eng.has_hard_violations(rs)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. CompliancePolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompliancePolicy:
    def test_pass(self):
        from iios.decision_policies import StaticCompliancePolicy
        p = StaticCompliancePolicy("cp1", "CP1", _pass_checker)
        r = p.check(_ctx())
        assert r.passed

    def test_fail(self):
        from iios.decision_policies import StaticCompliancePolicy
        p = StaticCompliancePolicy("cp2", "CP2", _fail_checker)
        r = p.check(_ctx())
        assert r.violated
        assert r.blocks_decision  # default mandatory=True

    def test_category(self):
        from iios.decision_policies import StaticCompliancePolicy, ComplianceCategory
        p = StaticCompliancePolicy("cp3", "CP3", _pass_checker, category=ComplianceCategory.REGULATORY)
        assert p.category == ComplianceCategory.REGULATORY

    def test_condition_skip(self):
        from iios.decision_policies import StaticCompliancePolicy
        p = StaticCompliancePolicy("cp4", "CP4", _fail_checker, condition=lambda ctx: False)
        r = p.check(_ctx())
        assert r.passed  # skipped via condition


# ═══════════════════════════════════════════════════════════════════════════════
# 21. ComplianceReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceReport:
    def test_build_pass(self):
        from iios.decision_policies import StaticCompliancePolicy, build_compliance_report
        p   = StaticCompliancePolicy("rpt1", "RPT1", _pass_checker)
        res = [p.check(_ctx())]
        rpt = build_compliance_report(res, context_id="ctx1", source_id="src1")
        assert rpt.passed
        assert rpt.mandatory_failures == 0

    def test_build_fail(self):
        from iios.decision_policies import StaticCompliancePolicy, build_compliance_report
        p   = StaticCompliancePolicy("rpt2", "RPT2", _fail_checker)
        res = [p.check(_ctx())]
        rpt = build_compliance_report(res)
        assert not rpt.passed
        assert rpt.mandatory_failures == 1
        assert len(rpt.violations) == 1

    def test_to_dict(self):
        from iios.decision_policies import build_compliance_report
        rpt = build_compliance_report([])
        d   = rpt.to_dict()
        assert "report_id" in d
        assert "passed"    in d


# ═══════════════════════════════════════════════════════════════════════════════
# 22. ComplianceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceEngine:
    def test_evaluate_pass(self):
        from iios.decision_policies import StaticCompliancePolicy, ComplianceEngine
        eng = ComplianceEngine()
        p   = StaticCompliancePolicy("compeng1", "CE1", _pass_checker)
        rpt = eng.evaluate(_ctx(), policies=[p])
        assert rpt.passed

    def test_evaluate_fail(self):
        from iios.decision_policies import StaticCompliancePolicy, ComplianceEngine
        eng = ComplianceEngine()
        p   = StaticCompliancePolicy("compeng2", "CE2", _fail_checker)
        rpt = eng.evaluate(_ctx(), policies=[p])
        assert not rpt.passed

    def test_register_and_evaluate(self):
        from iios.decision_policies import StaticCompliancePolicy, ComplianceEngine
        eng = ComplianceEngine()
        p   = StaticCompliancePolicy("compeng3", "CE3", _pass_checker)
        eng.register(p)
        rpt = eng.evaluate(_ctx())
        assert rpt.passed
        assert rpt.total_checked == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 23. PolicyEvaluator
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluator:
    def test_empty_request_approves(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, PolicyVerdict
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest()
        r   = ev.evaluate(req)
        assert r.verdict == PolicyVerdict.APPROVE
        assert r.approved

    def test_rules_pass(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticRule
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            rules=[StaticRule("evr1", "EVR1", _pass_eval)]
        )
        r = ev.evaluate(req)
        assert r.approved
        assert r.passed_rules == 1

    def test_rules_fail_rejects(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticRule, PolicyVerdict
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            rules=[StaticRule("evr2", "EVR2", _fail_eval)]
        )
        r = ev.evaluate(req)
        assert r.verdict  == PolicyVerdict.REJECT
        assert not r.approved

    def test_constraint_hard_rejects(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticConstraint, PolicyVerdict
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            constraints=[StaticConstraint("evc1", "EVC1", _fail_validator, mandatory=True)]
        )
        r = ev.evaluate(req)
        assert r.verdict == PolicyVerdict.REJECT

    def test_constraint_soft_approves(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticConstraint, PolicyVerdict
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            constraints=[StaticConstraint("evc2", "EVC2", _fail_validator, mandatory=False)]
        )
        r = ev.evaluate(req)
        assert r.verdict == PolicyVerdict.APPROVE
        assert r.soft_warnings == 1

    def test_compliance_fail_rejects(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticCompliancePolicy, PolicyVerdict
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            compliance_pols=[StaticCompliancePolicy("evcp1", "EVCP1", _fail_checker)]
        )
        r = ev.evaluate(req)
        assert r.verdict == PolicyVerdict.REJECT

    def test_audit_mode_always_approves(self):
        from iios.decision_policies import (
            PolicyEvaluator, PolicyEvaluationRequest, StaticRule,
            EvaluationMode, PolicyVerdict
        )
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            rules=[StaticRule("evaud1", "EVAUD1", _fail_eval)],
            evaluation_mode=EvaluationMode.AUDIT,
        )
        r = ev.evaluate(req)
        assert r.verdict == PolicyVerdict.APPROVE

    def test_policy_score_computed(self):
        from iios.decision_policies import PolicyEvaluator, PolicyEvaluationRequest, StaticRule
        ev  = PolicyEvaluator()
        req = PolicyEvaluationRequest(
            rules=[
                StaticRule("evsc1", "EVSC1", _pass_eval),
                StaticRule("evsc2", "EVSC2", _pass_eval),
            ]
        )
        r = ev.evaluate(req)
        assert r.policy_score == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. ConflictDetector
# ═══════════════════════════════════════════════════════════════════════════════

class TestConflictDetector:
    def test_no_conflicts_clean(self):
        from iios.decision_policies import ConflictDetector, StaticRule
        det   = ConflictDetector()
        rule  = StaticRule("cd1", "CD1", _pass_eval)
        r     = rule.evaluate(_ctx())
        conflicts = det.detect_rule_conflicts([r])
        assert conflicts == []

    def test_duplicate_constraint_id_conflict(self):
        from iios.decision_policies import ConflictDetector, ConstraintResult
        det = ConflictDetector()
        r1  = ConstraintResult("dup_id", "DUP", passed=True, is_hard=True)
        r2  = ConstraintResult("dup_id", "DUP", passed=False, is_hard=True)
        c   = det.detect_constraint_conflicts([r1, r2])
        assert len(c) == 1
        assert "dup_id" in c[0]

    def test_detect_all(self):
        from iios.decision_policies import ConflictDetector
        det = ConflictDetector()
        out = det.detect_all([], [])
        assert isinstance(out, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. PolicyRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyRegistry:
    def test_register_get_rule(self):
        from iios.decision_policies import get_policy_registry, StaticRule
        reg  = get_policy_registry()
        rule = StaticRule("preg_r1", "PREG_R1", _pass_eval)
        reg.register_rule(rule)
        assert reg.get_rule("preg_r1") is rule

    def test_duplicate_rule_raises(self):
        from iios.decision_policies import get_policy_registry, StaticRule, PolicyAlreadyExistsError
        reg  = get_policy_registry()
        rule = StaticRule("preg_r2", "PREG_R2", _pass_eval)
        reg.register_rule(rule)
        with pytest.raises(PolicyAlreadyExistsError):
            reg.register_rule(rule)

    def test_register_constraint(self):
        from iios.decision_policies import get_policy_registry, StaticConstraint
        reg = get_policy_registry()
        c   = StaticConstraint("preg_c1", "PREG_C1", _pass_validator)
        reg.register_constraint(c)
        assert reg.get_constraint("preg_c1") is c

    def test_register_compliance(self):
        from iios.decision_policies import get_policy_registry, StaticCompliancePolicy
        reg = get_policy_registry()
        p   = StaticCompliancePolicy("preg_p1", "PREG_P1", _pass_checker)
        reg.register_compliance(p)
        assert reg.get_compliance("preg_p1") is p

    def test_register_group(self):
        from iios.decision_policies import get_policy_registry, RuleGroup, GroupOperator
        reg = get_policy_registry()
        g   = RuleGroup("preg_g1", "PREG_G1", GroupOperator.AND)
        reg.register_group(g)
        assert reg.get_group("preg_g1") is g

    def test_not_found_raises(self):
        from iios.decision_policies import get_policy_registry, PolicyNotFoundError
        with pytest.raises(PolicyNotFoundError):
            get_policy_registry().get_rule("ghost_rule")

    def test_stats(self):
        from iios.decision_policies import get_policy_registry
        s = get_policy_registry().stats()
        for k in ("total_rules", "total_groups", "total_constraints", "total_compliance"):
            assert k in s

    def test_singleton(self):
        from iios.decision_policies import get_policy_registry
        assert get_policy_registry() is get_policy_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 26. PolicyFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyFactory:
    def test_make_rule(self):
        from iios.decision_policies import PolicyFactory, StaticRule
        r = PolicyFactory.make_rule("fr1", "FR1", _pass_eval)
        assert isinstance(r, StaticRule)
        assert r.rule_id == "fr1"

    def test_make_dynamic_rule(self):
        from iios.decision_policies import PolicyFactory, DynamicRule
        r = PolicyFactory.make_dynamic_rule("fd1", "FD1", _pass_eval)
        assert isinstance(r, DynamicRule)

    def test_make_composite_rule(self):
        from iios.decision_policies import PolicyFactory, StaticRule, CompositeRule
        children = [StaticRule("fc1", "FC1", _pass_eval)]
        r = PolicyFactory.make_composite_rule("fcomp1", "FCOMP1", children)
        assert isinstance(r, CompositeRule)

    def test_make_bounded_constraint(self):
        from iios.decision_policies import PolicyFactory, BoundedConstraint
        c = PolicyFactory.make_bounded_constraint("fb1", "FB1", "score", min_val=0.0, max_val=1.0)
        assert isinstance(c, BoundedConstraint)
        r = c.validate(_ctx({"score": 0.5}))
        assert r.passed

    def test_make_threshold_constraint(self):
        from iios.decision_policies import PolicyFactory, ThresholdConstraint
        c = PolicyFactory.make_threshold_constraint("ft1", "FT1", "score", 0.5, above=True)
        assert isinstance(c, ThresholdConstraint)

    def test_make_compliance_policy(self):
        from iios.decision_policies import PolicyFactory, StaticCompliancePolicy
        p = PolicyFactory.make_compliance_policy("fcp1", "FCP1", _pass_checker)
        assert isinstance(p, StaticCompliancePolicy)
        r = p.check(_ctx())
        assert r.passed


# ═══════════════════════════════════════════════════════════════════════════════
# 27. PolicyManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyManager:
    def test_register_and_evaluate_rule(self):
        from iios.decision_policies import get_policy_manager, StaticRule, PolicyVerdict
        mgr  = get_policy_manager()
        rule = StaticRule("pm_r1", "PM_R1", _pass_eval)
        mgr.register_rule(rule)
        r = mgr.evaluate(_ctx(), rules=[rule])
        assert r.approved

    def test_evaluate_hard_constraint_rejects(self):
        from iios.decision_policies import get_policy_manager, StaticConstraint, PolicyVerdict
        mgr = get_policy_manager()
        c   = StaticConstraint("pm_c1", "PM_C1", _fail_validator, mandatory=True)
        mgr.register_constraint(c)
        r = mgr.evaluate(_ctx(), constraints=[c])
        assert not r.approved

    def test_register_compliance_policy(self):
        from iios.decision_policies import get_policy_manager, StaticCompliancePolicy
        mgr = get_policy_manager()
        p   = StaticCompliancePolicy("pm_cp1", "PM_CP1", _pass_checker)
        mgr.register_compliance_policy(p)
        assert mgr.get_compliance_policy("pm_cp1") is p

    def test_evaluate_all_registered(self):
        from iios.decision_policies import get_policy_manager, StaticRule
        mgr  = get_policy_manager()
        rule = StaticRule("pm_all1", "PM_ALL1", _pass_eval)
        mgr.register_rule(rule)
        r = mgr.evaluate_all_registered(_ctx())
        assert r.approved

    def test_stats(self):
        from iios.decision_policies import get_policy_manager
        s = get_policy_manager().stats()
        assert "total_rules" in s

    def test_singleton(self):
        from iios.decision_policies import get_policy_manager
        assert get_policy_manager() is get_policy_manager()

    def test_get_rule(self):
        from iios.decision_policies import get_policy_manager, StaticRule
        mgr  = get_policy_manager()
        rule = StaticRule("pm_get1", "PM_GET1", _pass_eval)
        mgr.register_rule(rule)
        assert mgr.get_rule("pm_get1") is rule


# ═══════════════════════════════════════════════════════════════════════════════
# 28. DecisionPolicyEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionPolicyEngine:
    def _engine(self):
        from iios.decision_policies import get_decision_policy_engine
        eng = get_decision_policy_engine()
        eng.initialize()
        return eng

    def test_initialize_and_is_running(self):
        eng = self._engine()
        assert eng.is_running

    def test_double_initialize_raises(self):
        from iios.decision_policies import EngineAlreadyRunningError
        eng = self._engine()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        from iios.decision_policies import get_decision_policy_engine, EngineNotInitializedError
        eng = get_decision_policy_engine()
        with pytest.raises(EngineNotInitializedError):
            eng.evaluate(_ctx())

    def test_shutdown(self):
        eng = self._engine()
        eng.shutdown()
        assert not eng.is_running

    def test_evaluate_pass(self):
        from iios.decision_policies import StaticRule
        eng  = self._engine()
        rule = StaticRule("dpe_r1", "DPE_R1", _pass_eval)
        r    = eng.evaluate(_ctx(), rules=[rule])
        assert r.approved

    def test_evaluate_fail(self):
        from iios.decision_policies import StaticRule
        eng  = self._engine()
        rule = StaticRule("dpe_r2", "DPE_R2", _fail_eval)
        r    = eng.evaluate(_ctx(), rules=[rule])
        assert not r.approved

    def test_register_rule(self):
        from iios.decision_policies import StaticRule
        eng  = self._engine()
        rule = StaticRule("dpe_reg1", "DPE_REG1", _pass_eval)
        eng.register_rule(rule)
        # verify it shows up in stats
        s = eng.stats()
        assert s.get("total_rules", 0) >= 1

    def test_register_constraint(self):
        from iios.decision_policies import StaticConstraint
        eng = self._engine()
        c   = StaticConstraint("dpe_c1", "DPE_C1", _pass_validator)
        eng.register_constraint(c)

    def test_register_compliance_policy(self):
        from iios.decision_policies import StaticCompliancePolicy
        eng = self._engine()
        p   = StaticCompliancePolicy("dpe_cp1", "DPE_CP1", _pass_checker)
        eng.register_compliance_policy(p)

    def test_evaluate_all(self):
        eng = self._engine()
        r   = eng.evaluate_all(_ctx())
        assert r is not None

    def test_health_running(self):
        eng = self._engine()
        h   = eng.health()
        assert h["status"] == "healthy"

    def test_health_stopped(self):
        from iios.decision_policies import get_decision_policy_engine
        eng = get_decision_policy_engine()
        h   = eng.health()
        assert h["status"] == "stopped"

    def test_stats_has_version(self):
        eng = self._engine()
        s   = eng.stats()
        assert s["engine_version"] == "1.0.0"

    def test_async_evaluate(self):
        from iios.decision_policies import StaticRule
        eng  = self._engine()
        rule = StaticRule("async_r1", "ASYNC_R1", _pass_eval)

        async def _run():
            return await eng.evaluate_async(_ctx(), rules=[rule])

        r = asyncio.run(_run())
        assert r.approved

    def test_version_constant(self):
        from iios.decision_policies import DecisionPolicyEngine
        assert DecisionPolicyEngine.VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# 29. Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_evaluations(self):
        from iios.decision_policies import get_decision_policy_engine, StaticRule
        eng = get_decision_policy_engine()
        eng.initialize()

        errors:  list = []
        results: list = []

        def _eval():
            try:
                rule = StaticRule(str(uuid.uuid4()), "CONC", _pass_eval)
                r    = eng.evaluate(_ctx(), rules=[rule])
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_eval) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors  == []
        assert len(results) == 20

    def test_concurrent_registry_singletons(self):
        from iios.decision_policies import get_policy_registry
        regs = []

        def _get():
            regs.append(get_policy_registry())

        threads = [threading.Thread(target=_get) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is regs[0] for r in regs)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. Package imports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_key_symbols_importable(self):
        import iios.decision_policies as dp
        for sym in (
            "DecisionPolicyEngine", "get_decision_policy_engine",
            "PolicyManager", "PolicyFactory",
            "Rule", "StaticRule", "DynamicRule", "ConditionalRule", "CompositeRule",
            "RuleGroup", "RuleEngine",
            "Constraint", "HardConstraint", "SoftConstraint",
            "BoundedConstraint", "ThresholdConstraint",
            "CompliancePolicy", "StaticCompliancePolicy",
            "PolicyEvaluationRequest", "PolicyEvaluationResult",
            "ConflictDetector",
        ):
            assert hasattr(dp, sym), f"Missing: {sym}"

    def test_exception_hierarchy(self):
        from iios.decision_policies import (
            PolicyEngineError, RuleNotFoundError,
            ConstraintAlreadyExistsError, EngineNotInitializedError,
        )
        assert issubclass(RuleNotFoundError,         PolicyEngineError)
        assert issubclass(ConstraintAlreadyExistsError, PolicyEngineError)
        assert issubclass(EngineNotInitializedError, PolicyEngineError)

    def test_version_accessible(self):
        import iios.decision_policies as dp
        assert dp.__version__ == "1.0.0"
        assert dp.__layer__   == "LAYER-10-POLICY"
