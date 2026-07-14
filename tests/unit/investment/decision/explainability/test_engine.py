"""tests/unit/investment/decision/explainability/test_engine.py
Tests for DecisionExplainabilityEngine (lifecycle, sync/async explain,
query API, caching, stats, health, custom template).
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from iios.investment.decision.explainability.decision_explainability_engine import (
    DecisionExplainabilityEngine,
)
from iios.investment.decision.explainability.decision_narrative import (
    DecisionNarrative,
    NarrativeReport,
    NarrativeTemplate,
)
from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    ExplainabilityStatus,
    ExplanationFormat,
)
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.explanation_statistics import ExplanationStatistics


# ─── lifecycle ────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_start_stop(self):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.stop()

    def test_start_sets_ready(self):
        engine = DecisionExplainabilityEngine()
        engine.start()
        h = engine.health()
        # status may advance to GENERATING during explain, but starts as READY
        assert h.status in {ExplainabilityStatus.READY, ExplainabilityStatus.INITIALIZING}
        engine.stop()

    def test_explain_after_stop_raises(self, rich_input):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.stop()
        d_id = str(uuid.uuid4())
        with pytest.raises(RuntimeError):
            engine.explain_sync(
                rich_input.evidence_snapshot,
                rich_input.reasoning_snapshot,
                rich_input.confidence_snapshot,
                rich_input.risk_snapshot,
                d_id,
            )


# ─── explain_sync ─────────────────────────────────────────────────────────────

class TestExplainSync:
    def test_returns_snapshot(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        engine.stop()
        assert isinstance(snap, ExplanationSnapshot)

    def test_decision_id_used(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        engine.stop()
        assert snap.decision_id == decision_id

    def test_auto_generates_decision_id(self, rich_input):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
        )
        engine.stop()
        assert snap.decision_id is not None

    def test_score_in_range(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        engine.stop()
        assert 0.0 <= snap.explainability_score <= 100.0

    def test_outcome_valid(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        engine.stop()
        assert snap.outcome in list(DecisionOutcome)

    def test_minimal_input(self, minimal_input):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            minimal_input.evidence_snapshot,
            minimal_input.reasoning_snapshot,
            minimal_input.confidence_snapshot,
            minimal_input.risk_snapshot,
        )
        engine.stop()
        assert snap is not None


# ─── async explain ────────────────────────────────────────────────────────────

class TestExplainAsync:
    def test_async_returns_same_type(self, rich_input, decision_id):
        async def run():
            engine = DecisionExplainabilityEngine()
            engine.start()
            snap = await engine.explain(
                rich_input.evidence_snapshot,
                rich_input.reasoning_snapshot,
                rich_input.confidence_snapshot,
                rich_input.risk_snapshot,
                decision_id,
            )
            engine.stop()
            return snap

        snap = asyncio.run(run())
        assert isinstance(snap, ExplanationSnapshot)

    def test_async_decision_id(self, rich_input, decision_id):
        async def run():
            engine = DecisionExplainabilityEngine()
            engine.start()
            snap = await engine.explain(
                rich_input.evidence_snapshot,
                rich_input.reasoning_snapshot,
                rich_input.confidence_snapshot,
                rich_input.risk_snapshot,
                decision_id,
            )
            engine.stop()
            return snap

        snap = asyncio.run(run())
        assert snap.decision_id == decision_id


# ─── query API ────────────────────────────────────────────────────────────────

class TestQueryAPI:
    def _engine_with_snap(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        return engine, snap

    def test_get_snapshot(self, rich_input, decision_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        found = engine.get_snapshot(snap.snapshot_id)
        assert found is snap
        engine.stop()

    def test_get_latest(self, rich_input, decision_id, subject_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        found = engine.get_latest(subject_id)
        assert found is snap
        engine.stop()

    def test_get_history(self, rich_input, decision_id, subject_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        history = engine.get_history(subject_id)
        assert snap in history
        engine.stop()

    def test_get_by_decision(self, rich_input, decision_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        found = engine.get_by_decision(decision_id)
        assert found is snap
        engine.stop()

    def test_unknown_snapshot_returns_none(self, rich_input, decision_id):
        engine, _ = self._engine_with_snap(rich_input, decision_id)
        assert engine.get_snapshot("nonexistent-id") is None
        engine.stop()

    def test_unknown_subject_returns_none(self, rich_input, decision_id):
        engine, _ = self._engine_with_snap(rich_input, decision_id)
        assert engine.get_latest("NONEXISTENT") is None
        engine.stop()

    def test_outcome_series(self, rich_input, decision_id, subject_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        series = engine.outcome_series(subject_id)
        assert len(series) >= 1
        engine.stop()

    def test_score_series(self, rich_input, decision_id, subject_id):
        engine, snap = self._engine_with_snap(rich_input, decision_id)
        series = engine.score_series(subject_id)
        assert len(series) >= 1
        engine.stop()


# ─── stats ───────────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_after_explain(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        s = engine.stats()
        assert isinstance(s, ExplanationStatistics)
        assert s.total_explanations >= 1
        engine.stop()

    def test_stats_successful_increments(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        s = engine.stats()
        assert s.successful >= 1
        engine.stop()


# ─── health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_after_start(self):
        engine = DecisionExplainabilityEngine()
        engine.start()
        h = engine.health()
        assert h.status in {ExplainabilityStatus.READY, ExplainabilityStatus.GENERATING}
        engine.stop()

    def test_health_total_updates(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        h = engine.health()
        assert h.total_generations >= 1
        engine.stop()

    def test_health_is_healthy_after_success(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        h = engine.health()
        assert h.is_healthy
        engine.stop()


# ─── views ────────────────────────────────────────────────────────────────────

class TestViewAPI:
    def _snap(self, engine, rich_input, decision_id):
        return engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )

    def test_executive_view(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = self._snap(engine, rich_input, decision_id)
        v    = engine.executive_view(snap)
        assert v.decision_id == decision_id
        engine.stop()

    def test_analyst_view(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = self._snap(engine, rich_input, decision_id)
        v    = engine.analyst_view(snap)
        assert v.decision_id == decision_id
        engine.stop()

    def test_developer_view(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = self._snap(engine, rich_input, decision_id)
        v    = engine.developer_view(snap)
        assert v.decision_id == decision_id
        engine.stop()


# ─── formatting ──────────────────────────────────────────────────────────────

class TestFormatting:
    def test_format_dict(self, rich_input, decision_id):
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        d = engine.format(snap, ExplanationFormat.DICT)
        assert isinstance(d, dict)
        engine.stop()

    def test_format_json(self, rich_input, decision_id):
        import json
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        j = engine.format(snap, ExplanationFormat.JSON)
        parsed = json.loads(j)
        assert isinstance(parsed, dict)
        engine.stop()


# ─── counterfactual ──────────────────────────────────────────────────────────

class TestCounterfactual:
    def test_counterfactual_returns_report(self, rich_input, decision_id):
        from iios.investment.decision.explainability.counterfactual_engine import (
            CounterfactualReport,
        )
        engine = DecisionExplainabilityEngine()
        engine.start()
        snap = engine.explain_sync(
            rich_input.evidence_snapshot,
            rich_input.reasoning_snapshot,
            rich_input.confidence_snapshot,
            rich_input.risk_snapshot,
            decision_id,
        )
        r = engine.counterfactual(snap)
        assert isinstance(r, CounterfactualReport)
        engine.stop()
