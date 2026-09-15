"""
tests/test_kde_idr_evidence_bridge.py
========================================
Self-Learning Ecosystem -- Post-roadmap Item 4: KDE Discovery -> IDR
evidence bridge (kde/kde_idr_evidence_bridge.py).

T01  Discoveries below MIN_OVERALL_SCORE are skipped
T02  Discoveries with no dna_ids are skipped
T03  Qualifying discovery produces one bounded proposal per dna_id
T04  Evidence confidence/effect_size are capped at MAX_EVIDENCE_CONFIDENCE
     even for a perfect (1.0) discovery score
T05  Re-evaluating the same discoveries does not create duplicate proposals
T06  get_pending_proposals() excludes already-merged proposals, supports
     dna_id filter
T07  request_live_merge() calls IDRRepository.add_evidence() exactly once
     with the correct dna_id, marks the proposal merged, appends to the
     merge ledger
T08  request_live_merge() returns False for an unknown discovery/dna_id
     pair and never touches IDRRepository
T09  request_live_merge() fails open (False) if IDRRepository.add_evidence
     raises
T10  evaluate_discoveries_for_idr_evidence() fails open (empty list) if
     given garbage input
T11  Safety: no automatic caller anywhere in the repo invokes
     request_live_merge() from an EOD/scheduler loop (source-text scan of
     orchestrator/master_orchestrator.py and hkap/hkap_kde_bridge.py)
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


def test_t01_below_threshold_skipped(_isolated_store):
    d = _discovery(overall=0.10)
    result = bridge.evaluate_discoveries_for_idr_evidence([d])
    assert result == []
    assert bridge.get_pending_proposals() == []


def test_t02_no_dna_ids_skipped(_isolated_store):
    d = _discovery(dna_ids=[], overall=0.90)
    result = bridge.evaluate_discoveries_for_idr_evidence([d])
    assert result == []


def test_t03_qualifying_discovery_one_proposal_per_dna_id(_isolated_store):
    d = _discovery(dna_ids=["feat_a::UP", "feat_b::DOWN"], overall=0.80)
    result = bridge.evaluate_discoveries_for_idr_evidence([d])
    assert len(result) == 2
    dna_ids_seen = {p["dna_id"] for p in result}
    assert dna_ids_seen == {"feat_a::UP", "feat_b::DOWN"}
    for p in result:
        assert p["discovery_id"] == d.discovery_id
        assert p["merged"] is False


def test_t04_evidence_bounded_even_for_perfect_score(_isolated_store):
    d = _discovery(overall=1.0)
    result = bridge.evaluate_discoveries_for_idr_evidence([d])
    assert len(result) == 1
    assert result[0]["confidence"] <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert result[0]["effect_size"] <= bridge.MAX_EVIDENCE_CONFIDENCE
    assert result[0]["sample_size"] <= bridge.MAX_EVIDENCE_SAMPLE


def test_t05_reevaluate_no_duplicates(_isolated_store):
    d = _discovery(overall=0.80)
    first = bridge.evaluate_discoveries_for_idr_evidence([d])
    second = bridge.evaluate_discoveries_for_idr_evidence([d])
    assert len(first) == 1
    assert len(second) == 0
    assert len(bridge.get_pending_proposals()) == 1


def test_t06_pending_proposals_filter_and_merged_exclusion(_isolated_store):
    d1 = _discovery(discovery_id="KDE-A", dna_ids=["feat_a::UP"], overall=0.80)
    d2 = _discovery(discovery_id="KDE-B", dna_ids=["feat_b::UP"], overall=0.80)
    bridge.evaluate_discoveries_for_idr_evidence([d1, d2])

    assert len(bridge.get_pending_proposals()) == 2
    assert len(bridge.get_pending_proposals(dna_id="feat_a::UP")) == 1

    with patch("market_learning.idr_repository.IDRRepository") as MockRepo:
        MockRepo.return_value.add_evidence = MagicMock()
        ok = bridge.request_live_merge("KDE-A", "feat_a::UP", operator="test")
    assert ok is True
    assert len(bridge.get_pending_proposals()) == 1
    assert bridge.get_pending_proposals()[0]["dna_id"] == "feat_b::UP"


def test_t07_request_live_merge_calls_add_evidence_correctly(_isolated_store):
    d = _discovery(discovery_id="KDE-C", dna_ids=["feat_c::UP"], overall=0.80)
    bridge.evaluate_discoveries_for_idr_evidence([d])

    with patch("market_learning.idr_repository.IDRRepository") as MockRepo:
        mock_instance = MockRepo.return_value
        mock_instance.add_evidence = MagicMock()
        ok = bridge.request_live_merge("KDE-C", "feat_c::UP", operator="alice")

    assert ok is True
    mock_instance.add_evidence.assert_called_once()
    call_args = mock_instance.add_evidence.call_args
    assert call_args[0][0] == "feat_c::UP"
    ev = call_args[0][1]
    assert ev.dna_id == "feat_c::UP"
    assert ev.confidence <= bridge.MAX_EVIDENCE_CONFIDENCE

    history = bridge.get_merge_history()
    assert len(history) == 1
    assert history[0]["merged_by"] == "alice"
    assert history[0]["merged"] is True


def test_t08_unknown_pair_returns_false_never_touches_repo(_isolated_store):
    with patch("market_learning.idr_repository.IDRRepository") as MockRepo:
        ok = bridge.request_live_merge("NOPE", "nope::UP")
    assert ok is False
    MockRepo.assert_not_called()


def test_t09_request_live_merge_fails_open(_isolated_store):
    d = _discovery(discovery_id="KDE-D", dna_ids=["feat_d::UP"], overall=0.80)
    bridge.evaluate_discoveries_for_idr_evidence([d])

    with patch("market_learning.idr_repository.IDRRepository") as MockRepo:
        MockRepo.return_value.add_evidence.side_effect = RuntimeError("boom")
        ok = bridge.request_live_merge("KDE-D", "feat_d::UP")
    assert ok is False
    # still pending, not marked merged
    assert len(bridge.get_pending_proposals(dna_id="feat_d::UP")) == 1


def test_t10_evaluate_fails_open_on_garbage_input(_isolated_store):
    result = bridge.evaluate_discoveries_for_idr_evidence([object(), None, 42])
    assert result == []


def test_t11_no_automatic_live_merge_caller():
    orch_src = open("orchestrator/master_orchestrator.py", encoding="utf-8").read()
    bridge_src = open("hkap/hkap_kde_bridge.py", encoding="utf-8").read()
    assert "request_live_merge" not in orch_src
    assert "request_live_merge" not in bridge_src
    assert "evaluate_discoveries_for_idr_evidence" in bridge_src
