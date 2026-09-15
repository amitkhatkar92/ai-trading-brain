"""
tests/test_prr_pipeline_root_cause.py
=========================================
Root-cause fix: production_readiness/ph5_daily_pipeline.py::run_daily_pipeline()
was dead code, and prr_runner.py's _collect_prr_data() never set
data["pipeline"], so ph9_certification.py's Daily_ILC_Operational check
always hard-coded a PASS/INFO placeholder regardless of real PGA/ILC health.

Fix: build_pipeline_result_from_live_stages() wraps the orchestrator's OWN
already-executed PGA/ILC result dicts into a real DailyPipelineResult --
never re-runs PGA/ILC. run_prr()/_collect_prr_data() gained an optional
`pipeline` parameter (default None, fully backward compatible). ph9's
narrative text no longer hard-codes "/6".

T01  build_pipeline_result_from_live_stages() with both PGA+ILC OK ->
     stages_completed=2, stages_failed=0, both sub-stages success=True
T02  ... with ILC status != "OK" -> ilc stage success=False, stages_failed=1
T03  ... with both None (neither ran this cycle) -> stages_completed=0,
     stages_failed=0, pga/ilc both None
T04  ph9_certification.build_certificate(): Daily_ILC_Operational now
     reflects the REAL ilc success (CRITICAL fail when ILC actually failed)
T05  ph9_certification.build_certificate(): PASSES (severity=INFO) when
     the real ILC stage succeeded, with an accurate "X/Y stages" narrative
     (no hard-coded "/6")
T06  run_prr(pipeline=None) still behaves exactly as before (backward
     compatible default -- Daily_ILC_Operational falls back to the
     "not yet run" INFO-only placeholder)
T07  _collect_prr_data() threads the `pipeline` argument through to
     build_certificate() correctly
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from production_readiness.ph5_daily_pipeline import build_pipeline_result_from_live_stages
from production_readiness.ph9_certification import build_certificate


class TestBuildPipelineResultFromLiveStages:
    def test_T01_both_stages_ok(self):
        result = build_pipeline_result_from_live_stages(
            pga_result={"status": "OK", "n_gainers": 5},
            ilc_result={"status": "OK", "learning_score": 72.0},
            report_date="2026-09-15",
        )
        assert result.stages_completed == 2
        assert result.stages_failed == 0
        assert result.pga.success is True
        assert result.ilc.success is True
        assert result.gva is None and result.sd_review is None

    def test_T02_ilc_failed_status(self):
        result = build_pipeline_result_from_live_stages(
            pga_result={"status": "OK"},
            ilc_result={"status": "NO_DATA"},
        )
        assert result.ilc.success is False
        assert result.stages_completed == 1
        assert result.stages_failed == 1

    def test_T03_neither_ran_this_cycle(self):
        result = build_pipeline_result_from_live_stages(pga_result=None, ilc_result=None)
        assert result.pga is None
        assert result.ilc is None
        assert result.stages_completed == 0
        assert result.stages_failed == 0


class TestPh9CertificationRealSignal:
    def test_T04_critical_fail_when_ilc_really_failed(self):
        pipeline = build_pipeline_result_from_live_stages(
            pga_result={"status": "OK"}, ilc_result={"status": "TIMEOUT"},
        )
        cert = build_certificate(pipeline=pipeline, today="2026-09-15")
        check = next(c for c in cert.checks if c.check_name == "Daily_ILC_Operational")
        assert check.passed is False
        assert check.severity == "CRITICAL"
        assert cert.verdict == "NOT_READY"

    def test_T05_passes_with_accurate_narrative_no_hardcoded_six(self):
        pipeline = build_pipeline_result_from_live_stages(
            pga_result={"status": "OK"}, ilc_result={"status": "OK"},
        )
        cert = build_certificate(pipeline=pipeline, today="2026-09-15")
        check = next(c for c in cert.checks if c.check_name == "Daily_ILC_Operational")
        assert check.passed is True
        assert check.severity == "INFO"
        assert "2/2 stages OK" in check.detail
        assert "/6" not in check.detail


class TestBackwardCompatibility:
    def test_T06_run_prr_default_pipeline_none_unchanged(self):
        from production_readiness.prr_runner import _collect_prr_data
        data = _collect_prr_data("2026-09-15", dry_run=True)
        assert data["pipeline"] is None
        check = next(c for c in data["certificate"].checks if c.check_name == "Daily_ILC_Operational")
        assert check.passed is True
        assert check.severity == "INFO"
        assert "not yet called this cycle" not in check.detail  # uses the real placeholder text
        assert "runs at 15:35 IST" in check.detail

    def test_T07_collect_prr_data_threads_pipeline_through(self):
        from production_readiness.prr_runner import _collect_prr_data
        pipeline = build_pipeline_result_from_live_stages(
            pga_result={"status": "OK"}, ilc_result={"status": "OK"},
        )
        data = _collect_prr_data("2026-09-15", dry_run=True, pipeline=pipeline)
        assert data["pipeline"] is pipeline
        check = next(c for c in data["certificate"].checks if c.check_name == "Daily_ILC_Operational")
        assert "2/2 stages OK" in check.detail
