"""
tests/test_sandy_supervisor.py
==================================
Self-Learning Ecosystem Phase 7a — "Sandy" Master Meta-Learning Supervisor
(core data-gathering, trend classification, keyword query answering).

T01  poll_all_agents() returns a report for every registered poller, never
     raises even when several individual pollers fail
T02  A single failing poller does not prevent the others from reporting
T03  Trend classification: UNKNOWN on first poll (no prior snapshot)
T04  Trend classification: ACTIVE when evidence_count increased since the
     last snapshot
T05  Trend classification: IDLE when evidence_count is unchanged and the
     last snapshot is older than IDLE_THRESHOLD_DAYS
T06  answer("sandy help") / answer("hi sandy") / answer("sandy report") /
     answer("sandy status <name>") all route correctly
T07  answer() with an unrecognised name returns a helpful fallback,
     never raises
T08  daily_digest() never raises even if poll_all_agents() itself blows up
T09  Never imports execution_engine/order_manager/broker/risk_control/dhan_feed
T10  New accessors: PGA get_last_run_summary(), KDA-CRE-001
     get_refinement_status()/get_ledger_history(), RSL-001
     get_active_adjustments_status() -- all read-only, never raise, and
     reflect real written data
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from sandy.sandy_models import AgentHealthReport, TREND_ACTIVE, TREND_IDLE, TREND_UNKNOWN
from sandy.sandy_supervisor import SandySupervisor
import sandy.sandy_supervisor as sandy_mod


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path):
    history_file = tmp_path / "health_history.jsonl"
    with patch.object(sandy_mod, "HISTORY_DIR", str(tmp_path)), \
         patch.object(sandy_mod, "HISTORY_FILE", str(history_file)):
        yield history_file


def _fake_report(name, evidence_count=5):
    return AgentHealthReport(
        name=name, category="SELF_LEARNING_PHASE", stage="ACTIVE",
        evidence_count=evidence_count, summary="test",
    )


class TestPollingResilience:
    def test_T01_polls_all_registered_agents(self):
        sup = SandySupervisor()
        with patch.object(sup, "_poll_options_ks_bridge", return_value=_fake_report("A")), \
             patch.object(sup, "_poll_ars_hypothesis_bridge", return_value=_fake_report("B")), \
             patch.object(sup, "_poll_pga_learning", return_value=_fake_report("C")), \
             patch.object(sup, "_poll_rejection_attribution", return_value=_fake_report("D")), \
             patch.object(sup, "_poll_production_readiness", return_value=_fake_report("E")), \
             patch.object(sup, "_poll_hkap_kde_bridge", return_value=_fake_report("F")), \
             patch.object(sup, "_poll_kda_cre", return_value=_fake_report("G")), \
             patch.object(sup, "_poll_rsl_001", return_value=_fake_report("H")), \
             patch.object(sup, "_poll_strategy_performance", return_value=_fake_report("I")), \
             patch.object(sup, "_poll_regime_strategy_map", return_value=_fake_report("J")), \
             patch.object(sup, "_poll_ars_scheduler", return_value=_fake_report("K")), \
             patch.object(sup, "_poll_ikn_bridge", return_value=_fake_report("L")):
            reports = sup.poll_all_agents()
        assert set(reports.keys()) == set("ABCDEFGHIJKL")

    def test_T02_one_failing_poller_does_not_block_others(self):
        sup = SandySupervisor()
        with patch.object(sup, "_poll_options_ks_bridge", side_effect=RuntimeError("boom")), \
             patch.object(sup, "_poll_ars_hypothesis_bridge", return_value=_fake_report("B")), \
             patch.object(sup, "_poll_pga_learning", return_value=_fake_report("C")), \
             patch.object(sup, "_poll_rejection_attribution", return_value=_fake_report("D")), \
             patch.object(sup, "_poll_production_readiness", return_value=_fake_report("E")), \
             patch.object(sup, "_poll_hkap_kde_bridge", return_value=_fake_report("F")), \
             patch.object(sup, "_poll_kda_cre", return_value=_fake_report("G")), \
             patch.object(sup, "_poll_rsl_001", return_value=_fake_report("H")), \
             patch.object(sup, "_poll_strategy_performance", return_value=_fake_report("I")), \
             patch.object(sup, "_poll_regime_strategy_map", return_value=_fake_report("J")), \
             patch.object(sup, "_poll_ars_scheduler", return_value=_fake_report("K")), \
             patch.object(sup, "_poll_ikn_bridge", return_value=_fake_report("L")):
            reports = sup.poll_all_agents()
        assert "A" not in reports
        assert set(reports.keys()) == set("BCDEFGHIJKL")


class TestTrendClassification:
    def _minimal_sup(self):
        sup = SandySupervisor()
        patchers = [
            patch.object(sup, "_poll_ars_hypothesis_bridge", return_value=None),
            patch.object(sup, "_poll_pga_learning", return_value=None),
            patch.object(sup, "_poll_rejection_attribution", return_value=None),
            patch.object(sup, "_poll_production_readiness", return_value=None),
            patch.object(sup, "_poll_hkap_kde_bridge", return_value=None),
            patch.object(sup, "_poll_kda_cre", return_value=None),
            patch.object(sup, "_poll_rsl_001", return_value=None),
            patch.object(sup, "_poll_strategy_performance", return_value=None),
            patch.object(sup, "_poll_regime_strategy_map", return_value=None),
        ]
        for p in patchers:
            p.start()
        return sup, patchers

    def test_T03_unknown_on_first_poll(self):
        sup, patchers = self._minimal_sup()
        try:
            with patch.object(sup, "_poll_options_ks_bridge", return_value=_fake_report("Options", 5)):
                reports = sup.poll_all_agents()
            assert reports["Options"].trend == TREND_UNKNOWN
        finally:
            for p in patchers:
                p.stop()

    def test_T04_active_when_evidence_grew(self, _isolated_history):
        sup, patchers = self._minimal_sup()
        try:
            with patch.object(sup, "_poll_options_ks_bridge", return_value=_fake_report("Options", 5)):
                sup.poll_all_agents()
            with patch.object(sup, "_poll_options_ks_bridge", return_value=_fake_report("Options", 8)):
                reports = sup.poll_all_agents()
            assert reports["Options"].trend == TREND_ACTIVE
        finally:
            for p in patchers:
                p.stop()

    def test_T05_idle_when_unchanged_and_stale(self, _isolated_history):
        sup, patchers = self._minimal_sup()
        try:
            stale_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            with patch.object(sandy_mod.SandySupervisor, "_load_last_snapshot",
                               return_value={"Options": {"evidence_count": 5, "polled_at": stale_ts}}):
                with patch.object(sup, "_poll_options_ks_bridge", return_value=_fake_report("Options", 5)):
                    reports = sup.poll_all_agents()
            assert reports["Options"].trend == TREND_IDLE
            assert any("No new evidence" in i for i in reports["Options"].issues)
        finally:
            for p in patchers:
                p.stop()


class TestKeywordAnswering:
    def test_T06_all_recognised_keywords_route_correctly(self):
        sup = SandySupervisor()
        with patch.object(sup, "poll_all_agents", return_value={"HKAP -> KDE Discovery Bridge (Phase 6)": _fake_report("HKAP -> KDE Discovery Bridge (Phase 6)")}):
            assert "Sandy" in sup.answer("hi sandy") or "checked" in sup.answer("hi sandy")
            assert "stands right now" in sup.answer("sandy report")
            assert "HKAP" in sup.answer("sandy status hkap")
            assert "help" in sup.answer("sandy help").lower()

    def test_T07_unrecognised_agent_name_is_graceful(self):
        sup = SandySupervisor()
        with patch.object(sup, "poll_all_agents", return_value={"X": _fake_report("X")}):
            reply = sup.answer("sandy status nonexistent")
        assert "recognise" in reply.lower() or "know" in reply.lower()


class TestFailOpen:
    def test_T08_daily_digest_never_raises(self):
        sup = SandySupervisor()
        with patch.object(sup, "poll_all_agents", side_effect=RuntimeError("boom")):
            result = sup.daily_digest()
        assert "error" in result.lower()


class TestSafetyContract:
    def test_T09_no_forbidden_imports(self):
        for fname in ("sandy_supervisor.py", "sandy_models.py", "__init__.py"):
            src_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sandy", fname,
            )
            src = open(src_path, encoding="utf-8").read()
            for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
                assert f"import {forbidden}" not in src, f"{fname}: forbidden import {forbidden}"
                assert f"from {forbidden}" not in src, f"{fname}: forbidden import {forbidden}"


class TestNewAccessors:
    def test_T10a_pga_last_run_summary(self, tmp_path):
        from predictive_gap.pga_learning import get_last_run_summary
        day_dir = tmp_path / "2026-09-10"
        day_dir.mkdir()
        (day_dir / "pga_learning_actions.json").write_text(json.dumps([
            {"category": "E", "outcome": "CLE_SCHEDULED"},
            {"category": "E", "outcome": "CLE_SCHEDULED"},
        ]))
        summary = get_last_run_summary(pga_dir=tmp_path)
        assert summary["total_actions"] == 2
        assert summary["by_category"] == {"E": 2}

    def test_T10a_pga_none_when_no_reports(self, tmp_path):
        from predictive_gap.pga_learning import get_last_run_summary
        assert get_last_run_summary(pga_dir=tmp_path) is None

    def test_T10b_kda_cre_refinement_status(self):
        from knowledge_authority.kda_constant_refinement_engine import get_refinement_status
        status = get_refinement_status()
        assert "per_constant" in status
        assert set(status["per_constant"].keys()) == {
            "_ESS_DECISION_ELIGIBLE", "_STABILITY_DECISION_MIN", "_CONTRADICTION_DECISION_MIN",
        }

    def test_T10b_kda_cre_ledger_history_never_raises(self):
        from knowledge_authority.kda_constant_refinement_engine import get_ledger_history
        result = get_ledger_history(n=5)
        assert isinstance(result, list)

    def test_T10c_rsl_001_active_adjustments_status(self):
        from scripts.knowledge_system.ranking_adjustment_engine_001 import get_active_adjustments_status
        status = get_active_adjustments_status()
        assert "candidates" in status
        assert "active_config" in status
