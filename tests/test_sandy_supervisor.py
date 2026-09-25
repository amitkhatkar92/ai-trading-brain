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
T11  "sandy status <name>" acknowledges an ALL_AGENTS roster member that
     has no dedicated poller instead of falsely claiming it's unrecognised
T12  "sandy agents"/"sandy coverage" reports N/total poller coverage
T13  New pollers _poll_debate_agents / _poll_capital_risk_engine wrap
     their underlying read-only accessors correctly; the CapitalRiskEngine
     accessor is routed through learning_system/capital_risk_facade.py
     (never risk_control directly) to respect T09
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


_ALL_POLLER_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWX"
_ALL_POLLER_NAMES = [
    "_poll_options_ks_bridge", "_poll_ars_hypothesis_bridge", "_poll_pga_learning",
    "_poll_rejection_attribution", "_poll_production_readiness", "_poll_hkap_kde_bridge",
    "_poll_kda_cre", "_poll_rsl_001", "_poll_strategy_performance", "_poll_regime_strategy_map",
    "_poll_ars_scheduler", "_poll_ikn_bridge", "_poll_debate_weight_refinement",
    "_poll_dtrace_scheduler", "_poll_regime_map_refinement", "_poll_shm_regime_health",
    "_poll_trust_weighted_ranking", "_poll_shm_profile_refinement", "_poll_sizing_bounds_refinement",
    "_poll_capital_reserve_readiness", "_poll_options_health", "_poll_debate_agents",
    "_poll_capital_risk_engine", "_poll_cle_fingerprint_refinement",
]


def _patch_all_pollers(sup, skip_first_with_error=False):
    """Build an ExitStack patching every registered poller with a fake
    report named after its position's letter (A, B, C, ...). Avoids the
    'too many statically nested blocks' SyntaxError that a 23-deep chained
    `with a, b, c, ...:` statement hits."""
    from contextlib import ExitStack
    stack = ExitStack()
    for letter, method_name in zip(_ALL_POLLER_LETTERS, _ALL_POLLER_NAMES):
        if skip_first_with_error and letter == "A":
            stack.enter_context(patch.object(sup, method_name, side_effect=RuntimeError("boom")))
        else:
            stack.enter_context(patch.object(sup, method_name, return_value=_fake_report(letter)))
    return stack


class TestPollingResilience:
    def test_T01_polls_all_registered_agents(self):
        sup = SandySupervisor()
        with _patch_all_pollers(sup):
            reports = sup.poll_all_agents()
        assert set(reports.keys()) == set(_ALL_POLLER_LETTERS)

    def test_T02_one_failing_poller_does_not_block_others(self):
        sup = SandySupervisor()
        with _patch_all_pollers(sup, skip_first_with_error=True):
            reports = sup.poll_all_agents()
        assert "A" not in reports
        assert set(reports.keys()) == set(_ALL_POLLER_LETTERS) - {"A"}


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
        with patch.object(sup, "poll_all_agents", return_value={"X": _fake_report("X")}), \
             patch.object(sup, "_lookup_roster_agent", return_value=[]):
            reply = sup.answer("sandy status nonexistent")
        assert "recognise" in reply.lower() or "know" in reply.lower()

    def test_T11_roster_agent_without_poller_is_acknowledged(self):
        """An agent that exists in ALL_AGENTS but has no dedicated poller
        must never be reported as unrecognised -- it should get an honest
        'runs deterministically, no dedicated poller yet' reply."""
        sup = SandySupervisor()
        with patch.object(sup, "poll_all_agents", return_value={"X": _fake_report("X")}), \
             patch.object(sup, "_lookup_roster_agent", return_value=["RiskManagerAI"]):
            reply = sup.answer("sandy status riskmanagerai")
        assert "RiskManagerAI" in reply
        assert "don't recognise" not in reply.lower()

    def test_T12_sandy_agents_reports_coverage(self):
        sup = SandySupervisor()
        with patch.object(sup, "poll_all_agents", return_value={"X": _fake_report("X"), "Y": _fake_report("Y")}), \
             patch("orchestrator.master_orchestrator.ALL_AGENTS", ["a"] * 62):
            reply = sup.answer("sandy agents")
        assert "2/62" in reply


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


class TestNewPollers:
    def test_T13a_poll_debate_agents_wraps_accuracy_accessor(self):
        sup = SandySupervisor()
        fake_accuracy = {"RiskManagerAI": {"sample_size": 12, "correct_count": 8}}
        with patch("debate_system.debate_vote_tracker.get_debater_accuracy", return_value=fake_accuracy):
            report = sup._poll_debate_agents()
        assert report.stage == "ACTIVE"
        assert report.evidence_count == 12
        assert "1 debater(s)" in report.summary

    def test_T13b_poll_debate_agents_no_data(self):
        sup = SandySupervisor()
        with patch("debate_system.debate_vote_tracker.get_debater_accuracy", return_value={}):
            report = sup._poll_debate_agents()
        assert report.stage == "NO DATA YET"
        assert report.evidence_count == 0

    def test_T13c_poll_capital_risk_engine_wraps_facade(self):
        sup = SandySupervisor()
        with patch("learning_system.capital_risk_facade.get_last_cycle_dominant_rejection_reason",
                   return_value="BUDGET"):
            report = sup._poll_capital_risk_engine()
        assert report.stage == "ACTIVE"
        assert "BUDGET" in report.summary

    def test_T13d_poll_capital_risk_engine_no_rejections(self):
        sup = SandySupervisor()
        with patch("learning_system.capital_risk_facade.get_last_cycle_dominant_rejection_reason",
                   return_value="NONE"):
            report = sup._poll_capital_risk_engine()
        assert report.stage == "NO REJECTIONS LAST CYCLE"

    def test_T13e_facade_reexports_real_risk_control_accessor(self):
        """The facade must genuinely forward to risk_control's real getter
        (not just exist) -- risk_control itself may import this freely,
        only sandy/ is restricted."""
        from learning_system.capital_risk_facade import get_last_cycle_dominant_rejection_reason
        from risk_control.capital_risk_engine import (
            get_last_cycle_dominant_rejection_reason as real_getter,
        )
        assert get_last_cycle_dominant_rejection_reason() == real_getter()

    def test_T13f_sandy_never_imports_risk_control_even_with_new_poller(self):
        """Regression guard duplicating T09's intent specifically for the
        newly-added _poll_capital_risk_engine method."""
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sandy", "sandy_supervisor.py",
        )
        src = open(src_path, encoding="utf-8").read()
        assert "from risk_control" not in src
        assert "import risk_control" not in src
        assert "learning_system.capital_risk_facade" in src
