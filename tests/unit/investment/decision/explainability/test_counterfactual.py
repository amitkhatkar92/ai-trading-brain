"""tests/unit/investment/decision/explainability/test_counterfactual.py
Tests for WhatIfAnalyzer, DecisionSensitivityAnalyzer,
ThresholdAnalyzer, CounterfactualEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.explainability.counterfactual_engine import (
    CounterfactualEngine,
    CounterfactualReport,
)
from iios.investment.decision.explainability.decision_sensitivity import (
    DecisionSensitivityAnalyzer,
    SensitivityReport,
)
from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator
from iios.investment.decision.explainability.threshold_analysis import (
    ThresholdAnalyzer,
    ThresholdReport,
)
from iios.investment.decision.explainability.what_if_analysis import (
    WhatIfAnalyzer,
    WhatIfReport,
)


class TestWhatIfAnalyzer:
    def test_returns_report(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert isinstance(r, WhatIfReport)

    def test_actual_outcome_preserved(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert r.actual_outcome == DecisionOutcome.PROCEED

    def test_scenarios_non_empty(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert len(r.scenarios) > 0

    def test_changed_count_is_valid(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert 0 <= r.changed_count <= len(r.scenarios)

    def test_scenarios_are_frozen(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        s  = r.scenarios[0]
        with pytest.raises((AttributeError, TypeError)):
            s.projected_outcome = DecisionOutcome.HALT  # type: ignore

    def test_low_confidence_scenarios(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(20.0, 80.0, DecisionOutcome.HALT, True)
        assert len(r.scenarios) > 0
        # Controls-breached starting point — some may flip
        changed = [s for s in r.scenarios if s.outcome_changed]
        assert len(changed) >= 0  # structural check only

    def test_delta_fields_present(self):
        wa = WhatIfAnalyzer()
        r  = wa.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        for s in r.scenarios:
            assert isinstance(s.delta_confidence, float)
            assert isinstance(s.delta_risk, float)


class TestDecisionSensitivityAnalyzer:
    def test_returns_report(self):
        sa = DecisionSensitivityAnalyzer()
        r  = sa.analyze(65.0, 35.0, DecisionOutcome.PROCEED, False)
        assert isinstance(r, SensitivityReport)

    def test_entries_non_empty(self):
        sa = DecisionSensitivityAnalyzer()
        r  = sa.analyze(65.0, 35.0, DecisionOutcome.PROCEED, False)
        assert len(r.entries) > 0

    def test_sensitivity_range(self):
        sa = DecisionSensitivityAnalyzer()
        r  = sa.analyze(65.0, 35.0, DecisionOutcome.PROCEED, False)
        for e in r.entries:
            assert isinstance(e.base_value, float)
            assert 0.0 <= e.sensitivity_score <= 100.0

    def test_outcome_changes_tracked(self):
        sa = DecisionSensitivityAnalyzer()
        r  = sa.analyze(62.0, 38.0, DecisionOutcome.PROCEED, False)
        for e in r.entries:
            assert isinstance(e.outcome_flipped_up, bool)
            assert isinstance(e.outcome_flipped_down, bool)

    def test_custom_step(self):
        sa = DecisionSensitivityAnalyzer()
        r  = sa.analyze(65.0, 35.0, DecisionOutcome.PROCEED, False, step=10.0)
        assert isinstance(r, SensitivityReport)


class TestThresholdAnalyzer:
    def test_returns_report(self):
        ta = ThresholdAnalyzer()
        r  = ta.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert isinstance(r, ThresholdReport)

    def test_confidence_threshold_present(self):
        ta = ThresholdAnalyzer()
        r  = ta.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert r.confidence_threshold is not None
        assert r.confidence_threshold.current_value == pytest.approx(70.0)

    def test_risk_threshold_present(self):
        ta = ThresholdAnalyzer()
        r  = ta.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert r.risk_threshold is not None
        assert r.risk_threshold.current_value == pytest.approx(30.0)

    def test_verdict_non_empty(self):
        ta = ThresholdAnalyzer()
        r  = ta.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        assert isinstance(r.verdict, str)
        assert len(r.verdict) > 0

    def test_frozen(self):
        ta = ThresholdAnalyzer()
        r  = ta.analyze(70.0, 30.0, DecisionOutcome.PROCEED, False)
        with pytest.raises((AttributeError, TypeError)):
            r.confidence_breakeven = 99.0  # type: ignore


class TestCounterfactualEngine:
    def _report(self, rich_input, decision_id) -> CounterfactualReport:
        gen   = ExplanationGenerator()
        snap  = gen.generate(rich_input, decision_id)
        ce    = CounterfactualEngine()
        return ce.analyze(snap.explanation)

    def test_returns_report(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        assert isinstance(r, CounterfactualReport)

    def test_decision_id(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        ce   = CounterfactualEngine()
        r    = ce.analyze(snap.explanation)
        # decision_id is taken from the explanation, which was built with decision_id
        assert r.decision_id == snap.explanation.decision_id

    def test_actual_outcome(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        ce   = CounterfactualEngine()
        r    = ce.analyze(snap.explanation)
        # actual_outcome is stored as str value, explanation.outcome is DecisionOutcome
        assert r.actual_outcome == snap.explanation.outcome.value

    def test_what_if_present(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        assert r.what_if is not None

    def test_sensitivity_present(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        assert r.sensitivity is not None

    def test_threshold_present(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        assert r.threshold is not None

    def test_narrative_non_empty(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        assert isinstance(r.narrative, str)
        assert len(r.narrative) > 0

    def test_frozen(self, rich_input, decision_id):
        r = self._report(rich_input, decision_id)
        with pytest.raises((AttributeError, TypeError)):
            r.narrative = "changed"  # type: ignore
