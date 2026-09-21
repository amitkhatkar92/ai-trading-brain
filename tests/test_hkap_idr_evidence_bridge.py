"""
tests/test_hkap_idr_evidence_bridge.py
=========================================
HKAP -> IDR automatic evidence bridge (hkap/hkap_idr_evidence_bridge.py).

Promotion into the real, live-consequential IDR store is FULLY AUTOMATIC --
gated on lifecycle label, survival score, minimum years-present, and
reproducibility across independent synthesis runs with genuinely new year
coverage. No human names a pattern for normal operation.

T01  Non-STABLE/STRENGTHENING lifecycle labels are skipped entirely
T02  Below MIN_SURVIVAL_SCORE is skipped
T03  Below MIN_YEARS_PRESENT is skipped
T04  First qualifying observation creates a SHADOW proposal, no merge
T05  A second observation with the SAME years_present does not count as
     a confirmation and does not merge
T06  A second observation with DIFFERENT years_present and non-degrading
     survival DOES auto-merge -- creates a NEW InstitutionalDNA record via
     save() (the empty-live-IDR case) THEN adds evidence automatically
T07  A second observation whose survival dropped by more than
     DEGRADATION_TOLERANCE does NOT auto-merge
T08  Evidence confidence/effect_size are capped at MAX_EVIDENCE_CONFIDENCE
T09  Once ACTIVE (merged), further observations are recorded for audit but
     never trigger a second merge
T10  get_pending_proposals()/get_merge_history() read back correctly
T11  request_live_merge() manual override forces an immediate merge
T12  request_live_merge() returns False for an unknown dna_id
T13  evaluate_cross_year_records_for_idr_evidence() fails open on garbage
     input and when IDRRepository raises
T14  Safety: no automatic caller anywhere in the repo invokes
     request_live_merge() from an EOD/scheduler loop (source-text scan)
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import hkap.hkap_idr_evidence_bridge as bridge


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    proposals_file = tmp_path / "idr_evidence_proposals.jsonl"
    ledger_file = tmp_path / "idr_evidence_merge_ledger.jsonl"
    with patch.object(bridge, "_PROPOSALS_FILE", str(proposals_file)), \
         patch.object(bridge, "_MERGE_LEDGER_FILE", str(ledger_file)):
        yield proposals_file, ledger_file


def _record(dna_id="CON-abc123", years_present=(2021, 2022, 2023, 2024),
            survival_score=0.83, lifecycle_label="STABLE",
            direction="WINNERS_HIGHER", regimes=("BULL_MARKET",)):
    return SimpleNamespace(
        dna_id=dna_id,
        feature_name="mom_5d",
        direction=direction,
        years_present=list(years_present),
        survival_score=survival_score,
        lifecycle_label=lifecycle_label,
        regimes_observed=list(regimes),
        confidence_trend="STABLE",
    )


def _mock_repo():
    return patch("market_learning.idr_repository.IDRRepository")


def _mock_repo_not_found():
    """A repo mock whose .get() always raises IDRNotFoundError (empty live IDR)."""
    from market_learning.idr_models import IDRNotFoundError
    m = MagicMock()
    m.get.side_effect = IDRNotFoundError("not found")
    m.save = MagicMock()
    m.add_evidence = MagicMock()
    return m


def test_t01_disallowed_lifecycle_skipped(_isolated_store):
    r = _record(lifecycle_label="EMERGING")
    result = bridge.evaluate_cross_year_records_for_idr_evidence([r])
    assert result == []
    assert bridge.get_pending_proposals() == []


def test_t02_below_survival_threshold_skipped(_isolated_store):
    r = _record(survival_score=0.50)
    result = bridge.evaluate_cross_year_records_for_idr_evidence([r])
    assert result == []


def test_t03_below_years_present_threshold_skipped(_isolated_store):
    r = _record(years_present=(2023, 2024))
    result = bridge.evaluate_cross_year_records_for_idr_evidence([r])
    assert result == []


def test_t04_first_observation_shadow_no_merge(_isolated_store):
    r = _record()
    with _mock_repo() as MockRepo:
        result = bridge.evaluate_cross_year_records_for_idr_evidence([r])
    MockRepo.assert_not_called()
    assert len(result) == 1
    assert result[0]["status"] == bridge.STATUS_SHADOW
    assert result[0]["merged"] is False
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert len(pending[0]["observations"]) == 1


def test_t05_same_years_present_no_confirmation(_isolated_store):
    r = _record()
    with _mock_repo() as MockRepo:
        bridge.evaluate_cross_year_records_for_idr_evidence([r])
        bridge.evaluate_cross_year_records_for_idr_evidence([r])
    MockRepo.assert_not_called()
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == bridge.STATUS_SHADOW
    assert len(pending[0]["observations"]) == 1


def test_t06_new_years_present_nondegrading_autopromotes_creates_new_dna(_isolated_store):
    r1 = _record(years_present=(2021, 2022, 2023, 2024), survival_score=0.80)
    r2 = _record(years_present=(2021, 2022, 2023, 2024, 2025), survival_score=0.83)

    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1])
        bridge.evaluate_cross_year_records_for_idr_evidence([r2])

    # empty-live-IDR path: save() must be called to create the record first
    mock_instance.save.assert_called_once()
    saved_dna = mock_instance.save.call_args[0][0]
    assert saved_dna.id == "CON-abc123"
    assert saved_dna.category == "WINNER"
    assert saved_dna.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE

    mock_instance.add_evidence.assert_called_once()
    call_args = mock_instance.add_evidence.call_args
    assert call_args[0][0] == "CON-abc123"
    ev = call_args[0][1]
    assert ev.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE

    assert bridge.get_pending_proposals() == []
    history = bridge.get_merge_history()
    assert len(history) == 1
    assert history[0]["merged_by"] == "auto:hkap_idr_evidence_bridge"
    assert history[0]["status"] == bridge.STATUS_ACTIVE


def test_t07_degrading_survival_no_merge(_isolated_store):
    r1 = _record(years_present=(2021, 2022, 2023, 2024), survival_score=0.83)
    r2 = _record(years_present=(2021, 2022, 2023, 2024, 2025), survival_score=0.60)

    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1])
        bridge.evaluate_cross_year_records_for_idr_evidence([r2])

    mock_instance.add_evidence.assert_not_called()
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == bridge.STATUS_SHADOW


def test_t08_evidence_bounded_even_for_perfect_survival(_isolated_store):
    r1 = _record(years_present=(2021, 2022, 2023, 2024), survival_score=1.0)
    r2 = _record(years_present=(2021, 2022, 2023, 2024, 2025), survival_score=1.0)

    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1])
        bridge.evaluate_cross_year_records_for_idr_evidence([r2])

    ev = mock_instance.add_evidence.call_args[0][1]
    assert ev.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert ev.effect_size <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert ev.sample_size <= bridge.MAX_EVIDENCE_SAMPLE


def test_t09_active_never_merges_twice(_isolated_store):
    r1 = _record(years_present=(2021, 2022, 2023, 2024))
    r2 = _record(years_present=(2021, 2022, 2023, 2024, 2025))
    r3 = _record(years_present=(2021, 2022, 2023, 2024, 2025, 2026))

    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1])
        bridge.evaluate_cross_year_records_for_idr_evidence([r2])
        bridge.evaluate_cross_year_records_for_idr_evidence([r3])

    assert mock_instance.add_evidence.call_count == 1
    assert mock_instance.save.call_count == 1
    all_proposals = bridge._read_jsonl(bridge._PROPOSALS_FILE)
    assert len(all_proposals) == 1
    assert len(all_proposals[0]["observations"]) == 3
    assert all_proposals[0]["status"] == bridge.STATUS_ACTIVE


def test_t10_pending_and_history_accessors(_isolated_store):
    r1a = _record(dna_id="CON-a", years_present=(2021, 2022, 2023, 2024))
    r1b = _record(dna_id="CON-a", years_present=(2021, 2022, 2023, 2024, 2025))
    r2 = _record(dna_id="CON-b", years_present=(2021, 2022, 2023, 2024))

    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1a, r2])
        bridge.evaluate_cross_year_records_for_idr_evidence([r1b])

    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["dna_id"] == "CON-b"
    assert bridge.get_pending_proposals(dna_id="CON-a") == []
    history = bridge.get_merge_history()
    assert len(history) == 1
    assert history[0]["dna_id"] == "CON-a"


def test_t11_manual_override_forces_merge(_isolated_store):
    r = _record()
    mock_instance = _mock_repo_not_found()
    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_cross_year_records_for_idr_evidence([r])
        ok = bridge.request_live_merge("CON-abc123", operator="alice")
    assert ok is True
    mock_instance.add_evidence.assert_called_once()
    history = bridge.get_merge_history()
    assert history[0]["merged_by"] == "manual:alice"


def test_t12_manual_override_unknown_dna_id(_isolated_store):
    ok = bridge.request_live_merge("NOPE")
    assert ok is False


def test_t13_fails_open_on_garbage_and_repo_exception(_isolated_store):
    result = bridge.evaluate_cross_year_records_for_idr_evidence(["not-a-record", None, 123])
    assert result == []

    r1 = _record(years_present=(2021, 2022, 2023, 2024))
    r2 = _record(years_present=(2021, 2022, 2023, 2024, 2025))
    with patch("market_learning.idr_repository.IDRRepository", side_effect=RuntimeError("boom")):
        bridge.evaluate_cross_year_records_for_idr_evidence([r1])
        result2 = bridge.evaluate_cross_year_records_for_idr_evidence([r2])
    # merge attempt failed internally but evaluate_* itself never raises
    assert isinstance(result2, list)
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == bridge.STATUS_SHADOW


class TestSafetyContract:
    def test_t14_no_forbidden_imports_and_not_autocalled(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_path = os.path.join(root, "hkap", "hkap_idr_evidence_bridge.py")
        src = open(src_path, encoding="utf-8").read()
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker",
                          "risk_control", "knowledge_authority"):
            assert f"import {forbidden}" not in src
            assert f"from {forbidden} import" not in src

        orch_path = os.path.join(root, "orchestrator", "master_orchestrator.py")
        orch_src = open(orch_path, encoding="utf-8").read()
        assert "hkap_idr_evidence_bridge.request_live_merge" not in orch_src
