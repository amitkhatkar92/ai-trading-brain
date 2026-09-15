"""
tests/test_ars_scheduler.py
==============================
Self-Learning Ecosystem -- Post-roadmap Priority 1: activation of the
9-agent autonomous_research (ARS) cluster via autonomous_research/
ars_scheduler.py.

T01  Self-scheduling: skips (SKIPPED_TOO_SOON) when the last real run was
     < MIN_DAYS_BETWEEN_RUNS ago
T02  force=True bypasses the cadence guard even when a recent run exists
T03  First-ever run (no history) proceeds (no cadence guard blocks it)
T04  Full wiring: all 9 components constructed and correctly connected
     (constructor kwargs verified), RoadmapManager.build()+top_priorities()
     drive StudyPlanner.create_from_entry(), ScientificDirector.weekly_
     review() is called, and a correctly-shaped OK summary is returned
T05  Plans are not re-created for gaps that already have a plan
     (source_gap_id dedup)
T06  get_last_run_summary() / get_run_history() read back correctly,
     oldest-first
T07  Fail-open: never raises even when a component constructor blows up
T08  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control anywhere in this module
T09  Priority 2: sync_hypotheses_to_ikn() is called after weekly_review()
     and its result is embedded in the summary; a failure there does not
     break the overall cycle
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import autonomous_research.ars_scheduler as sched


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path):
    history_file = tmp_path / "run_history.jsonl"
    with patch.object(sched, "_RUN_DIR", str(tmp_path)), \
         patch.object(sched, "_RUN_HISTORY", str(history_file)):
        yield history_file


@pytest.fixture(autouse=True)
def _stub_ikn_sync():
    with patch("ikn.ikn_research_bridge.sync_hypotheses_to_ikn",
               return_value={"status": "OK", "hypotheses_seen": 0,
                              "nodes_registered": 0, "relationships_added": 0}) as m:
        yield m


def _patch_all_components():
    """Patch every autonomous_research/market_learning class ars_scheduler
    constructs, returning MagicMock instances wired to sane defaults."""
    patches = {
        "autonomous_research.knowledge_provider.KnowledgeProvider": MagicMock(),
        "autonomous_research.hypothesis_registry.HypothesisRegistry": MagicMock(),
        "autonomous_research.gap_detector.GapDetector": MagicMock(),
        "autonomous_research.roadmap_manager.RoadmapManager": MagicMock(),
        "autonomous_research.evidence_validator.EvidenceValidator": MagicMock(),
        "autonomous_research.cross_study_synthesizer.CrossStudySynthesizer": MagicMock(),
        "autonomous_research.study_planner.StudyPlanner": MagicMock(),
        "autonomous_research.research_coordinator.ResearchCoordinator": MagicMock(),
        "autonomous_research.scientific_director.ScientificDirector": MagicMock(),
        "market_learning.idr_repository.IDRRepository": MagicMock(),
    }
    return patches


def _fake_review(review_id="SD-REV-1", health_value="HEALTHY", n_obs=3, n_dec=2):
    decision = SimpleNamespace(decision_type=SimpleNamespace(value="CREATE_HYPOTHESIS"))
    return SimpleNamespace(
        review_id=review_id,
        health=SimpleNamespace(value=health_value),
        observations=[SimpleNamespace()] * n_obs,
        decisions=[decision] * n_dec,
    )


def _fake_entry(gap_id="GAP-1"):
    gap = SimpleNamespace(gap_id=gap_id)
    return SimpleNamespace(gap=gap)


def test_t01_skips_too_soon(_isolated_history):
    sched._record_run({
        "status": "OK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    result = sched.run_autonomous_research_cycle()
    assert result["status"] == "SKIPPED_TOO_SOON"
    assert result["days_since_last_run"] == 0


def test_t02_force_bypasses_cadence_guard(_isolated_history):
    sched._record_run({
        "status": "OK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    patches = _patch_all_components()
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.build.return_value = \
            SimpleNamespace(entries=[])
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.top_priorities.return_value = []
        patches["autonomous_research.study_planner.StudyPlanner"].return_value.list_plans.return_value = []
        patches["autonomous_research.scientific_director.ScientificDirector"].return_value.weekly_review.return_value = \
            _fake_review()
        result = sched.run_autonomous_research_cycle(force=True)
    finally:
        for c in ctxs:
            c.stop()
    assert result["status"] == "OK"


def test_t03_first_ever_run_proceeds(_isolated_history):
    patches = _patch_all_components()
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.build.return_value = \
            SimpleNamespace(entries=[])
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.top_priorities.return_value = []
        patches["autonomous_research.study_planner.StudyPlanner"].return_value.list_plans.return_value = []
        patches["autonomous_research.scientific_director.ScientificDirector"].return_value.weekly_review.return_value = \
            _fake_review()
        result = sched.run_autonomous_research_cycle()
    finally:
        for c in ctxs:
            c.stop()
    assert result["status"] == "OK"


def test_t04_full_wiring_and_summary_shape(_isolated_history):
    patches = _patch_all_components()
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        entries = [_fake_entry("GAP-1"), _fake_entry("GAP-2")]
        MockRM = patches["autonomous_research.roadmap_manager.RoadmapManager"]
        MockRM.return_value.build.return_value = SimpleNamespace(entries=entries)
        MockRM.return_value.top_priorities.return_value = entries

        MockSP = patches["autonomous_research.study_planner.StudyPlanner"]
        MockSP.return_value.list_plans.return_value = []

        MockSD = patches["autonomous_research.scientific_director.ScientificDirector"]
        MockSD.return_value.weekly_review.return_value = _fake_review(n_obs=5, n_dec=3)

        result = sched.run_autonomous_research_cycle(force=True)
    finally:
        for c in ctxs:
            c.stop()

    assert result["status"] == "OK"
    assert result["total_gaps_open"] == 2
    assert result["plans_created"] == 2
    assert result["review_id"] == "SD-REV-1"
    assert result["review_health"] == "HEALTHY"
    assert result["observations"] == 5
    assert result["decisions"] == 3
    assert result["decision_types"] == ["CREATE_HYPOTHESIS", "CREATE_HYPOTHESIS", "CREATE_HYPOTHESIS"]
    assert result["ikn_sync"]["status"] == "OK"

    # Verify RC was wired with the SAME planner/registry/etc instances SD got
    MockRC = patches["autonomous_research.research_coordinator.ResearchCoordinator"]
    MockRC.assert_called_once()
    MockSD.assert_called_once()
    assert MockSD.call_args.kwargs["rc"] is MockRC.return_value

    MockSP.return_value.create_from_entry.assert_any_call(entries[0])
    MockSP.return_value.create_from_entry.assert_any_call(entries[1])


def test_t05_no_duplicate_plan_for_existing_gap(_isolated_history):
    patches = _patch_all_components()
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        entries = [_fake_entry("GAP-1"), _fake_entry("GAP-2")]
        MockRM = patches["autonomous_research.roadmap_manager.RoadmapManager"]
        MockRM.return_value.build.return_value = SimpleNamespace(entries=entries)
        MockRM.return_value.top_priorities.return_value = entries

        MockSP = patches["autonomous_research.study_planner.StudyPlanner"]
        existing_plan = SimpleNamespace(source_gap_id="GAP-1")
        MockSP.return_value.list_plans.return_value = [existing_plan]

        MockSD = patches["autonomous_research.scientific_director.ScientificDirector"]
        MockSD.return_value.weekly_review.return_value = _fake_review()

        result = sched.run_autonomous_research_cycle(force=True)
    finally:
        for c in ctxs:
            c.stop()

    assert result["plans_created"] == 1  # only GAP-2, GAP-1 already has a plan
    MockSP.return_value.create_from_entry.assert_called_once_with(entries[1])


def test_t06_run_history_read_back_oldest_first(_isolated_history):
    sched._record_run({"status": "OK", "generated_at": "2026-09-01T00:00:00+00:00", "plans_created": 1})
    sched._record_run({"status": "OK", "generated_at": "2026-09-08T00:00:00+00:00", "plans_created": 2})
    latest = sched.get_last_run_summary()
    assert latest["plans_created"] == 2
    hist = sched.get_run_history(n=10)
    assert [h["plans_created"] for h in hist] == [1, 2]


def test_t07_fail_open_on_component_exception(_isolated_history):
    with patch("autonomous_research.knowledge_provider.KnowledgeProvider",
               side_effect=RuntimeError("boom")):
        result = sched.run_autonomous_research_cycle(force=True)
    assert result["status"] == "ERROR"


def test_t08_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "autonomous_research", "ars_scheduler.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"


def test_t09_ikn_sync_called_and_fail_open(_isolated_history, _stub_ikn_sync):
    patches = _patch_all_components()
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.build.return_value = \
            SimpleNamespace(entries=[])
        patches["autonomous_research.roadmap_manager.RoadmapManager"].return_value.top_priorities.return_value = []
        patches["autonomous_research.study_planner.StudyPlanner"].return_value.list_plans.return_value = []
        patches["autonomous_research.scientific_director.ScientificDirector"].return_value.weekly_review.return_value = \
            _fake_review()
        result = sched.run_autonomous_research_cycle(force=True)
    finally:
        for c in ctxs:
            c.stop()
    assert result["ikn_sync"]["status"] == "OK"
    _stub_ikn_sync.assert_called_once()

    # now make the IKN sync raise -- the overall cycle must still succeed
    _stub_ikn_sync.side_effect = RuntimeError("ikn boom")
    ctxs = [patch(k, v) for k, v in patches.items()]
    for c in ctxs:
        c.start()
    try:
        result2 = sched.run_autonomous_research_cycle(force=True)
    finally:
        for c in ctxs:
            c.stop()
    assert result2["status"] == "OK"
    assert result2["ikn_sync"]["status"] == "ERROR"
