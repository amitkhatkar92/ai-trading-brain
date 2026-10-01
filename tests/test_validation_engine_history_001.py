"""
tests/test_validation_engine_history_001.py
==============================================
DTA-VALIDATION-REPORT-SURFACE-001

ValidationEngine.validate() already runs daily at EOD (gated on >=30
official trades) and already logs its own verdict -- but the returned
ValidationReport was discarded by the only call site, so nothing could
query "what was the last verdict" or see a trend over time.

Covers the additive, research-only persistence + read-only accessors +
Sandy poller. Zero decision/execution impact: advisory-only.
"""
from __future__ import annotations

from unittest.mock import patch

from validation_engine.validation_history import (
    get_latest_validation_report,
    get_validation_report_history,
    record_validation_report,
)


class _FakeStage:
    def __init__(self, stage, passed, score, weight):
        self.stage, self.passed, self.score, self.weight = stage, passed, score, weight


class _FakeReport:
    def __init__(self, strategy_name="Portfolio", overall_score=72.5,
                 verdict="APPROVED", stage_scores=None):
        self.strategy_name = strategy_name
        self.overall_score = overall_score
        self.verdict = verdict
        self.stage_scores = stage_scores or [_FakeStage("backtest", True, 80.0, 0.25)]


class TestValidationHistoryPersistence:

    def test_T01_record_and_read_back(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        with patch("validation_engine.validation_history._HISTORY_PATH", path):
            record_validation_report(_FakeReport(), trading_date="2026-09-30")
            hist = get_validation_report_history()
        assert len(hist) == 1
        assert hist[0]["trading_date"] == "2026-09-30"
        assert hist[0]["verdict"] == "APPROVED"
        assert hist[0]["overall_score"] == 72.5
        assert hist[0]["stage_scores"][0]["stage"] == "backtest"

    def test_T02_latest_accessor_returns_most_recent(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        with patch("validation_engine.validation_history._HISTORY_PATH", path):
            record_validation_report(_FakeReport(verdict="CONDITIONAL"), trading_date="2026-09-29")
            record_validation_report(_FakeReport(verdict="APPROVED"), trading_date="2026-09-30")
            latest = get_latest_validation_report()
        assert latest["trading_date"] == "2026-09-30"
        assert latest["verdict"] == "APPROVED"

    def test_T03_latest_accessor_none_when_empty(self, tmp_path):
        path = str(tmp_path / "does_not_exist.jsonl")
        with patch("validation_engine.validation_history._HISTORY_PATH", path):
            assert get_latest_validation_report() is None

    def test_T04_record_never_raises_on_bad_input(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        with patch("validation_engine.validation_history._HISTORY_PATH", path):
            record_validation_report(object())  # missing every expected attribute

    def test_T05_write_failure_fails_open(self, tmp_path):
        blocker = tmp_path / "blocker_file"
        blocker.write_text("x")
        bad_path = str(blocker / "sub" / "history.jsonl")
        with patch("validation_engine.validation_history._HISTORY_PATH", bad_path):
            record_validation_report(_FakeReport())


class TestSandyPoller:

    def test_T06_poller_reports_no_data_when_empty(self, tmp_path):
        from sandy.sandy_supervisor import SandySupervisor
        with patch("validation_engine.get_latest_validation_report", return_value=None), \
             patch("validation_engine.get_validation_report_history", return_value=[]):
            report = SandySupervisor()._poll_validation_engine()
        assert report.stage == "NO DATA YET"
        assert report.evidence_count == 0

    def test_T07_poller_surfaces_latest_verdict(self):
        from sandy.sandy_supervisor import SandySupervisor
        latest = {"verdict": "APPROVED", "overall_score": 81.0, "trading_date": "2026-09-30"}
        with patch("validation_engine.get_latest_validation_report", return_value=latest), \
             patch("validation_engine.get_validation_report_history", return_value=[latest]):
            report = SandySupervisor()._poll_validation_engine()
        assert report.stage == "APPROVED"
        assert "81.0" in report.summary


class TestSafetyContract:

    def test_T08_no_forbidden_imports(self):
        import inspect
        import validation_engine.validation_history as mod
        src = inspect.getsource(mod)
        for forbidden in ("import execution_engine", "import order_manager",
                          "import risk_control", "import dhan_feed", "from broker"):
            assert forbidden not in src, f"forbidden import found: {forbidden}"
