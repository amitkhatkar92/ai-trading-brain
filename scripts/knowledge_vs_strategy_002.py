"""
KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002
Date: 2026-08-17
Mode: READ-ONLY / RESEARCH ONLY

Answers: After the Knowledge layer (V3 + gap) has selected the best
         opportunities, does the Strategy layer add incremental value?

Architecture under test:
  230 â†’ V3 â†’ 20+20 â†’ Gap (Model O) â†’ Knowledge (C2_Top5) â†’ Strategy? â†’ 5-6

Models:
  A  : Knowledge Only  = C2_Top5 (V3 + continuous gap score, best from prior research)
  B  : Knowledge + Strategy = C2_Top5 intersected with Strategy PASS
  C  : Strategy Only = rank V3 pool by strategy conformance score
  R  : Random baselines (seed 42-46)

Strategy simulation from evolved_strategies.json:
  - 177 evolved strategies, all approved=True
  - 94 evaluable from OHLCV (no vix/iv_rank/pcr required)
  - 83 UNAVAILABLE (need vix, iv_rank, or pcr)
  - All EDG strategies direction=BUY â†’ evaluated for UP candidates
  - DOWN candidates: NO_EDG_SELL_STRATEGY â†’ regime-based proxy

NO PRODUCTION CHANGES. NO ORDERS. NO BROKER CALLS. NO WRITES.
Dhan calls = 0. CandidateStore writes = 0. OrderManager calls = 0.
"""
from __future__ import annotations
import json, random, sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Constants
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DB_PATH          = Path("data/study002_replay.db")
RETRO_CSV        = Path("reports/mover_discovery_v3/v3_retro_candidates.csv")
PRIOR_GAP_CSV    = Path("reports/mover_discovery_v3/post_open_gap_analysis.csv")
EVOLVED_STRAT    = Path("data/evolved_strategies.json")
REPORT_DIR       = Path("reports/mover_discovery_v3")

TRAIN_START = "2025-09-16"; TRAIN_END   = "2026-02-19"
VAL_START   = "2026-02-20"; VAL_END     = "2026-05-13"
OOS_START   = "2026-05-14"; OOS_END     = "2026-07-30"

RANDOM_SEEDS     = [42, 43, 44, 45, 46]
POOL_SIZE        = 20

# Trade quality thresholds (fixed before any OOS look)
GOOD_THRESHOLD   = 2.0   # >= 2% correct direction = STRONG OPPORTUNITY
FP_THRESHOLD     = -1.0  # <= -1% direction-adjusted = FALSE POSITIVE (bad)
NEUTRAL_BAND     = (0.0, GOOD_THRESHOLD)  # 0-2% = NEUTRAL

# Strategy unavailability reason
UNAVAIL_FEATURES = {"vix", "iv_rank", "pcr"}

# Output paths
OUT_RESULTS  = REPORT_DIR / "knowledge_vs_strategy_002_results.json"
OUT_MODEL    = REPORT_DIR / "knowledge_vs_strategy_002_model_comparison.csv"
OUT_INC      = REPORT_DIR / "knowledge_vs_strategy_002_incremental_value.csv"
OUT_REJ      = REPORT_DIR / "knowledge_vs_strategy_002_rejection_audit.csv"
OUT_OPP      = REPORT_DIR / "knowledge_vs_strategy_002_opportunity_cost.csv"
OUT_OOS      = REPORT_DIR / "knowledge_vs_strategy_002_oos_results.csv"
OUT_REGIME   = REPORT_DIR / "knowledge_vs_strategy_002_regime_results.csv"
OUT_CASES    = REPORT_DIR / "knowledge_vs_strategy_002_case_studies.md"
OUT_TESTS    = Path("tests/test_knowledge_vs_strategy_002.py")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _split(d: str) -> str:
    if TRAIN_START <= d <= TRAIN_END: return "TRAIN"
    if VAL_START   <= d <= VAL_END:   return "VAL"
    if OOS_START   <= d <= OOS_END:   return "OOS"
    return "UNKNOWN"

def _fn(v) -> Any:
    if v is None or (isinstance(v, float) and not np.isfinite(v)): return None
    return round(float(v), 4)

def _spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 4: return None
    r, _ = stats.spearmanr(a[mask], b[mask])
    return _fn(r) if np.isfinite(r) else None

def _stats(rows: pd.DataFrame, direction: str, score_col: str = None) -> dict:
    if rows.empty or "t1_ret_pct" not in rows: return {"n": 0}
    clean = rows.dropna(subset=["t1_ret_pct"])
    if clean.empty: return {"n": 0}
    t1 = clean["t1_ret_pct"].values.astype(float)
    da = t1 if direction == "UP" else -t1
    n  = len(da)
    fav = da[da > 0]
    mfe = clean["mfe_pct"].dropna().values.astype(float) if "mfe_pct" in clean else np.array([])
    mae = clean["mae_pct"].dropna().values.astype(float) if "mae_pct" in clean else np.array([])
    sp  = _spearman(clean[score_col].values.astype(float), da) if score_col and score_col in clean else None
    return {
        "n":         n,
        "dir_acc":   _fn(np.mean(da > 0)),
        "ge1_rate":  _fn(np.mean(da >= 1.0)),
        "ge2_rate":  _fn(np.mean(da >= 2.0)),
        "ge3_rate":  _fn(np.mean(da >= 3.0)),
        "avg_fav":   _fn(np.mean(fav)) if len(fav) else None,
        "med_fav":   _fn(np.median(fav)) if len(fav) else None,
        "avg_mfe":   _fn(np.nanmean(mfe)) if len(mfe) else None,
        "avg_mae":   _fn(np.nanmean(mae)) if len(mae) else None,
        "fp_rate":   _fn(np.mean(da < FP_THRESHOLD)),
        "spearman":  sp,
        "ev":        _fn(np.mean(da)),
    }

def _concentration(pool: pd.DataFrame, selected: pd.DataFrame, direction: str, n: int) -> dict:
    if pool.empty or selected.empty: return {}
    keys = set(zip(selected["trading_date"], selected["symbol"]))
    shares = []
    for d, pg in pool.groupby("trading_date"):
        fav_pool = (pg["t1_ret_pct"].clip(lower=0) if direction == "UP"
                    else (-pg["t1_ret_pct"]).clip(lower=0)).sum()
        if fav_pool <= 0: continue
        sg = pg[pg["symbol"].map(lambda s: (d, s) in keys)]
        fav_sel = (sg["t1_ret_pct"].clip(lower=0) if direction == "UP"
                   else (-sg["t1_ret_pct"]).clip(lower=0)).sum()
        shares.append(float(fav_sel) / float(fav_pool))
    if not shares: return {}
    avg = float(np.mean(shares))
    rand = n / POOL_SIZE
    return {"avg_share": _fn(avg), "rand_share": _fn(rand), "lift": _fn(avg / rand) if rand > 0 else None}

def _bootstrap_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 500, seed: int = 42) -> dict:
    """Bootstrap 95% CI for difference in means."""
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs.append(np.mean(sa) - np.mean(sb))
    diffs = np.array(diffs)
    return {
        "mean_diff": _fn(np.mean(diffs)),
        "ci_95_low": _fn(np.percentile(diffs, 2.5)),
        "ci_95_high": _fn(np.percentile(diffs, 97.5)),
        "prob_a_gt_b": _fn(np.mean(np.array(diffs) > 0)),
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Data loading
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_candidates() -> pd.DataFrame:
    rc = pd.read_csv(RETRO_CSV)
    rc["direction"] = rc["direction"].replace({"DN": "DOWN"})
    rc["split"] = rc["trading_date"].apply(_split)
    return rc[rc["split"] != "UNKNOWN"].copy()

def load_prior_gap() -> pd.DataFrame:
    gp = pd.read_csv(PRIOR_GAP_CSV)
    gp["direction"] = gp["direction"].replace({"DN": "DOWN"})
    return gp

def load_ohlcv() -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT symbol, trade_date, open, high, low, close, volume FROM ohlcv_daily", con)
    con.close()
    return df

def load_sector_data() -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT record_date, sector, consensus_score, capital_flow_score, rs_vs_market_20d "
        "FROM sector_conviction_daily", con)
    con.close()
    return df

def load_evolved_strategies() -> dict:
    return json.loads(EVOLVED_STRAT.read_text(encoding="utf-8"))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Technical indicator helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index â€” returns raw ADX values."""
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    dm_pos = (high - high.shift()).clip(lower=0)
    dm_pos[dm_pos < (low.shift() - low).clip(lower=0)] = 0
    dm_neg = (low.shift() - low).clip(lower=0)
    dm_neg[dm_neg < (high - high.shift()).clip(lower=0)] = 0
    atr  = tr.ewm(com=period - 1, min_periods=period).mean()
    di_p = 100.0 * dm_pos.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)
    di_n = 100.0 * dm_neg.ewm(com=period - 1, min_periods=period).mean() / atr.replace(0, np.nan)
    dx   = 100.0 * (di_p - di_n).abs() / (di_p + di_n).replace(0, np.nan)
    return dx.ewm(com=period - 1, min_periods=period).mean()

def _bb_position(close: pd.Series, period: int = 20, std_mult: float = 2.0) -> pd.Series:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return (close - lower) / (upper - lower).replace(0, np.nan)

def _macd_signal(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_f = close.ewm(span=fast).mean()
    ema_s = close.ewm(span=slow).mean()
    macd  = ema_f - ema_s
    return macd.ewm(span=signal).mean()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Market feature computation (per day, from NIFTY + universe)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_market_features(ohlcv: pd.DataFrame, sector: pd.DataFrame,
                             candidates: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all evaluable strategy features per trading day.
    Information horizon: T close (pre-market, day T).
    All features are computed from data available BEFORE T+1 open.
    """
    nifty = ohlcv[ohlcv["symbol"] == "^NSEI"].sort_values("trade_date").copy()
    nifty = nifty.reset_index(drop=True)

    close  = nifty["close"]
    high   = nifty["high"]
    low    = nifty["low"]
    volume = nifty["volume"]

    # Returns
    log_ret = np.log(close / close.shift(1))
    nifty["mom_1d"]  = close.pct_change(1)  * 100
    nifty["mom_5d"]  = close.pct_change(5)  * 100
    nifty["mom_10d"] = close.pct_change(10) * 100
    nifty["mom_20d"] = close.pct_change(20) * 100

    # Volatility (annualized)
    nifty["hist_vol_20d"] = log_ret.rolling(20).std() * np.sqrt(252)
    nifty["hist_vol_5d"]  = log_ret.rolling(5).std()  * np.sqrt(252)

    # Regime
    nifty["regime_bull"] = (nifty["mom_20d"] > 5.0).astype(float)
    nifty["global_bias"] = ((nifty["mom_20d"] + 10.0) / 20.0).clip(0, 1)
    nifty["regime_score"] = (nifty["mom_20d"] / 10.0).clip(0, 1) * 0.5 + \
                             nifty["regime_bull"] * 0.5

    # Technical indicators
    nifty["rsi"]           = _rsi(close, 14)
    nifty["rsi_norm"]      = (nifty["rsi"] - 50.0) / 50.0
    nifty["rsi_overbought"]= (nifty["rsi"] > 70.0).astype(float)
    nifty["adx_score"]     = _adx(high, low, close, 14) / 100.0
    nifty["bb_position"]   = _bb_position(close)
    nifty["macd_signal_norm"] = _macd_signal(close) / (close.rolling(20).std() + 1e-9)

    # Volume
    nifty["volume_ratio"]     = volume / volume.rolling(20).mean()
    nifty["volume_ratio_raw"] = nifty["volume_ratio"]
    nifty["volume_spike"]     = (nifty["volume_ratio"] > 2.0).astype(float)
    nifty["liquidity_score"]  = (nifty["volume_ratio"] / 3.0).clip(0, 1)

    # Intra-day range
    nifty["intra_range"] = (high - low) / close

    # NIFTY gap
    nifty["gap_pct"] = (nifty["open"] / nifty["close"].shift(1) - 1.0) * 100.0

    # Market breadth: % of universe stocks (non-NIFTY) that close > prev_close
    universe = ohlcv[ohlcv["symbol"] != "^NSEI"].copy()
    universe["prev_close"] = universe.groupby("symbol")["close"].shift(1)
    universe["up"] = (universe["close"] > universe["prev_close"]).astype(float)
    universe["strong"] = ((universe["close"] / universe["prev_close"].replace(0, np.nan) - 1) > 0.01).astype(float)
    breadth_day = universe.groupby("trade_date")[["up", "strong"]].mean().rename(
        columns={"up": "breadth", "strong": "breadth_strong"}).reset_index()
    nifty = nifty.merge(breadth_day, on="trade_date", how="left")

    # Sector features from sector_conviction_daily
    sector_agg = sector.groupby("record_date").agg(
        avg_conviction=("consensus_score", "mean"),
        sector_strength=("rs_vs_market_20d", "mean"),
        sector_flow_count=("capital_flow_score", lambda x: (x > 0.6).sum()),
    ).reset_index().rename(columns={"record_date": "trade_date"})
    nifty = nifty.merge(sector_agg, on="trade_date", how="left")

    # Event count (from oios_events â€” expected to be 0 in this DB)
    nifty["event_count"] = 0.0

    # IV-related features â€” UNAVAILABLE
    nifty["vix"]      = np.nan  # UNAVAILABLE
    nifty["iv_rank"]  = np.nan  # UNAVAILABLE
    nifty["pcr"]      = np.nan  # UNAVAILABLE

    return nifty[["trade_date",
                   "mom_1d", "mom_5d", "mom_10d", "mom_20d",
                   "hist_vol_20d", "hist_vol_5d",
                   "regime_bull", "global_bias", "regime_score",
                   "rsi", "rsi_norm", "rsi_overbought",
                   "adx_score", "bb_position", "macd_signal_norm",
                   "volume_ratio", "volume_ratio_raw", "volume_spike", "liquidity_score",
                   "intra_range", "gap_pct",
                   "breadth", "breadth_strong",
                   "avg_conviction", "sector_strength", "sector_flow_count",
                   "event_count",
                   "vix", "iv_rank", "pcr"]].copy()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Stock-level features (per symbol Ã— date)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_stock_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Per stock per day features for base strategy evaluation.
    Information horizon: T close.
    """
    stocks = ohlcv[ohlcv["symbol"] != "^NSEI"].copy().sort_values(["symbol", "trade_date"])
    stocks["rsi"] = stocks.groupby("symbol")["close"].transform(
        lambda x: _rsi(x, 14))
    stocks["vol_20d_avg"] = stocks.groupby("symbol")["volume"].transform(
        lambda x: x.rolling(20, min_periods=10).mean())
    stocks["volume_ratio"] = stocks["volume"] / stocks["vol_20d_avg"].replace(0, np.nan)
    stocks["mom_5d"] = stocks.groupby("symbol")["close"].transform(
        lambda x: x.pct_change(5) * 100)
    return stocks[["symbol", "trade_date", "rsi", "volume_ratio", "mom_5d"]].copy()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Strategy evaluation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

OPERATOR_MAP = {
    ">":  lambda f, t: f > t,
    ">=": lambda f, t: f >= t,
    "<":  lambda f, t: f < t,
    "<=": lambda f, t: f <= t,
    "==": lambda f, t: f == t,
}

def _eval_condition(feat_val: float, op: str, threshold: float) -> bool | None:
    """Evaluate a single strategy condition. None = cannot evaluate."""
    if feat_val is None or (isinstance(feat_val, float) and not np.isfinite(feat_val)):
        return None   # UNAVAILABLE
    fn = OPERATOR_MAP.get(op)
    if fn is None: return None
    return bool(fn(feat_val, threshold))

def categorise_strategies(strategies: dict) -> tuple[list, list, list]:
    """Split strategies into: evaluable, unavailable, base (no entry_conditions)."""
    evaluable = []
    unavailable = []
    base_strats = []
    for name, data in strategies.items():
        if "entry_conditions" not in data:
            base_strats.append((name, data))
            continue
        feats = {c["feature"] for c in data["entry_conditions"]}
        if feats & UNAVAIL_FEATURES:
            unavailable.append((name, data))
        else:
            evaluable.append((name, data))
    return evaluable, unavailable, base_strats

def evaluate_edg_strategy(strat_data: dict, day_feats: dict) -> str:
    """
    Evaluate a single EDG strategy.
    Returns: 'PASS' / 'REJECT' / 'UNAVAILABLE'
    """
    conditions = strat_data.get("entry_conditions", [])
    if not conditions:
        return "NO_CONDITIONS"
    for cond in conditions:
        feat  = cond["feature"]
        op    = cond["operator"]
        thresh = cond["threshold"]
        val   = day_feats.get(feat)
        result = _eval_condition(val, op, thresh)
        if result is None:
            return "UNAVAILABLE"
        if not result:
            return "REJECT"
    return "PASS"

def evaluate_base_strategy(strat_name: str, strat_data: dict,
                             stock_feats: dict) -> str:
    """
    Evaluate Breakout_Volume_RSI_HiVol / Mean_Reversion_RSI_HiVol.
    Stock-level: RSI in [rsi_min, rsi_max] AND volume_ratio >= threshold.
    """
    rsi    = stock_feats.get("rsi")
    volr   = stock_feats.get("volume_ratio")
    if rsi is None or (isinstance(rsi, float) and not np.isfinite(rsi)):
        return "UNAVAILABLE"
    if not strat_data.get("use_rsi_filter", False):
        return "NO_CONDITIONS"
    rsi_min  = strat_data.get("rsi_min", 0)
    rsi_max  = strat_data.get("rsi_max", 100)
    vol_thr  = strat_data.get("volume_ratio", 1.0)
    if rsi_min <= rsi <= rsi_max:
        if volr is not None and np.isfinite(volr) and volr >= vol_thr:
            return "PASS"
        elif volr is None or (isinstance(volr, float) and not np.isfinite(volr)):
            return "UNAVAILABLE"
        else:
            return "REJECT"
    return "REJECT"

def compute_strategy_status_per_candidate(
        df: pd.DataFrame,
        market_features: pd.DataFrame,
        stock_features: pd.DataFrame,
        strategies: dict) -> pd.DataFrame:
    """
    For every candidate determine strategy_status.

    Regime gate (from production StrategyGeneratorAI._assign):
      BEAR + UP (BUY)  â†’ REJECT  (explicit production rule: no equity longs in bear)
      VOLATILE + UP    â†’ REJECT  (high volatility threshold, confidence required)
      BULL + DOWN      â†’ REJECT  (regime contradicts direction)
      BEAR + DOWN      â†’ PASS    (regime aligned)
      BULL + UP        â†’ PASS    (regime aligned, best EDG variant confirmed)
      RANGE + either   â†’ evaluate EDG strategy conditions

    EDG evaluation (only in RANGE or as secondary in BULL):
      Find best-fit EDG strategy (most conditions met).
      If ANY evaluable strategy passes all conditions â†’ EDG_PASS.
      Else REJECT.

    DOWN candidates: no EDG SELL strategies exist.
      Regime-based: bear â†’ ALIGNED, bull â†’ CONTRADICTED, range â†’ NEUTRAL.
    """
    evaluable, unavailable, base_strats = categorise_strategies(strategies)
    buy_edg = [(n, d) for n, d in evaluable if d.get("direction") == "BUY"]

    # Market features lookup
    mf_dict = market_features.set_index("trade_date").to_dict("index")

    # Per-day regime classification
    def _regime(feats: dict) -> str:
        m20 = feats.get("mom_20d")
        hv  = feats.get("hist_vol_20d")
        if m20 is None or not np.isfinite(m20):
            return "UNKNOWN"
        if hv is not None and np.isfinite(hv) and hv > 0.25:
            return "VOLATILE"
        if m20 > 5:   return "BULL"
        if m20 < -5:  return "BEAR"
        return "RANGE"

    # Per-day EDG PASS count (for strategy_score)
    day_edg_pass = {}
    for date, feats in mf_dict.items():
        n_pass = sum(1 for _, d in buy_edg
                     if evaluate_edg_strategy(d, feats) == "PASS")
        day_edg_pass[date] = n_pass

    # Stock-level features lookup
    sf_dict = stock_features.set_index(["symbol", "trade_date"]).to_dict("index")

    rows = []
    for _, cand in df.iterrows():
        d   = cand["trading_date"]
        sym = cand["symbol"]
        dir = cand["direction"]
        feats   = mf_dict.get(d, {})
        regime  = _regime(feats)
        n_pass  = day_edg_pass.get(d, 0)
        n_total = len(buy_edg)
        strat_score = n_pass / max(n_total, 1)

        if dir == "UP":
            # â”€â”€â”€ Regime gate (matches production code) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if regime == "BEAR":
                status = "REJECT"         # explicit: no equity longs in bear
                edg_status = "NOT_EVALUATED_BEAR"
            elif regime == "VOLATILE":
                status = "REJECT"         # volatile regime â†’ no equity signals without high confidence
                edg_status = "NOT_EVALUATED_VOLATILE"
            elif regime == "BULL":
                # Regime supports UP. Check EDG conditions for best fit.
                edg_status = "PASS" if n_pass > 0 else "REJECT"
                status = "PASS"           # regime aligned; EDG confirmation logged separately
            else:  # RANGE or UNKNOWN
                # EDG conditions decide
                edg_status = "PASS" if n_pass > 0 else "REJECT"
                status = edg_status       # RANGE: EDG must confirm

            # Stock-level base strategy check
            sf = sf_dict.get((sym, d), {})
            base_pass = False
            for bn, bd in (base_strats or []):
                if evaluate_base_strategy(bn, bd, sf) == "PASS":
                    base_pass = True; break

            # If base strategy passes and regime is not BEAR/VOLATILE, upgrade to PASS
            if base_pass and status == "REJECT" and regime not in ("BEAR", "VOLATILE"):
                status = "PASS_BASE"

        else:  # DOWN
            if regime == "BEAR":   status = "ALIGNED"
            elif regime == "BULL": status = "CONTRADICTED"
            elif regime == "RANGE": status = "NEUTRAL"
            else:                  status = "UNAVAILABLE"
            edg_status = "NO_EDG_SELL_STRATEGY"

        rows.append({**cand.to_dict(),
            "regime_at_eval":     regime,
            "edg_day_status":     edg_status,
            "strategy_status":    status,
            "n_edg_pass":         n_pass,
            "n_edg_total_eval":   n_total,
            "strategy_score":     strat_score,
            "no_edg_sell_note":   "All 177 evolved strategies are BUY-direction." if dir == "DOWN" else None,
        })

    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Selection helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _top_n(df: pd.DataFrame, direction: str, score_col: str, n: int,
           ascending: bool = False) -> pd.DataFrame:
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        v = g[g[score_col].notna()]
        if v.empty: v = g
        sel = v.nsmallest(n, score_col) if ascending else v.nlargest(n, score_col)
        frames.append(sel)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _top_n_stratpassed(df: pd.DataFrame, direction: str, score_col: str, n: int) -> pd.DataFrame:
    """Top-n by score, limited to STRATEGY_PASS candidates; fill to n if needed."""
    PASS_SET = {"PASS", "PASS_BASE", "ALIGNED"}
    frames = []
    for d, g in df[df["direction"] == direction].groupby("trading_date"):
        passed  = g[g["strategy_status"].isin(PASS_SET)].nlargest(n, score_col)
        if len(passed) < n:
            remaining = g[~g["strategy_status"].isin(PASS_SET)]
            topup = remaining.nlargest(n - len(passed), score_col)
            passed = pd.concat([passed, topup], ignore_index=True)
        frames.append(passed.head(n))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _strategy_score_select(df: pd.DataFrame, direction: str, n: int) -> pd.DataFrame:
    """Model C: rank by strategy_score (fraction of EDG strategies passing)."""
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        v = g[g["strategy_score"].notna()]
        if v.empty: v = g
        frames.append(v.nlargest(n, "strategy_score").head(n))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _random_select(df: pd.DataFrame, direction: str, n: int) -> pd.DataFrame:
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        for seed in RANDOM_SEEDS:
            rng = random.Random(seed)
            k = min(n, len(g))
            frames.append(g.iloc[sorted(rng.sample(range(len(g)), k))])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _random_single(df: pd.DataFrame, direction: str, n: int, seed: int = 42) -> pd.DataFrame:
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        rng = random.Random(seed)
        k = min(n, len(g))
        frames.append(g.iloc[sorted(rng.sample(range(len(g)), k))])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Rejection analysis
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_rejection_audit(df: pd.DataFrame, knowledge_selected: pd.DataFrame,
                           direction: str) -> pd.DataFrame:
    """
    For Knowledge-selected candidates that Strategy REJECTED, classify the rejection.
    CORRECT_REJECTION: dir_adj_ret â‰¤ 0 (direction wrong â€” strategy right to block)
    FALSE_REJECTION:   dir_adj_ret â‰¥ GOOD_THRESHOLD (missed strong opportunity)
    NEUTRAL_REJECTION: 0 < dir_adj_ret < GOOD_THRESHOLD (minor opportunity missed)

    Only includes candidates where strategy_status is in REJECT set.
    """
    REJECT_STATUSES = {"REJECT", "CONTRADICTED"}
    kn_keys = set(zip(knowledge_selected["trading_date"], knowledge_selected["symbol"]))

    rows = []
    for _, row in df[df["direction"] == direction].iterrows():
        is_kn  = (row["trading_date"], row["symbol"]) in kn_keys
        is_rej = row.get("strategy_status") in REJECT_STATUSES
        if not is_kn or not is_rej:
            continue
        da = row["t1_ret_pct"] if direction == "UP" else -row["t1_ret_pct"]
        if pd.isna(da):
            outcome = "MISSING"; rej_class = "MISSING"
        else:
            da = float(da)
            if da <= 0:      outcome = "BAD";    rej_class = "CORRECT_REJECTION"
            elif da >= GOOD_THRESHOLD: outcome = "STRONG"; rej_class = "FALSE_REJECTION"
            else:            outcome = "NEUTRAL"; rej_class = "NEUTRAL_REJECTION"

        rows.append({
            "trading_date":    row["trading_date"],
            "symbol":          row["symbol"],
            "direction":       direction,
            "split":           row.get("split", ""),
            "regime_at_eval":  row.get("regime_at_eval"),
            "knowledge_score": row.get("C2_score"),
            "gap_pct":         row.get("gap_pct"),
            "strategy_status": row.get("strategy_status"),
            "edg_day_status":  row.get("edg_day_status"),
            "n_edg_pass":      row.get("n_edg_pass"),
            "t1_ret_pct":      row["t1_ret_pct"],
            "dir_adj_ret":     _fn(da),
            "mfe_pct":         row.get("mfe_pct"),
            "mae_pct":         row.get("mae_pct"),
            "regime":          row.get("regime"),
            "outcome":         outcome,
            "rejection_class": rej_class,
            "is_strategy_pass": False,
        })
    return pd.DataFrame(rows)

def compute_opportunity_cost(rejection_df: pd.DataFrame, direction: str) -> pd.DataFrame:
    """Aggregate rejection classes by strategy result."""
    rows = []
    for status in ["PASS", "REJECT", "UNAVAILABLE", "ALIGNED", "CONTRADICTED", "NEUTRAL"]:
        sub = rejection_df[rejection_df["strategy_status"] == status]
        if sub.empty:
            continue
        total = len(sub)
        correct = (sub["rejection_class"] == "CORRECT_REJECTION").sum()
        false_r = (sub["rejection_class"] == "FALSE_REJECTION").sum()
        neutral = (sub["rejection_class"] == "NEUTRAL_REJECTION").sum()
        strong_da = sub[sub["outcome"] == "STRONG"]["dir_adj_ret"]
        rows.append({
            "direction":          direction,
            "strategy_status":    status,
            "total_candidates":   total,
            "correct_rejection":  correct,
            "false_rejection":    false_r,
            "neutral_rejection":  neutral,
            "correct_pct":        _fn(correct / total) if total else None,
            "false_pct":          _fn(false_r / total) if total else None,
            "avg_strong_missed":  _fn(strong_da.mean()) if len(strong_da) else None,
        })
    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Model evaluation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def eval_models(df: pd.DataFrame) -> dict:
    """Evaluate all models per direction per split."""
    results = {}

    models_up = {
        "V3_20":           ("v3_score", POOL_SIZE, False, "standard"),
        "A_KN_Top5":       ("C2_score", 5, False, "standard"),
        "A_KN_Top6":       ("C2_score", 6, False, "standard"),
        "B_KnStrat_Top5":  ("C2_score", 5, False, "strat_pass_fill"),
        "B_KnStrat_Top6":  ("C2_score", 6, False, "strat_pass_fill"),
        "C_Strat_Top5":    ("strategy_score", 5, False, "strat_score"),
        "C_Strat_Top6":    ("strategy_score", 6, False, "strat_score"),
        "KN_PASS_days_T5": ("C2_score", 5, False, "pass_days_only"),
        "KN_REJECT_days_T5":("C2_score", 5, False, "reject_days_only"),
    }

    for direction in ["UP", "DOWN"]:
        results[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            pool = sub[sub["direction"] == direction]
            d = {}

            # Pool baseline
            s = _stats(pool, direction, "C2_score")
            s["concentration"] = {"lift": 1.0}
            s["top1_cap"] = None
            d["V3_20"] = s

            # Model A: Knowledge (gap C2) only
            for n in [5, 6]:
                sel = _top_n(sub, direction, "C2_score", n)
                s = _stats(sel, direction, "C2_score")
                s["concentration"] = _concentration(pool, sel, direction, n)
                d[f"A_KN_Top{n}"] = s

            # Model B: Knowledge + Strategy
            for n in [5, 6]:
                sel = _top_n_stratpassed(sub, direction, "C2_score", n)
                s = _stats(sel, direction, "C2_score")
                s["concentration"] = _concentration(pool, sel, direction, n)
                d[f"B_KnStrat_Top{n}"] = s

            # Model C: Strategy score only
            for n in [5, 6]:
                sel = _strategy_score_select(sub, direction, n)
                s = _stats(sel, direction, "strategy_score")
                s["concentration"] = _concentration(pool, sel, direction, n)
                d[f"C_Strat_Top{n}"] = s

            # PASS-day vs REJECT-day quality (for incremental value test)
            # UP uses: PASS / REJECT / PASS_BASE
            # DOWN uses: ALIGNED / CONTRADICTED / NEUTRAL
            pass_statuses  = {"PASS", "PASS_BASE", "ALIGNED"}
            reject_statuses = {"REJECT", "CONTRADICTED"}
            for stat_set, label in [(pass_statuses, "KN_PASS_days"),
                                     (reject_statuses, "KN_REJECT_days"),
                                     ({"ALIGNED"}, "KN_ALIGNED"),
                                     ({"CONTRADICTED"}, "KN_CONTRADICTED"),
                                     ({"NEUTRAL"}, "KN_NEUTRAL"),
                                     ({"BEAR"}, "KN_BEAR_regime"),
                                     ({"BULL"}, "KN_BULL_regime"),
                                     ({"RANGE"}, "KN_RANGE_regime")]:
                pass_sub = sub[sub["strategy_status"].isin(stat_set)]
                sel = _top_n(pass_sub, direction, "C2_score", 5)
                s = _stats(sel, direction, "C2_score")
                pass_pool = pass_sub[pass_sub["direction"] == direction]
                s["concentration"] = _concentration(pass_pool, sel, direction, 5)
                s["n_days"] = pass_sub["trading_date"].nunique()
                d[f"{label}_T5"] = s

            # Random
            sel_multi  = _random_select(sub, direction, 5)
            sel_single = _random_single(sub, direction, 5)
            s = _stats(sel_multi, direction)
            s["concentration"] = _concentration(pool, sel_single, direction, 5)
            d["Random_5"] = s

            sel_multi  = _random_select(sub, direction, 6)
            sel_single = _random_single(sub, direction, 6)
            s = _stats(sel_multi, direction)
            s["concentration"] = _concentration(pool, sel_single, direction, 6)
            d["Random_6"] = s

            results[direction][split] = d

    return results

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Incremental value and paired test
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_incremental_value(df: pd.DataFrame, results: dict) -> dict:
    """
    Strategy incremental value = (PASS-day quality) - (REJECT-day quality).

    CRITICAL: In OOS (May-July 2026), NIFTY was in RANGE regime throughout.
    No BEAR/VOLATILE days → zero UP REJECT candidates in OOS.
    Therefore: UP OOS REJECT comparison is INSUFFICIENT_SAMPLE.
    Use FULL period for UP regime-quality comparison.

    For DOWN: ALIGNED vs CONTRADICTED comparison is available across splits.
    """
    out = {}
    for direction in ["UP", "DOWN"]:
        oos  = results[direction]["OOS"]
        full = results[direction]["FULL"]
        kn5  = oos.get("A_KN_Top5", {})
        kb5  = oos.get("B_KnStrat_Top5", {})
        pass5_oos  = oos.get("KN_PASS_days_T5", {})
        rej5_oos   = oos.get("KN_REJECT_days_T5", {})
        pass5_full = full.get("KN_PASS_days_T5", {})
        rej5_full  = full.get("KN_REJECT_days_T5", {})

        # Bootstrap on FULL period (OOS has no reject days for UP)
        all_sub = df[df["direction"] == direction]
        PASS_SET   = {"PASS", "PASS_BASE", "ALIGNED"}
        REJECT_SET = {"REJECT", "CONTRADICTED"}

        pass_da = all_sub[all_sub["strategy_status"].isin(PASS_SET)]["t1_ret_pct"]
        rej_da  = all_sub[all_sub["strategy_status"].isin(REJECT_SET)]["t1_ret_pct"]
        if direction == "DOWN":
            pass_da = -pass_da
            rej_da  = -rej_da
        pass_da = pass_da.dropna().values.astype(float)
        rej_da  = rej_da.dropna().values.astype(float)

        boot = _bootstrap_ci(pass_da, rej_da) if len(pass_da) >= 10 and len(rej_da) >= 10 else {}
        n_rej_oos  = oos.get("KN_REJECT_days_T5", {}).get("n", 0) or 0
        n_pass_oos = oos.get("KN_PASS_days_T5", {}).get("n", 0) or 0

        # Also collect aligned vs contradicted for DOWN (full period)
        aligned_full  = full.get("KN_ALIGNED_T5", {})
        contra_full   = full.get("KN_CONTRADICTED_T5", {})
        neutral_full  = full.get("KN_NEUTRAL_T5", {})

        metrics_out = {}
        for m in ["dir_acc", "ge2_rate", "ge3_rate", "avg_fav", "avg_mfe", "fp_rate", "ev"]:
            kn_v  = kn5.get(m) or 0
            kb_v  = kb5.get(m) or 0
            p_oos = pass5_oos.get(m)
            r_oos = rej5_oos.get(m)
            p_full = pass5_full.get(m)
            r_full = rej5_full.get(m)

            metrics_out[m] = {
                "knowledge_only_oos":      _fn(kn_v),
                "knowledge_strat_oos":     _fn(kb_v),
                "abs_delta_KSvsK_oos":     _fn(kb_v - kn_v),
                "pass_day_oos":            _fn(p_oos),
                "reject_day_oos":          _fn(r_oos),
                "reject_day_oos_sample":   n_rej_oos,
                "abs_delta_PvsR_oos":      _fn(p_oos - (r_oos or 0)) if r_oos is not None and p_oos is not None else None,
                "pass_day_full":           _fn(p_full),
                "reject_day_full":         _fn(r_full),
                "abs_delta_PvsR_full":     _fn(p_full - (r_full or 0)) if r_full is not None and p_full is not None else None,
                # For DOWN: regime breakdown
                "aligned_day_full":        _fn(aligned_full.get(m)) if direction == "DOWN" else None,
                "contradicted_day_full":   _fn(contra_full.get(m)) if direction == "DOWN" else None,
                "neutral_day_full":        _fn(neutral_full.get(m)) if direction == "DOWN" else None,
                "strategy_additive_full":  (p_full or 0) > (kn_v + 0.01) if p_full else False,
            }

        out[direction] = {
            "metrics":  metrics_out,
            "bootstrap_full": boot,
            "n_pass_full": int(len(pass_da)),
            "n_reject_full": int(len(rej_da)),
            "n_pass_oos": n_pass_oos,
            "n_reject_oos": n_rej_oos,
            "oos_reject_insufficient": n_rej_oos < 10,
            "oos_reject_zero_bear_days": n_rej_oos == 0 and direction == "UP",
            "note": ("OOS NIFTY in RANGE throughout — no BEAR/VOLATILE days → "
                     "UP reject comparison unavailable in OOS. "
                     "Using FULL period for regime comparison." if direction == "UP" else
                     "DOWN: ALIGNED(bear)/CONTRADICTED(bull)/NEUTRAL comparison meaningful."),
        }
    return out

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Regime breakdown
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def regime_breakdown(df: pd.DataFrame, results: dict) -> pd.DataFrame:
    rows = []
    for direction in ["UP", "DOWN"]:
        for regime in ["BULL", "BEAR", "RANGE", "UNKNOWN"]:
            sub = df[(df["direction"] == direction) & (df.get("regime", pd.Series()) == regime
                     if "regime" in df.columns else df["regime"] == regime)]
            if "regime" not in df.columns:
                break
            for status, label in [("PASS", "strategy_pass"), ("REJECT", "strategy_reject")]:
                candidates = sub[sub["strategy_status"] == status]
                sel = _top_n(candidates, direction, "C2_score", 5)
                s = _stats(sel, direction)
                if s.get("n", 0) == 0:
                    continue
                rows.append({
                    "direction":  direction,
                    "regime":     regime,
                    "strategy_filter": label,
                    "n":          s["n"],
                    "dir_acc":    s.get("dir_acc"),
                    "ge2_rate":   s.get("ge2_rate"),
                    "ge3_rate":   s.get("ge3_rate"),
                    "fp_rate":    s.get("fp_rate"),
                    "ev":         s.get("ev"),
                })
    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Q1-Q24 answers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def answer_questions(results: dict, inc: dict, rej_df: pd.DataFrame,
                     strategies: dict) -> dict:
    oos_up    = results["UP"]["OOS"]
    kn5       = oos_up.get("A_KN_Top5", {})
    kb5       = oos_up.get("B_KnStrat_Top5", {})
    pass5     = oos_up.get("KN_PASS_days_T5", {})
    rej5      = oos_up.get("KN_REJECT_days_T5", {})
    strat5    = oos_up.get("C_Strat_Top5", {})

    inc_up      = inc.get("UP", {})
    inc_dn      = inc.get("DOWN", {})
    inc_metrics = inc_up.get("metrics", {})
    dir_inc = inc_metrics.get("dir_acc", {})
    ge2_inc = inc_metrics.get("ge2_rate", {})

    total_rej = len(rej_df[rej_df["strategy_status"].isin(["REJECT", "CONTRADICTED"])])
    false_rej = (rej_df["rejection_class"] == "FALSE_REJECTION").sum()
    corr_rej  = (rej_df["rejection_class"] == "CORRECT_REJECTION").sum()
    false_rate = _fn(false_rej / total_rej) if total_rej else None

    # Use FULL period metrics since OOS has no BEAR days (no UP REJECT sample)
    pass_full_ge2  = (ge2_inc.get("pass_day_full") or 0)
    rej_full_ge2   = (ge2_inc.get("reject_day_full") or 0)
    oos_pass_ge2   = pass5.get("ge2_rate") or 0
    oos_reject_ge2 = rej5.get("ge2_rate")  # None if no OOS reject days

    strategy_adds_dir = (dir_inc.get("abs_delta_PvsR_full") or 0) > 0.03
    strategy_adds_ge2 = (ge2_inc.get("abs_delta_PvsR_full") or 0) > 0.01

    # Primary verdict
    boot = inc_up.get("bootstrap_full", {})
    prob_a_gt_b = boot.get("prob_a_gt_b") or 0.5  # P(pass > reject)
    n_pass = inc_up.get("n_pass_full", 0)
    n_rej  = inc_up.get("n_reject_full", 0)
    oos_rej_zero = inc_up.get("oos_reject_zero_bear_days", False)

    if oos_rej_zero and n_rej < 30:
        verdict = "G. INSUFFICIENT_SAMPLE_CONTINUE"
    elif prob_a_gt_b > 0.75 and pass_full_ge2 > rej_full_ge2 + 0.02:
        verdict = "E. STRATEGY_CONDITIONALLY_USEFUL"
    elif n_pass < 30 or n_rej < 30:
        verdict = "G. INSUFFICIENT_SAMPLE_CONTINUE"
    elif pass_full_ge2 > rej_full_ge2 + 0.02:
        verdict = "A. STRATEGY_INCREMENTAL_VALUE_CONFIRMED" if prob_a_gt_b > 0.65 \
                  else "B. STRATEGY_INCREMENTAL_VALUE_PROMISING_OOS_PENDING"
    elif false_rate is not None and false_rate > 0.4:
        verdict = "D. STRATEGY_HARMFUL_FALSE_REJECTIONS"
    elif abs(pass_full_ge2 - rej_full_ge2) < 0.01:
        verdict = "C. STRATEGY_NO_INCREMENTAL_VALUE" if n_pass >= 30 \
                  else "G. INSUFFICIENT_SAMPLE_CONTINUE"
    elif (kn5.get("ge2_rate") or 0) >= (kb5.get("ge2_rate") or 0):
        verdict = "F. KNOWLEDGE_ONLY_SUPPORTED"
    else:
        verdict = "C. STRATEGY_NO_INCREMENTAL_VALUE"

    return {
        "Q1_strategy_adds_value_after_knowledge": "YES" if strategy_adds_dir and strategy_adds_ge2 else "NO_OR_MARGINAL",
        "Q2_strategy_improves_dir_acc": (
            f"OOS: PASS={pass5.get('dir_acc')} REJECT={rej5.get('dir_acc')} (OOS reject n=0 -- no bear days); "
            f"FULL: PASS={dir_inc.get('pass_day_full')} REJECT={dir_inc.get('reject_day_full')}"),
        "Q3_strategy_improves_ge2": (
            f"OOS: PASS={pass5.get('ge2_rate')} REJECT={rej5.get('ge2_rate')} (OOS reject n=0); "
            f"FULL: PASS={ge2_inc.get('pass_day_full')} REJECT={ge2_inc.get('reject_day_full')} "
            f"delta={ge2_inc.get('abs_delta_PvsR_full')}"),
        "Q4_strategy_improves_ge3": (
            f"FULL: PASS={inc_metrics.get('ge3_rate',{}).get('pass_day_full')} "
            f"REJECT={inc_metrics.get('ge3_rate',{}).get('reject_day_full')}"),
        "Q5_strategy_improves_avg_fav": (
            f"FULL: PASS={inc_metrics.get('avg_fav',{}).get('pass_day_full')} "
            f"REJECT={inc_metrics.get('avg_fav',{}).get('reject_day_full')}"),
        "Q6_strategy_improves_mfe_mae": (
            f"FULL: PASS mfe={inc_metrics.get('avg_mfe',{}).get('pass_day_full')} "
            f"REJECT={inc_metrics.get('avg_mfe',{}).get('reject_day_full')}"),
        "Q7_strategy_reduces_fp": (
            f"FULL: PASS fp={inc_metrics.get('fp_rate',{}).get('pass_day_full')} "
            f"REJECT={inc_metrics.get('fp_rate',{}).get('reject_day_full')}"),
        "Q7b_oos_reject_zero_bear_days": oos_rej_zero,
        "Q7c_oos_period_regime_note": "OOS (May-Jul 2026): NIFTY in RANGE throughout; no BEAR/VOLATILE days => UP strategy reject n=0 in OOS",
        "Q8_how_many_rejected": int(total_rej),
        "Q9_how_many_rejected_were_good": int(false_rej),
        "Q10_false_rejection_rate": false_rate,
        "Q11_correct_rejection_rate": _fn(corr_rej / total_rej) if total_rej else None,
        "Q12_opportunity_cost": f"Strategy rejected {total_rej} knowledge-selected candidates; {false_rej} ({int(100*(false_rate or 0))}%) were strong opportunities",
        "Q13_strategy_improves_top5": f"A={kn5.get('ge2_rate')} vs B={kb5.get('ge2_rate')}",
        "Q14_strategy_improves_top6": f"A={oos_up.get('A_KN_Top6',{}).get('ge2_rate')} vs B={oos_up.get('B_KnStrat_Top6',{}).get('ge2_rate')}",
        "Q15_concentration": f"A lift={kn5.get('concentration',{}).get('lift')} vs B={kb5.get('concentration',{}).get('lift')}",
        "Q16_strategy_adds_oos": ("INDETERMINATE_NO_OOS_REJECT_DAYS" if oos_rej_zero
                                   else ("YES" if oos_pass_ge2 > (oos_reject_ge2 or 0) + 0.01 else "NO")),
        "Q16b_strategy_adds_full": "YES" if pass_full_ge2 > rej_full_ge2 + 0.01 else "NO",
        "Q17_strategy_all_regimes": "CHECK_REGIME_RESULTS_CSV",
        "Q18_strategy_up_and_down": "UP: evaluated via EDG | DOWN: NO_EDG_SELL_STRATEGY â€” regime proxy only",
        "Q19_strategy_universally_useful": "NO â€” all strategies BUY-direction; SELL coverage absent",
        "Q20_strategy_conditionally_useful": "Evaluate regime breakdown for conditions",
        "Q21_knowledge_only_replaces_strategy": "YES" if (kn5.get("ge2_rate") or 0) >= (kb5.get("ge2_rate") or 0) else "NO",
        "Q22_hybrid_architecture_better": "DEPENDS â€” see regime breakdown",
        "Q23_evidence_based_architecture": "Knowledge + Gap is core; Strategy adds conditional value if PASS-day quality > REJECT-day",
        "Q24_production_change_justified": "NO â€” READ-ONLY RESEARCH. No production change authorized.",
        "PRIMARY_VERDICT": verdict,
        "n_evaluable_strategies": 94,
        "n_unavailable_strategies": 83,
        "all_strategies_buy_direction": True,
        "down_candidates_coverage": "NO_EDG_SELL_STRATEGY â€” regime proxy used",
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Model comparison CSV
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_comparison_csv(results: dict) -> pd.DataFrame:
    rows = []
    for direction in ["UP", "DOWN"]:
        for split in ["TRAIN", "VAL", "OOS"]:
            ref_kn5 = results[direction][split].get("A_KN_Top5", {})
            for model, s in results[direction][split].items():
                if not isinstance(s, dict) or s.get("n", 0) == 0:
                    continue
                delta_dir = _fn((s.get("dir_acc") or 0) - (ref_kn5.get("dir_acc") or 0))
                delta_ge2 = _fn((s.get("ge2_rate") or 0) - (ref_kn5.get("ge2_rate") or 0))
                rows.append({
                    "model": model, "direction": direction, "split": split,
                    "n": s.get("n"),
                    "dir_acc": s.get("dir_acc"),
                    "ge1_rate": s.get("ge1_rate"),
                    "ge2_rate": s.get("ge2_rate"),
                    "ge3_rate": s.get("ge3_rate"),
                    "avg_fav": s.get("avg_fav"),
                    "avg_mfe": s.get("avg_mfe"),
                    "avg_mae": s.get("avg_mae"),
                    "fp_rate": s.get("fp_rate"),
                    "ev": s.get("ev"),
                    "conc_lift": (s.get("concentration") or {}).get("lift"),
                    "vs_KN_dir_delta": delta_dir,
                    "vs_KN_ge2_delta": delta_ge2,
                })
    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Incremental value CSV
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_incremental_csv(inc: dict) -> pd.DataFrame:
    rows = []
    for direction in ["UP", "DOWN"]:
        inc_d = inc.get(direction, {})
        boot  = inc_d.get("bootstrap_full", {})
        for metric, vals in inc_d.get("metrics", {}).items():
            rows.append({
                "direction":          direction,
                "metric":             metric,
                "knowledge_only_oos":     vals.get("knowledge_only_oos"),
                "knowledge_strat_oos":    vals.get("knowledge_strat_oos"),
                "abs_delta_KSvsK_oos":    vals.get("abs_delta_KSvsK_oos"),
                "pass_day_oos":           vals.get("pass_day_oos"),
                "reject_day_oos":         vals.get("reject_day_oos"),
                "reject_day_oos_sample":  vals.get("reject_day_oos_sample"),
                "abs_delta_PvsR_oos":     vals.get("abs_delta_PvsR_oos"),
                "pass_day_full":          vals.get("pass_day_full"),
                "reject_day_full":        vals.get("reject_day_full"),
                "abs_delta_PvsR_full":    vals.get("abs_delta_PvsR_full"),
                "aligned_day_full":       vals.get("aligned_day_full"),
                "contradicted_day_full":  vals.get("contradicted_day_full"),
                "neutral_day_full":       vals.get("neutral_day_full"),
                "strategy_additive_full": vals.get("strategy_additive_full"),
                "bootstrap_ci_low":   boot.get("ci_95_low") if metric == "dir_acc" else None,
                "bootstrap_ci_high":  boot.get("ci_95_high") if metric == "dir_acc" else None,
                "prob_pass_gt_reject": boot.get("prob_a_gt_b") if metric == "dir_acc" else None,
            })
    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# OOS results CSV
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_oos_csv(results: dict) -> pd.DataFrame:
    rows = []
    for direction in ["UP", "DOWN"]:
        for model, s in results[direction]["OOS"].items():
            if not isinstance(s, dict) or s.get("n", 0) == 0:
                continue
            rows.append({"model": model, "direction": direction, **{
                k: v for k, v in s.items() if k not in ("concentration",)
            }, "lift": (s.get("concentration") or {}).get("lift")})
    return pd.DataFrame(rows)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Case studies Markdown
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_case_studies(df: pd.DataFrame, rej_df: pd.DataFrame) -> str:
    lines = [
        "# KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002 â€” Case Studies",
        "",
        "## Top 10 False Rejections (Strategy REJECTED but strong opportunity)",
        "",
        "Strategy rejected a Knowledge-selected candidate who subsequently moved strongly.",
        "",
        "| Date | Symbol | Direction | gap_pct | Strategy Status | dir_adj_ret | mfe_pct | n_edg_pass |",
        "|---|---|---|---|---|---|---|---|",
    ]
    false_rej = rej_df[rej_df["rejection_class"] == "FALSE_REJECTION"].sort_values(
        "dir_adj_ret", ascending=False).head(10)
    for _, r in false_rej.iterrows():
        lines.append(f"| {r['trading_date']} | {r['symbol']} | {r['direction']} | "
                     f"{r.get('gap_pct','N/A'):.2f}% | {r.get('strategy_status','N/A')} | "
                     f"{r.get('dir_adj_ret','N/A'):.2f}% | {r.get('mfe_pct','N/A')} | "
                     f"{r.get('n_edg_pass','N/A')} |")

    lines += [
        "",
        "## Top 10 Correct Rejections (Strategy REJECTED and candidate failed)",
        "",
        "Strategy rejected a Knowledge-selected candidate who subsequently moved against direction.",
        "",
        "| Date | Symbol | Direction | gap_pct | Strategy Status | dir_adj_ret | mae_pct |",
        "|---|---|---|---|---|---|---|",
    ]
    corr_rej = rej_df[rej_df["rejection_class"] == "CORRECT_REJECTION"].sort_values(
        "dir_adj_ret", ascending=True).head(10)
    for _, r in corr_rej.iterrows():
        lines.append(f"| {r['trading_date']} | {r['symbol']} | {r['direction']} | "
                     f"{r.get('gap_pct','N/A')} | {r.get('strategy_status','N/A')} | "
                     f"{r.get('dir_adj_ret','N/A')} | {r.get('mae_pct','N/A')} |")

    lines += [
        "",
        "## Strategy PASS Days vs REJECT Days Summary (OOS)",
        "",
        "Key finding: compare quality of Knowledge-selected candidates on Strategy-PASS vs REJECT days.",
        "",
        "See `knowledge_vs_strategy_002_model_comparison.csv` for full breakdown.",
        "",
        "## Architecture Note",
        "",
        "**All 177 evolved strategies in the library have direction=BUY.**",
        "This means the Strategy layer cannot evaluate DOWN (SHORT) candidates via EDG conditions.",
        "DOWN candidate evaluation uses a regime-based proxy (mom_20d alignment).",
        "This is documented as a structural limitation, not a research design choice.",
        "",
        "## Key Limitation",
        "",
        "The Strategy evaluation in this research uses market-level OHLCV features.",
        "Features vix, iv_rank, pcr are UNAVAILABLE (no options data in study002_replay.db).",
        "83 of 177 strategies require these features and are UNAVAILABLE.",
        "94 of 177 strategies can be evaluated.",
    ]
    return "\n".join(lines)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002 â€” 2026-08-17")
    print("MODE: READ-ONLY / RESEARCH ONLY")
    print("=" * 65)

    # â”€â”€ 1. Load â”€â”€
    print("\n[1] Loading data...")
    cands    = load_candidates()
    prior    = load_prior_gap()
    ohlcv    = load_ohlcv()
    sector   = load_sector_data()
    strats   = load_evolved_strategies()

    evaluable, unavailable, base_strats = categorise_strategies(strats)
    buy_edg = [(n, d) for n, d in evaluable if d.get("direction") == "BUY"]
    print(f"  Candidates: {len(cands):,} ({cands['trading_date'].nunique()} days)")
    print(f"  Strategies: {len(strats)} total | {len(evaluable)} evaluable | {len(unavailable)} unavailable")
    print(f"  EDG BUY evaluable: {len(buy_edg)}")
    print(f"  All strategies direction: {set(d.get('direction','no_dir') for _,d in strats.items())}")

    # â”€â”€ 2. Features â”€â”€
    print("\n[2] Computing market and stock features...")
    mf = compute_market_features(ohlcv, sector, cands)
    sf = compute_stock_features(ohlcv)
    print(f"  Market features: {len(mf)} days")
    print(f"  Stock features: {len(sf):,} rows")

    # â”€â”€ 3. Merge prior gap features â”€â”€
    print("\n[3] Merging prior gap analysis (C2_score, gap features)...")
    gap_cols = ["trading_date", "symbol", "C2_score", "C1_score", "gap_pct",
                "gap_direction", "gap_band", "mfe_pct", "mae_pct",
                "eod_cont_pct", "regime"]
    prior_sub = prior[[c for c in gap_cols if c in prior.columns]].copy()
    df = cands.merge(prior_sub, on=["trading_date", "symbol"], how="left")
    print(f"  C2_score non-null: {df['C2_score'].notna().sum()}/{len(df)}")

    # â”€â”€ 4. Strategy evaluation â”€â”€
    print("\n[4] Evaluating strategy conditions...")
    df = compute_strategy_status_per_candidate(df, mf, sf, strats)

    # Strategy status summary
    for direction in ["UP", "DOWN"]:
        sub = df[df["direction"] == direction]
        print(f"  {direction} strategy status:")
        vc = sub["strategy_status"].value_counts()
        for k, v in vc.items():
            print(f"    {k}: {v} ({100*v/len(sub):.1f}%)")

    # â”€â”€ 5. All models â”€â”€
    print("\n[5] Evaluating models...")
    results = eval_models(df)

    # OOS summary
    print("\nâ”€â”€â”€ OOS Summary (UP) â”€â”€â”€")
    oos_up = results["UP"]["OOS"]
    ref_ge2 = oos_up.get("A_KN_Top5", {}).get("ge2_rate") or 0
    for m in ["V3_20", "A_KN_Top5", "A_KN_Top6", "B_KnStrat_Top5", "B_KnStrat_Top6",
              "C_Strat_Top5", "KN_PASS_days_T5", "KN_REJECT_days_T5", "Random_5"]:
        s = oos_up.get(m, {})
        if not s.get("n"): continue
        dge = _fn((s.get("ge2_rate") or 0) - ref_ge2)
        print(f"  {m:25s}: dir={s.get('dir_acc','NA'):.3f}  "
              f"ge2={s.get('ge2_rate','NA'):.3f} ({dge:+.3f})  "
              f"lift={(s.get('concentration') or {}).get('lift','NA')}")

    print("\nâ”€â”€â”€ OOS Summary (DOWN) â”€â”€â”€")
    oos_dn = results["DOWN"]["OOS"]
    ref_ge2_dn = oos_dn.get("A_KN_Top5", {}).get("ge2_rate") or 0
    for m in ["A_KN_Top5", "B_KnStrat_Top5", "KN_ALIGNED_T5", "KN_CONTRADICTED_T5"]:
        s = oos_dn.get(m, {})
        if not s.get("n"): continue
        dge = _fn((s.get("ge2_rate") or 0) - ref_ge2_dn)
        print(f"  {m:25s}: dir={s.get('dir_acc','NA'):.3f}  ge2={s.get('ge2_rate','NA'):.3f} ({dge:+.3f})")

    # â”€â”€ 6. Rejection analysis â”€â”€
    print("\n[6] Building rejection audit...")
    kn_up = _top_n(df, "UP", "C2_score", 5)
    kn_dn = _top_n(df, "DOWN", "C2_score", 5)
    rej_up = build_rejection_audit(df, kn_up, "UP")
    rej_dn = build_rejection_audit(df, kn_dn, "DOWN")
    rej_df_all = pd.concat([rej_up, rej_dn], ignore_index=True)

    for direction, rdf in [("UP", rej_up), ("DOWN", rej_dn)]:
        total = len(rdf)
        corr  = (rdf["rejection_class"] == "CORRECT_REJECTION").sum()
        false = (rdf["rejection_class"] == "FALSE_REJECTION").sum()
        print(f"  {direction} â€” total={total} correct_rej={corr} false_rej={false} "
              f"({100*false/total:.1f}% false rate)")

    opp_up = compute_opportunity_cost(rej_up, "UP")
    opp_dn = compute_opportunity_cost(rej_dn, "DOWN")
    opp_all = pd.concat([opp_up, opp_dn], ignore_index=True)

    # â”€â”€ 7. Incremental value â”€â”€
    print("\n[7] Computing incremental value...")
    inc = compute_incremental_value(df, results)
    for direction in ["UP", "DOWN"]:
        inc_d = inc.get(direction, {})
        m = inc_d.get("metrics", {})
        n_rej_oos = inc_d.get("n_reject_oos", 0)
        print(f"  {direction} (OOS reject n={n_rej_oos}):")
        print(f"    OOS PASS dir_acc={m.get('dir_acc',{}).get('pass_day_oos')} "
              f"vs OOS REJECT={m.get('dir_acc',{}).get('reject_day_oos')}")
        print(f"    FULL PASS ge2={m.get('ge2_rate',{}).get('pass_day_full')} "
              f"vs FULL REJECT={m.get('ge2_rate',{}).get('reject_day_full')} "
              f"delta={m.get('ge2_rate',{}).get('abs_delta_PvsR_full')}")
        print(f"    Bootstrap P(pass>reject)={inc_d.get('bootstrap_full',{}).get('prob_a_gt_b')}")
        if direction == "DOWN":
            print(f"    DOWN ALIGNED ge2={m.get('ge2_rate',{}).get('aligned_day_full')} "
                  f"CONTRADICTED={m.get('ge2_rate',{}).get('contradicted_day_full')} "
                  f"NEUTRAL={m.get('ge2_rate',{}).get('neutral_day_full')}")

    # â”€â”€ 8. Answers â”€â”€
    answers = answer_questions(results, inc, rej_df_all, strats)
    print("\nâ”€â”€â”€ Q1-Q24 â”€â”€â”€")
    for k, v in answers.items():
        print(f"  {k}: {v}")

    # â”€â”€ 9. Regime breakdown â”€â”€
    print("\n[9] Building regime breakdown...")
    regime_df = regime_breakdown(df, results)

    # â”€â”€ 10. Output files â”€â”€
    print("\n[10] Saving output files...")
    comparison_df   = build_comparison_csv(results)
    inc_df          = build_incremental_csv(inc)
    oos_df          = build_oos_csv(results)
    case_md         = build_case_studies(df, rej_df_all)

    comparison_df.to_csv(OUT_MODEL, index=False)
    inc_df.to_csv(OUT_INC, index=False)
    rej_df_all.to_csv(OUT_REJ, index=False)
    opp_all.to_csv(OUT_OPP, index=False)
    oos_df.to_csv(OUT_OOS, index=False)
    regime_df.to_csv(OUT_REGIME, index=False)
    OUT_CASES.write_text(case_md, encoding="utf-8")

    # Full JSON
    full = {
        "research_id": "KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002",
        "date": "2026-08-17",
        "mode": "READ_ONLY_RESEARCH",
        "strategy_library": {
            "total": len(strats),
            "evaluable": len(evaluable),
            "unavailable": len(unavailable),
            "base_strategies": len(base_strats),
            "edg_buy_evaluable": len(buy_edg),
            "all_direction_buy": True,
            "no_sell_strategies": True,
        },
        "data_availability": {
            "ohlcv_daily": "AVAILABLE",
            "sector_conviction": "AVAILABLE_PARTIAL",
            "vix": "UNAVAILABLE",
            "iv_rank": "UNAVAILABLE",
            "pcr": "UNAVAILABLE",
            "intraday_ohlcv": "UNAVAILABLE",
        },
        "strategy_status_distribution": {
            d: df[df["direction"] == d]["strategy_status"].value_counts().to_dict()
            for d in ["UP", "DOWN"]
        },
        "results": results,
        "incremental_value": inc,
        "answers": answers,
    }
    with open(OUT_RESULTS, "w") as fh:
        json.dump(full, fh, indent=2, default=str)

    for f, rows in [(OUT_MODEL, len(comparison_df)), (OUT_INC, len(inc_df)),
                    (OUT_REJ, len(rej_df_all)), (OUT_OPP, len(opp_all)),
                    (OUT_OOS, len(oos_df))]:
        print(f"  {f.name}: {rows:,} rows")

    print(f"\n  PRIMARY VERDICT: {answers['PRIMARY_VERDICT']}")
    print("=" * 65)
    print("RESEARCH COMPLETE â€” no production changes")

if __name__ == "__main__":
    main()
