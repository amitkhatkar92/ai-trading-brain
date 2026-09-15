"""
tests/test_hkap_kde_bridge.py
================================
Self-Learning Ecosystem Phase 6 — HKAP -> KDE evidence expansion.

T01  run_hkap_kde_discovery() returns INSUFFICIENT_YEARS when fewer than
     min_years packages are available, and never calls KDEEngine
T02  ... with >=2 real-shaped packages, runs CrossYearAnalyzer + KDEEngine
     and returns a correctly-shaped OK summary
T03  get_latest_discovery_run()/get_discovery_run_history() read back what
     was recorded, oldest-first
T04  run_hkap_kde_discovery() never raises even when HKAPEngine() itself
     raises (fail-open)
T05  HKAPEngine.get_completed_packages() only returns COMPLETE-status
     packages, never PENDING/FAILED
T06  Never imports execution_engine/order_manager/broker/risk_control/
     knowledge_authority (safety contract)
T07  snapshot_builder.HistoricalSnapshotBuilder._load_or_download()
     root-cause fix: survives a MultiIndex-columned yfinance DataFrame
     (newer yfinance/numpy shape) without raising
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import hkap.hkap_kde_bridge as bridge


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path):
    history_file = tmp_path / "run_history.jsonl"
    with patch.object(bridge, "HISTORY_DIR", str(tmp_path)), \
         patch.object(bridge, "HISTORY_FILE", str(history_file)):
        yield history_file


def _fake_package(year, status="COMPLETE"):
    from hkap.hkap_models import YearKnowledgePackage
    return YearKnowledgePackage(
        year=year, status=status, market_profile=None, dna_snapshot=None,
        edge_snapshot=None, sd_review=None, prior_years_context=[],
        trading_days_analyzed=0, universe_size=0, completed_at="",
        reports=[], stage_statuses={},
    )


class TestInsufficientYears:
    def test_T01_insufficient_years_skips_kde(self, _isolated_history):
        with patch("hkap.hkap_engine.HKAPEngine") as MockEngine:
            MockEngine.return_value.get_completed_packages.return_value = {
                2023: _fake_package(2023),
            }
            with patch("kde.kde_engine.KDEEngine") as MockKDE:
                result = bridge.run_hkap_kde_discovery(min_years=2)
        assert result["status"] == "INSUFFICIENT_YEARS"
        assert result["years_available"] == [2023]
        MockKDE.assert_not_called()


class TestDiscoveryRun:
    def test_T02_runs_analyzer_and_kde_with_enough_years(self, _isolated_history):
        packages = {2023: _fake_package(2023), 2024: _fake_package(2024)}
        with patch("hkap.hkap_engine.HKAPEngine") as MockEngine:
            MockEngine.return_value.get_completed_packages.return_value = packages
            with patch("hkap.cross_year_analyzer.CrossYearAnalyzer") as MockAnalyzer:
                MockAnalyzer.return_value.analyze.return_value = ([], [])
                with patch("kde.kde_engine.KDEEngine") as MockKDE:
                    fake_result = MagicMock()
                    fake_result.discoveries = []
                    fake_result.statistics.high_value_count = 0
                    fake_result.statistics.avg_score = 0.0
                    fake_result.reports = ["data/kde/reports/DISCOVERY_SUMMARY.md"]
                    MockKDE.return_value.run.return_value = fake_result
                    result = bridge.run_hkap_kde_discovery(min_years=2)
        assert result["status"] == "OK"
        assert result["years_used"] == [2023, 2024]
        assert result["total_discoveries"] == 0
        MockAnalyzer.return_value.analyze.assert_called_once_with(packages)


class TestHistoryPersistence:
    def test_T03_history_read_back(self, _isolated_history):
        bridge._record_run({"status": "OK", "years_used": [2023, 2024], "total_discoveries": 3})
        bridge._record_run({"status": "OK", "years_used": [2023, 2024, 2025], "total_discoveries": 5})
        latest = bridge.get_latest_discovery_run()
        assert latest["total_discoveries"] == 5
        hist = bridge.get_discovery_run_history(n=10)
        assert [h["total_discoveries"] for h in hist] == [3, 5]


class TestFailOpen:
    def test_T04_never_raises_when_engine_raises(self, _isolated_history):
        with patch("hkap.hkap_engine.HKAPEngine", side_effect=RuntimeError("boom")):
            result = bridge.run_hkap_kde_discovery()
        assert result["status"] == "ERROR"


class TestGetCompletedPackages:
    def test_T05_only_returns_complete_status(self):
        from hkap.hkap_config import HKAPConfig
        from hkap.hkap_engine import HKAPEngine
        with patch.object(HKAPEngine, "_load_persisted_results"), \
             patch.object(HKAPEngine, "_build_default_ptue", return_value=MagicMock()):
            engine = HKAPEngine(config=HKAPConfig(years=[2020, 2021, 2022]))
        engine._results = {
            2020: _fake_package(2020, status="COMPLETE"),
            2021: _fake_package(2021, status="FAILED"),
            2022: _fake_package(2022, status="PENDING"),
        }
        completed = engine.get_completed_packages()
        assert list(completed.keys()) == [2020]


class TestSafetyContract:
    def test_T06_no_forbidden_imports(self):
        import os
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "hkap", "hkap_kde_bridge.py",
        )
        src = open(src_path, encoding="utf-8").read()
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker",
                          "risk_control", "knowledge_authority"):
            assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
            assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"


class TestSnapshotBuilderRootCauseFix:
    def test_T07_survives_multiindex_columns(self, tmp_path):
        from hkap.snapshot_builder import HistoricalSnapshotBuilder

        idx = pd.date_range("2023-01-02", periods=3, freq="D")
        cols = pd.MultiIndex.from_product([["Close", "High", "Low", "Volume"], ["RELIANCE.NS"]])
        fake_df = pd.DataFrame(
            [[100.0, 101.0, 99.0, 1000.0],
             [101.0, 102.0, 100.0, 1100.0],
             [102.0, 103.0, 101.0, 1200.0]],
            index=idx, columns=cols,
        )

        builder = HistoricalSnapshotBuilder(cache_dir=tmp_path, sector_map={}, dry_run=False)
        with patch("yfinance.download", return_value=fake_df):
            data = builder._load_or_download("RELIANCE", 2023, "2023-01-01", "2023-01-05")

        assert data is not None
        assert data["closes"] == [100.0, 101.0, 102.0]
        assert data["volumes"] == [1000.0, 1100.0, 1200.0]
