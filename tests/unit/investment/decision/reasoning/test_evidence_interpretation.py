"""tests/unit/investment/decision/reasoning/test_evidence_interpretation.py"""
from __future__ import annotations

import pytest

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.reasoning.context_analyzer import ContextAnalyzer
from iios.investment.decision.reasoning.evidence_interpreter import EvidenceInterpreter
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.relationship_mapper import RelationshipMapper, RelationshipType
from iios.investment.decision.reasoning.signal_interpreter import SignalInterpreter


# ========================= EvidenceInterpreter ===========================

class TestEvidenceInterpreter:
    def test_interpret_snapshot(self, rich_evidence_snapshot):
        interp = EvidenceInterpreter()
        signals, step = interp.interpret_snapshot(rich_evidence_snapshot)
        assert len(signals) == rich_evidence_snapshot.item_count
        assert step.step_type == ReasoningStepType.EVIDENCE_REVIEW

    def test_signals_have_neutral_direction_by_default(self, minimal_evidence_snapshot):
        interp = EvidenceInterpreter()
        signals, _ = interp.interpret_snapshot(minimal_evidence_snapshot)
        assert all(s.direction == SignalDirection.NEUTRAL for s in signals)

    def test_trace_ids_match_evidence(self, rich_evidence_snapshot):
        interp = EvidenceInterpreter()
        signals, _ = interp.interpret_snapshot(rich_evidence_snapshot)
        ev_trace_ids = {i.trace_id for i in rich_evidence_snapshot.items}
        sig_trace_ids = {s.trace_id for s in signals}
        assert sig_trace_ids == ev_trace_ids

    def test_step_cites_all_items(self, rich_evidence_snapshot):
        interp = EvidenceInterpreter()
        _, step = interp.interpret_snapshot(rich_evidence_snapshot)
        assert len(step.evidence_trace_ids) == rich_evidence_snapshot.item_count


# ========================= ContextAnalyzer ===============================

class TestContextAnalyzer:
    def test_positive_dominant(self, positive_signals):
        analyzer = ContextAnalyzer()
        profile, step = analyzer.analyze("INFY", "equity", positive_signals)
        assert profile.dominant_direction == SignalDirection.POSITIVE
        assert profile.positive_signals == len(positive_signals)

    def test_negative_dominant(self, negative_signals):
        analyzer = ContextAnalyzer()
        profile, _ = analyzer.analyze("INFY", "equity", negative_signals)
        assert profile.dominant_direction == SignalDirection.NEGATIVE

    def test_neutral_when_empty(self):
        analyzer = ContextAnalyzer()
        profile, _ = analyzer.analyze("X", "equity", [])
        assert profile.dominant_direction == SignalDirection.NEUTRAL
        assert profile.total_signals == 0

    def test_source_diversity(self, mixed_signals):
        analyzer = ContextAnalyzer()
        profile, _ = analyzer.analyze("X", "equity", mixed_signals)
        assert 0.0 <= profile.source_diversity <= 1.0

    def test_step_type(self, positive_signals):
        analyzer = ContextAnalyzer()
        _, step = analyzer.analyze("X", "equity", positive_signals)
        assert step.step_type == ReasoningStepType.CONTEXT_ANALYSIS

    def test_to_dict(self, mixed_signals):
        analyzer = ContextAnalyzer()
        profile, _ = analyzer.analyze("X", "equity", mixed_signals)
        d = profile.to_dict()
        assert "dominant_direction" in d
        assert "source_diversity" in d


# ========================= SignalInterpreter =============================

class TestSignalInterpreter:
    def test_rsi_overbought(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("rsi_14", 75.0)
        result = interp.interpret(sig)
        assert result.direction == SignalDirection.NEGATIVE

    def test_rsi_oversold(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("rsi_14", 25.0)
        result = interp.interpret(sig)
        assert result.direction == SignalDirection.POSITIVE

    def test_rsi_neutral(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("rsi_14", 50.0)
        result = interp.interpret(sig)
        assert result.direction == SignalDirection.NEUTRAL

    def test_win_rate_positive(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("win_rate", 0.60)
        assert interp.interpret(sig).direction == SignalDirection.POSITIVE

    def test_win_rate_negative(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("win_rate", 0.35)
        assert interp.interpret(sig).direction == SignalDirection.NEGATIVE

    def test_unknown_key_stays_neutral(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("unknown_key_xyz", 999)
        assert interp.interpret(sig).direction == SignalDirection.NEUTRAL

    def test_interpret_all_returns_step(self, mixed_signals):
        interp = SignalInterpreter()
        labelled, step = interp.interpret_all(mixed_signals)
        assert len(labelled) == len(mixed_signals)
        assert step.step_type == ReasoningStepType.SIGNAL_INTERPRETATION

    def test_custom_rule_injected(self, make_signal):
        def custom_rule(v):
            return SignalDirection.POSITIVE, "custom always positive"
        interp = SignalInterpreter(extra_rules={"my_key": custom_rule})
        sig = make_signal("my_key", 0)
        assert interp.interpret(sig).direction == SignalDirection.POSITIVE

    def test_interpretation_text_set(self, make_signal):
        interp = SignalInterpreter()
        sig = make_signal("rsi_14", 75.0)
        result = interp.interpret(sig)
        assert "overbought" in result.interpretation.lower()


# ========================= RelationshipMapper ============================

class TestRelationshipMapper:
    def test_same_key_same_direction_corroborating(self, make_signal):
        mapper = RelationshipMapper()
        sigs = [
            make_signal("rsi_14", 75.0, SignalDirection.NEGATIVE, EvidenceSourceType.MARKET),
            make_signal("rsi_14", 78.0, SignalDirection.NEGATIVE, EvidenceSourceType.MARKET),
        ]
        rmap, step = mapper.map(sigs)
        assert rmap.corroborating_count >= 1

    def test_same_key_opposite_direction_contradicting(self, make_signal):
        mapper = RelationshipMapper()
        sigs = [
            make_signal("pe_ratio", 10.0, SignalDirection.POSITIVE, EvidenceSourceType.COMPANY),
            make_signal("pe_ratio", 50.0, SignalDirection.NEGATIVE, EvidenceSourceType.COMPANY),
        ]
        rmap, _ = mapper.map(sigs)
        assert rmap.contradicting_count >= 1

    def test_empty_signals(self):
        mapper = RelationshipMapper()
        rmap, _ = mapper.map([])
        assert len(rmap.relationships) == 0

    def test_step_type(self, mixed_signals):
        mapper = RelationshipMapper()
        _, step = mapper.map(mixed_signals)
        assert step.step_type == ReasoningStepType.RELATIONSHIP_MAPPING

    def test_to_dict(self, mixed_signals):
        mapper = RelationshipMapper()
        rmap, _ = mapper.map(mixed_signals)
        d = rmap.to_dict()
        assert "corroborating" in d
        assert "contradicting" in d

    def test_conflict_fraction_range(self, mixed_signals):
        mapper = RelationshipMapper()
        rmap, _ = mapper.map(mixed_signals)
        assert 0.0 <= rmap.conflict_fraction <= 1.0
