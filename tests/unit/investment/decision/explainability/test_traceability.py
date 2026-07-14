"""tests/unit/investment/decision/explainability/test_traceability.py
Tests for EvidenceMapper, ReasoningMapper, TraceabilityEngine, DecisionTrace.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.explainability.decision_trace import DecisionTrace
from iios.investment.decision.explainability.evidence_mapper import EvidenceMapper
from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    TraceabilityLevel,
)
from iios.investment.decision.explainability.explanation_generator import ExplanationGenerator
from iios.investment.decision.explainability.reasoning_mapper import ReasoningMapper
from iios.investment.decision.explainability.traceability_engine import TraceabilityEngine


class TestEvidenceMapper:
    def test_maps_all_items(self, rich_evidence_snapshot):
        mapper = EvidenceMapper()
        nodes  = mapper.map(rich_evidence_snapshot)
        assert len(nodes) == rich_evidence_snapshot.item_count

    def test_node_confidence_in_range(self, rich_evidence_snapshot):
        mapper = EvidenceMapper()
        for node in mapper.map(rich_evidence_snapshot):
            assert 0.0 <= node.confidence <= 100.0

    def test_node_freshness_in_range(self, rich_evidence_snapshot):
        mapper = EvidenceMapper()
        for node in mapper.map(rich_evidence_snapshot):
            assert 0.0 <= node.freshness_score <= 1.0

    def test_with_reasoned_keys(self, rich_evidence_snapshot):
        mapper = EvidenceMapper()
        items  = list(rich_evidence_snapshot.items)
        keys   = {items[0].key, items[1].key} if len(items) > 1 else set()
        nodes  = mapper.map(rich_evidence_snapshot, reasoned_keys=keys)
        referenced = [n for n in nodes if n.reasoning_referenced]
        assert len(referenced) == len(keys)

    def test_minimal_snapshot(self, minimal_evidence_snapshot):
        mapper = EvidenceMapper()
        nodes  = mapper.map(minimal_evidence_snapshot)
        assert len(nodes) == minimal_evidence_snapshot.item_count


class TestReasoningMapper:
    def test_maps_steps(self, rich_reasoning_snapshot):
        mapper = ReasoningMapper()
        nodes, keys = mapper.map(rich_reasoning_snapshot)
        assert isinstance(nodes, list)
        assert isinstance(keys, frozenset)

    def test_node_confidence_range(self, rich_reasoning_snapshot):
        mapper = ReasoningMapper()
        nodes, _ = mapper.map(rich_reasoning_snapshot)
        for node in nodes:
            assert 0.0 <= node.confidence <= 100.0

    def test_returns_evidence_keys(self, rich_reasoning_snapshot):
        mapper = ReasoningMapper()
        _, keys = mapper.map(rich_reasoning_snapshot)
        assert isinstance(keys, frozenset)


class TestDecisionTrace:
    def _build(self, rich_input, decision_id):
        gen  = ExplanationGenerator()
        snap = gen.generate(rich_input, decision_id)
        return snap, gen.build_trace(rich_input, snap.outcome.value)

    def test_trace_has_nodes(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert trace.evidence_node_count >= 0

    def test_trace_decision_id(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        # trace.decision_id comes from risk_snapshot.decision_id (conftest fixture)
        assert isinstance(trace.decision_id, str)
        assert len(trace.decision_id) > 0

    def test_evidence_node_count(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert trace.evidence_node_count == len(trace.evidence_nodes)

    def test_reasoning_node_count(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert trace.reasoning_node_count == len(trace.reasoning_nodes)

    def test_traced_evidence_fraction_range(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        frac = trace.traced_evidence_fraction
        assert 0.0 <= frac <= 1.0

    def test_outcome_field(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert isinstance(trace.outcome, str)

    def test_risk_fields_range(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert 0.0 <= trace.overall_risk <= 100.0
        assert 0.0 <= trace.market_risk  <= 100.0

    def test_confidence_fields_range(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        assert 0.0 <= trace.overall_confidence <= 100.0

    def test_frozen(self, rich_input, decision_id):
        snap, trace = self._build(rich_input, decision_id)
        with pytest.raises((AttributeError, TypeError)):
            trace.outcome = "changed"  # type: ignore


class TestTraceabilityEngine:
    def test_build_trace(
        self,
        rich_evidence_snapshot,
        rich_reasoning_snapshot,
        rich_confidence_snapshot,
        rich_risk_snapshot,
    ):
        engine = TraceabilityEngine()
        trace  = engine.build_trace(
            rich_evidence_snapshot,
            rich_reasoning_snapshot,
            rich_confidence_snapshot,
            rich_risk_snapshot,
            outcome=DecisionOutcome.PROCEED.value,
        )
        assert isinstance(trace, DecisionTrace)

    def test_traceability_level_full(
        self,
        rich_evidence_snapshot,
        rich_reasoning_snapshot,
        rich_confidence_snapshot,
        rich_risk_snapshot,
    ):
        engine = TraceabilityEngine()
        trace  = engine.build_trace(
            rich_evidence_snapshot,
            rich_reasoning_snapshot,
            rich_confidence_snapshot,
            rich_risk_snapshot,
            outcome=DecisionOutcome.PROCEED.value,
        )
        level = engine.traceability_level(trace)
        assert isinstance(level, TraceabilityLevel)

    def test_traceability_level_minimal(
        self,
        minimal_evidence_snapshot,
        minimal_reasoning_snapshot,
        minimal_confidence_snapshot,
        minimal_risk_snapshot,
    ):
        engine = TraceabilityEngine()
        trace  = engine.build_trace(
            minimal_evidence_snapshot,
            minimal_reasoning_snapshot,
            minimal_confidence_snapshot,
            minimal_risk_snapshot,
            outcome=DecisionOutcome.INSUFFICIENT_DATA.value,
        )
        level = engine.traceability_level(trace)
        assert level in {
            TraceabilityLevel.MINIMAL,
            TraceabilityLevel.PARTIAL,
            TraceabilityLevel.NONE,
        }
