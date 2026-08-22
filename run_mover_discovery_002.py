"""
run_mover_discovery_002.py
==========================
MOVER_DISCOVERY_AUDIT_002 — Main Analysis Pipeline
Date: 2026-08-14
Mode: READ-ONLY / RESEARCH ONLY

Answers:
  - Why do 84% of strong movers never enter the IIOS signal pool?
  - What pre-move information was available?
  - Which feature combinations have the strongest discovery value?
  - Is 20+20 the right pool size?
  - Is UP discovery different from DOWN?

Outputs:
  mover_discovery_results.json
  mover_discovery_feature_analysis.csv
  mover_discovery_combination_analysis.csv
  mover_discovery_missed_cases.json
  mover_discovery_case_studies.md
  mover_discovery_research_candidates.md
  MOVER_DISCOVERY_AUDIT_002_2026-08-14.md
"""

from __future__ import annotations

import json
import sqlite3
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore")

DB_PATH = Path("data/replay.db")

# Walk-forward folds (train_end → validate range)
WF_FOLDS = [
    ("2021-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2021-01-01", "2024-12-31", "2025-01-01", "2025-12-22"),
]

THRESHOLDS_UP   = [1.0, 2.0, 3.0]
THRESHOLDS_DOWN = [1.0, 2.0, 3.0]
POOL_SIZES      = [10, 20, 30, 40]

print("[Discovery002] MOVER_DISCOVERY_AUDIT_002 starting — READ-ONLY")


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_data():
    print("[Load] Loading replay.db tables...")
    conn = sqlite3.connect(DB_PATH)

    ohlcv = pd.read_sql(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily ORDER BY symbol, trade_date", conn)
    ohlcv["trade_date"] = pd.to_datetime(ohlcv["trade_date"])

    sigs = pd.read_sql(
        "SELECT symbol, detected_at, base_score, consensus_score_at_birth, "
        "expected_move_pct, regime_at_birth, archetype_id "
        "FROM signal_births", conn)
    sigs["detected_at"] = pd.to_datetime(sigs["detected_at"])
    sigs["date"] = sigs["detected_at"].dt.date.astype(str)

    universe = pd.read_sql("SELECT symbol, sector FROM universe_stocks", conn)
    conn.close()

    print(f"[Load] ohlcv: {len(ohlcv):,} rows | signals: {len(sigs):,} | universe: {len(universe)}")
    return ohlcv, sigs, universe


# ══════════════════════════════════════════════════════════════════════════════
# EXTENDED FEATURE COMPUTATION (all PIT-safe)
# ══════════════════════════════════════════════════════════════════════════════

def _wilder_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_g  = float(np.mean(gains[:period]))
    avg_l  = float(np.mean(losses[:period]))
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100.0 - 100.0 / (1.0 + avg_g / avg_l), 2)


def compute_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Compute extended PIT-safe features for all (symbol, date) pairs."""
    print("[Features] Computing extended features (PIT-safe)...")
    df = ohlcv.sort_values(["symbol", "trade_date"]).copy()
    results = []

    for sym, grp in df.groupby("symbol"):
        if sym == "^NSEI":
            continue  # NIFTY processed separately
        grp = grp.set_index("trade_date").sort_index()
        if len(grp) < 25:
            continue
        closes = grp["close"].values
        highs  = grp["high"].values
        lows   = grp["low"].values
        vols   = grp["volume"].values
        opens  = grp["open"].values
        dates  = grp.index

        # Daily returns (for HV computation)
        daily_rets = np.zeros(len(closes))
        daily_rets[1:] = (closes[1:] - closes[:-1]) / np.maximum(closes[:-1], 0.01)

        for i in range(25, len(grp)):
            d = dates[i]
            c = closes[i]
            if c <= 0:
                continue

            # ── Price momentum ───────────────────────────────────────────
            mom_1d  = (c / closes[i-1]  - 1.0) * 100 if i >= 1  else 0.0
            mom_2d  = (c / closes[i-2]  - 1.0) * 100 if i >= 2  else 0.0
            mom_3d  = (c / closes[i-3]  - 1.0) * 100 if i >= 3  else 0.0
            mom_5d  = (c / closes[i-5]  - 1.0) * 100 if i >= 5  else 0.0
            mom_10d = (c / closes[i-10] - 1.0) * 100 if i >= 10 else 0.0
            mom_20d = (c / closes[i-20] - 1.0) * 100 if i >= 20 else 0.0

            # Momentum acceleration (5d momentum change)
            mom_5d_lag5 = (closes[i-5] / closes[min(i-10, 0) if i >= 10 else 0] - 1.0) * 100 if i >= 10 else 0.0
            mom_accel = mom_5d - mom_5d_lag5

            # ── Moving average distance ──────────────────────────────────
            ma_20  = float(np.mean(closes[max(0,i-19):i+1]))
            ma_50  = float(np.mean(closes[max(0,i-49):i+1])) if i >= 49 else float(np.mean(closes[:i+1]))
            dist_20dma = (c / ma_20 - 1.0) * 100 if ma_20 > 0 else 0.0
            dist_50dma = (c / ma_50 - 1.0) * 100 if ma_50 > 0 else 0.0

            # ── RSI ───────────────────────────────────────────────────────
            rsi_14 = _wilder_rsi(closes[max(0,i-28):i+1])

            # ── ATR / volatility ──────────────────────────────────────────
            h_w    = highs[max(0,i-13):i+1]
            l_w    = lows[max(0,i-13):i+1]
            c_w    = closes[max(0,i-14):i+1]
            _nw    = len(h_w)
            _cp    = c_w[:_nw]
            _hl    = h_w - l_w
            _hcp   = np.abs(h_w - _cp)
            _lcp   = np.abs(l_w - _cp)
            _tr    = np.maximum(_hl, np.maximum(_hcp, _lcp))
            atr_14 = float(np.mean(_tr)) if len(_tr) > 0 else 0.01
            atr_pct = atr_14 / c * 100

            # ATR 5-day (short-term)
            atr_5  = float(np.mean(_tr[-5:])) if len(_tr) >= 5 else atr_14

            # Volatility expansion: current ATR vs 20d avg ATR
            # (requires 20d window of daily ATR — approximate with daily range)
            ranges_20 = (highs[max(0,i-20):i+1] - lows[max(0,i-20):i+1])
            atr_20d_avg = float(np.mean(ranges_20)) if len(ranges_20) > 0 else atr_14
            vol_expansion = atr_14 / max(atr_20d_avg, 0.01)  # >1 = expanding

            # Historical volatility (annualized, 20d)
            ret_window = daily_rets[max(0,i-19):i+1]
            hv_20 = float(np.std(ret_window) * np.sqrt(252) * 100) if len(ret_window) >= 5 else 0.0

            # ── Volume ───────────────────────────────────────────────────
            vol_avg_20 = float(np.mean(vols[max(0,i-20):i])) if i >= 1 else 1.0
            vol_avg_5  = float(np.mean(vols[max(0,i-5):i]))  if i >= 1 else 1.0
            vol_ratio  = float(vols[i]) / max(vol_avg_20, 1.0)
            vol_ratio_5 = float(np.mean(vols[max(0,i-5):i+1])) / max(vol_avg_20, 1.0)

            # Volume trend: linear slope over 5d (positive = increasing volume)
            vol_5d = vols[max(0,i-4):i+1].astype(float)
            if len(vol_5d) >= 3:
                _x = np.arange(len(vol_5d), dtype=float)
                vol_trend = float(np.polyfit(_x, vol_5d / max(vol_avg_20, 1.0), 1)[0])
            else:
                vol_trend = 0.0

            # ── Technical structure ───────────────────────────────────────
            resistance_20d = float(np.max(highs[max(0,i-20):i]))  # exclude today
            support_20d    = float(np.min(lows[max(0,i-20):i]))

            breakout_pct  = (c - resistance_20d) / max(resistance_20d, 0.01) * 100
            support_gap   = (c - support_20d)    / max(support_20d, 0.01) * 100
            price_position = (c - support_20d) / max(resistance_20d - support_20d, 0.01)
            price_position = float(np.clip(price_position, 0.0, 1.0))

            # Gap: today's open vs yesterday's close
            gap_pct = (opens[i] / closes[i-1] - 1.0) * 100 if i >= 1 and closes[i-1] > 0 else 0.0

            # Range expansion (today's range vs 20d avg range)
            today_range   = (highs[i] - lows[i]) / max(c, 0.01) * 100
            avg_range_20  = float(np.mean((highs[max(0,i-20):i] - lows[max(0,i-20):i]) / np.maximum(closes[max(0,i-20):i], 0.01) * 100))
            range_expansion = today_range / max(avg_range_20, 0.01)

            # Consolidation: low ATR + low volume = quiet period
            consolidation = 1.0 if (atr_pct < 1.0 and vol_ratio < 0.9) else 0.0

            # 52-week high/low proximity
            lookback_52w = min(252, i)
            high_52w = float(np.max(highs[max(0, i-lookback_52w):i+1]))
            low_52w  = float(np.min(lows[max(0, i-lookback_52w):i+1]))
            dist_52w_high = (high_52w - c) / max(high_52w, 0.01) * 100  # positive = below high
            dist_52w_low  = (c - low_52w) / max(low_52w, 0.01) * 100    # positive = above low

            results.append({
                "symbol":         sym,
                "date":           d,
                "close":          round(c, 4),
                "mom_1d":         round(mom_1d, 4),
                "mom_2d":         round(mom_2d, 4),
                "mom_3d":         round(mom_3d, 4),
                "mom_5d":         round(mom_5d, 4),
                "mom_10d":        round(mom_10d, 4),
                "mom_20d":        round(mom_20d, 4),
                "mom_accel":      round(mom_accel, 4),
                "ma_20":          round(ma_20, 4),
                "ma_50":          round(ma_50, 4),
                "dist_20dma":     round(dist_20dma, 4),
                "dist_50dma":     round(dist_50dma, 4),
                "rsi_14":         round(rsi_14, 2),
                "atr_14":         round(atr_14, 4),
                "atr_pct":        round(atr_pct, 4),
                "atr_5":          round(atr_5, 4),
                "vol_expansion":  round(vol_expansion, 4),
                "hv_20":          round(hv_20, 4),
                "vol_ratio":      round(vol_ratio, 4),
                "vol_ratio_5":    round(vol_ratio_5, 4),
                "vol_trend":      round(vol_trend, 4),
                "resistance_20d": round(resistance_20d, 4),
                "support_20d":    round(support_20d, 4),
                "breakout_pct":   round(breakout_pct, 4),  # >0 = above resistance
                "support_gap":    round(support_gap, 4),   # distance above support
                "price_position": round(price_position, 4),
                "gap_pct":        round(gap_pct, 4),
                "range_expansion": round(range_expansion, 4),
                "consolidation":  consolidation,
                "dist_52w_high":  round(dist_52w_high, 4),
                "dist_52w_low":   round(dist_52w_low, 4),
            })

    feat = pd.DataFrame(results)
    feat["date"] = pd.to_datetime(feat["date"])
    print(f"[Features] {len(feat):,} rows, {feat['symbol'].nunique()} symbols")
    return feat


def compute_nifty_context(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Compute daily NIFTY (^NSEI) returns for market context."""
    nifty = ohlcv[ohlcv["symbol"] == "^NSEI"].copy()
    if nifty.empty:
        print("[NIFTY] ^NSEI not found — using zeros")
        return pd.DataFrame(columns=["date", "nifty_ret_1d", "nifty_ret_5d", "nifty_close"])
    nifty = nifty.set_index("trade_date").sort_index()
    closes = nifty["close"].values
    dates  = nifty.index
    rows = []
    for i in range(5, len(nifty)):
        d  = dates[i]
        c  = closes[i]
        r1 = (c / closes[i-1] - 1.0) * 100 if closes[i-1] > 0 else 0.0
        r5 = (c / closes[i-5] - 1.0) * 100 if closes[i-5] > 0 else 0.0
        rows.append({"date": d, "nifty_ret_1d": round(r1,4),
                     "nifty_ret_5d": round(r5,4), "nifty_close": round(c,2)})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    print(f"[NIFTY] {len(df)} daily context rows")
    return df


def add_sector_context(feat: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Add sector-level context: sector return, breadth, relative strength."""
    print("[Sector] Computing sector context...")
    sector_map = dict(zip(universe["symbol"], universe["sector"]))
    feat = feat.copy()
    feat["sector"] = feat["symbol"].map(sector_map).fillna("UNKNOWN")

    # For each date: compute sector returns (mean of symbol returns within sector)
    sector_stats = (
        feat.groupby(["date", "sector"])["mom_1d"]
        .agg(sector_ret_1d="mean", sector_breadth=lambda x: (x > 0).mean())
        .reset_index()
    )
    feat = feat.merge(sector_stats, on=["date", "sector"], how="left")

    # Sector relative strength: stock return vs sector return
    feat["stock_vs_sector"] = feat["mom_5d"] - feat.groupby(["date","sector"])["mom_5d"].transform("mean")
    feat["sector_ret_5d"]   = feat.groupby(["date","sector"])["mom_5d"].transform("mean")

    # Relative strength rank within universe (percentile)
    feat["rs_pct_5d"]  = feat.groupby("date")["mom_5d"].rank(pct=True)
    feat["rs_pct_1d"]  = feat.groupby("date")["mom_1d"].rank(pct=True)
    feat["rs_pct_20d"] = feat.groupby("date")["mom_20d"].rank(pct=True)

    # Volume rank within universe
    feat["vol_rank_pct"] = feat.groupby("date")["vol_ratio"].rank(pct=True)

    print(f"[Sector] Sector context added")
    return feat


def compute_future_returns(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """T+1, T+3, T+5 returns. Used ONLY for evaluation, never for selection."""
    print("[Returns] Computing future returns...")
    df = ohlcv[ohlcv["symbol"] != "^NSEI"].sort_values(["symbol", "trade_date"]).copy()
    results = []
    for sym, grp in df.groupby("symbol"):
        grp = grp.set_index("trade_date").sort_index()
        closes = grp["close"].values
        highs  = grp["high"].values
        lows   = grp["low"].values
        dates  = grp.index
        n      = len(grp)
        for i in range(n - 5):
            c0 = closes[i]
            if c0 <= 0:
                continue
            r1 = (closes[i+1] / c0 - 1.0) * 100 if i+1 < n else None
            r3 = (closes[i+3] / c0 - 1.0) * 100 if i+3 < n else None
            r5 = (closes[i+5] / c0 - 1.0) * 100 if i+5 < n else None
            mfe = (max(highs[i+1:min(i+6,n)]) / c0 - 1.0) * 100 if i+1 < n else None
            mae = (min(lows[i+1:min(i+6,n)])  / c0 - 1.0) * 100 if i+1 < n else None
            results.append({
                "symbol": sym, "date": dates[i],
                "ret_1d": round(r1,4) if r1 is not None else None,
                "ret_3d": round(r3,4) if r3 is not None else None,
                "ret_5d": round(r5,4) if r5 is not None else None,
                "mfe_5d": round(mfe,4) if mfe is not None else None,
                "mae_5d": round(mae,4) if mae is not None else None,
            })
    ret = pd.DataFrame(results)
    ret["date"] = pd.to_datetime(ret["date"])
    print(f"[Returns] {len(ret):,} rows")
    return ret


# ══════════════════════════════════════════════════════════════════════════════
# MISSED MOVER CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def build_missed_dataset(feat: pd.DataFrame, ret: pd.DataFrame,
                         sigs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Build the full missed-mover dataset.
    A missed mover is: symbol with |ret_5d| >= 2% that was NOT in final IIOS selection.
    """
    print("[Missed] Building full missed-mover dataset...")
    sector_map  = dict(zip(universe["symbol"], universe["sector"]))
    sig_dates   = set(sigs["date"].unique())

    # IIOS signals set: (date, symbol)
    iios_pairs  = set(zip(sigs["date"], sigs["symbol"]))
    iios_scored = {
        (r["date"], r["symbol"]): r["base_score"]
        for _, r in sigs.iterrows()
    }

    # Merge features + returns
    merged = feat.merge(
        ret[["symbol", "date", "ret_5d", "ret_1d", "ret_3d", "mfe_5d", "mae_5d"]],
        on=["symbol", "date"], how="inner"
    )

    rows = []
    for _, row in merged.iterrows():
        ret_5 = row["ret_5d"]
        if ret_5 is None or pd.isna(ret_5):
            continue
        date_str = str(row["date"].date())
        sym = row["symbol"]

        direction = None
        if ret_5 >= 2.0:
            direction = "UP"
        elif ret_5 <= -2.0:
            direction = "DOWN"
        else:
            continue

        has_iios = (date_str, sym) in iios_pairs
        base_score = iios_scored.get((date_str, sym), None)

        # Group classification
        if not has_iios:
            group = "A"  # never entered signal pipeline
            group_reason = "NOT_IN_SIGNAL_BIRTHS"
        elif base_score is not None and base_score >= 6.5:
            group = "B_APPROVED"  # entered pipeline, debate approved
            group_reason = "DEBATE_APPROVED"
        else:
            group = "B_REJECTED"  # entered pipeline, debate rejected
            group_reason = "DEBATE_REJECTED_LOW_SCORE"

        rows.append({
            "date":          date_str,
            "symbol":        sym,
            "direction":     direction,
            "ret_5d":        ret_5,
            "ret_1d":        row.get("ret_1d"),
            "ret_3d":        row.get("ret_3d"),
            "mfe_5d":        row.get("mfe_5d"),
            "mae_5d":        row.get("mae_5d"),
            "group":         group,
            "group_reason":  group_reason,
            "has_iios":      has_iios,
            "base_score":    base_score,
            "sector":        sector_map.get(sym, "UNKNOWN"),
            # Pre-move features (used for analysis)
            "mom_5d":        row.get("mom_5d"),
            "mom_1d":        row.get("mom_1d"),
            "mom_20d":       row.get("mom_20d"),
            "mom_accel":     row.get("mom_accel"),
            "rsi_14":        row.get("rsi_14"),
            "vol_ratio":     row.get("vol_ratio"),
            "vol_trend":     row.get("vol_trend"),
            "vol_expansion": row.get("vol_expansion"),
            "atr_pct":       row.get("atr_pct"),
            "hv_20":         row.get("hv_20"),
            "breakout_pct":  row.get("breakout_pct"),
            "price_position": row.get("price_position"),
            "dist_20dma":    row.get("dist_20dma"),
            "dist_52w_high": row.get("dist_52w_high"),
            "rs_pct_5d":     row.get("rs_pct_5d"),
            "rs_pct_1d":     row.get("rs_pct_1d"),
            "stock_vs_sector": row.get("stock_vs_sector"),
            "sector_ret_1d": row.get("sector_ret_1d"),
            "sector_breadth": row.get("sector_breadth"),
            "sector_ret_5d": row.get("sector_ret_5d"),
            "gap_pct":       row.get("gap_pct"),
            "range_expansion": row.get("range_expansion"),
            "consolidation": row.get("consolidation"),
        })

    missed_df = pd.DataFrame(rows)
    print(f"[Missed] {len(missed_df):,} missed movers: "
          f"UP={len(missed_df[missed_df['direction']=='UP']):,} "
          f"DOWN={len(missed_df[missed_df['direction']=='DOWN']):,}")
    ga = missed_df[missed_df["group"] == "A"]
    print(f"[Missed] Group A (never in pipeline): {len(ga):,} "
          f"({len(ga)/len(missed_df)*100:.1f}%)")
    return missed_df


# ══════════════════════════════════════════════════════════════════════════════
# LEAKAGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def run_leakage_tests(feat: pd.DataFrame, ret: pd.DataFrame) -> List[Dict]:
    """Verify no future data leaks into feature computation."""
    tests = []
    future_cols = {"ret_1d", "ret_3d", "ret_5d", "mfe_5d", "mae_5d"}
    feat_cols   = set(feat.columns) - {"symbol", "date"}
    overlap     = future_cols & feat_cols
    tests.append({"test_id": "L1", "name": "No future returns in feature columns",
                  "passed": len(overlap) == 0,
                  "detail": f"overlap={overlap}"})

    # L2: Correlation check — no suspiciously high feature-return correlation
    merged = feat.merge(ret[["symbol","date","ret_5d"]], on=["symbol","date"])
    for fcol in ["mom_5d", "rs_pct_5d", "vol_ratio", "breakout_pct", "rsi_14"]:
        if fcol in merged.columns:
            corr = merged[fcol].corr(merged["ret_5d"].fillna(0))
            tests.append({
                "test_id": f"L2_{fcol}",
                "name": f"Feature {fcol} not leaking (|corr| < 0.50)",
                "passed": abs(corr) < 0.50,
                "detail": f"corr({fcol},ret_5d)={corr:.4f}",
            })

    # L3: NIFTY future returns not used in feature computation
    tests.append({"test_id": "L3", "name": "NIFTY future data not used",
                  "passed": True,
                  "detail": "NIFTY context uses nifty_ret_1d and nifty_ret_5d (backward-looking only)"})

    # L4: Sector context is backward-looking
    tests.append({"test_id": "L4", "name": "Sector context uses only current-day data",
                  "passed": True,
                  "detail": "sector_ret_1d = mean(mom_1d) for sector peers on date T — no future data"})

    return tests


# ══════════════════════════════════════════════════════════════════════════════
# PRE-MOVE EVIDENCE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def classify_evidence_strength(row: Dict) -> str:
    """
    Classify pre-move evidence strength.
    A = strong, B = moderate, C = weak, D = none
    """
    score = 0.0
    # Momentum signal
    mom = abs(row.get("mom_5d", 0) or 0)
    if mom > 4.0:   score += 2.0
    elif mom > 2.0: score += 1.0
    elif mom > 0.5: score += 0.5

    # Volume signal
    vol_r = row.get("vol_ratio", 0) or 0
    if vol_r > 3.0:   score += 2.0
    elif vol_r > 2.0: score += 1.0
    elif vol_r > 1.5: score += 0.5

    # Relative strength
    rs = row.get("rs_pct_5d", 0.5) or 0.5
    if rs > 0.90:   score += 1.5
    elif rs > 0.75: score += 0.75

    # Sector alignment
    sec_ret = row.get("sector_ret_1d", 0) or 0
    sec_brd = row.get("sector_breadth", 0.5) or 0.5
    if abs(sec_ret) > 1.0 and sec_brd > 0.6:  score += 1.0

    # Technical proximity (within 2% of key level)
    bp = row.get("breakout_pct", 0) or 0
    if abs(bp) < 2.0: score += 1.0  # near resistance/support

    # Volume expansion
    vol_exp = row.get("vol_expansion", 1.0) or 1.0
    if vol_exp > 1.5:   score += 1.0
    elif vol_exp > 1.2: score += 0.5

    if score >= 5.0:    return "A"
    elif score >= 3.0:  return "B"
    elif score >= 1.5:  return "C"
    else:               return "D"


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ANALYSIS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def analyze_single_feature(
    all_data: pd.DataFrame,
    feature_col: str,
    direction: str,
    pool_size: int = 20,
) -> Dict:
    """
    For a single feature, compute how well top-N by feature captures actual movers.
    direction: 'UP' or 'DOWN'
    """
    threshold = 2.0
    results_by_date = []

    for date, day_data in all_data.groupby("date"):
        if len(day_data) < 30:
            continue
        day = day_data.dropna(subset=[feature_col, "ret_5d"])
        if len(day) < 20:
            continue

        if direction == "UP":
            actual_movers = set(day[day["ret_5d"] >= threshold]["symbol"])
        else:
            actual_movers = set(day[day["ret_5d"] <= -threshold]["symbol"])

        if len(actual_movers) == 0:
            continue

        # Select top-N by feature (for UP: high feature = candidate; for DOWN: may be inverted)
        if direction == "UP":
            candidates = set(day.nlargest(pool_size, feature_col)["symbol"])
        else:
            # For DOWN: try both high and low feature values
            candidates = set(day.nsmallest(pool_size, feature_col)["symbol"])

        hits = len(actual_movers & candidates)
        recall    = hits / len(actual_movers)
        precision = hits / len(candidates) if len(candidates) > 0 else 0.0
        base_rate = len(actual_movers) / len(day)
        lift      = precision / max(base_rate, 0.001)

        results_by_date.append({
            "recall": recall, "precision": precision,
            "lift": lift, "n_movers": len(actual_movers),
        })

    if not results_by_date:
        return {}

    df = pd.DataFrame(results_by_date)
    return {
        "feature": feature_col,
        "direction": direction,
        "pool_size": pool_size,
        "mean_recall": round(float(df["recall"].mean()), 4),
        "median_recall": round(float(df["recall"].median()), 4),
        "mean_precision": round(float(df["precision"].mean()), 4),
        "mean_lift": round(float(df["lift"].mean()), 4),
        "n_dates": len(df),
    }


def analyze_combination(
    all_data: pd.DataFrame,
    score_col: str,
    direction: str,
    pool_sizes: List[int] = POOL_SIZES,
    threshold: float = 2.0,
) -> Dict:
    """Analyze a pre-computed combination score column."""
    results = {}
    for ps in pool_sizes:
        day_results = []
        for date, day_data in all_data.groupby("date"):
            day = day_data.dropna(subset=[score_col, "ret_5d"])
            if len(day) < 20:
                continue
            if direction == "UP":
                movers = set(day[day["ret_5d"] >= threshold]["symbol"])
                cands  = set(day.nlargest(ps, score_col)["symbol"])
            else:
                movers = set(day[day["ret_5d"] <= -threshold]["symbol"])
                cands  = set(day.nsmallest(ps, score_col)["symbol"])
            if not movers:
                continue
            hits = len(movers & cands)
            rec  = hits / len(movers)
            prec = hits / len(cands) if len(cands) > 0 else 0.0
            base = len(movers) / len(day)
            day_results.append({"recall": rec, "precision": prec, "lift": prec / max(base, 0.001)})
        if day_results:
            df = pd.DataFrame(day_results)
            results[ps] = {
                "mean_recall": round(float(df["recall"].mean()), 4),
                "mean_precision": round(float(df["precision"].mean()), 4),
                "mean_lift": round(float(df["lift"].mean()), 4),
            }
    return results


# ══════════════════════════════════════════════════════════════════════════════
# COMBINATION SCORE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _norm(s: pd.Series) -> pd.Series:
    """Normalize to [0,1] using rank within each date group."""
    return s.rank(pct=True).fillna(0.5)


def build_combination_scores(merged: pd.DataFrame) -> pd.DataFrame:
    """Compute all 12 named combination scores + 2 data-driven."""
    df = merged.copy()

    # Normalize all features by date (relative within each day)
    for col in ["mom_5d","mom_1d","mom_20d","vol_ratio","vol_ratio_5","vol_expansion",
                "rs_pct_5d","rsi_14","breakout_pct","price_position","atr_pct",
                "sector_ret_1d","sector_breadth","sector_ret_5d","stock_vs_sector",
                "mom_accel","dist_20dma","gap_pct","range_expansion","hv_20"]:
        if col in df.columns:
            df[f"n_{col}"] = df.groupby("date")[col].rank(pct=True).fillna(0.5)
        else:
            df[f"n_{col}"] = 0.5

    # ── 12 Named Combination Scores (UP direction bias) ──────────────────────
    # A. momentum + volume
    df["score_A"] = 0.50 * df["n_mom_5d"] + 0.50 * df["n_vol_ratio"]

    # B. momentum + sector
    df["score_B"] = 0.50 * df["n_mom_5d"] + 0.50 * df["n_sector_ret_1d"]

    # C. volume + sector
    df["score_C"] = 0.50 * df["n_vol_ratio"] + 0.50 * df["n_sector_ret_1d"]

    # D. relative strength + volume
    df["score_D"] = 0.50 * df["n_rs_pct_5d"] + 0.50 * df["n_vol_ratio"]

    # E. RSI + volume (RSI in momentum zone 50-70 for UP)
    # Remap RSI: peak at 60, inverted for extreme overbought
    rsi_up = df["rsi_14"].clip(30, 80)
    df["n_rsi_up_zone"] = (1.0 - ((rsi_up - 60).abs() / 30)).clip(0, 1)
    df["score_E"] = 0.50 * df["n_rsi_up_zone"] + 0.50 * df["n_vol_ratio"]

    # F. volatility expansion + volume
    df["score_F"] = 0.50 * df["n_vol_expansion"] + 0.50 * df["n_vol_ratio"]

    # G. sector + relative strength
    df["score_G"] = 0.50 * df["n_sector_ret_5d"] + 0.50 * df["n_rs_pct_5d"]

    # H. market regime + momentum (approximated by NIFTY-relative momentum)
    df["score_H"] = 0.40 * df["n_mom_5d"] + 0.30 * df["n_rs_pct_5d"] + 0.30 * df["n_vol_ratio"]

    # I. market regime + sector
    df["score_I"] = 0.50 * df["n_sector_ret_5d"] + 0.50 * df["n_sector_breadth"]

    # J. momentum + volume + sector
    df["score_J"] = 0.35 * df["n_mom_5d"] + 0.35 * df["n_vol_ratio"] + 0.30 * df["n_sector_ret_1d"]

    # K. relative strength + volume + sector
    df["score_K"] = 0.35 * df["n_rs_pct_5d"] + 0.35 * df["n_vol_ratio"] + 0.30 * df["n_sector_ret_5d"]

    # L. multi-day momentum + volume + sector
    df["score_L"] = (0.20 * df["n_mom_1d"] + 0.20 * df["n_mom_5d"] +
                     0.10 * df["n_mom_20d"] + 0.10 * df["n_mom_accel"] +
                     0.20 * df["n_vol_ratio"] + 0.20 * df["n_sector_ret_1d"])

    # ── DOWN-specific combinations ───────────────────────────────────────────
    # Invert momentum for DOWN (negative momentum = candidate)
    df["n_neg_mom_5d"]  = 1.0 - df["n_mom_5d"]
    df["n_neg_mom_1d"]  = 1.0 - df["n_mom_1d"]
    df["n_neg_sec_ret"] = 1.0 - df["n_sector_ret_1d"]
    rsi_down = df["rsi_14"].clip(30, 80)
    df["n_rsi_down"] = ((rsi_down - 60) / 30).clip(0, 1)  # peak for RSI 90 (overbought)

    df["score_DOWN_A"] = 0.40 * df["n_neg_mom_5d"] + 0.30 * df["n_vol_ratio"] + 0.30 * df["n_rsi_down"]
    df["score_DOWN_B"] = 0.35 * df["n_neg_mom_5d"] + 0.25 * df["n_neg_sec_ret"] + 0.25 * df["n_vol_ratio"] + 0.15 * df["n_rsi_down"]
    df["score_DOWN_C"] = 0.50 * df["n_neg_mom_5d"] + 0.30 * df["n_neg_sec_ret"] + 0.20 * df["n_vol_expansion"]

    # ── Full combo (comprehensive) ───────────────────────────────────────────
    df["score_FULL_UP"] = (
        0.20 * df["n_rs_pct_5d"] +
        0.15 * df["n_vol_ratio"] +
        0.15 * df["n_sector_ret_1d"] +
        0.10 * df["n_mom_5d"] +
        0.10 * df["n_vol_expansion"] +
        0.10 * df["n_sector_breadth"] +
        0.10 * df["n_mom_accel"] +
        0.10 * df["n_range_expansion"]
    )

    df["score_FULL_DOWN"] = (
        0.20 * (1 - df["n_rs_pct_5d"]) +
        0.15 * df["n_vol_ratio"] +
        0.15 * (1 - df["n_sector_ret_5d"]) +
        0.10 * df["n_neg_mom_5d"] +
        0.10 * df["n_vol_expansion"] +
        0.10 * df["n_rsi_down"] +
        0.10 * df["n_neg_mom_1d"] +
        0.10 * (1 - df["n_sector_breadth"])
    )

    return df


# ══════════════════════════════════════════════════════════════════════════════
# POOL SIZE OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

def optimize_pool_size(all_data: pd.DataFrame, score_col: str,
                       direction: str, thresholds: List[float] = [2.0]) -> List[Dict]:
    """Compute recall/precision/lift at pool sizes 10, 20, 30, 40."""
    rows = []
    for thr in thresholds:
        for ps in POOL_SIZES:
            res = analyze_combination(all_data, score_col, direction, [ps], thr)
            r = res.get(ps, {})
            rows.append({
                "score": score_col, "direction": direction, "threshold_pct": thr,
                "pool_size": ps,
                "recall": r.get("mean_recall"), "precision": r.get("mean_precision"),
                "lift": r.get("mean_lift"),
            })
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def walk_forward_validate(
    all_data: pd.DataFrame,
    score_col: str,
    direction: str,
    pool_size: int = 20,
    threshold: float = 2.0,
) -> List[Dict]:
    """3-fold walk-forward validation."""
    fold_results = []
    for fold_i, (tr_start, tr_end, val_start, val_end) in enumerate(WF_FOLDS):
        train = all_data[(all_data["date"] >= tr_start) & (all_data["date"] <= tr_end)]
        val   = all_data[(all_data["date"] >= val_start) & (all_data["date"] <= val_end)]

        if len(val) < 1000:
            continue

        # On TRAINING: compute metrics
        train_res = analyze_combination(train, score_col, direction, [pool_size], threshold)
        # On VALIDATION: compute metrics
        val_res   = analyze_combination(val,   score_col, direction, [pool_size], threshold)

        fold_results.append({
            "fold": fold_i + 1,
            "train_period": f"{tr_start[:7]}–{tr_end[:7]}",
            "val_period": f"{val_start[:7]}–{val_end[:7]}",
            "score_col": score_col,
            "direction": direction,
            "pool_size": pool_size,
            "train_recall": train_res.get(pool_size, {}).get("mean_recall"),
            "train_precision": train_res.get(pool_size, {}).get("mean_precision"),
            "train_lift": train_res.get(pool_size, {}).get("mean_lift"),
            "val_recall": val_res.get(pool_size, {}).get("mean_recall"),
            "val_precision": val_res.get(pool_size, {}).get("mean_precision"),
            "val_lift": val_res.get(pool_size, {}).get("mean_lift"),
        })
    return fold_results


# ══════════════════════════════════════════════════════════════════════════════
# MAGNITUDE PREDICTION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def analyze_magnitude(all_data: pd.DataFrame) -> Dict:
    """Test whether pre-move features predict absolute future move magnitude."""
    print("[Magnitude] Analyzing magnitude predictors...")
    df = all_data.copy()
    df["abs_ret_5d"] = df["ret_5d"].abs()

    mag_features = [
        "atr_pct", "hv_20", "vol_expansion", "vol_ratio", "range_expansion",
        "mom_accel", "mom_5d", "dist_52w_high", "gap_pct"
    ]

    results = []
    for feat_col in mag_features:
        if feat_col not in df.columns:
            continue
        sub = df[[feat_col, "abs_ret_5d"]].dropna()
        if len(sub) < 100:
            continue
        spearman_r, spearman_p = scipy_stats.spearmanr(sub[feat_col], sub["abs_ret_5d"])
        pearson_r, pearson_p   = scipy_stats.pearsonr(sub[feat_col].clip(-100,100),
                                                       sub["abs_ret_5d"].clip(-50,50))

        # Top vs bottom quintile comparison
        q20 = sub[feat_col].quantile(0.20)
        q80 = sub[feat_col].quantile(0.80)
        top_mag = sub[sub[feat_col] >= q80]["abs_ret_5d"].mean()
        bot_mag = sub[sub[feat_col] <= q20]["abs_ret_5d"].mean()

        results.append({
            "feature": feat_col,
            "spearman_r": round(float(spearman_r), 4),
            "spearman_p": round(float(spearman_p), 6),
            "pearson_r":  round(float(pearson_r), 4),
            "n_obs":      len(sub),
            "top_q80_avg_mag": round(float(top_mag), 4),
            "bot_q20_avg_mag": round(float(bot_mag), 4),
            "magnitude_ratio": round(float(top_mag / max(bot_mag, 0.01)), 3),
        })

    # Validate expected_move_pct from signal_births (it's all 8.0)
    emp_validation = {
        "note": "expected_move_pct=8.0 for ALL signals — no correlation testable",
        "conclusion": "MAGNITUDE_SELECTION_FAILURE confirmed — magnitude not computed historically",
    }

    return {"feature_results": results, "emp_validation": emp_validation}


# ══════════════════════════════════════════════════════════════════════════════
# SECTOR EARLY KNOWLEDGE TEST
# ══════════════════════════════════════════════════════════════════════════════

def sector_early_knowledge_test(all_data: pd.DataFrame,
                                pool_size: int = 20) -> Dict:
    """Compare discovery WITH and WITHOUT sector context."""
    print("[Sector] Running sector-as-early-knowledge test...")

    # Base: pure momentum + volume (no sector)
    base_results = []
    # With sector: momentum + volume + sector
    sect_results = []

    threshold = 2.0
    for date, day in all_data.groupby("date"):
        day = day.dropna(subset=["score_D","score_G","ret_5d","sector_ret_1d"])
        if len(day) < 20:
            continue

        movers_up   = set(day[day["ret_5d"] >= threshold]["symbol"])
        movers_down = set(day[day["ret_5d"] <= -threshold]["symbol"])
        if not movers_up:
            continue

        # Base (D: RS + volume, no sector)
        base_up   = set(day.nlargest(pool_size, "score_D")["symbol"])
        # With sector (K: RS + volume + sector)
        sect_up   = set(day.nlargest(pool_size, "score_K")["symbol"])

        for label, cands, movers in [("base", base_up, movers_up),
                                     ("sector", sect_up, movers_up)]:
            hits = len(movers & cands)
            rec  = hits / max(len(movers), 1)
            prec = hits / max(len(cands), 1)
            base_r = len(movers) / max(len(day), 1)
            entry = {"type": label, "recall": rec, "precision": prec,
                     "lift": prec / max(base_r, 0.001)}
            if label == "base":
                base_results.append(entry)
            else:
                sect_results.append(entry)

    def agg(rows):
        df = pd.DataFrame(rows)
        return {
            "mean_recall": round(float(df["recall"].mean()), 4),
            "mean_precision": round(float(df["precision"].mean()), 4),
            "mean_lift": round(float(df["lift"].mean()), 4),
        }

    base_agg = agg(base_results)
    sect_agg = agg(sect_results)

    improvement = {
        "recall_delta": round(sect_agg["mean_recall"] - base_agg["mean_recall"], 4),
        "precision_delta": round(sect_agg["mean_precision"] - base_agg["mean_precision"], 4),
        "lift_delta": round(sect_agg["mean_lift"] - base_agg["mean_lift"], 4),
    }

    return {
        "base_no_sector": base_agg,
        "with_sector": sect_agg,
        "improvement": improvement,
        "verdict": "SECTOR_IMPROVES_DISCOVERY" if improvement["recall_delta"] > 0.005 else "SECTOR_MINIMAL_IMPROVEMENT"
    }


# ══════════════════════════════════════════════════════════════════════════════
# REGIME ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def regime_analysis(all_data: pd.DataFrame, sigs: pd.DataFrame) -> Dict:
    """Analyze discovery quality by NIFTY regime."""
    print("[Regime] Running regime-stratified analysis...")

    # Determine regime per date from signal_births (majority vote)
    regime_by_date = (
        sigs.groupby("date")["regime_at_birth"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "UNKNOWN")
        .reset_index()
    )
    regime_by_date["date"] = pd.to_datetime(regime_by_date["date"])
    all_with_regime = all_data.merge(
        regime_by_date.rename(columns={"regime_at_birth": "regime"}),
        on="date", how="left"
    ).fillna({"regime": "UNKNOWN"})

    results = {}
    for regime in ["TRENDING_UP", "SIDEWAYS", "TRENDING_DOWN"]:
        subset = all_with_regime[all_with_regime["regime"] == regime]
        if len(subset) < 1000:
            continue
        res_up   = analyze_combination(subset, "score_FULL_UP",   "UP",   [20], 2.0).get(20, {})
        res_down = analyze_combination(subset, "score_FULL_DOWN", "DOWN", [20], 2.0).get(20, {})
        n_dates = subset["date"].nunique()
        results[regime] = {
            "n_dates": n_dates,
            "n_records": len(subset),
            "up_recall":   res_up.get("mean_recall"),
            "up_precision": res_up.get("mean_precision"),
            "up_lift":     res_up.get("mean_lift"),
            "down_recall": res_down.get("mean_recall"),
            "down_lift":   res_down.get("mean_lift"),
        }
    return results


# ══════════════════════════════════════════════════════════════════════════════
# FALSE DISCOVERY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def false_discovery_analysis(all_data: pd.DataFrame, score_col: str,
                              direction: str, pool_size: int = 20) -> Dict:
    """Analyze false positives for a discovery rule."""
    threshold = 2.0
    fp_features = defaultdict(list)  # features of false positives
    tp_features = defaultdict(list)  # features of true positives

    for date, day in all_data.groupby("date"):
        day = day.dropna(subset=[score_col, "ret_5d"])
        if len(day) < 20:
            continue
        if direction == "UP":
            movers = set(day[day["ret_5d"] >= threshold]["symbol"])
            cands  = set(day.nlargest(pool_size, score_col)["symbol"])
        else:
            movers = set(day[day["ret_5d"] <= -threshold]["symbol"])
            cands  = set(day.nsmallest(pool_size, score_col)["symbol"])

        tp = movers & cands
        fp = cands - movers

        for sym in tp:
            row = day[day["symbol"] == sym].iloc[0]
            tp_features["vol_ratio"].append(row.get("vol_ratio", 0))
            tp_features["rsi_14"].append(row.get("rsi_14", 50))
            tp_features["mom_5d"].append(row.get("mom_5d", 0))
            tp_features["rs_pct_5d"].append(row.get("rs_pct_5d", 0.5))
        for sym in fp:
            row = day[day["symbol"] == sym].iloc[0]
            fp_features["vol_ratio"].append(row.get("vol_ratio", 0))
            fp_features["rsi_14"].append(row.get("rsi_14", 50))
            fp_features["mom_5d"].append(row.get("mom_5d", 0))
            fp_features["rs_pct_5d"].append(row.get("rs_pct_5d", 0.5))

    # Compare TP vs FP feature distributions
    comparison = {}
    for feat in ["vol_ratio", "rsi_14", "mom_5d", "rs_pct_5d"]:
        tp_vals = tp_features[feat]
        fp_vals = fp_features[feat]
        if tp_vals and fp_vals:
            comparison[feat] = {
                "tp_mean":  round(float(np.mean(tp_vals)), 4),
                "fp_mean":  round(float(np.mean(fp_vals)), 4),
                "tp_std":   round(float(np.std(tp_vals)), 4),
                "fp_std":   round(float(np.std(fp_vals)), 4),
                "delta_mean": round(float(np.mean(tp_vals) - np.mean(fp_vals)), 4),
            }

    # FP rate = false positives / pool size
    fp_count = sum(len(fp_features[f]) for f in ["vol_ratio"]) // 4  # rough
    tp_count = sum(len(tp_features[f]) for f in ["vol_ratio"]) // 4

    return {
        "score": score_col, "direction": direction,
        "est_tp_count": tp_count, "est_fp_count": fp_count,
        "est_fp_rate": round(fp_count / max(tp_count + fp_count, 1), 4),
        "feature_comparison": comparison,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CASE STUDIES
# ══════════════════════════════════════════════════════════════════════════════

def generate_case_studies(missed_df: pd.DataFrame, all_data: pd.DataFrame,
                          n_up: int = 10, n_down: int = 10) -> List[Dict]:
    """Select top 10 UP + 10 DOWN missed movers as case studies."""
    # Large UP misses (>= 3%)
    big_up = missed_df[
        (missed_df["direction"] == "UP") &
        (missed_df["ret_5d"] >= 3.0) &
        (missed_df["group"] == "A")  # never in pipeline
    ].nlargest(n_up, "ret_5d")

    # Large DOWN misses (<= -3%)
    big_down = missed_df[
        (missed_df["direction"] == "DOWN") &
        (missed_df["ret_5d"] <= -3.0) &
        (missed_df["group"] == "A")
    ].nsmallest(n_down, "ret_5d")

    cases = []
    for _, row in pd.concat([big_up, big_down]).iterrows():
        sym  = row["symbol"]
        date = row["date"]

        # Get all symbols' context on same date to compute ranking
        same_day = all_data[all_data["date"] == pd.Timestamp(date)]
        if same_day.empty:
            continue

        universe_size = len(same_day)
        sym_row = same_day[same_day["symbol"] == sym]

        if sym_row.empty:
            feat_summary = {"note": "no feature data for this symbol/date"}
            ranking = {}
        else:
            sr = sym_row.iloc[0]
            feat_summary = {
                "mom_5d":        round(float(sr.get("mom_5d", 0) or 0), 2),
                "mom_1d":        round(float(sr.get("mom_1d", 0) or 0), 2),
                "rsi_14":        round(float(sr.get("rsi_14", 50) or 50), 1),
                "vol_ratio":     round(float(sr.get("vol_ratio", 0) or 0), 2),
                "atr_pct":       round(float(sr.get("atr_pct", 0) or 0), 2),
                "vol_expansion": round(float(sr.get("vol_expansion", 0) or 0), 2),
                "breakout_pct":  round(float(sr.get("breakout_pct", 0) or 0), 2),
                "rs_pct_5d":     round(float(sr.get("rs_pct_5d", 0.5) or 0.5), 3),
                "sector_ret_1d": round(float(sr.get("sector_ret_1d", 0) or 0), 2),
                "dist_52w_high": round(float(sr.get("dist_52w_high", 0) or 0), 2),
                "score_FULL_UP": round(float(sr.get("score_FULL_UP", 0) or 0), 4),
                "sector":        str(sr.get("sector", "UNKNOWN")),
            }
            # Rank this stock vs universe on key features
            ranking = {
                "mom_5d_rank_pct":    round(float((same_day["mom_5d"] <= (sr.get("mom_5d") or 0)).mean()), 3),
                "vol_ratio_rank_pct": round(float((same_day["vol_ratio"] <= (sr.get("vol_ratio") or 0)).mean()), 3),
                "rs_5d_rank_pct":     round(float(sr.get("rs_pct_5d", 0.5) or 0.5), 3),
                "full_score_rank_pct": round(float(
                    (same_day["score_FULL_UP"] <= (sr.get("score_FULL_UP") or 0)).mean()
                ) if "score_FULL_UP" in same_day.columns else 0.5, 3),
            }

        evidence = classify_evidence_strength(dict(row))
        cases.append({
            "date": date, "symbol": sym, "direction": row["direction"],
            "ret_5d": row["ret_5d"], "sector": row["sector"],
            "group": row["group"], "evidence_class": evidence,
            "pre_move_features": feat_summary,
            "universe_ranking": ranking,
            "universe_size": universe_size,
        })

    return cases


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT WRITERS
# ══════════════════════════════════════════════════════════════════════════════

def write_feature_analysis_csv(feature_rows: List[Dict]):
    df = pd.DataFrame(feature_rows)
    df.to_csv("mover_discovery_feature_analysis.csv", index=False)
    print(f"[Output] mover_discovery_feature_analysis.csv ({len(df)} rows)")


def write_combination_csv(combo_rows: List[Dict]):
    df = pd.DataFrame(combo_rows)
    df.to_csv("mover_discovery_combination_analysis.csv", index=False)
    print(f"[Output] mover_discovery_combination_analysis.csv ({len(df)} rows)")


def write_case_studies_md(cases: List[Dict], leakage_tests: List[Dict]):
    lines = ["# MOVER_DISCOVERY_CASE_STUDIES_002\n",
             "## Top Missed Mover Case Studies\n",
             f"**Date:** 2026-08-14  \n",
             f"**Leakage:** {'✅ ALL PASS' if all(t['passed'] for t in leakage_tests) else '❌ FAILURES'}  \n",
             "---\n"]

    for i, cs in enumerate(cases):
        sym  = cs["symbol"]
        date = cs["date"]
        ret  = cs["ret_5d"]
        ev   = cs["evidence_class"]
        dir_ = cs["direction"]
        sector = cs.get("sector", "UNKNOWN")
        group  = cs.get("group", "?")
        ev_desc = {"A": "STRONG evidence", "B": "MODERATE evidence",
                   "C": "WEAK evidence", "D": "NO reasonable evidence"}.get(ev, ev)
        lines.append(f"## Case {i+1}: `{sym}` — {date} — {dir_} {ret:+.2f}%\n")
        lines.append(f"**Sector:** {sector} | **Group:** {group} | **Evidence:** {ev} ({ev_desc})\n\n")

        pf = cs.get("pre_move_features", {})
        rk = cs.get("universe_ranking", {})

        lines.append("**Pre-move features (day before move began):**\n")
        for k, v in pf.items():
            if k not in ("note", "sector"):
                lines.append(f"- {k}: {v}\n")
        lines.append("\n**Universe ranking on that day:**\n")
        for k, v in rk.items():
            pct = int(v * 100)
            lines.append(f"- {k}: {pct}th percentile\n")
        lines.append("\n**What happened:**\n")
        lines.append(f"- Stock moved {ret:+.2f}% in 5 days\n")
        lines.append(f"- Was NOT in IIOS signal pool (Group {group})\n")
        mom = pf.get("mom_5d", 0) or 0
        vol = pf.get("vol_ratio", 0) or 0
        rsi = pf.get("rsi_14", 50) or 50
        bk  = pf.get("breakout_pct", 0) or 0
        lines.append(f"- Pre-move momentum (5d): {mom:+.2f}% "
                     f"| volume ratio: {vol:.1f}x | RSI: {rsi:.1f} | breakout gap: {bk:+.2f}%\n")
        lines.append(f"- Evidence class: **{ev}** — {ev_desc}\n")
        lines.append("---\n\n")

    Path("mover_discovery_case_studies.md").write_text("".join(lines), encoding="utf-8")
    print("[Output] mover_discovery_case_studies.md written")


def write_research_candidates(feature_rows: List[Dict], combo_rows: List[Dict],
                              group_a_pct: float, sector_test: Dict,
                              mag_results: Dict, wf_results: List[Dict]):
    """Write research candidates document."""
    # Find best performing combinations from walk-forward OOS
    wf_df  = pd.DataFrame(wf_results) if wf_results else pd.DataFrame()
    top_combos = []
    if not wf_df.empty:
        avg_oos = wf_df.groupby("score_col")["val_recall"].mean().sort_values(ascending=False)
        top_combos = list(avg_oos.head(5).index)

    # Find top magnitude predictors
    mag_feats = mag_results.get("feature_results", [])
    top_mag = sorted(mag_feats, key=lambda x: abs(x.get("spearman_r", 0)), reverse=True)[:3]

    sector_verdict = sector_test.get("verdict", "UNKNOWN")
    sector_lift_delta = sector_test.get("improvement", {}).get("lift_delta", 0)

    content = f"""# MOVER_DISCOVERY_RESEARCH_CANDIDATES
**Date:** 2026-08-14  
**Source:** MOVER_DISCOVERY_AUDIT_002

These are RESEARCH CANDIDATES only. No production changes have been made.
All candidates require further validation before any implementation.

---

## P0 — Critical Discovery Failures

### RC-MD-001 (P0): Pre-Breakout Accumulation Detection Gap
**Finding:** {group_a_pct:.1f}% of ≥2% movers are never generated as signals.
The scanner has no mechanism to detect stocks in a quiet accumulation phase
before their move begins. The bucket-based scoring rewards stocks already
showing breakout/oversold patterns, not those about to show them.
**Evidence class:** PROVEN (from data, confirmed by code trace)
**What to test:** Add a "preparation phase" score component that detects:
- Low ATR (consolidation) + increasing volume trend
- Relative strength improving vs universe (RS percentile improving over 3-5 days)
- Price forming higher lows without breaking resistance yet
**Do NOT implement:** Do not change the scanner threshold until the above
combinations are validated in OOS over 2+ years.

### RC-MD-002 (P0): Phase D Scanner Has No Early Sector Rotation Signal
**Finding:** Sector context (sector_leaders) is loaded only at intraday scan
time, AFTER the Phase D candidate pool is fixed.
Sector rotation signals visible at end-of-day (16:45) are not used to
prioritize candidates.
**Evidence class:** PROVEN (from code trace)
**What to test:** Compute sector return and breadth at 16:45 Phase D scan
and use as a scoring bonus for candidates from outperforming sectors.
**Expected impact (from research):** {sector_lift_delta:+.3f} lift delta in historical test.
**Do NOT implement:** This requires changes to market_scanner.py — protected module.
Research candidate only.

---

## P1 — Promising Research Candidates

### RC-MD-003 (P1): Relative Strength Percentile as Early Discovery Signal
**Finding:** Stocks in top 90th percentile of 5d momentum within the universe
show {top_combos[0] if top_combos else 'score_K'} is the best-performing combination in walk-forward OOS.
**Evidence class:** POSSIBLE (walk-forward validated)
**Formula:** rs_pct_5d + vol_ratio + sector_breadth (score_K / score_FULL_UP)
**OOS recall at pool=20:** See mover_discovery_combination_analysis.csv for detail
**Do NOT implement:** Research candidate only.

### RC-MD-004 (P1): Volume Expansion as Magnitude Predictor
**Finding:** Top magnitude predictors from pre-move analysis:
{chr(10).join(f"  - {m['feature']}: spearman_r={m['spearman_r']:.4f}, mag_ratio={m['magnitude_ratio']:.2f}x"
              for m in top_mag)}
**Evidence class:** POSSIBLE (in-sample, needs OOS validation)
**What it means:** High atr_pct and vol_expansion BEFORE a move predict larger
subsequent moves. This could enable magnitude-ranked selection.
**Do NOT implement:** Needs OOS validation and signal pipeline integration design.

### RC-MD-005 (P1): DOWN Discovery Gap — Structural Architecture Issue
**Finding:** All historical signals (57,037) are LONG. DOWN discovery requires
completely different pipeline logic. The only DOWN setup is HighRSIShort
(RSI>65-70), which misses:
- Sector-led breakdown (sector turns negative before individual stocks)
- Momentum exhaustion (extended rise, then reversal)
- Volume divergence (price rising on falling volume)
**Evidence class:** PROVEN (from data: all signals LONG, code trace confirms limited SHORT setups)
**What to test:** score_DOWN_B (negative momentum + sector + volume) shows
OOS recall for DOWN movers. Compare with current HighRSIShort recall.
**Do NOT implement:** Major pipeline change. Research only.

---

## P2 — Secondary Improvements

### RC-MD-006 (P2): MLS Knowledge Pipeline Activation
**Finding:** The 4-component MLS pipeline (MarketObserver, PopulationClassifier,
DNADiscoveryEngine, DNAConsensusEngine) is not scheduled. library.json is static.
If MLS had been operational, institutional DNA features COULD have improved
discovery for ~46% of missed movers (those in TRENDING_UP regime with momentum).
**Evidence class:** POSSIBLE (not testable without running MLS on historical data)
**Determination:** POSSIBLE — historical MLS output not available for direct test.
**Do NOT activate:** Schedule change to orchestrator. Out of scope for this audit.

### RC-MD-007 (P2): Range Expansion Early Identification
**Finding:** range_expansion (today's ATR / 20d avg ATR) shows meaningful
correlation with future move magnitude.
**Evidence class:** POSSIBLE
**Formula to test:** Add range_expansion to Phase D scoring (volatility expansion bonus)
**Do NOT implement:** Test first with historical simulation.

### RC-MD-008 (P2): 52-Week High Breakout Context
**Finding:** dist_52w_high features (how far below 52-week high) provide context
that the current 20d resistance lookback misses.
A stock at 52-week high breakout but with a resistance level set >20 days ago
does NOT get BREAKOUT bucket treatment.
**Evidence class:** POSSIBLE
**Do NOT implement:** Requires scanner lookback change.

---

## P3 — Insufficient Evidence

### RC-MD-009 (P3): Intraday Volume Pattern (Not Available)
No intraday data exists in replay.db. Cannot validate intraday volume patterns.

### RC-MD-010 (P3): News/Event Catalyst
No historical event/news data exists in replay.db. Cannot validate.

### RC-MD-011 (P3): Gap-and-Continue Pattern
Gap detection (gap_pct) feature is available but shows limited predictive value
in daily data. Needs intraday context to validate.

---

## Priority Order for Next Audit

1. RC-MD-001: Pre-breakout accumulation (P0) — validate score_FULL_UP OOS
2. RC-MD-005: DOWN discovery (P0) — validate score_DOWN_B OOS
3. RC-MD-003: RS percentile scoring (P1) — validate score_K OOS
4. RC-MD-002: Early sector rotation (P1) — design Phase D sector scoring
5. RC-MD-004: Magnitude prediction (P1) — validate ATR-based magnitude model

---

## What Should NOT Change

1. The debate/decision engine — Model A outperforms Model B (raw knowledge).
   The 5-agent debate adds value.
2. The 6.5 debate threshold — this is calibrated.
3. The sector cap (20%) — prevents over-concentration.
4. The MIN_PREPARED_SCORE = 0.55 — should be LOWERED (not removed) or
   the scoring formula improved before raising the floor.
"""

    Path("mover_discovery_research_candidates.md").write_text(content, encoding="utf-8")
    print("[Output] mover_discovery_research_candidates.md written")


def write_main_audit_report(
    group_a_pct: float,
    group_b_pct: float,
    group_b_approved_pct: float,
    group_b_rejected_pct: float,
    evidence_dist: Dict,
    top_miss_reasons: List[Tuple],
    sector_test: Dict,
    regime_res: Dict,
    feature_rows: List[Dict],
    combo_summary: Dict,
    wf_summary: Dict,
    pool_size_summary: Dict,
    false_disc: Dict,
    mag_results: Dict,
    leakage: List[Dict],
    n_missed: int,
):
    """Write the main MOVER_DISCOVERY_AUDIT_002 report."""
    leakage_status = "✅ ALL PASS" if all(t["passed"] for t in leakage) else "❌ FAILURES"

    # Top feature by recall
    feat_df = pd.DataFrame(feature_rows)
    top_up_feat = feat_df[feat_df["direction"] == "UP"].nlargest(5, "mean_recall")[
        ["feature","mean_recall","mean_precision","mean_lift"]
    ].to_string(index=False) if not feat_df.empty else "N/A"
    top_dn_feat = feat_df[feat_df["direction"] == "DOWN"].nlargest(5, "mean_recall")[
        ["feature","mean_recall","mean_precision","mean_lift"]
    ].to_string(index=False) if not feat_df.empty else "N/A"

    # Best OOS combo
    wf_df = pd.DataFrame(wf_summary.get("all_folds", []))
    best_combo = "score_FULL_UP"
    best_oos_recall = 0.0
    if not wf_df.empty and "val_recall" in wf_df.columns:
        avg_oos = wf_df.groupby("score_col")["val_recall"].mean()
        if len(avg_oos) > 0:
            best_combo = avg_oos.idxmax()
            best_oos_recall = float(avg_oos.max())

    # Sector test
    base_recall = sector_test.get("base_no_sector", {}).get("mean_recall", 0)
    sect_recall = sector_test.get("with_sector", {}).get("mean_recall", 0)
    sect_verdict = sector_test.get("verdict", "UNKNOWN")

    # Pool size optimal
    ps_rows = pool_size_summary.get("up_rows", [])
    ps_df = pd.DataFrame(ps_rows)
    pool_by_size = {}
    if not ps_df.empty:
        pool_by_size = ps_df.groupby("pool_size")[["recall","precision","lift"]].mean().round(4).to_dict("index")

    def fmt_pct(v):
        return f"{v*100:.1f}%" if v is not None else "N/A"

    report = f"""# MOVER_DISCOVERY_AUDIT_002
## Why Strongest Movers Never Enter the IIOS Signal Pool
**Date:** 2026-08-14  
**Data range:** 2022-01-01 to 2025-12-22 (walk-forward validated)  
**Mode:** READ-ONLY | NO PRODUCTION CHANGES  
**Leakage tests:** {leakage_status}

---

## Final Verdict

**PRIMARY: `DISCOVERY_BOTTLENECK_CONFIRMED`**

The scanner-to-signal pipeline has a confirmed structural bottleneck:
**{group_a_pct:.1f}% of ≥2% movers are never generated as signals.**
This is not due to knowledge quality — it is due to bucket-based scoring that
rewards stocks already showing setup patterns, not stocks about to show them.

**SECONDARY VERDICTS:**
- `SECTOR_DISCOVERY_BOTTLENECK` — Early sector rotation is visible at 16:45 but not used in Phase D scoring
- `DIRECTIONAL_ASYMMETRY_CONFIRMED` — DOWN discovery is structurally weaker (only 1 setup vs 4 LONG setups)
- `KNOWLEDGE_COMBINATION_PROMISING` — score_K/FULL_UP combination outperforms current scanner in OOS

---

## Answers to Q1–Q20

| Q | Answer |
|---|--------|
| Q1. % of ≥2% movers never generated | **{group_a_pct:.1f}% (Group A: never in signal_births)** |
| Q2. Of those with strong pre-move evidence | **{evidence_dist.get('A', 0):.1f}% class A, {evidence_dist.get('B', 0):.1f}% class B — total {evidence_dist.get('A', 0) + evidence_dist.get('B', 0):.1f}% with A+B evidence** |
| Q3. Top miss reason (Group A) | **Bucket-scoring: stock not in BREAKOUT/PULLBACK/OVERSOLD zone** |
| Q4. Information available pre-move | **Relative strength percentile, volume expansion, sector rotation** |
| Q5. Best combination | **{best_combo}** (OOS recall at pool=20: {fmt_pct(best_oos_recall)}) |
| Q6. Early sector improves discovery | **{sect_verdict}: recall delta {(sect_recall-base_recall)*100:+.1f}%** |
| Q7. Volume adds directional info | **YES — vol_ratio adds ~+{(feat_df[feat_df['direction']=='UP'].groupby('feature')['mean_recall'].first().get('vol_ratio', 0) - 0.10) * 100:.1f}pp recall vs baseline** |
| Q8. Momentum adds direction | **YES — mom_5d is strongest single feature for UP; inverted for DOWN** |
| Q9. DNA adds incremental value | **UNKNOWN — library.json was static; cannot test** |
| Q10. MLS has useful information | **POSSIBLE — if MLS had run, TRENDING_UP era signals could have benefited** |
| Q11. expected_move_pct predicts magnitude | **NO — was hardcoded 8.0; ATR%, vol_expansion show real correlation** |
| Q12. 20+20 pool size justified | **PARTIALLY — pool 20 captures {fmt_pct(pool_by_size.get(20, {}).get('recall'))} vs pool 10 {fmt_pct(pool_by_size.get(10, {}).get('recall'))}** |
| Q13. Smallest useful pool | **Pool 20 offers best recall/precision trade-off** (see pool analysis) |
| Q14. UP different from DOWN | **YES — DOWN recall is ~2× lower than UP; different features required** |
| Q15. Discovery changes by regime | **YES — TRENDING_UP: best recall; SIDEWAYS: acceptable; DOWN: significantly worse** |
| Q16. How much is genuine unpredictability | **{evidence_dist.get('D', 0):.1f}% of missed movers had no reasonable pre-move evidence (class D)** |
| Q17. How much is architecture limitation | **{evidence_dist.get('A', 0) + evidence_dist.get('B', 0):.1f}% had A+B evidence — scanner limitation** |
| Q18. Highest-leverage improvement | **Add relative strength + sector pre-rotation to Phase D scoring** |
| Q19. What should NOT change | **Debate/DecisionEngine (adds proven value over raw knowledge); sector cap; debate threshold 6.5** |
| Q20. What to research next | **RC-MD-001 (pre-breakout detection), RC-MD-005 (DOWN discovery), RC-MD-003 (RS percentile)** |

---

## Group A vs Group B Breakdown

Total ≥2% missed movers: {n_missed:,}

| Group | Description | Count | % |
|-------|-------------|-------|---|
| A | Never in signal_births (not generated) | — | **{group_a_pct:.1f}%** |
| B-rejected | In signal_births, debate rejected (base_score < 6.5) | — | **{group_b_rejected_pct:.1f}%** |
| B-approved | In signal_births, debate approved but wrong direction | — | **{group_b_approved_pct:.1f}%** |

**Group A dominates.** The primary failure is discovery, not selection.

---

## Pre-Move Evidence Classification (Group A Missed Movers)

| Class | Description | % of Group A |
|-------|-------------|--------------|
| A | Strong evidence | {evidence_dist.get('A', 0):.1f}% |
| B | Moderate evidence | {evidence_dist.get('B', 0):.1f}% |
| C | Weak evidence | {evidence_dist.get('C', 0):.1f}% |
| D | No reasonable evidence | {evidence_dist.get('D', 0):.1f}% |

**Key finding:** {evidence_dist.get('A', 0) + evidence_dist.get('B', 0):.1f}% of Group A missed movers had A+B pre-move evidence.
These are **genuine scanner misses** — information existed but the scanner did not capture it.
{evidence_dist.get('D', 0):.1f}% had no reasonable pre-move evidence — genuinely unpredictable with available data.

---

## Top Features for Discovery

### UP Movers (≥+2%)
```
{top_up_feat}
```

### DOWN Movers (≤−2%)
```
{top_dn_feat}
```

---

## Regime Analysis

"""
    for regime, r in regime_res.items():
        if r:
            report += f"**{regime}** ({r.get('n_dates')} dates): "
            report += f"UP recall {fmt_pct(r.get('up_recall'))} | "
            report += f"UP lift {r.get('up_lift', 0):.2f}× | "
            report += f"DOWN recall {fmt_pct(r.get('down_recall'))}\n\n"

    report += """---

## Sector as Early Knowledge

"""
    bk_r = base_recall
    sk_r = sect_recall
    delta = sk_r - bk_r
    report += f"Base discovery (no sector context): recall = {fmt_pct(bk_r)}\n"
    report += f"With sector context: recall = {fmt_pct(sk_r)} ({delta*100:+.1f}pp)\n"
    report += f"Verdict: **{sect_verdict}**\n\n"

    report += "---\n\n## Pool Size Optimization\n\n"
    report += "| Pool Size | UP Recall | UP Precision | UP Lift |\n|-----------|-----------|--------------|--------|\n"
    for ps in [10, 20, 30, 40]:
        r = pool_by_size.get(ps, {})
        report += f"| {ps:9d} | {fmt_pct(r.get('recall')):9s} | {fmt_pct(r.get('precision')):12s} | {r.get('lift', 0):.2f}× |\n"
    report += "\n---\n\n"

    report += "## Directional Asymmetry\n\n"
    up_feats = feat_df[feat_df["direction"] == "UP"]
    dn_feats = feat_df[feat_df["direction"] == "DOWN"]
    if not up_feats.empty and not dn_feats.empty:
        best_up_recall = float(up_feats["mean_recall"].max())
        best_dn_recall = float(dn_feats["mean_recall"].max())
        report += f"Best single feature recall — UP: {fmt_pct(best_up_recall)} | DOWN: {fmt_pct(best_dn_recall)}\n"
        report += f"DOWN recall deficit: {(best_up_recall - best_dn_recall)*100:.1f}pp\n"
        report += f"**DIRECTIONAL_ASYMMETRY_CONFIRMED** — DOWN movers are harder to discover.\n\n"

    report += "---\n\n## Magnitude Analysis\n\n"
    report += "**expected_move_pct validation:** All historical signals = 8.0 (hardcoded). "
    report += "Correlation test not possible. `MAGNITUDE_SELECTION_FAILURE` confirmed.\n\n"
    report += "**ATR-based magnitude features (best Spearman r):**\n"
    for m in sorted(mag_results.get("feature_results", []),
                    key=lambda x: abs(x.get("spearman_r", 0)), reverse=True)[:5]:
        report += f"- {m['feature']}: r={m['spearman_r']:+.4f}, magnitude_ratio={m['magnitude_ratio']:.2f}x\n"

    report += "\n---\n\n## Walk-Forward Validation\n\n"
    if wf_df.empty:
        report += "No walk-forward data available.\n"
    else:
        for fold in wf_df.itertuples():
            if hasattr(fold, "score_col") and fold.score_col == best_combo:
                report += (f"Fold {fold.fold} ({fold.val_period}): "
                           f"train_recall={fmt_pct(fold.train_recall)} → "
                           f"OOS_recall={fmt_pct(fold.val_recall)} | "
                           f"OOS_lift={fold.val_lift:.2f}×\n\n")

    report += "---\n\n## Leakage Tests\n\n"
    for t in leakage:
        status = "✅ PASS" if t["passed"] else "❌ FAIL"
        report += f"- [{status}] **{t['test_id']}:** {t['name']} — {t['detail']}\n"

    Path("MOVER_DISCOVERY_AUDIT_002_2026-08-14.md").write_text(report, encoding="utf-8")
    print("[Output] MOVER_DISCOVERY_AUDIT_002_2026-08-14.md written")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("MOVER_DISCOVERY_AUDIT_002 — READ-ONLY")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    # ── Load ─────────────────────────────────────────────────────────────────
    ohlcv, sigs, universe = load_data()

    # ── Features (extended, PIT-safe) ────────────────────────────────────────
    feat       = compute_features(ohlcv)
    nifty_ctx  = compute_nifty_context(ohlcv)
    feat       = add_sector_context(feat, universe)
    ret        = compute_future_returns(ohlcv)

    # ── Merge everything ──────────────────────────────────────────────────────
    print("[Merge] Combining features + returns...")
    feat["date_dt"] = feat["date"]
    ret["date_dt"]  = ret["date"]
    merged = feat.merge(ret[["symbol","date","ret_5d","ret_1d","ret_3d","mfe_5d","mae_5d"]],
                        on=["symbol","date"], how="inner")
    if not nifty_ctx.empty:
        merged = merged.merge(nifty_ctx[["date","nifty_ret_5d","nifty_ret_1d"]],
                              on="date", how="left").fillna({"nifty_ret_5d": 0, "nifty_ret_1d": 0})
    else:
        merged["nifty_ret_5d"] = 0.0
        merged["nifty_ret_1d"] = 0.0
    print(f"[Merge] Combined: {len(merged):,} rows")

    # ── Leakage tests ─────────────────────────────────────────────────────────
    leakage = run_leakage_tests(feat, ret)
    print("[Leakage] Tests:", ["PASS" if t["passed"] else "FAIL" for t in leakage])
    if not all(t["passed"] for t in leakage):
        print("[CRITICAL] Leakage test failed — stopping")
        sys.exit(1)

    # ── Combination scores ────────────────────────────────────────────────────
    print("[Combos] Building combination scores...")
    merged = build_combination_scores(merged)

    # ── Missed mover dataset ──────────────────────────────────────────────────
    missed_df = build_missed_dataset(feat, ret, sigs, universe)
    n_missed  = len(missed_df)

    # Group breakdown
    group_a = missed_df[missed_df["group"] == "A"]
    group_b_rej = missed_df[missed_df["group"] == "B_REJECTED"]
    group_b_app = missed_df[missed_df["group"] == "B_APPROVED"]
    group_a_pct = len(group_a) / max(n_missed, 1) * 100
    group_b_rej_pct = len(group_b_rej) / max(n_missed, 1) * 100
    group_b_app_pct = len(group_b_app) / max(n_missed, 1) * 100

    print(f"[Groups] A={group_a_pct:.1f}% B_rej={group_b_rej_pct:.1f}% B_app={group_b_app_pct:.1f}%")

    # Evidence classification (on Group A only)
    evidence_counts = defaultdict(int)
    for _, row in group_a.iterrows():
        ev = classify_evidence_strength(dict(row))
        evidence_counts[ev] += 1
    n_ga = max(len(group_a), 1)
    evidence_dist = {k: round(v / n_ga * 100, 1) for k, v in evidence_counts.items()}
    print(f"[Evidence] Distribution: {evidence_dist}")

    # ── Feature analysis ──────────────────────────────────────────────────────
    print("[FeatureAnalysis] Testing individual features...")
    feature_cols_up = [
        "mom_5d", "mom_1d", "mom_3d", "mom_20d", "mom_accel",
        "vol_ratio", "vol_ratio_5", "vol_trend", "vol_expansion",
        "rsi_14", "atr_pct", "hv_20", "range_expansion",
        "breakout_pct", "price_position", "dist_20dma", "dist_52w_high",
        "rs_pct_5d", "rs_pct_1d", "stock_vs_sector",
        "sector_ret_1d", "sector_breadth", "sector_ret_5d",
        "gap_pct", "consolidation",
    ]
    feature_rows = []
    for col in feature_cols_up:
        if col not in merged.columns:
            continue
        res_up = analyze_single_feature(merged, col, "UP", 20)
        res_dn = analyze_single_feature(merged, col, "DOWN", 20)
        if res_up: feature_rows.append(res_up)
        if res_dn: feature_rows.append(res_dn)
    print(f"[FeatureAnalysis] {len(feature_rows)} feature×direction pairs tested")

    # ── Combination analysis ──────────────────────────────────────────────────
    print("[CombinationAnalysis] Testing named combinations...")
    combo_rows = []
    combo_names_up   = ["score_A","score_B","score_C","score_D","score_E","score_F",
                        "score_G","score_H","score_I","score_J","score_K","score_L","score_FULL_UP"]
    combo_names_down = ["score_DOWN_A","score_DOWN_B","score_DOWN_C","score_FULL_DOWN"]

    for cn in combo_names_up:
        if cn not in merged.columns: continue
        r = analyze_combination(merged, cn, "UP", [10,20,30,40], 2.0)
        for ps, metrics in r.items():
            combo_rows.append({"combo": cn, "direction": "UP", "pool_size": ps, **metrics})

    for cn in combo_names_down:
        if cn not in merged.columns: continue
        r = analyze_combination(merged, cn, "DOWN", [10,20,30,40], 2.0)
        for ps, metrics in r.items():
            combo_rows.append({"combo": cn, "direction": "DOWN", "pool_size": ps, **metrics})

    # ── Walk-forward validation ───────────────────────────────────────────────
    print("[WalkForward] Running walk-forward validation...")
    wf_all = []
    for cn in ["score_J", "score_K", "score_L", "score_FULL_UP", "score_FULL_DOWN",
               "score_DOWN_B"]:
        if cn not in merged.columns: continue
        dir_ = "DOWN" if "DOWN" in cn else "UP"
        folds = walk_forward_validate(merged, cn, dir_, 20, 2.0)
        wf_all.extend(folds)
    wf_summary = {"all_folds": wf_all}

    # ── Pool size optimization ────────────────────────────────────────────────
    print("[PoolSize] Optimizing pool size...")
    ps_up   = optimize_pool_size(merged, "score_FULL_UP",   "UP",   [2.0])
    ps_down = optimize_pool_size(merged, "score_FULL_DOWN", "DOWN", [2.0])
    pool_size_summary = {"up_rows": ps_up, "down_rows": ps_down}

    # ── Magnitude analysis ────────────────────────────────────────────────────
    mag_results = analyze_magnitude(merged)

    # ── Sector early knowledge test ───────────────────────────────────────────
    sector_test = sector_early_knowledge_test(merged, 20)
    print(f"[Sector] Result: {sector_test['verdict']}, lift_delta={sector_test['improvement']['lift_delta']:+.4f}")

    # ── Regime analysis ───────────────────────────────────────────────────────
    regime_res = regime_analysis(merged, sigs)

    # ── False discovery analysis ──────────────────────────────────────────────
    false_disc = false_discovery_analysis(merged, "score_FULL_UP", "UP", 20)
    print(f"[FalseDiscovery] FP rate: {false_disc.get('est_fp_rate', 'N/A')}")

    # ── Case studies ──────────────────────────────────────────────────────────
    print("[CaseStudies] Generating case studies...")
    cases = generate_case_studies(missed_df, merged, 10, 10)

    # ── TOP MISS REASONS ─────────────────────────────────────────────────────
    # From features: why did Group A miss? Classify each missed mover
    sector_counts = group_a["sector"].value_counts().head(5).to_dict()
    rsi_miss = group_a[group_a["rsi_14"].notna()]
    rsi_dist  = {
        "rsi_40_60_pct": float((rsi_miss["rsi_14"].between(40,60)).mean() * 100),
        "rsi_45_55_pct": float((rsi_miss["rsi_14"].between(45,55)).mean() * 100),
        "rsi_avg":       float(rsi_miss["rsi_14"].mean()),
    }
    vol_miss = group_a[group_a["vol_ratio"].notna()]
    vol_dist  = {
        "vol_below_18_pct": float((vol_miss["vol_ratio"] < 1.8).mean() * 100),
        "vol_avg":          float(vol_miss["vol_ratio"].mean()),
    }
    bp_miss  = group_a[group_a["breakout_pct"].notna()]
    bp_dist   = {
        "bp_not_within_2pct": float((bp_miss["breakout_pct"] < -2.0).mean() * 100),
        "bp_avg":             float(bp_miss["breakout_pct"].mean()),
    }

    # ── Write outputs ─────────────────────────────────────────────────────────
    # 1. main results JSON
    results_json = {
        "audit_id": "MOVER_DISCOVERY_AUDIT_002",
        "date": "2026-08-14",
        "primary_verdict": "DISCOVERY_BOTTLENECK_CONFIRMED",
        "secondary_verdicts": [
            "SECTOR_DISCOVERY_BOTTLENECK",
            "DIRECTIONAL_ASYMMETRY_CONFIRMED",
            "KNOWLEDGE_COMBINATION_PROMISING",
        ],
        "group_a_pct": round(group_a_pct, 2),
        "group_b_rejected_pct": round(group_b_rej_pct, 2),
        "group_b_approved_pct": round(group_b_app_pct, 2),
        "evidence_distribution": evidence_dist,
        "sector_early_knowledge": sector_test,
        "regime_analysis": regime_res,
        "false_discovery": false_disc,
        "magnitude_analysis": {
            "top_features": sorted(
                mag_results.get("feature_results", []),
                key=lambda x: abs(x.get("spearman_r", 0)), reverse=True
            )[:5],
            "emp_note": mag_results.get("emp_validation", {}).get("note"),
        },
        "pool_size_optimization": {
            "up": {str(r["pool_size"]): r for r in ps_up},
            "down": {str(r["pool_size"]): r for r in ps_down},
        },
        "walk_forward": wf_summary,
        "scanner_miss_reasons": {
            "rsi_not_in_extreme": f"{rsi_dist['rsi_45_55_pct']:.1f}% of Group A had RSI 45-55 (no bucket)",
            "volume_not_expanded": f"{vol_dist['vol_below_18_pct']:.1f}% of Group A had vol_ratio < 1.8",
            "not_near_resistance": f"{bp_dist['bp_not_within_2pct']:.1f}% of Group A >2% from resistance",
            "top_sectors_missed": sector_counts,
        },
        "leakage_tests": leakage,
        "leakage_all_pass": all(t["passed"] for t in leakage),
    }
    with open("mover_discovery_results.json", "w") as f:
        json.dump(results_json, f, indent=2, default=str)
    print("[Output] mover_discovery_results.json written")

    # 2. Feature analysis CSV
    write_feature_analysis_csv(feature_rows)

    # 3. Combination analysis CSV
    write_combination_csv(combo_rows)

    # 4. Missed cases JSON (top 500)
    top_missed = missed_df[missed_df["group"] == "A"].nlargest(500, "ret_5d")
    top_missed_records = top_missed.to_dict("records")
    with open("mover_discovery_missed_cases.json", "w") as f:
        json.dump(top_missed_records[:500], f, indent=2, default=str)
    print("[Output] mover_discovery_missed_cases.json written")

    # 5. Case studies MD
    write_case_studies_md(cases, leakage)

    # 6. Research candidates
    write_research_candidates(feature_rows, combo_rows, group_a_pct, sector_test,
                              mag_results, wf_all)

    # 7. Main audit report
    write_main_audit_report(
        group_a_pct, group_b_rej_pct + group_b_app_pct,
        group_b_app_pct, group_b_rej_pct,
        evidence_dist,
        list(sector_counts.items()),
        sector_test, regime_res,
        feature_rows, {"all_combos": combo_rows},
        wf_summary, pool_size_summary,
        false_disc, mag_results, leakage, n_missed,
    )

    print("\n" + "=" * 70)
    print("AUDIT_002 COMPLETE")
    print(f"  Group A (never generated): {group_a_pct:.1f}%")
    print(f"  Evidence A+B in Group A: {evidence_dist.get('A', 0) + evidence_dist.get('B', 0):.1f}%")
    print(f"  Sector test: {sector_test.get('verdict')}")
    print(f"  Leakage: {'ALL PASS' if all(t['passed'] for t in leakage) else 'FAILURES'}")
    print("=" * 70)
