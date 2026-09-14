"""
Test Suite — Self-Learning Ecosystem Phase 2 (structural prerequisite):
ScientificHypothesis structured subject fields + HypothesisRegistry
get_confirmed_adjustment() bridge accessor.

This is INFRASTRUCTURE ONLY -- no wiring into knowledge_authority/ is
included or tested here (that wiring is a separate, explicitly-approved
contract per this repo's own KDA change workflow). These tests prove the
new accessor is dormant by construction until a hypothesis is BOTH given a
structured subject AND genuinely reaches CONFIRMED status.

T01-T02  New fields default to None, backward-compatible with pre-existing
         hypotheses that predate this field (from_dict on old-shape data)
T03      create_hypothesis() persists subject_type/subject_value/direction
T04      get_confirmed_adjustment() returns 0.0 with no matching hypothesis
T05      ... returns 0.0 when matching hypothesis is NOT CONFIRMED (any
         other status, including VALIDATED just below it)
T06      ... returns a bounded POSITIVE delta for a CONFIRMED POSITIVE match
T07      ... returns a bounded NEGATIVE delta for a CONFIRMED NEGATIVE match
T08      ... averages + clamps across multiple CONFIRMED matches
T09      PGA Category A now populates SYMBOL/subject_value/POSITIVE
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    import autonomous_research.hypothesis_registry as hr_mod
    monkeypatch.setattr(hr_mod, "_DEFAULT_REGISTRY_PATH", tmp_path / "test_registry.json")
    yield


def _make_registry():
    from autonomous_research.knowledge_provider import KnowledgeProvider
    from autonomous_research.hypothesis_registry import HypothesisRegistry
    return HypothesisRegistry(knowledge_provider=KnowledgeProvider())


def _confirm(reg, hypothesis_id, actor="test"):
    from autonomous_research.hypothesis_models import HypothesisStatus, ValidationResult
    from datetime import datetime
    reg.update_status(hypothesis_id, HypothesisStatus.UNDER_REVIEW, actor=actor, reason="r")
    reg.update_status(hypothesis_id, HypothesisStatus.APPROVED, actor=actor, reason="r")
    reg.update_status(hypothesis_id, HypothesisStatus.PLANNED, actor=actor, reason="r")
    reg.update_status(hypothesis_id, HypothesisStatus.RUNNING, actor=actor, reason="r")
    reg.set_validation_result(
        hypothesis_id,
        ValidationResult(
            validated_at=datetime.now(), validated_by=actor, verdict="PASS",
            findings=["ok"], study_ids=[], metrics={}, notes="",
        ),
        actor=actor,
    )
    reg.update_status(hypothesis_id, HypothesisStatus.VALIDATED, actor=actor, reason="r")
    reg.update_status(hypothesis_id, HypothesisStatus.CONFIRMED, actor=actor, reason="r")


def _basic_kwargs(**overrides):
    from autonomous_research.hypothesis_models import HypothesisClassification, HypothesisPriority
    kw = dict(
        title="Test hypothesis",
        research_question="Does X help?",
        description="test",
        origin="test",
        priority=HypothesisPriority.MEDIUM,
        classification=HypothesisClassification.PERFORMANCE_GAP,
        knowledge_gap="test gap",
        expected_knowledge_gain="test gain",
        validation_method="test method",
    )
    kw.update(overrides)
    return kw


class TestBackwardCompatibility:
    def test_T01_new_fields_default_to_none(self):
        reg = _make_registry()
        h = reg.create_hypothesis(**_basic_kwargs())
        assert h.subject_type is None
        assert h.subject_value is None
        assert h.direction is None

    def test_T02_from_dict_handles_pre_existing_shape_without_new_keys(self):
        """T02: a hypothesis dict from BEFORE this field existed (no
        subject_type/subject_value/direction keys at all) parses cleanly."""
        from autonomous_research.hypothesis_models import ScientificHypothesis
        old_shape = {
            "hypothesis_id": "H-OLD-001",
            "title": "Pre-existing hypothesis",
            "research_question": "q",
            "description": "d",
            "origin": "o",
            "origin_study": None,
            "created_at": "2026-08-01T00:00:00",
            "created_by": "system",
            "priority": "MEDIUM",
            "confidence": 0.5,
            "status": "PROPOSED",
            "classification": "MANUAL",
            "supporting_evidence": [],
            "knowledge_gap": "gap",
            "expected_knowledge_gain": "gain",
            "required_data": {},
            "dependencies": [],
            "validation_method": "method",
            "validation_result": None,
            "decision_history": [],
            "last_reviewed": None,
            "notes": [],
            # deliberately NO subject_type/subject_value/direction keys
        }
        h = ScientificHypothesis.from_dict(old_shape)
        assert h.subject_type is None
        assert h.subject_value is None
        assert h.direction is None


class TestCreateHypothesisWithSubject:
    def test_T03_persists_subject_fields(self):
        reg = _make_registry()
        h = reg.create_hypothesis(**_basic_kwargs(
            subject_type="SYMBOL", subject_value="RELIANCE", direction="POSITIVE",
        ))
        fetched = reg.get(h.hypothesis_id)
        assert fetched.subject_type == "SYMBOL"
        assert fetched.subject_value == "RELIANCE"
        assert fetched.direction == "POSITIVE"


class TestGetConfirmedAdjustment:
    def test_T04_no_match_returns_zero(self):
        reg = _make_registry()
        reg.create_hypothesis(**_basic_kwargs(
            subject_type="SYMBOL", subject_value="RELIANCE", direction="POSITIVE",
        ))
        assert reg.get_confirmed_adjustment("SYMBOL", "TCS") == 0.0

    def test_T05_matching_but_not_confirmed_returns_zero(self):
        reg = _make_registry()
        h = reg.create_hypothesis(**_basic_kwargs(
            subject_type="SYMBOL", subject_value="RELIANCE", direction="POSITIVE",
        ))
        # left in PROPOSED -- never confirmed
        assert reg.get_confirmed_adjustment("SYMBOL", "RELIANCE") == 0.0
        # advance to VALIDATED (one step short of CONFIRMED) -- still zero
        from autonomous_research.hypothesis_models import HypothesisStatus, ValidationResult
        from datetime import datetime
        reg.update_status(h.hypothesis_id, HypothesisStatus.UNDER_REVIEW, actor="t", reason="r")
        reg.update_status(h.hypothesis_id, HypothesisStatus.APPROVED, actor="t", reason="r")
        reg.update_status(h.hypothesis_id, HypothesisStatus.PLANNED, actor="t", reason="r")
        reg.update_status(h.hypothesis_id, HypothesisStatus.RUNNING, actor="t", reason="r")
        reg.set_validation_result(
            h.hypothesis_id,
            ValidationResult(validated_at=datetime.now(), validated_by="t", verdict="PASS",
                              findings=[], study_ids=[], metrics={}, notes=""),
            actor="t",
        )
        reg.update_status(h.hypothesis_id, HypothesisStatus.VALIDATED, actor="t", reason="r")
        assert reg.get_confirmed_adjustment("SYMBOL", "RELIANCE") == 0.0

    def test_T06_confirmed_positive_gives_bounded_positive_delta(self):
        reg = _make_registry()
        h = reg.create_hypothesis(**_basic_kwargs(
            subject_type="SYMBOL", subject_value="RELIANCE", direction="POSITIVE",
            confidence=0.8,
        ))
        _confirm(reg, h.hypothesis_id)
        delta = reg.get_confirmed_adjustment("SYMBOL", "RELIANCE", max_delta=0.05)
        assert 0.0 < delta <= 0.05
        assert delta == pytest.approx(0.05 * 0.8)

    def test_T07_confirmed_negative_gives_bounded_negative_delta(self):
        reg = _make_registry()
        h = reg.create_hypothesis(**_basic_kwargs(
            subject_type="SYMBOL", subject_value="INFY", direction="NEGATIVE",
            confidence=1.0,
        ))
        _confirm(reg, h.hypothesis_id)
        delta = reg.get_confirmed_adjustment("SYMBOL", "INFY", max_delta=0.05)
        assert delta == pytest.approx(-0.05)

    def test_T08_averages_and_clamps_multiple_matches(self):
        reg = _make_registry()
        h1 = reg.create_hypothesis(**_basic_kwargs(
            title="H1", subject_type="SYMBOL", subject_value="TCS",
            direction="POSITIVE", confidence=1.0,
        ))
        h2 = reg.create_hypothesis(**_basic_kwargs(
            title="H2", subject_type="SYMBOL", subject_value="TCS",
            direction="POSITIVE", confidence=1.0,
        ))
        _confirm(reg, h1.hypothesis_id)
        _confirm(reg, h2.hypothesis_id)
        delta = reg.get_confirmed_adjustment("SYMBOL", "TCS", max_delta=0.05)
        assert delta == pytest.approx(0.05)  # both maxed out, average = max, clamp is a no-op here


class TestPGACategoryASubjectPopulation:
    def test_T09_category_a_populates_symbol_subject(self):
        from predictive_gap.pga_learning import (
            LearningAction, TARGET_CALIBRATION, _try_create_hypothesis_cat_a,
        )
        action = LearningAction(
            action_id="PGA-T09",
            category="A",
            symbol="WIPRO",
            action_type="calibrate_feature_weight",
            target_system=TARGET_CALIBRATION,
            description="test",
            payload={
                "symbol": "WIPRO", "miss_type": "MISSED_WINNER",
                "primary_cause": "RiskFilter", "dna_coverage": 2,
                "daily_return_pct": 5.0, "action": "review_threshold",
            },
        )
        ok = _try_create_hypothesis_cat_a(action)
        assert ok is True

        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        h = reg.list_all()[0]
        assert h.subject_type == "SYMBOL"
        assert h.subject_value == "WIPRO"
        assert h.direction == "POSITIVE"
