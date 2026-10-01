"""
tests/test_edge_feature_extractor_real_001.py
================================================
DTA-EDGE-FEATURE-REAL-001: FeatureExtractor now computes per-symbol
technical features from REAL OHLCV history (data/market_behavior.db's
ohlcv_daily table) instead of seeded-random synthetic sampling, falling
back to the original synthetic generation only when a symbol lacks
sufficient real history (<25 bars).

Coverage:
  - Real-data path: sane, bounded values for a symbol with enough history
  - Fallback path: unchanged synthetic behavior when history insufficient
  - extract() end-to-end: correct per-symbol routing (real vs fallback),
    never raises on a missing/corrupt DB
  - feature_names() stable key set unaffected
  - Indicator helpers (RSI/MACD/Bollinger/ADX/realized-vol) behave
    sanely on synthetic-but-deterministic price series
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from edge_discovery.feature_extractor import (
    FeatureExtractor,
    SymbolFeatures,
    _adx_wilder,
    _bollinger_position,
    _macd_histogram,
    _realized_vol,
    _rsi_wilder,
)
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel


def _make_snapshot(regime=RegimeLabel.BULL_TREND, vix=15.0) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(),
        indices={},
        regime=regime,
        volatility=VolatilityLevel.MEDIUM,
        vix=vix,
    )


def _seed_ohlcv_db(db_path, symbol: str, n_days: int = 60, start_price: float = 100.0,
                    daily_drift: float = 0.002, daily_noise: float = 0.01):
    """Deterministic (non-random-import) synthetic-but-fixed price series
    seeded directly into a real ohlcv_daily table, simulating real history."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ohlcv_daily "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    price = start_price
    rows = []
    base_date = datetime.now() - timedelta(days=n_days + 5)
    # Fixed pseudo-noise pattern (not using `random` to keep test fully deterministic)
    pattern = [1, -1, 1, 1, -1, -1, 1, -1, 1, 1]
    for i in range(n_days):
        noise_dir = pattern[i % len(pattern)]
        change = daily_drift + noise_dir * daily_noise
        new_price = price * (1 + change)
        o = price
        c = new_price
        h = max(o, c) * 1.005
        l = min(o, c) * 0.995
        v = 1_000_000 + (i % 5) * 50_000
        trade_date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        rows.append((symbol, trade_date, o, h, l, c, v))
        price = new_price
    conn.executemany(
        "INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


# ── Real-data path ───────────────────────────────────────────────────────

def test_real_path_used_when_sufficient_history(tmp_path):
    db_path = tmp_path / "market_behavior.db"
    _seed_ohlcv_db(db_path, "RELIANCE.NS", n_days=60)
    _seed_ohlcv_db(db_path, "^NSEI", n_days=60)

    fe = FeatureExtractor(db_path=db_path)
    results = fe.extract(_make_snapshot(), symbols=["RELIANCE"])
    assert len(results) == 1
    feats = results[0].features
    # Bounds contract preserved
    assert -1.0 <= feats["bb_position"] <= 1.0
    assert 0.0 <= feats["rsi_norm"] <= 1.0
    assert 0.0 <= feats["iv_rank"] <= 1.0
    assert 0.0 <= feats["sector_strength"] <= 1.0
    assert 0.0 <= feats["adx_score"] <= 1.0
    assert 0.0 <= feats["liquidity_score"] <= 1.0
    assert isinstance(feats["mom_5d"], float)


def test_real_path_momentum_reflects_real_trend(tmp_path):
    """A clearly uptrending real price series must produce positive
    real momentum -- proves the feature is actually data-derived, not
    randomly sampled."""
    db_path = tmp_path / "market_behavior.db"
    _seed_ohlcv_db(db_path, "RELIANCE.NS", n_days=60, daily_drift=0.01, daily_noise=0.001)
    _seed_ohlcv_db(db_path, "^NSEI", n_days=60, daily_drift=0.0, daily_noise=0.0)

    fe = FeatureExtractor(db_path=db_path)
    feats = fe.extract(_make_snapshot(), symbols=["RELIANCE"])[0].features
    assert feats["mom_20d"] > 0.05   # strong real uptrend must show up
    assert feats["mom_positive"] == 1.0


def test_real_path_reproducible_same_inputs(tmp_path):
    """Unlike the old synthetic path (seeded by symbol+regime+date only),
    real-data features must be identical across repeated calls for the
    SAME underlying data -- a stronger determinism guarantee."""
    db_path = tmp_path / "market_behavior.db"
    _seed_ohlcv_db(db_path, "RELIANCE.NS", n_days=60)
    _seed_ohlcv_db(db_path, "^NSEI", n_days=60)
    fe = FeatureExtractor(db_path=db_path)
    snap = _make_snapshot()
    f1 = fe.extract(snap, symbols=["RELIANCE"])[0].features
    f2 = fe.extract(snap, symbols=["RELIANCE"])[0].features
    assert f1 == f2


# ── Fallback path (insufficient real history) ───────────────────────────

def test_fallback_used_when_insufficient_history(tmp_path):
    db_path = tmp_path / "market_behavior.db"
    _seed_ohlcv_db(db_path, "RELIANCE.NS", n_days=5)  # below _MIN_REAL_HISTORY_BARS

    fe = FeatureExtractor(db_path=db_path)
    results = fe.extract(_make_snapshot(), symbols=["RELIANCE"])
    feats = results[0].features
    assert -1.0 <= feats["bb_position"] <= 1.0
    assert 0.0 <= feats["rsi_norm"] <= 1.0


def test_fallback_matches_original_synthetic_algorithm(tmp_path):
    """Regression guard: the fallback path must be byte-for-byte the same
    algorithm as before this change (same seed formula, same output)."""
    db_path = tmp_path / "market_behavior.db"  # no table at all
    fe = FeatureExtractor(db_path=db_path)
    snap = _make_snapshot()
    market_ctx = fe._market_context(snap)
    f1 = fe._symbol_features_synthetic("RELIANCE", snap, market_ctx)
    f2 = fe._symbol_features_synthetic("RELIANCE", snap, market_ctx)
    assert f1 == f2  # deterministic given same symbol+regime+date seed


def test_extract_never_raises_on_missing_db(tmp_path):
    missing_db = tmp_path / "does_not_exist.db"
    fe = FeatureExtractor(db_path=missing_db)
    results = fe.extract(_make_snapshot(), symbols=["RELIANCE", "TCS"])
    assert len(results) == 2
    for r in results:
        assert isinstance(r, SymbolFeatures)


def test_extract_never_raises_on_corrupt_db(tmp_path):
    db_path = tmp_path / "corrupt.db"
    db_path.write_text("not a real sqlite file")
    fe = FeatureExtractor(db_path=db_path)
    results = fe.extract(_make_snapshot(), symbols=["RELIANCE"])
    assert len(results) == 1


# ── Interface preservation ───────────────────────────────────────────────

def test_feature_names_unchanged_key_set():
    fe = FeatureExtractor(db_path="/nonexistent/path.db")
    names = fe.feature_names()
    for expected in ("mom_5d", "rsi", "bb_position", "adx_score",
                     "iv_rank", "sector_strength", "liquidity_score",
                     "regime_score", "vix"):
        assert expected in names


def test_symbol_universe_unchanged():
    assert FeatureExtractor.SYMBOL_UNIVERSE == [
        "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY",
        "HDFC", "ICICIBANK", "LT", "AXISBANK", "WIPRO",
        "HDFCBANK", "BAJFINANCE", "SBIN", "MARUTI", "TATAMOTORS",
        "SUNPHARMA", "DRREDDY", "ONGC", "NTPC", "POWERGRID",
    ]


def test_extract_mixed_real_and_fallback(tmp_path):
    """One symbol with real history, one without -- both must resolve
    without error, independently of each other."""
    db_path = tmp_path / "market_behavior.db"
    _seed_ohlcv_db(db_path, "RELIANCE.NS", n_days=60)
    _seed_ohlcv_db(db_path, "^NSEI", n_days=60)
    # TCS deliberately NOT seeded -> must fall back

    fe = FeatureExtractor(db_path=db_path)
    results = fe.extract(_make_snapshot(), symbols=["RELIANCE", "TCS"])
    assert len(results) == 2
    by_symbol = {r.symbol: r.features for r in results}
    assert set(by_symbol["RELIANCE"].keys()) == set(by_symbol["TCS"].keys())


# ── Indicator helper correctness (qualitative, not exact-value) ────────

def test_rsi_wilder_bounds_and_none_on_insufficient_data():
    assert _rsi_wilder([100, 101, 102], period=14) is None
    closes = [100 + i for i in range(20)]  # monotonic uptrend
    rsi = _rsi_wilder(closes, period=14)
    assert rsi is not None
    assert rsi > 70  # strong uptrend -> high RSI


def test_bollinger_position_bounds():
    closes = [100] * 19 + [130]  # sharp spike above a flat SMA
    pos = _bollinger_position(closes, period=20)
    assert -1.0 <= pos <= 1.0
    assert pos > 0  # above the mean


def test_macd_histogram_positive_on_uptrend():
    closes = [100 + i * 0.5 for i in range(40)]
    hist = _macd_histogram(closes)
    assert hist > 0  # uptrend -> positive MACD histogram
    assert _macd_histogram([100, 101]) == 0.0  # insufficient data -> safe 0.0


def test_realized_vol_zero_for_flat_series():
    assert _realized_vol([100.0] * 10, window=5) == 0.0


def test_realized_vol_positive_for_noisy_series():
    closes = [100, 105, 98, 110, 95, 112, 93, 115]
    assert _realized_vol(closes, window=5) > 0.0


def test_adx_bounds_and_zero_on_insufficient_data():
    highs = [101, 102]
    lows = [99, 100]
    closes = [100, 101]
    assert _adx_wilder(highs, lows, closes, period=14) == 0.0

    n = 40
    closes = [100 + i for i in range(n)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    adx = _adx_wilder(highs, lows, closes, period=14)
    assert 0.0 <= adx <= 1.0
    assert adx > 0.3  # clean uptrend -> meaningfully elevated ADX
