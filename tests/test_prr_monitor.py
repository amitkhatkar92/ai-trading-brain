"""
tests/test_prr_monitor.py
============================
Self-Learning Ecosystem Phase 5 — production_readiness score -> monitoring
integration (advisory-only, no trade halt).

T01  record_daily_result() appends a JSON line with the expected fields
T02  get_certification_history(n) returns the last n records, oldest first
T03  get_latest_certification() returns None when no history exists
T04  get_latest_certification() returns the most recently appended record
T05  check_and_alert() fires on NOT_READY even with no prior history
T06  check_and_alert() fires when status changed since the last record
T07  check_and_alert() does NOT fire when status is unchanged and not NOT_READY
T08  check_and_alert() never raises when notifier itself raises (fail-open)
T09  Never imports anything from execution_engine/order_manager/broker/risk_control
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

import production_readiness.prr_monitor as prr_monitor


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path):
    history_file = tmp_path / "daily_summary_history.jsonl"
    with patch.object(prr_monitor, "HISTORY_DIR", str(tmp_path)), \
         patch.object(prr_monitor, "HISTORY_FILE", str(history_file)):
        yield history_file


def _summary(**overrides):
    base = dict(
        date="2026-09-15", certification_status="PRODUCTION_READY",
        ils_score=82.5, gva_score=71.0, critical_failures=0, warnings=1,
        elapsed_seconds=3.2,
    )
    base.update(overrides)
    return base


class TestRecording:
    def test_T01_record_appends_expected_fields(self, _isolated_history):
        prr_monitor.record_daily_result(_summary())
        lines = _isolated_history.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["certification_status"] == "PRODUCTION_READY"
        assert rec["ils_score"] == pytest.approx(82.5)
        assert rec["gva_score"] == pytest.approx(71.0)

    def test_T02_history_returns_last_n_oldest_first(self, _isolated_history):
        for i in range(5):
            prr_monitor.record_daily_result(_summary(date=f"2026-09-{10+i}"))
        hist = prr_monitor.get_certification_history(n=3)
        assert [r["date"] for r in hist] == ["2026-09-12", "2026-09-13", "2026-09-14"]


class TestLatestAccessor:
    def test_T03_returns_none_with_no_history(self, _isolated_history):
        assert prr_monitor.get_latest_certification() is None

    def test_T04_returns_most_recent_record(self, _isolated_history):
        prr_monitor.record_daily_result(_summary(date="2026-09-13", certification_status="NOT_READY"))
        prr_monitor.record_daily_result(_summary(date="2026-09-14", certification_status="PRODUCTION_READY"))
        latest = prr_monitor.get_latest_certification()
        assert latest["date"] == "2026-09-14"
        assert latest["certification_status"] == "PRODUCTION_READY"


class TestAlerting:
    def test_T05_alerts_on_not_ready_with_no_history(self, _isolated_history):
        notifier = MagicMock()
        prr_monitor.check_and_alert(_summary(certification_status="NOT_READY"), notifier=notifier)
        notifier.market_alert.assert_called_once()

    def test_T06_alerts_on_status_change(self, _isolated_history):
        prr_monitor.record_daily_result(_summary(certification_status="PRODUCTION_READY_WITH_OBSERVATIONS"))
        notifier = MagicMock()
        prr_monitor.check_and_alert(_summary(certification_status="PRODUCTION_READY"), notifier=notifier)
        notifier.market_alert.assert_called_once()

    def test_T07_no_alert_when_unchanged_and_ready(self, _isolated_history):
        prr_monitor.record_daily_result(_summary(certification_status="PRODUCTION_READY"))
        notifier = MagicMock()
        prr_monitor.check_and_alert(_summary(certification_status="PRODUCTION_READY"), notifier=notifier)
        notifier.market_alert.assert_not_called()

    def test_T08_fail_open_when_notifier_raises(self, _isolated_history):
        notifier = MagicMock()
        notifier.market_alert.side_effect = RuntimeError("boom")
        # Must not raise.
        prr_monitor.check_and_alert(_summary(certification_status="NOT_READY"), notifier=notifier)


class TestSafetyContract:
    def test_T09_no_forbidden_imports(self):
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "production_readiness", "prr_monitor.py",
        )
        src = open(src_path, encoding="utf-8").read()
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
            assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
            assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
