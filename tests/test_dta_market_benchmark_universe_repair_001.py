"""Focused tests for complete, date-correct eligible-universe benchmarks."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import opportunity_engine.market_opportunity_benchmark as benchmark
import predictive_gap.pga_collector as collector
from opportunity_engine.market_opportunity_benchmark import MoverCategory, MoverRecord, ClassifiedMover
from predictive_gap.pga_collector import SignalRecord, _fetch_price_data, _fetch_prices_local_then_network
from predictive_gap.pga_config import PGAConfig


def _create_ohlcv_db(path: Path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE ohlcv_daily "
            "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, "
            "close REAL, volume REAL)"
        )
        conn.executemany(
            "INSERT INTO ohlcv_daily(symbol, trade_date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def test_default_config_and_universe_loader_are_uncapped(tmp_path):
    symbols = [{"symbol": f"EQ{i:03d}.NS"} for i in range(500)]
    universe_file = tmp_path / "universe.json"
    universe_file.write_text(json.dumps(symbols), encoding="utf-8")

    with patch.object(collector, "UNIVERSE_FILE", universe_file):
        assert PGAConfig().max_symbols_for_price_fetch == 0
        loaded = collector._load_universe(PGAConfig().max_symbols_for_price_fetch)

    assert len(loaded) == 500
    assert loaded[0] == "EQ000"
    assert loaded[-1] == "EQ499"


def test_full_500_local_universe_coverage_and_scanned_extra_exclusion(tmp_path):
    report_date = "2026-11-11"
    universe = [f"EQ{i:03d}" for i in range(500)]
    local_rows = []
    for i, symbol in enumerate(universe):
        close = 100.0 + (i - 250) / 10
        local_rows.append((f"{symbol}.NS", report_date, 100.0, close, close, close, 1000.0))
    db_path = tmp_path / "market_behavior.db"
    _create_ohlcv_db(db_path, local_rows)

    extra_move = collector.StockMove(
        symbol="SCANNED_EXTRA", open_price=100, close_price=500,
        daily_return_pct=400, volume=10, move_type="GAINER",
        actual_direction="UP", data_source="yfinance",
    )
    with patch.object(collector, "MARKET_BEHAVIOR_DB", db_path), \
         patch.object(collector, "_load_market_stats", return_value={}), \
         patch.object(collector, "_load_ct_decisions", return_value=([], [])), \
         patch.object(collector, "_load_ct_signals", return_value=[
             SignalRecord("SCANNED_EXTRA", "UP", 7.0, "test", "cycle", "ts")
         ]), \
         patch.object(collector, "_load_executed_trades", return_value=[]), \
         patch("predictive_gap.scan_attrition.load_attrition", return_value=[]), \
         patch.object(collector, "_load_dna_coverage", return_value={}), \
         patch.object(collector, "_load_edge_coverage", return_value={}), \
         patch.object(collector, "_fetch_price_data", return_value={"SCANNED_EXTRA": extra_move}) as fetch:
        gainers, losers, coverage = benchmark._collect_nifty500_movers(
            report_date, 5, universe, {
                "universe_identity": "LIQUIDITY_SELECTED_ELIGIBLE_UNIVERSE",
                "membership_is_pit": True,
                "membership_status": "FROZEN_DATE_SNAPSHOT",
                "snapshot_path": "isolated",
            },
        )

    assert fetch.call_count == 1
    assert fetch.call_args.args[0] == ["SCANNED_EXTRA"]
    assert len(gainers) == len(losers) == 5
    assert all(m.symbol in universe for m in gainers + losers)
    assert gainers[0].symbol != "SCANNED_EXTRA"
    assert coverage["eligible_symbols"] == coverage["priced_symbols"] == 500
    assert coverage["missing_symbols"] == 0
    assert coverage["price_coverage_pct"] == 100.0
    assert gainers[0].benchmark_type == "NIFTY500"  # compatibility label
    assert gainers[0].universe_identity == "LIQUIDITY_SELECTED_ELIGIBLE_UNIVERSE"
    assert gainers[0].membership_is_pit is True


def test_local_prices_are_exact_date_and_only_missing_symbols_fall_back(tmp_path):
    report_date = "2026-11-11"
    db_path = tmp_path / "market_behavior.db"
    _create_ohlcv_db(db_path, [
        ("A.NS", report_date, 100, 103, 99, 102, 500),
        ("B.NS", "2026-11-10", 100, 110, 90, 109, 500),
    ])
    network_b = collector.StockMove(
        symbol="B", open_price=100, close_price=101, daily_return_pct=1,
        volume=20, move_type="NEUTRAL", actual_direction="UP", data_source="yfinance",
    )
    real_connect = sqlite3.connect
    close_calls = []

    class ConnectionProxy:
        def __init__(self, conn):
            self._conn = conn

        def execute(self, *args, **kwargs):
            return self._conn.execute(*args, **kwargs)

        def close(self):
            close_calls.append(True)
            self._conn.close()

    def tracked_connect(*args, **kwargs):
        return ConnectionProxy(real_connect(*args, **kwargs))

    with patch.object(collector, "MARKET_BEHAVIOR_DB", db_path), \
         patch.object(collector.sqlite3, "connect", side_effect=tracked_connect), \
         patch.object(collector, "_fetch_price_data", return_value={"B": network_b}) as fetch:
        moves = _fetch_prices_local_then_network(["A", "B"], report_date, batch_size=10)

    assert list(moves) == ["A", "B"]
    assert moves["A"].data_source == "local_ohlcv"
    assert moves["A"].close_price == 102
    assert moves["B"].data_source == "yfinance"
    fetch.assert_called_once_with(["B"], report_date)
    assert close_calls == [True]


def test_missing_exact_date_prices_are_reported_not_ranked(tmp_path):
    report_date = "2026-11-11"
    db_path = tmp_path / "market_behavior.db"
    _create_ohlcv_db(db_path, [
        ("A.NS", report_date, 100, 103, 99, 102, 500),
        ("B.NS", "2026-11-10", 100, 110, 90, 109, 500),
    ])
    with patch.object(collector, "MARKET_BEHAVIOR_DB", db_path), \
         patch.object(collector, "_load_market_stats", return_value={}), \
         patch.object(collector, "_load_ct_decisions", return_value=([], [])), \
         patch.object(collector, "_load_ct_signals", return_value=[]), \
         patch.object(collector, "_load_executed_trades", return_value=[]), \
         patch("predictive_gap.scan_attrition.load_attrition", return_value=[]), \
         patch.object(collector, "_load_dna_coverage", return_value={}), \
         patch.object(collector, "_load_edge_coverage", return_value={}), \
         patch.object(collector, "_fetch_price_data", return_value={}):
        gainers, losers, coverage = benchmark._collect_nifty500_movers(
            report_date, 5, ["A", "B"], {
                "universe_identity": "LIQUIDITY_SELECTED_ELIGIBLE_UNIVERSE",
                "membership_is_pit": False,
                "membership_status": "NON_PIT_NO_HISTORICAL_SNAPSHOT",
            },
        )

    assert coverage["eligible_symbols"] == 2
    assert coverage["priced_symbols"] == 1
    assert coverage["missing_symbols"] == 1
    assert coverage["missing_symbol_list"] == ["B"]
    assert coverage["price_coverage_pct"] == 50.0
    assert gainers and all(move.symbol == "A" for move in gainers + losers)
    assert gainers[0].membership_is_pit is False


def test_yfinance_fallback_does_not_substitute_prior_date(monkeypatch):
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame(
        {"Open": [100.0], "Close": [110.0], "Volume": [1000]},
        index=pd.to_datetime(["2026-11-10"]),
    )
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=lambda **kwargs: frame))

    assert _fetch_price_data(["A"], "2026-11-11") == {}


def test_yfinance_fallback_rejects_non_finite_exact_date_prices(monkeypatch):
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame(
        {"Open": [float("nan")], "Close": [110.0], "Volume": [1000]},
        index=pd.to_datetime(["2026-11-11"]),
    )
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=lambda **kwargs: frame))

    assert _fetch_price_data(["A"], "2026-11-11") == {}


def test_current_membership_snapshot_is_frozen_and_historical_is_not_fabricated(tmp_path):
    universe_file = tmp_path / "universe.json"
    universe_file.write_text(json.dumps([{"symbol": "A"}, {"symbol": "B"}]), encoding="utf-8")
    today = datetime.now().date().isoformat()

    with patch.object(benchmark, "BENCHMARK_DIR", tmp_path / "benchmark"), \
         patch.object(collector, "UNIVERSE_FILE", universe_file):
        first_symbols, first_metadata = benchmark._load_or_freeze_eligible_universe(today)
        universe_file.write_text(json.dumps([{"symbol": "C"}]), encoding="utf-8")
        repeated_symbols, repeated_metadata = benchmark._load_or_freeze_eligible_universe(today)
        historical_symbols, historical_metadata = benchmark._load_or_freeze_eligible_universe(
            "2020-01-02")

        snapshot = tmp_path / "benchmark" / "universe_snapshots" / f"eligible_universe_{today}.json"
        historical_snapshot = (
            tmp_path / "benchmark" / "universe_snapshots" / "eligible_universe_2020-01-02.json"
        )

    assert first_symbols == repeated_symbols == ["A", "B"]
    assert first_metadata["membership_is_pit"] is True
    assert repeated_metadata["membership_status"] == "FROZEN_DATE_SNAPSHOT"
    assert snapshot.exists()
    assert historical_symbols == ["C"]  # current fallback only, not claimed as historical
    assert historical_metadata["membership_is_pit"] is False
    assert historical_metadata["membership_status"] == "NON_PIT_NO_HISTORICAL_SNAPSHOT"
    assert not historical_snapshot.exists()


def test_benchmark_report_persists_coverage_metadata(tmp_path):
    with patch.object(benchmark, "BENCHMARK_DIR", tmp_path):
        benchmark._write_outputs("2026-11-11", [
            ClassifiedMover(
                MoverRecord(
                    trade_date="2026-11-11", symbol="A", benchmark_type="NIFTY500",
                    move_type="GAINER", daily_return_pct=2.0, direction="UP",
                    source="local_ohlcv", methodology="test", universe_size=500,
                ),
                MoverCategory.OUTSIDE_UNIVERSE,
            )
        ], report_metadata={
            "trade_date": "2026-11-11",
            "eligible_universe": {
                "universe_identity": "LIQUIDITY_SELECTED_ELIGIBLE_UNIVERSE",
                "membership_is_pit": False,
                "membership_status": "NON_PIT_NO_HISTORICAL_SNAPSHOT",
                "eligible_symbols": 500,
                "priced_symbols": 490,
                "missing_symbols": 10,
                "price_coverage_pct": 98.0,
                "official_index_constituents_verified": False,
            },
        })

    metadata = json.loads(
        (tmp_path / "MARKET_BENCHMARK_2026-11-11_metadata.json").read_text(encoding="utf-8")
    )
    markdown = (tmp_path / "MARKET_BENCHMARK_2026-11-11.md").read_text(encoding="utf-8")
    record = json.loads(
        (tmp_path / "MARKET_BENCHMARK_2026-11-11.jsonl").read_text(encoding="utf-8").strip()
    )
    assert metadata["eligible_universe"]["eligible_symbols"] == 500
    assert metadata["eligible_universe"]["priced_symbols"] == 490
    assert "500/490/10" in markdown
    assert "point-in-time=False" in markdown
    assert record["benchmark_type"] == "NIFTY500"
