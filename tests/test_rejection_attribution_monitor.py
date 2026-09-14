"""
tests/test_rejection_attribution_monitor.py
===============================================
Self-Learning Ecosystem Phase 4 — persistent rejection-attribution monitor.

T01  Immature rows (< MATURITY_DAYS old) are skipped, never fetched, remain PENDING
T02  Mature rows resolved via mocked OHLCV fetch -- update_price_follow called
     with the correct T+1/T+3/T+5 closes
T03  Rows with no fetchable data are skipped (skipped_no_data), remain PENDING
T04  get_reason_reliability returns None below min_samples
T05  get_reason_reliability returns real stats at/above min_samples
T06  run_daily_cycle never raises even when the tracker itself raises
T07  Daily summary JSONL gets a new line appended after a cycle
T08  Never imports anything from execution_engine/order_manager/broker APIs
T09  is_backfill=1 rows are excluded from reliability computation, even at
     or above the sample threshold
T10  Root-cause fix regression: rejection_audit.py's seed_synthetic_data()
     marks its seeded rows is_backfill=1, not 0
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from analysis.rejection_attribution_monitor import (
    MATURITY_DAYS,
    MIN_SAMPLES_FOR_RELIABILITY,
    RejectionAttributionMonitor,
)
from analysis.rejection_tracker import RejectionTracker


def _tracker(tmp_path) -> RejectionTracker:
    return RejectionTracker(db_path=str(tmp_path / "test_rejection_audit.db"))


def _ingest(tracker, symbol="RELIANCE", reason="LOW_SFT", days_ago=10, direction="LONG"):
    trade_date = (date.today() - timedelta(days=days_ago)).isoformat()
    return tracker.ingest_rejection(
        symbol=symbol, strategy="Equity_Breakout", trade_date=trade_date,
        decision_score=6.0, quality_score=6.5, quality_tier="MEDIUM",
        rejected_reason=reason, price_at_rejection=1000.0, direction=direction,
    )


class TestMaturityGating:
    def test_T01_immature_rows_skipped(self, tmp_path):
        tr = _tracker(tmp_path)
        _ingest(tr, days_ago=MATURITY_DAYS - 1)
        mon = RejectionAttributionMonitor(tracker=tr)
        with patch(
            "analysis.rejection_attribution_monitor._fetch_ohlcv_closes",
        ) as mock_fetch:
            result = mon.run_daily_cycle()
        mock_fetch.assert_not_called()
        assert result["skipped_immature"] == 1
        assert result["resolved"] == 0
        assert len(tr.get_pending()) == 1


class TestResolution:
    def test_T02_mature_row_resolved_with_correct_prices(self, tmp_path):
        tr = _tracker(tmp_path)
        row_id = _ingest(tr, days_ago=MATURITY_DAYS + 1)
        mon = RejectionAttributionMonitor(tracker=tr)
        with patch(
            "analysis.rejection_attribution_monitor._fetch_ohlcv_closes",
            return_value=[1010.0, 1015.0, 1030.0, 1040.0, 1050.0],
        ):
            result = mon.run_daily_cycle()
        assert result["resolved"] == 1
        assert len(tr.get_pending()) == 0
        row = tr._query_one("SELECT * FROM rejection_log WHERE id=?", (row_id,))
        assert row["price_1d"] == pytest.approx(1010.0)
        assert row["price_3d"] == pytest.approx(1030.0)
        assert row["price_5d"] == pytest.approx(1050.0)
        assert row["rejection_outcome"] == "FALSE_REJECTION"  # LONG, price went up

    def test_T03_no_data_skipped_stays_pending(self, tmp_path):
        tr = _tracker(tmp_path)
        _ingest(tr, days_ago=MATURITY_DAYS + 1)
        mon = RejectionAttributionMonitor(tracker=tr)
        with patch(
            "analysis.rejection_attribution_monitor._fetch_ohlcv_closes",
            return_value=[],
        ):
            result = mon.run_daily_cycle()
        assert result["skipped_no_data"] == 1
        assert result["resolved"] == 0
        assert len(tr.get_pending()) == 1


class TestReliabilityAccessor:
    def _confirm_and_resolve(self, tr, mon, n, reason="LOW_SFT"):
        ids = [_ingest(tr, reason=reason, days_ago=MATURITY_DAYS + 1) for _ in range(n)]
        with patch(
            "analysis.rejection_attribution_monitor._fetch_ohlcv_closes",
            return_value=[900.0, 890.0, 880.0, 870.0, 850.0],  # LONG, price fell -> CORRECT
        ):
            mon.run_daily_cycle()
        return ids

    def test_T04_below_min_samples_returns_none(self, tmp_path):
        tr = _tracker(tmp_path)
        mon = RejectionAttributionMonitor(tracker=tr)
        self._confirm_and_resolve(tr, mon, n=MIN_SAMPLES_FOR_RELIABILITY - 1)
        assert mon.get_reason_reliability("LOW_SFT") is None

    def test_T05_at_min_samples_returns_stats(self, tmp_path):
        tr = _tracker(tmp_path)
        mon = RejectionAttributionMonitor(tracker=tr)
        self._confirm_and_resolve(tr, mon, n=MIN_SAMPLES_FOR_RELIABILITY)
        stats = mon.get_reason_reliability("LOW_SFT")
        assert stats is not None
        assert stats["classified"] >= MIN_SAMPLES_FOR_RELIABILITY
        assert stats["accuracy_pct"] == pytest.approx(100.0)  # all CORRECT_REJECTION

    def test_T09_backfill_rows_excluded_from_reliability(self, tmp_path):
        tr = _tracker(tmp_path)
        mon = RejectionAttributionMonitor(tracker=tr)
        for _ in range(MIN_SAMPLES_FOR_RELIABILITY + 5):
            tr.ingest_rejection(
                symbol="RELIANCE", strategy="Equity_Breakout",
                trade_date=date.today().isoformat(), decision_score=6.0,
                quality_score=6.5, quality_tier="MEDIUM", rejected_reason="LOW_SFT",
                price_at_rejection=1000.0, direction="LONG",
                price_1d=990.0, price_3d=980.0, price_5d=950.0,  # classified at insert time
                is_backfill=True,
            )
        assert mon.get_reason_reliability("LOW_SFT") is None
        summary = mon._compute_reliability_summary()
        assert summary["classified_total"] == 0
        assert "LOW_SFT" not in summary["reasons_with_min_sample"]


class TestSyntheticSeederRootCauseFix:
    def test_T10_seeded_rows_marked_is_backfill(self, tmp_path):
        from analysis.rejection_audit import seed_synthetic_data

        db_path = str(tmp_path / "seed_test.db")
        n = seed_synthetic_data(db_path=db_path, years=1)
        assert n > 0

        tr = RejectionTracker(db_path=db_path)
        rows = tr.get_all()
        assert rows
        assert all(row["is_backfill"] == 1 for row in rows)


class TestFailOpen:
    def test_T06_run_daily_cycle_never_raises(self, tmp_path):
        tr = _tracker(tmp_path)

        class _BoomTracker:
            def get_pending(self):
                raise RuntimeError("boom")

        mon = RejectionAttributionMonitor(tracker=_BoomTracker())
        result = mon.run_daily_cycle()
        assert result["status"] == "ERROR"


class TestDailySummaryPersistence:
    def test_T07_summary_line_appended(self, tmp_path):
        tr = _tracker(tmp_path)
        _ingest(tr, days_ago=MATURITY_DAYS + 1)
        mon = RejectionAttributionMonitor(tracker=tr)
        summary_file = tmp_path / "daily_summary.jsonl"
        with patch("analysis.rejection_attribution_monitor.SUMMARY_DIR", str(tmp_path)), \
             patch("analysis.rejection_attribution_monitor.SUMMARY_FILE", str(summary_file)), \
             patch(
                "analysis.rejection_attribution_monitor._fetch_ohlcv_closes",
                return_value=[900.0, 890.0, 880.0, 870.0, 850.0],
             ):
            mon.run_daily_cycle()
        assert summary_file.exists()
        lines = summary_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["resolved_today"] == 1


class TestSafetyContract:
    def test_T08_no_forbidden_imports(self):
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "analysis", "rejection_attribution_monitor.py",
        )
        src = open(src_path, encoding="utf-8").read()
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker"):
            assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
            assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
