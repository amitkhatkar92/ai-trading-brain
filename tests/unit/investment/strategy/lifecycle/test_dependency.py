"""tests/unit/investment/strategy/lifecycle/test_dependency.py
Tests for: DependencyGraph, DependencyValidator, DependencyRegistry, DependencyEngine
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.lifecycle.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
    DependencyNode,
)
from iios.investment.strategy.lifecycle.dependency_validator import (
    DependencyValidationResult,
    DependencyValidator,
)
from iios.investment.strategy.lifecycle.dependency_registry import (
    DependencyDeclaration,
    DependencyRegistry,
    DependencyType,
)
from iios.investment.strategy.lifecycle.dependency_engine import (
    DependencyEngine,
)


# ── DependencyGraph ───────────────────────────────────────────────────────────

class TestDependencyGraph:
    def test_add_and_retrieve(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        assert "a" in g.get_dependencies("b")
        assert "b" in g.get_dependents("a")

    def test_self_dependency_raises(self):
        g = DependencyGraph()
        with pytest.raises(CyclicDependencyError):
            g.add_dependency("a", "a")

    def test_cycle_detection(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        g.add_dependency("c", "b")
        with pytest.raises(CyclicDependencyError):
            g.add_dependency("a", "c")  # a → c → b → a = cycle

    def test_topological_sort_simple(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        g.add_dependency("c", "b")
        order = g.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_topological_sort_no_deps(self):
        g = DependencyGraph()
        g.ensure_node("x")
        g.ensure_node("y")
        order = g.topological_sort()
        assert set(order) == {"x", "y"}

    def test_independent_sets_simple(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        batches = g.independent_sets()
        assert ["a"] in batches or "a" in batches[0]
        assert "b" in batches[-1]

    def test_independent_sets_parallel_group(self):
        g = DependencyGraph()
        # a and b are independent; c depends on both
        g.add_dependency("c", "a")
        g.add_dependency("c", "b")
        batches = g.independent_sets()
        first_batch = set(batches[0])
        assert "a" in first_batch or "b" in first_batch

    def test_remove_strategy(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        g.remove_strategy("a")
        assert "a" not in g.all_strategy_ids()
        assert "a" not in g.get_dependencies("b")

    def test_is_ready(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        assert g.is_ready("b", completed={"a"}) is True
        assert g.is_ready("b", completed=set()) is False

    def test_empty_graph_topological_sort(self):
        g = DependencyGraph()
        assert g.topological_sort() == []

    def test_empty_graph_independent_sets(self):
        g = DependencyGraph()
        assert g.independent_sets() == []

    def test_len(self):
        g = DependencyGraph()
        assert len(g) == 0
        g.ensure_node("x")
        assert len(g) == 1

    def test_get_dependencies_unknown(self):
        g = DependencyGraph()
        assert g.get_dependencies("no-such") == frozenset()

    def test_get_dependents_unknown(self):
        g = DependencyGraph()
        assert g.get_dependents("no-such") == frozenset()

    def test_remove_dependency(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        g.remove_dependency("b", "a")
        assert "a" not in g.get_dependencies("b")

    def test_diamond_dependency(self):
        # a → b, a → c, b → d, c → d
        g = DependencyGraph()
        g.add_dependency("b", "a")
        g.add_dependency("c", "a")
        g.add_dependency("d", "b")
        g.add_dependency("d", "c")
        order = g.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")


# ── DependencyValidator ───────────────────────────────────────────────────────

class TestDependencyValidator:
    def test_valid_graph(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        v = DependencyValidator()
        result = v.validate_graph(g, registered_strategy_ids={"a", "b"})
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_strategy_warning(self):
        g = DependencyGraph()
        g.add_dependency("b", "ghost")
        v = DependencyValidator()
        result = v.validate_graph(g, registered_strategy_ids={"b"})
        assert "ghost" in result.missing_strategies
        assert result.warnings  # warning issued but not an error

    def test_validate_single_self_dep(self):
        v = DependencyValidator()
        result = v.validate_single("a", ["a"])
        assert result.is_valid is False

    def test_validate_single_duplicate_warning(self):
        v = DependencyValidator()
        result = v.validate_single("b", ["a", "a"], registered_strategy_ids={"a", "b"})
        assert result.warnings  # duplicate reported as warning

    def test_validate_single_ok(self):
        v = DependencyValidator()
        result = v.validate_single("b", ["a"], registered_strategy_ids={"a", "b"})
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_graph_no_registered_ids(self):
        g = DependencyGraph()
        g.add_dependency("b", "a")
        v = DependencyValidator()
        result = v.validate_graph(g)
        assert result.is_valid is True

    def test_validation_result_add_error_marks_invalid(self):
        r = DependencyValidationResult()
        r.add_error("bad")
        assert r.is_valid is False
        assert "bad" in r.errors

    def test_validation_result_add_warning_stays_valid(self):
        r = DependencyValidationResult()
        r.add_warning("warn")
        assert r.is_valid is True
        assert "warn" in r.warnings


# ── DependencyRegistry ────────────────────────────────────────────────────────

class TestDependencyRegistry:
    def _decl(self, strategy_id="b", depends_on="a"):
        return DependencyDeclaration(
            strategy_id=strategy_id,
            depends_on=depends_on,
            dependency_type=DependencyType.STRATEGY,
        )

    def test_declare_and_retrieve(self):
        reg = DependencyRegistry()
        reg.declare(self._decl())
        deps = reg.get_dependency_ids("b")
        assert "a" in deps

    def test_required_dependency_ids(self):
        reg = DependencyRegistry()
        reg.declare(DependencyDeclaration("b", "a", required=True))
        reg.declare(DependencyDeclaration("b", "c", required=False))
        required = reg.get_required_dependency_ids("b")
        assert "a" in required
        assert "c" not in required

    def test_remove_strategy(self):
        reg = DependencyRegistry()
        reg.declare(self._decl())
        reg.remove_strategy("b")
        assert reg.get_dependency_ids("b") == frozenset()

    def test_all_declarations(self):
        reg = DependencyRegistry()
        reg.declare(self._decl("b", "a"))
        reg.declare(self._decl("c", "a"))
        all_decls = reg.all_declarations()
        assert len(all_decls) == 2

    def test_declare_many(self):
        reg = DependencyRegistry()
        decls = [self._decl("b", "a"), self._decl("c", "b")]
        reg.declare_many(decls)
        assert "a" in reg.get_dependency_ids("b")
        assert "b" in reg.get_dependency_ids("c")


# ── DependencyEngine ──────────────────────────────────────────────────────────

class TestDependencyEngine:
    def test_declare_and_topological_order(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        order = eng.topological_order()
        assert order.index("a") < order.index("b")

    def test_parallel_batches(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        batches = eng.parallel_batches()
        assert "a" in batches[0]
        assert "b" in batches[1]

    def test_cycle_rollback(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        with pytest.raises(CyclicDependencyError):
            eng.declare(DependencyDeclaration("a", "b"))
        # After rollback, "a" should not depend on "b"
        assert "b" not in eng.get_dependencies("a")

    def test_runtime_tracking(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a", required=True))
        eng.reset_cycle()
        assert eng.is_ready("b") is False
        eng.mark_completed("a")
        assert eng.is_ready("b") is True

    def test_reset_cycle_clears_completed(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        eng.mark_completed("a")
        assert eng.is_ready("b") is True
        eng.reset_cycle()
        assert eng.is_ready("b") is False

    def test_ready_to_run_filter(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a", required=True))
        eng.mark_completed("a")
        ready = eng.ready_to_run({"b", "c"})
        assert "b" in ready
        assert "c" in ready  # no deps → always ready

    def test_remove_strategy(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        eng.remove_strategy("a")
        assert "a" not in eng.topological_order()

    def test_validate(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a"))
        result = eng.validate(registered_ids={"a", "b"})
        assert result.is_valid is True

    def test_convenience_market_dependency(self):
        decl = DependencyEngine.market_dependency("strat-x")
        assert decl.strategy_id == "strat-x"
        assert decl.depends_on == "__market_intelligence__"
        assert decl.dependency_type == DependencyType.MARKET_INTELLIGENCE

    def test_convenience_company_dependency(self):
        decl = DependencyEngine.company_dependency("strat-x")
        assert decl.dependency_type == DependencyType.COMPANY_INTELLIGENCE

    def test_convenience_risk_dependency(self):
        decl = DependencyEngine.risk_dependency("strat-x")
        assert decl.dependency_type == DependencyType.RISK

    def test_len(self):
        eng = DependencyEngine()
        assert len(eng) == 0
        eng.declare(DependencyDeclaration("b", "a"))
        assert len(eng) == 2

    def test_no_deps_strategy_always_ready(self):
        eng = DependencyEngine()
        assert eng.is_ready("standalone") is True

    def test_optional_dependency_does_not_block(self):
        eng = DependencyEngine()
        eng.declare(DependencyDeclaration("b", "a", required=False))
        # "a" is optional — "b" is ready even if "a" not completed
        assert eng.is_ready("b") is True
