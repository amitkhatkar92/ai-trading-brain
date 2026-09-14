"""
tests/test_kda_phase2_bridge.py
=================================
Self-Learning Ecosystem Phase 2 — KDA wiring (approved contract).

Wires HypothesisRegistry.get_confirmed_adjustment() into
knowledge_authority/knowledge_decision_authority.py::_compute_authority(),
as a bounded +/-0.05 nudge to the existing `relevance` component only.

Never touches evidence_state, _determine_decision()'s categorical
BUY/SELL/HOLD/WAIT path, or any other component. Fail-open. Dormant
today (no CONFIRMED hypothesis exists in production with subject fields
set) -- these tests fabricate a CONFIRMED hypothesis in an isolated
registry to prove the bounded, wired behaviour when one DOES exist.

T01  Zero effect when no CONFIRMED hypothesis exists for the symbol
     (current real-world state)
T02  Bounded positive nudge from a fabricated CONFIRMED POSITIVE match
T03  Nudge is clamped -- relevance never leaves [0.1, 1.0]
T04  Fail-open: HypothesisRegistry raising leaves relevance unaffected
T05  composite_authority stays within [0, 1] with the nudge applied
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from tests.test_kda_001 import KDA, _bm, _obs


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    import autonomous_research.hypothesis_registry as hr_mod
    monkeypatch.setattr(hr_mod, "_DEFAULT_REGISTRY_PATH", tmp_path / "test_registry.json")
    yield


def _confirmed_hypothesis(symbol: str, direction: str, confidence: float = 1.0):
    """Create + fully confirm a hypothesis for `symbol` in the isolated registry."""
    from autonomous_research.hypothesis_models import (
        HypothesisClassification, HypothesisPriority, HypothesisStatus, ValidationResult,
    )
    from autonomous_research.hypothesis_registry import HypothesisRegistry
    from autonomous_research.knowledge_provider import KnowledgeProvider

    reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
    h = reg.create_hypothesis(
        title="Test hypothesis",
        research_question="Does X help?",
        description="test",
        origin="test",
        priority=HypothesisPriority.MEDIUM,
        classification=HypothesisClassification.PERFORMANCE_GAP,
        knowledge_gap="test gap",
        expected_knowledge_gain="test gain",
        validation_method="test method",
        subject_type="SYMBOL",
        subject_value=symbol,
        direction=direction,
        confidence=confidence,
    )
    actor = "test"
    reg.update_status(h.hypothesis_id, HypothesisStatus.UNDER_REVIEW, actor=actor, reason="r")
    reg.update_status(h.hypothesis_id, HypothesisStatus.APPROVED, actor=actor, reason="r")
    reg.update_status(h.hypothesis_id, HypothesisStatus.PLANNED, actor=actor, reason="r")
    reg.update_status(h.hypothesis_id, HypothesisStatus.RUNNING, actor=actor, reason="r")
    reg.set_validation_result(
        h.hypothesis_id,
        ValidationResult(
            validated_at=datetime.now(), validated_by=actor, verdict="PASS",
            findings=["ok"], study_ids=[], metrics={}, notes="",
        ),
        actor=actor,
    )
    reg.update_status(h.hypothesis_id, HypothesisStatus.VALIDATED, actor=actor, reason="r")
    reg.update_status(h.hypothesis_id, HypothesisStatus.CONFIRMED, actor=actor, reason="r")
    return h


class TestKDAPhase2Bridge:
    def test_T01_zero_effect_with_no_confirmed_hypothesis(self):
        """T01: empty (isolated) registry -> byte-identical relevance/composite."""
        rec = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=50.0))
        c = rec.authority_components
        expected_relevance = min(max(7.0 / 10.0, 0.1), 1.0)  # scanner_confidence=7.0 default
        assert c.relevance == pytest.approx(expected_relevance)

    def test_T02_bounded_positive_nudge_from_confirmed_match(self):
        """T02: a CONFIRMED POSITIVE hypothesis for this exact symbol nudges
        relevance up by max_delta * confidence, bounded to +0.05."""
        baseline = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=50.0))
        base_relevance = baseline.authority_components.relevance

        _confirmed_hypothesis("RELIANCE", "POSITIVE", confidence=0.8)
        rec = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=50.0))
        c = rec.authority_components

        delta = c.relevance - base_relevance
        assert 0.0 < delta <= 0.05
        assert delta == pytest.approx(0.05 * 0.8)

    def test_T03_relevance_never_leaves_bounds(self):
        """T03: even with a maxed-out CONFIRMED match, relevance stays <= 1.0."""
        _confirmed_hypothesis("RELIANCE", "POSITIVE", confidence=1.0)
        # scanner_confidence=10.0 -> relevance already at its 1.0 ceiling
        rec = KDA.evaluate(_obs(symbol="RELIANCE", scanner_confidence=10.0), behaviour=_bm(ess=50.0))
        assert rec.authority_components.relevance <= 1.0

        # A NEGATIVE match at the lowest scanner confidence must not push below 0.1.
        _confirmed_hypothesis("TCS", "NEGATIVE", confidence=1.0)
        rec2 = KDA.evaluate(_obs(symbol="TCS", scanner_confidence=0.0), behaviour=_bm(ess=50.0))
        assert rec2.authority_components.relevance >= 0.1

    def test_T04_fail_open_on_registry_exception(self):
        """T04: HypothesisRegistry raising leaves relevance exactly at its
        pre-bridge value (fail-open, byte-identical to no-bridge behaviour)."""
        baseline = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=50.0))
        base_relevance = baseline.authority_components.relevance

        with patch(
            "autonomous_research.hypothesis_registry.HypothesisRegistry",
            side_effect=RuntimeError("boom"),
        ):
            rec = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=50.0))
        assert rec.authority_components.relevance == pytest.approx(base_relevance)

    def test_T05_composite_authority_stays_bounded(self):
        """T05: composite_authority remains in [0, 1] with the nudge applied."""
        _confirmed_hypothesis("RELIANCE", "POSITIVE", confidence=1.0)
        rec = KDA.evaluate(_obs(symbol="RELIANCE"), behaviour=_bm(ess=150.0))
        assert 0.0 <= rec.knowledge_authority <= 1.0
