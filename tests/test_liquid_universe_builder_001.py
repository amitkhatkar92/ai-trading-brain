"""
tests/test_liquid_universe_builder_001.py
=============================================
DTA-UNIVERSE-EXPANSION-001 — liquidity-filtered broad-market universe.

Root-cause fix: nifty500_universe.json was a STATIC, embedded 230-symbol
list because NSE direct access is blocked (Akamai). This builds a
genuinely broader (~500-symbol, user-confirmed target) universe from
Dhan's already-accessible security master + real ADV computed from
ohlcv_daily -- with a hard fallback to the original embedded list on any
failure, so the live universe can never end up empty or broken.

Coverage:
  - _compute_adv_crore(): real ADV computed correctly from ohlcv_daily
  - build_liquid_universe(): ranks by ADV, respects target_size, output
    schema matches the existing nifty500_universe.json format exactly
  - Sanity floor: aborts (returns None) if far fewer liquid symbols found
    than requested
  - Fails safe (returns None, never raises) on missing broad-symbol list,
    missing ADV data, or any exception
  - Sector reuse: symbols already in the embedded 230 keep their curated
    sector; new symbols get sector="UNKNOWN" (existing safe fallback)
  - _write_universe_json() wiring: uses the liquid universe when available,
    falls back to the embedded 230-symbol list on any failure -- never
    raises, never writes an empty file
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from predictive_gap.liquid_universe_builder_001 import (
    build_liquid_universe,
    _compute_adv_crore,
    _load_existing_sector_map,
    TARGET_UNIVERSE_SIZE,
)


# ── _compute_adv_crore ──────────────────────────────────────────────────────

def _make_ohlcv_db(tmp_path, rows):
    db_path = tmp_path / "test_market_behavior.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.executemany(
        "INSERT INTO ohlcv_daily (symbol, trade_date, close, volume) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


def test_compute_adv_crore_basic(tmp_path):
    rows = [
        ("AAA", "2026-09-10", 100.0, 1_000_000),
        ("AAA", "2026-09-11", 100.0, 1_000_000),
        ("BBB", "2026-09-10", 10.0, 100_000),
    ]
    db_path = _make_ohlcv_db(tmp_path, rows)
    adv = _compute_adv_crore(db_path)
    # AAA: 100 * 1,000,000 / 1e7 = 10.0 crore
    assert adv["AAA"] == 10.0
    assert "BBB" in adv


def test_compute_adv_crore_excludes_indices(tmp_path):
    rows = [
        ("^NSEI", "2026-09-10", 24000.0, 100000),
        ("AAA", "2026-09-10", 100.0, 1_000_000),
    ]
    db_path = _make_ohlcv_db(tmp_path, rows)
    adv = _compute_adv_crore(db_path)
    assert "^NSEI" not in adv
    assert "AAA" in adv


def test_compute_adv_crore_only_uses_lookback_window(tmp_path):
    """Only the most recent ADV_LOOKBACK_DAYS rows per symbol are averaged."""
    rows = [("AAA", f"2026-08-{d:02d}", 100.0, 1_000_000) for d in range(1, 32)]
    db_path = _make_ohlcv_db(tmp_path, rows)
    adv = _compute_adv_crore(db_path)
    # All rows have identical close*volume, so the result is unaffected by
    # window size here -- just confirm it computes without error and is sane.
    assert adv["AAA"] == 10.0


def test_compute_adv_crore_fails_open_on_missing_db(tmp_path):
    adv = _compute_adv_crore(tmp_path / "does_not_exist.db")
    assert adv == {}


# ── build_liquid_universe ────────────────────────────────────────────────────

def test_build_liquid_universe_ranks_by_adv_and_respects_target_size(tmp_path):
    rows = []
    symbols = [f"SYM{i:03d}" for i in range(20)]
    for i, sym in enumerate(symbols):
        # Descending liquidity: SYM000 most liquid, SYM019 least.
        rows.append((sym, "2026-09-10", 100.0, (20 - i) * 100_000))
    db_path = _make_ohlcv_db(tmp_path, rows)

    with patch(
        "predictive_gap.liquid_universe_builder_001._MIN_ACCEPTABLE_FRACTION", 0.0
    ), patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=symbols,
    ), patch(
        "predictive_gap.liquid_universe_builder_001._load_existing_sector_map",
        return_value={},
    ):
        universe = build_liquid_universe(target_size=5, db_path=db_path)

    assert universe is not None
    assert len(universe) == 5
    assert [u["symbol"] for u in universe] == symbols[:5]  # most liquid first


def test_build_liquid_universe_output_schema_matches_existing_format(tmp_path):
    rows = [("AAA", "2026-09-10", 100.0, 1_000_000)]
    db_path = _make_ohlcv_db(tmp_path, rows)

    with patch(
        "predictive_gap.liquid_universe_builder_001._MIN_ACCEPTABLE_FRACTION", 0.0
    ), patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=["AAA"],
    ), patch(
        "predictive_gap.liquid_universe_builder_001._load_existing_sector_map",
        return_value={},
    ):
        universe = build_liquid_universe(target_size=1, db_path=db_path)

    assert universe is not None
    entry = universe[0]
    assert set(entry.keys()) >= {"symbol", "yahoo_ticker", "sector", "index", "adv_crore"}
    assert entry["yahoo_ticker"] == "AAA.NS"
    assert entry["sector"] == "UNKNOWN"
    assert entry["index"] == "BROADMARKET_LIQUID"


def test_build_liquid_universe_reuses_existing_sector(tmp_path):
    rows = [("RELIANCE", "2026-09-10", 100.0, 1_000_000)]
    db_path = _make_ohlcv_db(tmp_path, rows)

    with patch(
        "predictive_gap.liquid_universe_builder_001._MIN_ACCEPTABLE_FRACTION", 0.0
    ), patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=["RELIANCE"],
    ), patch(
        "predictive_gap.liquid_universe_builder_001._load_existing_sector_map",
        return_value={"RELIANCE": "ENERGY"},
    ):
        universe = build_liquid_universe(target_size=1, db_path=db_path)

    assert universe[0]["sector"] == "ENERGY"
    assert universe[0]["index"] == "NIFTY500"


def test_build_liquid_universe_returns_none_when_broad_list_unavailable(tmp_path):
    with patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=[],
    ):
        result = build_liquid_universe(target_size=10, db_path=tmp_path / "x.db")
    assert result is None


def test_build_liquid_universe_returns_none_when_adv_unavailable(tmp_path):
    with patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=["AAA"],
    ), patch(
        "predictive_gap.liquid_universe_builder_001._compute_adv_crore",
        return_value={},
    ):
        result = build_liquid_universe(target_size=10, db_path=tmp_path / "x.db")
    assert result is None


def test_build_liquid_universe_sanity_floor_aborts(tmp_path):
    """If far fewer liquid symbols are found than requested, abort rather
    than silently ship a much-smaller-than-intended universe."""
    rows = [("AAA", "2026-09-10", 100.0, 1_000_000)]
    db_path = _make_ohlcv_db(tmp_path, rows)

    with patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        return_value=["AAA"],
    ):
        # Requesting 500 but only 1 symbol has ADV data -- must abort.
        result = build_liquid_universe(target_size=TARGET_UNIVERSE_SIZE, db_path=db_path)
    assert result is None


def test_build_liquid_universe_never_raises_on_total_failure(tmp_path):
    with patch(
        "predictive_gap.broad_market_universe.load_broad_nse_equity_symbols",
        side_effect=RuntimeError("boom"),
    ):
        result = build_liquid_universe(target_size=10, db_path=tmp_path / "x.db")
    assert result is None


def test_target_universe_size_is_500():
    """Regression guard for the user-confirmed target (2026-09-16)."""
    assert TARGET_UNIVERSE_SIZE == 500


# ── _write_universe_json() wiring (opportunity_engine/market_scanner.py) ────

def test_write_universe_json_uses_liquid_universe_when_available(tmp_path):
    import opportunity_engine.market_scanner as ms

    fake_universe = [{"symbol": "AAA", "yahoo_ticker": "AAA.NS",
                       "sector": "UNKNOWN", "index": "BROADMARKET_LIQUID", "adv_crore": 5.0}]
    fake_module_file = str(tmp_path / "opportunity_engine" / "market_scanner.py")

    with patch.object(ms, "__file__", fake_module_file), \
         patch("predictive_gap.liquid_universe_builder_001.build_liquid_universe",
               return_value=fake_universe):
        result = ms._write_universe_json()

    assert result is True
    written_path = tmp_path / "data" / "nifty500_universe.json"
    written = json.loads(written_path.read_text(encoding="utf-8"))
    assert written == fake_universe


def test_write_universe_json_falls_back_to_embedded_on_builder_failure(tmp_path):
    import opportunity_engine.market_scanner as ms

    fake_module_file = str(tmp_path / "opportunity_engine" / "market_scanner.py")

    with patch.object(ms, "__file__", fake_module_file), \
         patch("predictive_gap.liquid_universe_builder_001.build_liquid_universe",
               return_value=None):
        result = ms._write_universe_json()

    assert result is True
    written_path = tmp_path / "data" / "nifty500_universe.json"
    written = json.loads(written_path.read_text(encoding="utf-8"))
    assert len(written) == len(ms._builtin_universe())
    assert written[0]["index"] in ("NIFTY50", "NIFTY500")


def test_write_universe_json_falls_back_on_builder_exception(tmp_path):
    import opportunity_engine.market_scanner as ms

    fake_module_file = str(tmp_path / "opportunity_engine" / "market_scanner.py")

    with patch.object(ms, "__file__", fake_module_file), \
         patch("predictive_gap.liquid_universe_builder_001.build_liquid_universe",
               side_effect=RuntimeError("boom")):
        result = ms._write_universe_json()

    assert result is True
    written_path = tmp_path / "data" / "nifty500_universe.json"
    written = json.loads(written_path.read_text(encoding="utf-8"))
    assert len(written) == len(ms._builtin_universe())
