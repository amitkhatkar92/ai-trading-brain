"""
Test Suite — Self-Learning Ecosystem Phase 3: PGA Category A -> Hypothesis Bridge
====================================================================================
Verifies predictive_gap/pga_learning.py's Category A wiring: registers a
miss as a HypothesisRegistry hypothesis for FUTURE validation, and never
touches any live risk/scanner threshold directly (the underlying evidence
is single-instance and survivorship-biased -- see
self_learning_ecosystem_master_plan.md Phase 3 finding).

Also proves a real, pre-existing bug fix: Category C's
_try_create_hypothesis() was calling HypothesisRegistry.create_hypothesis()
with parameters that don't exist on that method (rationale=, tags=,
classification=HypothesisClassification.PREDICTIVE_SIGNAL which isn't a
valid enum member) -- silently failing every single invocation before
this fix.

T01-T03  Category A creates a real, correctly-classified hypothesis
T04      Category A hypothesis lands in PROPOSED status (not auto-trusted)
T05      Category C (the pre-existing bug) now actually succeeds
T06      execute_actions() routes category A to HYPOTHESIS_CREATED_FOR_VALIDATION
T07      Fail-open: HypothesisRegistry exception does not propagate
T08      Safety: MIN_RR_RATIO is never touched by any of this
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from predictive_gap.pga_learning import (
    LearningAction, TARGET_CALIBRATION, TARGET_HYPOTHESIS_REG,
    _try_create_hypothesis, _try_create_hypothesis_cat_a, execute_actions,
)


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    """Redirect the hypothesis registry to a temp file for test isolation.
    _DEFAULT_REGISTRY_PATH is read fresh inside HypothesisRegistry.__init__
    on every call (not bound at import time), so patching the module
    attribute here safely isolates every registry instantiation made by
    the code under test -- including inside pga_learning.py's own
    functions, which never pass an explicit registry_path (correct for
    real production use, so the test must isolate at this layer instead
    of changing that function's signature just for testability)."""
    import autonomous_research.hypothesis_registry as hr_mod
    monkeypatch.setattr(hr_mod, "_DEFAULT_REGISTRY_PATH", tmp_path / "test_ars_hypothesis_registry.json")
    yield


def _cat_a_action(symbol="RELIANCE", primary_cause="RiskFilter", dna=5, move_pct=6.2):
    return LearningAction(
        action_id="PGA-TEST0001",
        category="A",
        symbol=symbol,
        action_type="calibrate_feature_weight",
        target_system=TARGET_CALIBRATION,
        description="test",
        payload={
            "symbol": symbol,
            "miss_type": "MISSED_WINNER",
            "primary_cause": primary_cause,
            "dna_coverage": dna,
            "daily_return_pct": move_pct,
            "action": "review_threshold",
        },
    )


def _cat_c_action(symbol="TCS"):
    return LearningAction(
        action_id="PGA-TEST0002",
        category="C",
        symbol=symbol,
        action_type="create_hypothesis",
        target_system=TARGET_HYPOTHESIS_REG,
        description="test",
        payload={
            "title": f"Why did {symbol} move without a signal?",
            "research_question": f"What caused {symbol} to move undetected?",
            "symbol": symbol,
            "date": "2026-09-14",
            "return_pct": 4.5,
            "miss_type": "MISSED_WINNER",
            "primary_cause": "PMCI",
            "dna_coverage": 3,
            "action": "create_hypothesis",
        },
    )


class TestCategoryAHypothesisBridge:
    def test_T01_creates_a_real_hypothesis(self):
        """T01: _try_create_hypothesis_cat_a succeeds and persists a hypothesis."""
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry

        ok = _try_create_hypothesis_cat_a(_cat_a_action())
        assert ok is True

        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        all_h = reg.list_all()
        assert len(all_h) == 1
        assert "RELIANCE" in all_h[0].title

    def test_T02_correct_classification_and_priority(self):
        """T02: hypothesis is classified PERFORMANCE_GAP, priority LOW (not auto-trusted)."""
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        from autonomous_research.hypothesis_models import (
            HypothesisClassification, HypothesisPriority,
        )

        _try_create_hypothesis_cat_a(_cat_a_action())
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        h = reg.list_all()[0]
        assert h.classification == HypothesisClassification.PERFORMANCE_GAP
        assert h.priority == HypothesisPriority.LOW

    def test_T03_description_flags_survivorship_bias_caveat(self):
        """T03: the hypothesis text itself warns future readers about the bias."""
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry

        _try_create_hypothesis_cat_a(_cat_a_action())
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        h = reg.list_all()[0]
        assert "must NOT be acted on" in h.description

    def test_T04_lands_in_proposed_status(self):
        """T04: new hypothesis starts in PROPOSED -- not auto-confirmed/trusted."""
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        from autonomous_research.hypothesis_models import HypothesisStatus

        _try_create_hypothesis_cat_a(_cat_a_action())
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        h = reg.list_all()[0]
        assert h.status == HypothesisStatus.PROPOSED


class TestCategoryCBugFix:
    def test_T05_category_c_hypothesis_creation_now_succeeds(self):
        """T05: regression test for the pre-existing bug (wrong kwargs / invalid
        enum member) -- Category C's hypothesis creation must actually work now."""
        ok = _try_create_hypothesis(_cat_c_action())
        assert ok is True


class TestExecuteActionsRouting:
    def test_T06_category_a_routes_to_hypothesis_created_for_validation(self):
        """T06: execute_actions() sets the correct outcome for category A."""
        from predictive_gap.pga_config import PGAConfig

        cfg = PGAConfig(dry_run=False)
        actions = [_cat_a_action()]
        result = execute_actions(actions, cfg, Path("data"))
        assert result[0].outcome == "HYPOTHESIS_CREATED_FOR_VALIDATION"
        assert result[0].scheduled is True

    def test_T07_bridge_exception_is_fail_open(self):
        """T07: any exception inside the bridge is swallowed, not raised."""
        from predictive_gap.pga_config import PGAConfig

        cfg = PGAConfig(dry_run=False)
        actions = [_cat_a_action()]
        with patch(
            "autonomous_research.knowledge_provider.KnowledgeProvider",
            side_effect=RuntimeError("simulated failure"),
        ):
            result = execute_actions(actions, cfg, Path("data"))
        assert result[0].outcome == "HYPOTHESIS_FAILED"
        assert result[0].scheduled is False


class TestSafetyNoLiveGateTouched:
    def test_T08_min_rr_ratio_never_touched(self):
        """T08: the actual live risk gate constant is completely untouched
        by any of this -- Category A only ever writes to the research
        hypothesis registry, never to risk_control."""
        from risk_control.risk_manager_ai import MIN_RR_RATIO as before
        from predictive_gap.pga_config import PGAConfig

        cfg = PGAConfig(dry_run=False)
        execute_actions([_cat_a_action(), _cat_a_action(symbol="INFY")], cfg, Path("data"))

        import importlib
        import risk_control.risk_manager_ai as rm
        importlib.reload(rm)
        assert rm.MIN_RR_RATIO == before == 2.0
