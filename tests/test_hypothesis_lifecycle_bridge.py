"""
tests/test_hypothesis_lifecycle_bridge.py
=============================================
DTA-ARS-HYPOTHESIS-LIFECYCLE-001 -- automated PROPOSED->CONFIRMED/REJECTED
lifecycle for scientific_director/SFR_AUTO origin hypotheses.

T01  PROPOSED with 0 evidence -- no change, nothing to advance yet
T02  PROPOSED with >=1 evidence -- advances all the way to RUNNING
T03  RUNNING + PASSED outcome -- advances to VALIDATED, seeds state
T04  RUNNING + PASSED_WITH_OBSERVATIONS -- also advances to VALIDATED
T05  RUNNING + FAILED, evidence_count below the rejection floor -- stays
     RUNNING (cold-start safeguard: insufficient evidence, not a real reject)
T06  RUNNING + FAILED, evidence_count at/above the floor -- REJECTED
T07  VALIDATED with no prior state (predates this bridge) -- state is
     seeded, no status change on this first observation
T08  VALIDATED, state exists, cooldown not yet elapsed -- no change
T09  VALIDATED, cooldown elapsed but no new evidence -- no change
T10  VALIDATED, cooldown elapsed + new evidence + still PASSED -- CONFIRMED
T11  VALIDATED, cooldown elapsed + new evidence + now FAILED -- REJECTED
     (reconfirm_rejected)
T12  KSL_AUTO origin hypotheses are never touched by this bridge
T13  Never raises on internal error (fail open)
T14  Safety-contract source scan: zero execution_engine/order_manager/
     risk_control/dhan_feed/broker imports
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

import autonomous_research.hypothesis_lifecycle_bridge as bridge
from autonomous_research.hypothesis_models import (
    HypothesisClassification, HypothesisPriority, HypothesisStatus,
)


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    import autonomous_research.hypothesis_registry as hr_mod
    monkeypatch.setattr(hr_mod, "_DEFAULT_REGISTRY_PATH", tmp_path / "test_registry.json")
    monkeypatch.setattr(bridge, "_STATE_PATH", str(tmp_path / "lifecycle_state.json"))
    yield


def _make_registry():
    from autonomous_research.knowledge_provider import KnowledgeProvider
    from autonomous_research.hypothesis_registry import HypothesisRegistry
    return HypothesisRegistry(knowledge_provider=KnowledgeProvider())


def _create_hypothesis(reg, origin="scientific_director", actor="SD"):
    return reg.create_hypothesis(
        title="Test hypothesis", research_question="RQ-TEST", description="d",
        origin=origin, priority=HypothesisPriority.MEDIUM,
        classification=HypothesisClassification.PERFORMANCE_GAP,
        knowledge_gap="g", expected_knowledge_gain="g", validation_method="m",
    )


def _attach_evidence(reg, hyp_id, n=1, actor="ResearchCoordinator"):
    from autonomous_research.hypothesis_models import EvidenceReference, EvidenceType
    import uuid
    for _ in range(n):
        reg.add_evidence(
            hyp_id,
            EvidenceReference(
                evidence_id=f"ev-{hyp_id}-{uuid.uuid4().hex[:8]}", evidence_type=EvidenceType.EXTERNAL,
                description="test evidence", added_at=datetime.now(), added_by=actor,
            ),
            actor=actor,
        )


def _fake_validation(outcome_name: str, total: float = 0.9):
    from autonomous_research.evidence_validator_models import ValidationOutcome
    result = MagicMock()
    result.outcome = ValidationOutcome[outcome_name]
    result.quality_score = MagicMock(total=total)
    return result


def _patched_validate(outcome_name: str):
    return patch(
        "autonomous_research.evidence_validator.EvidenceValidator.validate_hypothesis",
        return_value=_fake_validation(outcome_name),
    )


def test_t01_proposed_no_evidence_no_change():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    summary = bridge.sync_hypothesis_lifecycle()
    assert summary["advanced_to_running"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.PROPOSED


def test_t02_proposed_with_evidence_advances_to_running():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _attach_evidence(reg, h.hypothesis_id, n=1)
    with _patched_validate("FAILED"):  # low evidence -> stays RUNNING after advancing
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["advanced_to_running"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.RUNNING


def test_t03_running_passed_advances_to_validated():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _attach_evidence(reg, h.hypothesis_id, n=1)
    with _patched_validate("PASSED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["validated"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.VALIDATED


def test_t04_running_passed_with_observations_advances_to_validated():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _attach_evidence(reg, h.hypothesis_id, n=1)
    with _patched_validate("PASSED_WITH_OBSERVATIONS"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["validated"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.VALIDATED


def test_t05_failed_below_rejection_floor_stays_running():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _attach_evidence(reg, h.hypothesis_id, n=bridge.MIN_SAMPLE_FOR_REJECTION - 1)
    with _patched_validate("FAILED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["rejected"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.RUNNING


def test_t06_failed_at_rejection_floor_rejects():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _attach_evidence(reg, h.hypothesis_id, n=bridge.MIN_SAMPLE_FOR_REJECTION)
    with _patched_validate("FAILED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["rejected"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.REJECTED


def _advance_to_validated(reg, h, n_evidence=1):
    _attach_evidence(reg, h.hypothesis_id, n=n_evidence)
    with _patched_validate("PASSED"):
        bridge.sync_hypothesis_lifecycle()
    return _make_registry().get(h.hypothesis_id)


def test_t07_validated_no_prior_state_seeds_without_acting():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _advance_to_validated(reg, h)

    # Simulate "predates this bridge": wipe the state file that was just seeded
    import os
    if os.path.exists(bridge._STATE_PATH):
        os.remove(bridge._STATE_PATH)

    with _patched_validate("PASSED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["confirmed"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.VALIDATED


def test_t08_validated_cooldown_not_elapsed_no_change():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _advance_to_validated(reg, h)
    _attach_evidence(_make_registry(), h.hypothesis_id, n=1)  # new evidence, but no time passed
    with _patched_validate("PASSED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["confirmed"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.VALIDATED


def _age_state(hyp_id, days):
    state = bridge._load_state()
    state[hyp_id]["validated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat()
    bridge._save_state(state)


def test_t09_cooldown_elapsed_but_no_new_evidence_no_change():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _advance_to_validated(reg, h)
    _age_state(h.hypothesis_id, bridge.MIN_RECONFIRMATION_DAYS + 1)
    with _patched_validate("PASSED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["confirmed"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.VALIDATED


def test_t10_cooldown_elapsed_plus_new_evidence_plus_passed_confirms():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _advance_to_validated(reg, h)
    _age_state(h.hypothesis_id, bridge.MIN_RECONFIRMATION_DAYS + 1)
    _attach_evidence(_make_registry(), h.hypothesis_id, n=1)
    with _patched_validate("PASSED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["confirmed"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.CONFIRMED


def test_t11_cooldown_elapsed_plus_new_evidence_plus_failed_rejects():
    reg = _make_registry()
    h = _create_hypothesis(reg)
    _advance_to_validated(reg, h)
    _age_state(h.hypothesis_id, bridge.MIN_RECONFIRMATION_DAYS + 1)
    _attach_evidence(_make_registry(), h.hypothesis_id, n=1)
    with _patched_validate("FAILED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["reconfirm_rejected"] == 1
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.REJECTED


def test_t12_ksl_auto_origin_never_touched():
    reg = _make_registry()
    h = _create_hypothesis(reg, origin="KSL_AUTO")
    _attach_evidence(reg, h.hypothesis_id, n=bridge.MIN_SAMPLE_FOR_REJECTION)
    with _patched_validate("FAILED"):
        summary = bridge.sync_hypothesis_lifecycle()
    assert summary["checked"] == 0
    assert _make_registry().get(h.hypothesis_id).status == HypothesisStatus.PROPOSED


def test_t13_never_raises_on_internal_error():
    with patch("autonomous_research.knowledge_provider.KnowledgeProvider",
               side_effect=RuntimeError("boom")):
        result = bridge.sync_hypothesis_lifecycle()
    assert result.get("status") == "ERROR"


def test_t14_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "autonomous_research", "hypothesis_lifecycle_bridge.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
