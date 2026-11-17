"""Phase 1 measurement integrity: cost model, session-close band, price confirmation."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from data_integrity import session_close_reference as reference
from models.transaction_costs import InstrumentType, TransactionCostModel
from trade_monitoring.trade_monitor import TradeMonitor


def _model() -> TransactionCostModel:
    return TransactionCostModel()


def test_delivery_has_no_brokerage_and_pays_dp_charge_once():
    cost = _model().compute("X", 20, 170.0, 170.0, InstrumentType.EQUITY_DELIVERY)
    assert cost.brokerage == 0.0
    assert cost.dp_charges == 14.75
    assert cost.total_cost == pytest.approx(
        cost.stt + cost.exchange_charges + cost.gst + cost.sebi_charges
        + cost.stamp_duty + cost.slippage + cost.dp_charges, abs=0.02)


def test_typical_small_delivery_trade_costs_far_less_than_the_old_flat_fee_model():
    cost = _model().compute("X", 20, 170.0, 170.0, InstrumentType.EQUITY_DELIVERY)
    # Previously a flat Rs40 brokerage plus GST pushed this near Rs64.
    assert cost.total_cost < 35.0


def test_intraday_brokerage_is_the_lower_of_flat_fee_or_percentage_per_order():
    small = _model().compute("X", 10, 100.0, 100.0, InstrumentType.EQUITY_INTRADAY)
    assert small.brokerage == pytest.approx(0.6)       # 0.03% of Rs1,000 on each side
    large = _model().compute("X", 1000, 1000.0, 1000.0, InstrumentType.EQUITY_INTRADAY)
    assert large.brokerage == 40.0                      # Rs20 cap on each side
    assert small.dp_charges == 0.0


def test_options_and_futures_keep_flat_per_order_brokerage():
    for kind in (InstrumentType.OPTIONS, InstrumentType.FUTURES):
        assert _model().compute("X", 50, 100.0, 110.0, kind).brokerage == 40.0


def _database(path: Path, symbol: str = "SBIN.NS", bars: int = 20,
              last_date: str | None = None, close: float = 960.0) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    last = date.fromisoformat(last_date or "2026-10-05")
    for index in range(bars):
        day = (last - timedelta(days=bars - 1 - index)).isoformat()
        conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,?,?,?,?,?)",
                     (symbol, day, close, close * 1.01, close * 0.99, close, 1000))
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clear_reference_cache():
    reference._cache.clear()
    yield
    reference._cache.clear()


def test_sbin_style_gap_outside_band_is_implausible_but_normal_moves_are_not(tmp_path):
    db = tmp_path / "market.db"
    _database(db)
    kwargs = dict(today="2026-10-06", db_path=db)
    assert reference.is_implausible_price("SBIN", 819.05, **kwargs)
    assert not reference.is_implausible_price("SBIN", 950.0, **kwargs)
    assert not reference.is_implausible_price("SBIN.NS", 1000.0, **kwargs)
    close, lower, upper = reference.plausible_band("SBIN", **kwargs)
    assert close == 960.0 and lower < 960.0 < upper


def test_band_widens_for_volatile_symbols(tmp_path):
    db = tmp_path / "market.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    for index in range(20):
        day = (date(2026, 10, 5) - timedelta(days=19 - index)).isoformat()
        conn.execute("INSERT INTO ohlcv_daily VALUES ('WILD.NS',?,100,108,92,100,1)", (day,))
    conn.commit()
    conn.close()
    _, lower, _ = reference.plausible_band("WILD", today="2026-10-06", db_path=db)
    assert lower < 100 * (1 - reference.MIN_BAND)


@pytest.mark.parametrize("kwargs", [
    dict(bars=5),                          # too little history
    dict(last_date="2026-09-20"),          # reference too old
])
def test_missing_or_stale_reference_fails_open(tmp_path, kwargs):
    db = tmp_path / "market.db"
    _database(db, **kwargs)
    assert reference.plausible_band("SBIN", today="2026-10-06", db_path=db) is None
    assert not reference.is_implausible_price("SBIN", 1.0, today="2026-10-06", db_path=db)


def test_unknown_symbol_and_missing_database_fail_open(tmp_path):
    db = tmp_path / "market.db"
    _database(db)
    assert not reference.is_implausible_price("NOPE", 1.0, today="2026-10-06", db_path=db)
    assert not reference.is_implausible_price("SBIN", 1.0, today="2026-10-06",
                                              db_path=tmp_path / "absent.db")


def _monitor() -> TradeMonitor:
    monitor = TradeMonitor.__new__(TradeMonitor)
    monitor._abnormal_seen = {}
    return monitor


class _Order:
    symbol = "SBIN"


def test_abnormal_price_is_held_until_it_repeats_then_accepted():
    monitor = _monitor()
    with patch("data_integrity.session_close_reference.is_implausible_price", return_value=True):
        assert monitor._price_confirmed("o1", _Order, 819.05) is False
        assert monitor._price_confirmed("o1", _Order, 819.60) is True


def test_a_different_abnormal_price_restarts_confirmation():
    monitor = _monitor()
    with patch("data_integrity.session_close_reference.is_implausible_price", return_value=True):
        assert monitor._price_confirmed("o1", _Order, 819.05) is False
        assert monitor._price_confirmed("o1", _Order, 700.0) is False
        assert monitor._price_confirmed("o1", _Order, 701.0) is True


def test_normal_price_clears_pending_confirmation():
    monitor = _monitor()
    with patch("data_integrity.session_close_reference.is_implausible_price", return_value=True):
        monitor._price_confirmed("o1", _Order, 819.05)
    with patch("data_integrity.session_close_reference.is_implausible_price", return_value=False):
        assert monitor._price_confirmed("o1", _Order, 955.0) is True
    assert "o1" not in monitor._abnormal_seen


def test_reference_failure_never_blocks_an_exit():
    monitor = _monitor()
    with patch("data_integrity.session_close_reference.is_implausible_price",
               side_effect=RuntimeError("boom")):
        assert monitor._price_confirmed("o1", _Order, 1.0) is True


def test_confirmation_runs_before_the_price_becomes_the_trusted_baseline():
    source = (Path(__file__).resolve().parents[1] / "trade_monitoring" / "trade_monitor.py"
              ).read_text(encoding="utf-8")
    call = source.index("self._price_confirmed(oid, order, ltp)")
    baseline = source.index("self._last_good_ltp[oid] = ltp", call)
    assert call < baseline
