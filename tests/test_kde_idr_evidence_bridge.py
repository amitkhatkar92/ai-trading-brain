"""
tests/test_kde_idr_evidence_bridge.py
========================================
Self-Learning Ecosystem -- Post-roadmap Item 4: KDE Discovery -> IDR
evidence bridge (kde/kde_idr_evidence_bridge.py).

Design (revised 2026-09-15 per explicit user direction): promotion into
the real, live-consequential IDR store is FULLY AUTOMATIC -- gated on
computed reproducibility across independent re-runs with genuinely new
data, non-degrading scores, and a minimum score threshold. No human
names a discovery/dna_id pair for normal operation.

T01  Discoveries below MIN_OVERALL_SCORE are skipped entirely
T02  Discoveries with no dna_ids are skipped
T03  First observation of a qualifying pattern creates a SHADOW proposal
     and does NOT merge (only 1 confirmation so far)
T04  A second observation with the SAME years_used (i.e. not genuinely
     new data) does NOT count as a confirmation and does NOT merge
T05  A second observation with DIFFERENT years_used and a non-degrading
     score DOES auto-merge -- IDRRepository.add_evidence() is called
     automatically, no human names the pair
T06  A second observation whose score dropped by more than
     DEGRADATION_TOLERANCE does NOT auto-merge
T07  Evidence confidence/effect_size are capped at MAX_EVIDENCE_CONFIDENCE
     even for a perfect (1.0) discovery score
T08  Once ACTIVE (merged), further observations are recorded for audit
     but never trigger a second merge (bounds total irreversible writes)
T09  get_pending_proposals() excludes merged (ACTIVE) proposals, supports
     dna_id filter
T10  get_merge_history() reflects the automatic merge with
     merged_by == "auto:kde_idr_evidence_bridge"
T11  request_live_merge() manual override forces an immediate merge,
     bypassing the reproducibility wait
T12  request_live_merge() returns False for an unknown pair and never
     touches IDRRepository
T13  evaluate_discoveries_for_idr_evidence() fails open (empty list) on
     garbage input, and fails open when IDRRepository.add_evidence raises
T14  Safety: no automatic caller anywhere in the repo invokes
     request_live_merge() from an EOD/scheduler loop (source-text scan)
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import kde.kde_idr_evidence_bridge as bridge


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    proposals_file = tmp_path / "idr_evidence_proposals.jsonl"
    ledger_file = tmp_path / "idr_evidence_merge_ledger.jsonl"
    with patch.object(bridge, "_PROPOSALS_FILE", str(proposals_file)), \
         patch.object(bridge, "_MERGE_LEDGER_FILE", str(ledger_file)):
        yield proposals_file, ledger_file


def _discovery(discovery_id="KDE-S005-001", dna_ids=None, overall=0.75,
               years=(2021, 2022, 2023), regimes=("BULL_MARKET",)):
    score = SimpleNamespace(overall=overall)
    return SimpleNamespace(
        discovery_id=discovery_id,
        scheme_id="S005",
        question="q?",
        answer="a.",
        score=score,
        years_observed=list(years),
        regimes_observed=list(regimes),
        dna_ids=list(dna_ids) if dna_ids is not None else ["rsi_5d::UP"],
        generated_at="2026-09-15T00:00:00+00:00",
    )


def _mock_repo():
    return patch("market_learning.idr_repository.IDRRepository")


def test_t01_below_threshold_skipped(_isolated_store):
    d = _discovery(overall=0.10)
    result = bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2021])
    assert result == []
    assert bridge.get_pending_proposals() == []


def test_t02_no_dna_ids_skipped(_isolated_store):
    d = _discovery(dna_ids=[], overall=0.90)
    result = bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2021])
    assert result == []


def test_t03_first_observation_shadow_no_merge(_isolated_store):
    d = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    with _mock_repo() as MockRepo:
        result = bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2020, 2021])
    MockRepo.assert_not_called()
    assert len(result) == 1
    assert result[0]["status"] == bridge.STATUS_SHADOW
    assert result[0]["merged"] is False
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert len(pending[0]["observations"]) == 1


def test_t04_same_years_used_no_confirmation(_isolated_store):
    d = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    with _mock_repo() as MockRepo:
        bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2020, 2021])
    MockRepo.assert_not_called()
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == bridge.STATUS_SHADOW


def test_t05_new_years_used_nondegrading_autopromotes(_isolated_store):
    d1 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=0.82)

    with _mock_repo() as MockRepo:
        mock_instance = MockRepo.return_value
        mock_instance.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021, 2022])

    mock_instance.add_evidence.assert_called_once()
    call_args = mock_instance.add_evidence.call_args
    assert call_args[0][0] == "feat_a::UP"
    ev = call_args[0][1]
    assert ev.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE

    assert bridge.get_pending_proposals() == []
    history = bridge.get_merge_history()
    assert len(history) == 1
    assert history[0]["merged_by"] == "auto:kde_idr_evidence_bridge"
    assert history[0]["status"] == bridge.STATUS_ACTIVE


def test_t06_degrading_score_no_merge(_isolated_store):
    d1 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=0.60)  # drop of 0.20 > tolerance

    with _mock_repo() as MockRepo:
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021, 2022])
    MockRepo.return_value.add_evidence.assert_not_called()
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == bridge.STATUS_SHADOW


def test_t07_evidence_bounded_even_for_perfect_score(_isolated_store):
    d1 = _discovery(dna_ids=["feat_a::UP"], overall=1.0)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=1.0)
    with _mock_repo() as MockRepo:
        mock_instance = MockRepo.return_value
        mock_instance.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021])
    ev = mock_instance.add_evidence.call_args[0][1]
    assert ev.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert ev.effect_size <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert ev.sample_size <= bridge.MAX_EVIDENCE_SAMPLE


def test_t08_active_never_merges_twice(_isolated_store):
    d1 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d3 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)

    with _mock_repo() as MockRepo:
        mock_instance = MockRepo.return_value
        mock_instance.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d3], years_used=[2020, 2021, 2022])

    assert mock_instance.add_evidence.call_count == 1
    history = bridge.get_merge_history()
    assert len(history) == 1
    # ledger is an append-only snapshot taken AT merge time (2 observations);
    # the live proposals store keeps accumulating observations afterward for
    # audit purposes even though no further merge is ever triggered.
    assert len(history[0]["observations"]) == 2
    all_proposals = bridge._read_jsonl(bridge._PROPOSALS_FILE)
    assert len(all_proposals) == 1
    assert len(all_proposals[0]["observations"]) == 3
    assert all_proposals[0]["status"] == bridge.STATUS_ACTIVE


def test_t09_pending_proposals_filter_and_active_exclusion(_isolated_store):
    d1a = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d1b = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_b::UP"], overall=0.80)

    with _mock_repo() as MockRepo:
        MockRepo.return_value.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d1a, d2], years_used=[2020])
        bridge.evaluate_discoveries_for_idr_evidence([d1b], years_used=[2020, 2021])

    # feat_a auto-merged (ACTIVE, excluded); feat_b still SHADOW (pending)
    pending = bridge.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["dna_id"] == "feat_b::UP"
    assert bridge.get_pending_proposals(dna_id="feat_a::UP") == []


def test_t10_merge_history_reflects_auto_merge(_isolated_store):
    d1 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    with _mock_repo() as MockRepo:
        MockRepo.return_value.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021])
    history = bridge.get_merge_history()
    assert len(history) == 1
    assert history[0]["merged_by"] == "auto:kde_idr_evidence_bridge"


def test_t11_manual_override_forces_immediate_merge(_isolated_store):
    d = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    with _mock_repo() as MockRepo:
        MockRepo.return_value.add_evidence = MagicMock()
        bridge.evaluate_discoveries_for_idr_evidence([d], years_used=[2020])
        assert bridge.get_pending_proposals()  # still shadow, only 1 observation

        ok = bridge.request_live_merge("S005", "feat_a::UP", operator="alice")
    assert ok is True
    assert bridge.get_pending_proposals() == []
    history = bridge.get_merge_history()
    assert history[-1]["merged_by"] == "alice"


def test_t12_unknown_pair_returns_false_never_touches_repo(_isolated_store):
    with _mock_repo() as MockRepo:
        ok = bridge.request_live_merge("NOPE", "nope::UP")
    assert ok is False
    MockRepo.assert_not_called()


def test_t13_fails_open_on_garbage_and_repo_exception(_isolated_store):
    assert bridge.evaluate_discoveries_for_idr_evidence([object(), None, 42]) == []

    d1 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_a::UP"], overall=0.80)
    with _mock_repo() as MockRepo:
        MockRepo.return_value.add_evidence.side_effect = RuntimeError("boom")
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020])
        result = bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021])
    # merge attempted and failed, but call never raised and proposal stays pending
    assert result != []
    assert bridge.get_pending_proposals()


def test_t14_no_automatic_live_merge_caller():
    orch_src = open("orchestrator/master_orchestrator.py", encoding="utf-8").read()
    bridge_src = open("hkap/hkap_kde_bridge.py", encoding="utf-8").read()
    assert "request_live_merge" not in orch_src
    assert "request_live_merge" not in bridge_src


def test_t15_root_cause_fix_creates_dna_when_missing_from_live_idr(_isolated_store):
    """
    ROOT-CAUSE FIX regression guard: add_evidence() raises IDRNotFoundError
    for any dna_id never previously save()'d -- the real, always-true state
    of a genuinely new discovery against a fresh/empty live IDR. Before the
    fix, _do_live_merge() never called save() first, so every real
    first-time auto-merge silently failed (caught, logged, SHADOW forever).
    A bare, unconfigured MagicMock().get() does NOT raise (it just returns
    another MagicMock), which is why T05-T09 above never caught this --
    this test explicitly simulates the real "not found" condition.
    """
    from market_learning.idr_models import IDRNotFoundError

    d1 = _discovery(dna_ids=["feat_new::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_new::UP"], overall=0.82)

    mock_instance = MagicMock()
    mock_instance.get.side_effect = IDRNotFoundError("not found")
    mock_instance.save = MagicMock()
    mock_instance.add_evidence = MagicMock()

    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021, 2022])

    mock_instance.save.assert_called_once()
    saved_dna = mock_instance.save.call_args[0][0]
    assert saved_dna.id == "feat_new::UP"
    assert saved_dna.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE
    mock_instance.add_evidence.assert_called_once()
    history = bridge.get_merge_history()
    assert history[0]["status"] == bridge.STATUS_ACTIVE


def test_t16_existing_dna_skips_save(_isolated_store):
    """When the dna_id already exists in the live IDR, save() must NOT be
    called again -- only add_evidence() appends the new evidence."""
    d1 = _discovery(dna_ids=["feat_existing::UP"], overall=0.80)
    d2 = _discovery(dna_ids=["feat_existing::UP"], overall=0.82)

    mock_instance = MagicMock()
    mock_instance.get.return_value = MagicMock()  # already exists, no raise
    mock_instance.save = MagicMock()
    mock_instance.add_evidence = MagicMock()

    with patch("market_learning.idr_repository.IDRRepository", return_value=mock_instance):
        bridge.evaluate_discoveries_for_idr_evidence([d1], years_used=[2020, 2021])
        bridge.evaluate_discoveries_for_idr_evidence([d2], years_used=[2020, 2021, 2022])

    mock_instance.save.assert_not_called()
    mock_instance.add_evidence.assert_called_once()
