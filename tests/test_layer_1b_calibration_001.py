"""Layer 1B cross-sectional calibration: relative cutoffs keep base rates stable.

Measured on production data once bhav existed: the delivery archetype fired on ~20% of the
universe and the low-noise archetype on none, because both used absolute cutoffs chosen
without data. run_scan now derives the cutoffs from the scanned universe; direct detector
calls keep the original absolute defaults.
"""
from __future__ import annotations

import sqlite3

import pytest

from oios.scanners import layer_1b as l1b


def _window(symbol="X.NS", n=40, drift=0.004, half_range=0.012, volume=1000.0):
    closes, price = [], 100.0
    for _ in range(n):
        price *= 1 + drift
        closes.append(price)
    return l1b.PriceWindow(
        symbol=symbol, dates=[f"2026-10-{i:02d}" for i in range(n)], closes=closes,
        volumes=[volume] * n, highs=[c * (1 + half_range) for c in closes],
        lows=[c * (1 - half_range) for c in closes])


def _bhav(trend, latest=0.50, n=12):
    pcts = [latest - trend] * (n - 5) + [latest - trend + trend * i / 5 for i in range(1, 6)]
    pcts[-1] = latest
    return l1b.BhavWindow(symbol="X.NS", dates=[f"d{i}" for i in range(n)], delivery_pcts=pcts)


def test_quantile_interpolates():
    assert l1b._quantile([1, 2, 3, 4, 5], 0.5) == 3
    assert l1b._quantile([10, 20], 0.5) == 15
    assert l1b._quantile([7], 0.9) == 7
    assert l1b._quantile([0, 100], 0.95) == pytest.approx(95)


def test_delivery_detector_default_keeps_the_original_floor_and_min_trend_raises_it():
    pw, bw = _window(), _bhav(trend=0.08)
    assert l1b._detect_delivery_expansion(pw, bw, "2026-11-17", "RANGE") is not None
    assert l1b._detect_delivery_expansion(pw, bw, "2026-11-17", "RANGE", min_trend=0.15) is None
    strong = _bhav(trend=0.20)
    assert l1b._detect_delivery_expansion(pw, strong, "2026-11-17", "RANGE", min_trend=0.15) is not None


def test_low_noise_default_is_unchanged_and_a_relative_cutoff_can_fire_in_a_volatile_market():
    volatile_but_calm_for_this_market = _window(half_range=0.012)       # ATR about 2.4%
    assert 2.0 < volatile_but_calm_for_this_market.atr_pct(14) < 3.0
    assert l1b._detect_low_noise_strength(volatile_but_calm_for_this_market, "d", "RANGE") is None
    signal = l1b._detect_low_noise_strength(volatile_but_calm_for_this_market, "d", "RANGE", atr_cutoff=3.0)
    assert signal is not None and signal.archetype_id == "DNA_1B_LOW_NOISE_STRENGTH" and signal.qualifies


def test_low_noise_relative_cutoff_still_rejects_noisy_unaligned_or_violent_stocks():
    assert l1b._detect_low_noise_strength(_window(half_range=0.03), "d", "RANGE", atr_cutoff=3.0) is None
    assert l1b._detect_low_noise_strength(_window(drift=-0.004), "d", "RANGE", atr_cutoff=3.0) is None
    violent = _window(half_range=0.005)
    violent.highs[-4] = violent.closes[-4] * 1.10                       # one 10% range day in the window
    assert l1b._detect_low_noise_strength(violent, "d", "RANGE", atr_cutoff=3.0) is None


def test_cross_sectional_cutoffs_use_the_universe_and_fall_back_when_it_is_small():
    windows = [(_window(symbol=f"S{i}", half_range=0.004 + i * 0.0004), _bhav(trend=i * 0.01))
               for i in range(40)]
    min_trend, atr_cutoff = l1b._cross_sectional_cutoffs(windows)
    atrs = sorted(pw.atr_pct(14) for pw, _ in windows)
    assert atr_cutoff == pytest.approx(l1b._quantile(atrs, l1b.LOW_NOISE_ATR_QUANTILE))
    assert min_trend == pytest.approx(l1b._quantile([bw.trend(5) for _, bw in windows], 0.95))
    assert min_trend > l1b.DELIVERY_TREND_FLOOR
    assert l1b._cross_sectional_cutoffs(windows[:10]) == (l1b.DELIVERY_TREND_FLOOR, None)
    assert l1b._cross_sectional_cutoffs([]) == (l1b.DELIVERY_TREND_FLOOR, None)


def test_cutoff_never_drops_below_the_absolute_floor():
    quiet = [(_window(symbol=f"S{i}"), _bhav(trend=0.01)) for i in range(40)]
    assert l1b._cross_sectional_cutoffs(quiet)[0] == l1b.DELIVERY_TREND_FLOOR


def _database(symbols):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    conn.execute("CREATE TABLE bhav_daily (symbol TEXT, trade_date TEXT, delivery_pct REAL)")
    conn.execute("CREATE TABLE universe_stocks (symbol TEXT, sector TEXT, is_active INTEGER, sector_purity_score REAL)")
    for index, symbol in enumerate(symbols):
        window = _window(symbol=symbol, n=40, half_range=0.004 + index * 0.0003)
        conn.execute("INSERT INTO universe_stocks VALUES (?, 'S', 1, 1.0)", (symbol,))
        for i, close in enumerate(window.closes):
            day = f"2026-{9 + i // 28:02d}-{i % 28 + 1:02d}"
            conn.execute("INSERT INTO ohlcv_daily VALUES (?,?,?,?,?,?,?)",
                         (symbol, day, close, window.highs[i], window.lows[i], close, 1000.0))
            conn.execute("INSERT INTO bhav_daily VALUES (?,?,?)", (symbol, day, 0.40 + 0.005 * index * (i / 40)))
    conn.commit()
    return conn


def test_run_scan_is_selective_with_a_real_cross_section_and_writes_nothing():
    symbols = [f"S{i:02d}.NS" for i in range(60)]
    conn = _database(symbols)
    before = conn.total_changes
    last = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    result = l1b.run_scan(conn, symbols, last, "RANGE")
    by_type = {}
    for signal in result.qualifying_signals:
        by_type[signal.archetype_id] = by_type.get(signal.archetype_id, 0) + 1
    assert result.symbols_scanned == 60 and conn.total_changes == before
    assert by_type.get("DNA_1B_DELIVERY_EXPANSION", 0) <= 6          # top ~5% of 60 plus ties, not 36%
    assert 0 < by_type.get("DNA_1B_LOW_NOISE_STRENGTH", 0) <= 20     # fires, and only in the calm quintile
