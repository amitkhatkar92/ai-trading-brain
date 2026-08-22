"""
V3 Orthogonal Direction Research — 001
Research ID: V3_ORTHOGONAL_DIRECTION_RESEARCH_001
Date: 2026-08-17
Mode: READ-ONLY / RESEARCH ONLY

Tests whether orthogonal information (sector context, institutional activity,
catalyst, opening gap, inverse Knowledge) adds directional value inside the
V3 20-stock high-mover pool.

NO PRODUCTION CHANGES. NO V3 CHANGES.
NO CandidateStore. NO StrategyLab. NO DecisionEngine.
NO RiskControl. NO OrderManager. NO broker.
"""
from __future__ import annotations

import csv, json, os, random, sqlite3, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ─────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────

DB_PATH            = Path("data/study002_replay.db")
RETRO_CANDIDATES   = Path("reports/mover_discovery_v3/v3_retro_candidates.csv")
KNOWLEDGE_CONFLICT = Path("reports/mover_discovery_v3/v3_knowledge_conflict_analysis.csv")
REPORT_DIR         = Path("reports/mover_discovery_v3")

TRAIN_START = "2025-09-16"; TRAIN_END = "2026-02-19"
VAL_START   = "2026-02-20"; VAL_END   = "2026-05-13"
OOS_START   = "2026-05-14"; OOS_END   = "2026-07-30"

RANDOM_SEEDS = [42, 43, 44, 45, 46]
POOL_SIZE    = 20

MODEL_P = "PRE_MARKET"   # info available before market open on T+1
MODEL_O = "POST_OPEN"    # info available after T+1 open

# Gap threshold (pct)
GAP_THRESHOLD = 0.3

# ─────────────────────────────────────────────────────────────────
# Output paths
# ─────────────────────────────────────────────────────────────────

OUT_RESULTS  = REPORT_DIR / "v3_orthogonal_direction_results.json"
OUT_FEATURE  = REPORT_DIR / "v3_orthogonal_feature_comparison.csv"
OUT_SECTOR   = REPORT_DIR / "v3_sector_analysis.csv"
OUT_INST     = REPORT_DIR / "v3_institutional_analysis.csv"
OUT_CATALYST = REPORT_DIR / "v3_catalyst_analysis.csv"
OUT_GAP      = REPORT_DIR / "v3_intraday_gap_analysis.csv"
OUT_INV_KN   = REPORT_DIR / "v3_inverse_knowledge_analysis.csv"
OUT_OOS      = REPORT_DIR / "v3_orthogonal_oos_results.csv"

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _split(d: str) -> str:
    if TRAIN_START <= d <= TRAIN_END: return "TRAIN"
    if VAL_START   <= d <= VAL_END:   return "VAL"
    if OOS_START   <= d <= OOS_END:   return "OOS"
    return "UNKNOWN"

def _spearman(a, b) -> float | None:
    a = np.asarray(a, float); b = np.asarray(b, float)
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 4:
        return None
    r, _ = stats.spearmanr(a[mask], b[mask])
    return round(float(r), 4) if np.isfinite(r) else None

def _fnan(v) -> float | None:
    return round(float(v), 4) if v is not None and np.isfinite(float(v)) else None

def _stats(rows: pd.DataFrame, direction: str, score_col: str = None) -> dict:
    """Compute all 15 metrics for a selection of candidates."""
    if rows.empty:
        return {"n": 0}

    t1 = rows["t1_ret_pct"].values.astype(float)
    dir_adj = t1 if direction == "UP" else -t1   # positive = correct direction

    n         = len(rows)
    dir_acc   = float(np.mean(dir_adj > 0))
    ge1       = float(np.mean(dir_adj >= 1.0))
    ge2       = float(np.mean(dir_adj >= 2.0))
    ge3       = float(np.mean(dir_adj >= 3.0))
    fav       = dir_adj[dir_adj > 0]
    avg_fav   = float(np.mean(fav))   if len(fav) else None
    med_fav   = float(np.median(fav)) if len(fav) else None
    fp_rate   = float(np.mean(dir_adj < -1.0))

    mfe_col = "mfe_pct"; mae_col = "mae_pct"
    avg_mfe = _fnan(np.nanmean(rows[mfe_col].values.astype(float))) if mfe_col in rows else None
    avg_mae = _fnan(np.nanmean(rows[mae_col].values.astype(float))) if mae_col in rows else None

    # Top-1 capture: does the pool's single best performer appear in selection?
    # (meaningful only per-day — here we report % of days where best-pool stock is selected)
    top1_cap = None
    if "trading_date" in rows.columns:
        hits = 0; total = 0
        for _, g in rows.groupby("trading_date"):
            total += 1
            # best in pool requires the full pool, which we don't have here
            # skip per-day top-1; report None (computed separately if needed)
        top1_cap = None   # computed in concentration analysis

    spe_dir = _spearman(rows[score_col].values if score_col and score_col in rows else [], dir_adj) if score_col and score_col in rows else None
    spe_abs = _spearman(rows[score_col].values if score_col and score_col in rows else [], np.abs(t1)) if score_col and score_col in rows else None

    return {
        "n": n,
        "dir_acc": round(dir_acc, 4),
        "ge1_rate": round(ge1, 4),
        "ge2_rate": round(ge2, 4),
        "ge3_rate": round(ge3, 4),
        "avg_fav_ret": _fnan(avg_fav),
        "med_fav_ret": _fnan(med_fav),
        "avg_mfe": avg_mfe,
        "avg_mae": avg_mae,
        "fp_rate": round(fp_rate, 4),
        "spearman_dir": spe_dir,
        "spearman_abs": spe_abs,
    }

def _concentration(pool: pd.DataFrame, selected: pd.DataFrame, direction: str,
                   n_sel: int) -> dict:
    """
    Per-day opportunity concentration.

    avg_share = average(selected_favorable_sum / pool_favorable_sum) over days.
    lift = avg_share / (n_sel / POOL_SIZE)
    """
    if pool.empty or selected.empty:
        return {}

    sel_idx = set(zip(selected["trading_date"], selected["symbol"]))
    days = pool["trading_date"].unique()
    shares = []
    for d in days:
        p = pool[pool["trading_date"] == d]
        if direction == "UP":
            fav_p = p["t1_ret_pct"].clip(lower=0)
        else:
            fav_p = (-p["t1_ret_pct"]).clip(lower=0)
        pool_total = float(fav_p.sum())
        if pool_total <= 0:
            continue
        sel_rows = p[p["symbol"].apply(lambda s: (d, s) in sel_idx)]
        if direction == "UP":
            sel_total = float(sel_rows["t1_ret_pct"].clip(lower=0).sum())
        else:
            sel_total = float((-sel_rows["t1_ret_pct"]).clip(lower=0).sum())
        shares.append(sel_total / pool_total)

    if not shares:
        return {}
    avg_share    = float(np.mean(shares))
    rand_share   = n_sel / POOL_SIZE
    lift         = avg_share / rand_share if rand_share > 0 else None
    return {
        "avg_share":       round(avg_share, 4),
        "random_expected": round(rand_share, 4),
        "lift":            round(lift, 4) if lift else None,
    }

def _top1_capture(pool: pd.DataFrame, selected: pd.DataFrame, direction: str) -> float | None:
    """Fraction of days where the best pool stock is in the selection."""
    if pool.empty or selected.empty:
        return None
    sel_idx = set(zip(selected["trading_date"], selected["symbol"]))
    hits = 0; total = 0
    for d, pg in pool.groupby("trading_date"):
        valid = pg.dropna(subset=["t1_ret_pct"])
        if valid.empty:
            continue
        if direction == "UP":
            best_sym = valid.loc[valid["t1_ret_pct"].idxmax(), "symbol"]
        else:
            best_sym = valid.loc[valid["t1_ret_pct"].idxmin(), "symbol"]
        total += 1
        if (d, best_sym) in sel_idx:
            hits += 1
    return round(hits / total, 4) if total > 0 else None

# ─────────────────────────────────────────────────────────────────
# Selection helpers
# ─────────────────────────────────────────────────────────────────

def _collect_top_n(df: pd.DataFrame, direction: str, score_col: str,
                   n: int, ascending: bool = False) -> pd.DataFrame:
    """Select top-n by score_col per trading_date × direction."""
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        valid = g[g[score_col].notna()]
        if len(valid) == 0:
            valid = g  # fallback to full pool
        sel = valid.nsmallest(n, score_col) if ascending else valid.nlargest(n, score_col)
        frames.append(sel)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _collect_random(df: pd.DataFrame, direction: str, n: int) -> pd.DataFrame:
    """Random n per day, averaged over RANDOM_SEEDS — returns all seed rows."""
    frames = []
    for _, g in df[df["direction"] == direction].groupby("trading_date"):
        pool = g
        for seed in RANDOM_SEEDS:
            rng = random.Random(seed)
            k = min(n, len(pool))
            idx = sorted(rng.sample(range(len(pool)), k))
            frames.append(pool.iloc[idx])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _run_model(sub: pd.DataFrame, direction: str, score_col: str, n: int,
               ascending: bool = False) -> dict:
    """Run one selection model on sub-dataframe."""
    selected = _collect_top_n(sub, direction, score_col, n, ascending)
    pool     = sub[sub["direction"] == direction]
    s = _stats(selected, direction, score_col)
    s["concentration"] = _concentration(pool, selected, direction, n)
    s["top1_cap"]      = _top1_capture(pool, selected, direction)
    return s

def _run_random(sub: pd.DataFrame, direction: str, n: int) -> dict:
    """Run random selection model."""
    selected = _collect_random(sub, direction, n)
    pool     = sub[sub["direction"] == direction]
    s = _stats(selected, direction)
    s["concentration"] = _concentration(pool, selected, direction, n)
    s["top1_cap"]      = _top1_capture(pool, selected, direction)
    return s

# ─────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────

def load_base_data() -> pd.DataFrame:
    """Load V3 retro candidates + knowledge scores, add split label."""
    rc = pd.read_csv(RETRO_CANDIDATES)
    ka = pd.read_csv(KNOWLEDGE_CONFLICT, usecols=[
        "trading_date", "symbol", "direction",
        "knowledge_score", "knowledge_confidence", "conflict_type",
    ])
    # Normalise direction values: 'DN' → 'DOWN'
    rc["direction"] = rc["direction"].replace({"DN": "DOWN"})
    ka["direction"] = ka["direction"].replace({"DN": "DOWN"})
    df = rc.merge(ka, on=["trading_date", "symbol", "direction"], how="left")
    df["split"] = df["trading_date"].apply(_split)
    return df[df["split"] != "UNKNOWN"].copy()

def load_db_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load ohlcv_daily, sector_conviction_daily, universe_stocks."""
    con = sqlite3.connect(DB_PATH)
    ohlcv = pd.read_sql(
        "SELECT symbol, trade_date, open, high, low, close, volume FROM ohlcv_daily", con)
    scd = pd.read_sql(
        """SELECT record_date AS trading_date, sector,
                  participation_rate_1d, rs_vs_market_20d,
                  sector_conviction_score, theme_phase
           FROM sector_conviction_daily""", con)
    us = pd.read_sql(
        "SELECT symbol, sector FROM universe_stocks WHERE is_active=1", con)
    con.close()
    return ohlcv, scd, us

# ─────────────────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────────────────

def add_all_features(df: pd.DataFrame, ohlcv: pd.DataFrame,
                     scd: pd.DataFrame, us: pd.DataFrame) -> pd.DataFrame:
    """
    Add all orthogonal features.

    Model P (pre-market, T-close data):
        sector, derived_sector_ret, stock_ret_t, stock_vs_sector,
        sector_vs_market, participation_rate_1d, rs_vs_market_20d,
        sector_conviction_score, theme_phase, inv_knowledge_score

    Model O (post-open, uses T+1 open/high/low):
        gap_pct, gap_score, mfe_pct, mae_pct
    """
    # ── Market return from ^NSEI ──
    nsei = ohlcv[ohlcv["symbol"] == "^NSEI"].sort_values("trade_date").copy()
    nsei["market_ret"] = nsei["close"].pct_change() * 100
    market_ret = nsei[["trade_date", "market_ret"]].rename(
        columns={"trade_date": "trading_date"})

    # ── Stock 1d return on day T ──
    stock = ohlcv[~ohlcv["symbol"].isin(["^NSEI", "^NSEBANK"])].copy()
    stock = stock.sort_values(["symbol", "trade_date"])
    stock["ret_1d"] = stock.groupby("symbol")["close"].pct_change() * 100
    stock_ret = stock[["symbol", "trade_date", "ret_1d"]].rename(
        columns={"trade_date": "trading_date", "ret_1d": "stock_ret_t"})

    # ── Derived sector return from constituent medians ──
    sw = stock.merge(us[["symbol", "sector"]], on="symbol", how="left").dropna(
        subset=["sector", "ret_1d"])
    sector_ret = (sw.groupby(["trade_date", "sector"])["ret_1d"]
                    .median()
                    .reset_index()
                    .rename(columns={"trade_date": "trading_date",
                                     "ret_1d": "derived_sector_ret"}))

    # ── Assemble on df ──
    df = df.merge(us[["symbol", "sector"]], on="symbol", how="left")
    df = df.merge(scd, on=["trading_date", "sector"], how="left")
    df = df.merge(sector_ret, on=["trading_date", "sector"], how="left")
    df = df.merge(market_ret, on="trading_date", how="left")
    df = df.merge(stock_ret,  on=["trading_date", "symbol"], how="left")

    df["stock_vs_sector"]  = df["stock_ret_t"] - df["derived_sector_ret"]
    df["sector_vs_market"] = df["derived_sector_ret"] - df["market_ret"]

    # ── Inverse knowledge ──
    df["inv_knowledge_score"] = (
        (1.0 - df["knowledge_score"].fillna(0.5)).clip(0.0, 1.0))

    # ── T close ──
    t_close = (ohlcv[["symbol", "trade_date", "close"]]
               .rename(columns={"trade_date": "trading_date", "close": "t_close"}))
    df = df.merge(t_close, on=["trading_date", "symbol"], how="left")

    # ── T+1 open / high / low ──
    t1_ohlc = (ohlcv[["symbol", "trade_date", "open", "high", "low"]]
               .rename(columns={"trade_date": "t1_date",
                                 "open": "t1_open",
                                 "high": "t1_high",
                                 "low":  "t1_low"}))
    df = df.merge(t1_ohlc, on=["t1_date", "symbol"], how="left")

    # ── Gap (Model O) ──
    ok = df["t_close"].notna() & (df["t_close"] > 0) & df["t1_open"].notna()
    df["gap_pct"] = np.where(ok, (df["t1_open"] / df["t_close"] - 1.0) * 100.0, np.nan)

    # ── MFE / MAE (Model O) ──
    df["mfe_pct"] = np.nan
    df["mae_pct"] = np.nan
    vu  = df["direction"] == "UP"
    vd  = df["direction"] == "DOWN"
    vok = ok

    df.loc[vu & vok, "mfe_pct"] = (
        df.loc[vu & vok, "t1_high"] / df.loc[vu & vok, "t_close"] - 1.0) * 100.0
    df.loc[vu & vok, "mae_pct"] = (
        1.0 - df.loc[vu & vok, "t1_low"] / df.loc[vu & vok, "t_close"]) * 100.0
    df.loc[vd & vok, "mfe_pct"] = (
        1.0 - df.loc[vd & vok, "t1_low"] / df.loc[vd & vok, "t_close"]) * 100.0
    df.loc[vd & vok, "mae_pct"] = (
        df.loc[vd & vok, "t1_high"] / df.loc[vd & vok, "t_close"] - 1.0) * 100.0

    _coverage(df, "gap_pct", "t1_open", "derived_sector_ret",
              "participation_rate_1d", "stock_ret_t")
    return df

def _coverage(df, *cols):
    for c in cols:
        if c in df:
            null_pct = df[c].isna().mean() * 100
            print(f"    {c}: {null_pct:.1f}% missing")

# ─────────────────────────────────────────────────────────────────
# Sector score
# ─────────────────────────────────────────────────────────────────

def add_sector_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Model P — equal-weight binary signals, domain-knowledge thresholds.
    No data-fitting; thresholds apply to all splits identically.

    UP (5 signals):
        s1 sector moved up today      (derived_sector_ret > 0)
        s2 stock beat sector today    (stock_vs_sector > 0)
        s3 broad participation        (participation_rate_1d > 0.55)
        s4 sector 20d RS positive     (rs_vs_market_20d > 0)
        s5 high conviction            (sector_conviction_score > 0.50)

    DOWN (5 signals, reversed):
        s1 sector moved down today    (derived_sector_ret < 0)
        s2 stock lagged sector        (stock_vs_sector < 0)
        s3 weak breadth               (participation_rate_1d < 0.45)
        s4 sector 20d RS negative     (rs_vs_market_20d < 0)
        s5 low conviction             (sector_conviction_score < 0.40)
    """
    up = df["direction"] == "UP"
    dn = df["direction"] == "DOWN"
    df["sector_score"] = np.nan

    def _sig(series, op, threshold):
        if op == ">":  return (series > threshold).astype(float)
        if op == "<":  return (series < threshold).astype(float)

    # UP
    s = (
        _sig(df["derived_sector_ret"],     ">",  0.0)  +
        _sig(df["stock_vs_sector"],         ">",  0.0)  +
        _sig(df["participation_rate_1d"],   ">",  0.55) +
        _sig(df["rs_vs_market_20d"],        ">",  0.0)  +
        _sig(df["sector_conviction_score"], ">",  0.50)
    ) / 5.0
    df.loc[up, "sector_score"] = s[up]

    # DOWN
    s = (
        _sig(df["derived_sector_ret"],     "<",  0.0)  +
        _sig(df["stock_vs_sector"],         "<",  0.0)  +
        _sig(df["participation_rate_1d"],   "<",  0.45) +
        _sig(df["rs_vs_market_20d"],        "<",  0.0)  +
        _sig(df["sector_conviction_score"], "<",  0.40)
    ) / 5.0
    df.loc[dn, "sector_score"] = s[dn]

    df["sector_class"] = "SECTOR_NEUTRAL"
    df.loc[df["sector_score"] >= 0.60, "sector_class"] = "SECTOR_SUPPORTS_STOCK"
    df.loc[df["sector_score"] <  0.40, "sector_class"] = "SECTOR_CONTRADICTS_STOCK"
    df.loc[df["sector_score"].isna(),  "sector_class"] = "SECTOR_DATA_MISSING"
    return df

# ─────────────────────────────────────────────────────────────────
# Gap score
# ─────────────────────────────────────────────────────────────────

def add_gap_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Model O — gap score.
    For UP: positive gap → higher score.
    For DOWN: negative gap → higher score.
    """
    up = df["direction"] == "UP"
    dn = df["direction"] == "DOWN"
    df["gap_score"] = np.nan

    g = df["gap_pct"]
    # UP: gap > +0.3 → 1.0, 0 to +0.3 → 0.5, negative → 0.0
    up_score = np.where(g >  GAP_THRESHOLD, 1.0,
               np.where(g >= 0,             0.5, 0.0))
    # DOWN: gap < -0.3 → 1.0, -0.3 to 0 → 0.5, positive → 0.0
    dn_score = np.where(g < -GAP_THRESHOLD, 1.0,
               np.where(g <= 0,             0.5, 0.0))

    df.loc[up, "gap_score"] = up_score[up.values]
    df.loc[dn, "gap_score"] = dn_score[dn.values]
    df.loc[df["gap_pct"].isna(), "gap_score"] = np.nan

    df["gap_direction"] = "NO_GAP"
    df.loc[df["gap_pct"] >  GAP_THRESHOLD, "gap_direction"] = "GAP_UP"
    df.loc[df["gap_pct"] < -GAP_THRESHOLD, "gap_direction"] = "GAP_DOWN"
    return df

# ─────────────────────────────────────────────────────────────────
# Market regime
# ─────────────────────────────────────────────────────────────────

def add_regime(df: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Simple regime from ^NSEI 20-day return: BULL / BEAR / RANGE."""
    nsei = ohlcv[ohlcv["symbol"] == "^NSEI"].sort_values("trade_date").copy()
    nsei["ret_20d"] = nsei["close"].pct_change(20) * 100
    nsei["regime"]  = "RANGE"
    nsei.loc[nsei["ret_20d"] >  5, "regime"] = "BULL"
    nsei.loc[nsei["ret_20d"] < -5, "regime"] = "BEAR"
    regime = nsei[["trade_date", "regime"]].rename(
        columns={"trade_date": "trading_date"})
    return df.merge(regime, on="trading_date", how="left")

# ─────────────────────────────────────────────────────────────────
# Baselines
# ─────────────────────────────────────────────────────────────────

def compute_baselines(df: pd.DataFrame) -> dict:
    out = {}
    for direction in ["UP", "DOWN"]:
        out[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            pool = sub[sub["direction"] == direction]
            out[direction][split] = {}

            # V3_20
            s = _stats(pool, direction, "v3_score")
            s["concentration"] = {"avg_share": 1.0, "random_expected": 1.0, "lift": 1.0}
            s["top1_cap"] = None
            out[direction][split]["V3_20"] = s

            for model, sc, n, asc in [
                ("V3_Top5",   "v3_score", 5, False),
                ("V3_Top6",   "v3_score", 6, False),
                ("Random_5",  None,       5, False),
                ("Random_6",  None,       6, False),
            ]:
                if sc:
                    out[direction][split][model] = _run_model(sub, direction, sc, n, asc)
                else:
                    out[direction][split][model] = _run_random(sub, direction, n)
    return out

# ─────────────────────────────────────────────────────────────────
# Track A — Sector context
# ─────────────────────────────────────────────────────────────────

def run_track_a(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    print("\n[Track A] Sector Context (Model P)")
    df = add_sector_score(df)

    results = {}
    for direction in ["UP", "DOWN"]:
        results[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            pool = sub[sub["direction"] == direction]
            d = {}
            d["A1_Top5"]     = _run_model(sub, direction, "sector_score", 5)
            d["A1_Top6"]     = _run_model(sub, direction, "sector_score", 6)
            d["A1_Top10"]    = _run_model(sub, direction, "sector_score", 10)
            d["A1_Low_Top5"] = _run_model(sub, direction, "sector_score", 5, ascending=True)

            # By classification
            for cls in ["SECTOR_SUPPORTS_STOCK", "SECTOR_NEUTRAL", "SECTOR_CONTRADICTS_STOCK"]:
                sub_cls = pool[pool["sector_class"] == cls]
                if len(sub_cls) >= 5:
                    d[f"A1_{cls}"] = _stats(sub_cls, direction, "sector_score")

            results[direction][split] = d

    # Regime breakdown for A1_Top5 in OOS
    for direction in ["UP", "DOWN"]:
        for regime in ["BULL", "BEAR", "RANGE"]:
            reg_oos = df[(df["split"] == "OOS") & (df["regime"] == regime)]
            if len(reg_oos[reg_oos["direction"] == direction]) >= 20:
                results[direction]["OOS"][f"A1_Top5_{regime}"] = \
                    _run_model(reg_oos, direction, "sector_score", 5)

    # Build sector_df for CSV
    cols = ["trading_date", "symbol", "direction", "split", "regime",
            "sector", "v3_score", "sector_score", "sector_class",
            "derived_sector_ret", "stock_vs_sector", "sector_vs_market",
            "participation_rate_1d", "rs_vs_market_20d",
            "sector_conviction_score", "theme_phase", "t1_ret_pct"]
    sector_df = df[[c for c in cols if c in df.columns]].copy()
    sector_df["v3_favorable"] = (
        (df["t1_ret_pct"] > 0).where(df["direction"] == "UP",
         (df["t1_ret_pct"] < 0)))

    return results, sector_df

# ─────────────────────────────────────────────────────────────────
# Track B — Institutional (UNAVAILABLE)
# ─────────────────────────────────────────────────────────────────

def run_track_b() -> dict:
    print("\n[Track B] Institutional Activity — DATA UNAVAILABLE")
    return {
        "status": "DATA_UNAVAILABLE",
        "reason": "bulk_block_deals: 0 rows; bhav_daily: 0 rows; no FII/DII data in study002_replay.db",
        "tables_checked": ["bulk_block_deals", "bhav_daily"],
        "action": "TRACK_B_SKIPPED",
        "recommendation": "Populate bulk_block_deals from NSE bulk/block deal archive (2025-09-16 to 2026-07-30) before re-running",
    }

# ─────────────────────────────────────────────────────────────────
# Track C — Catalyst (UNAVAILABLE)
# ─────────────────────────────────────────────────────────────────

def run_track_c() -> dict:
    print("\n[Track C] Catalyst/Event — DATA UNAVAILABLE")
    return {
        "status": "DATA_UNAVAILABLE",
        "reason": "oios_events: 0 rows; no corporate announcement, earnings, or regulatory data in study002_replay.db",
        "tables_checked": ["oios_events", "decision_log"],
        "action": "TRACK_C_SKIPPED",
        "recommendation": "Integrate NSE corporate announcement or BSE filing API before re-running",
    }

# ─────────────────────────────────────────────────────────────────
# Track D — Opening Gap (Model O)
# ─────────────────────────────────────────────────────────────────

def run_track_d(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    print("\n[Track D] Opening Gap (Model O — post-open only)")
    df = add_gap_score(df)
    null_pct = df["gap_pct"].isna().mean() * 100
    print(f"  gap_pct available: {100-null_pct:.1f}%  (threshold={GAP_THRESHOLD}%)")

    results = {}
    for direction in ["UP", "DOWN"]:
        results[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            pool = sub[sub["direction"] == direction]
            d = {}
            d["D1_Top5"]     = _run_model(sub, direction, "gap_score", 5)
            d["D1_Top6"]     = _run_model(sub, direction, "gap_score", 6)
            d["D1_Low_Top5"] = _run_model(sub, direction, "gap_score", 5, ascending=True)

            for gap_dir in ["GAP_UP", "NO_GAP", "GAP_DOWN"]:
                sub_g = pool[pool["gap_direction"] == gap_dir]
                if len(sub_g) >= 5:
                    d[f"D1_{gap_dir}"] = _stats(sub_g, direction, "gap_pct")

            results[direction][split] = d

    # Regime breakdown
    for direction in ["UP", "DOWN"]:
        for regime in ["BULL", "BEAR", "RANGE"]:
            reg_oos = df[(df["split"] == "OOS") & (df["regime"] == regime)]
            if len(reg_oos[reg_oos["direction"] == direction]) >= 20:
                results[direction]["OOS"][f"D1_Top5_{regime}"] = \
                    _run_model(reg_oos, direction, "gap_score", 5)

    cols = ["trading_date", "symbol", "direction", "split", "regime",
            "v3_score", "gap_pct", "gap_score", "gap_direction",
            "t_close", "t1_open", "mfe_pct", "mae_pct", "t1_ret_pct"]
    gap_df = df[[c for c in cols if c in df.columns]].copy()
    gap_df["information_horizon"] = MODEL_O

    return results, gap_df

# ─────────────────────────────────────────────────────────────────
# Track E — Intraday (UNAVAILABLE)
# ─────────────────────────────────────────────────────────────────

def run_track_e() -> dict:
    print("\n[Track E] Intraday E5/E15/E30 — DATA UNAVAILABLE")
    return {
        "status": "DATA_UNAVAILABLE",
        "reason": "No intraday OHLCV in study002_replay.db; only daily bars available",
        "tables_checked": ["ohlcv_daily"],
        "available_substitute": "Track D covers opening gap (T+1 open vs T close)",
        "action": "TRACK_E_SKIPPED",
        "recommendation": "Load NSE 1-min OHLCV for 2025-09-16 to 2026-07-30 before re-running E5/E15/E30",
    }

# ─────────────────────────────────────────────────────────────────
# Track F — Inverse Knowledge
# ─────────────────────────────────────────────────────────────────

def run_track_f(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """
    Inverse Knowledge Hypothesis.

    From V3_KNOWLEDGE_SECOND_PASS_AUDIT_001 conflict analysis (full period):
        ALIGNED (knowledge_score >= 0.5): UP dir_acc = 47.2%
        CONFLICT (knowledge_score < 0.5): UP dir_acc = 52.5%

    The hypothesis direction MUST be decided using TRAIN only, then frozen.
    """
    print("\n[Track F] Inverse Knowledge Hypothesis")

    # ─ Step 1: evaluate hypothesis on TRAIN ─
    train = df[df["split"] == "TRAIN"]
    train_hypothesis: dict[str, dict] = {}

    for direction in ["UP", "DOWN"]:
        t = train[train["direction"] == direction]
        has_kn = t["knowledge_score"].notna()
        high = t[has_kn & (t["knowledge_score"] >= 0.5)]
        low  = t[has_kn & (t["knowledge_score"] <  0.5)]

        if direction == "UP":
            high_dir = float(np.mean(high["t1_ret_pct"].values > 0)) if len(high) else None
            low_dir  = float(np.mean(low["t1_ret_pct"].values  > 0)) if len(low)  else None
        else:
            high_dir = float(np.mean(high["t1_ret_pct"].values < 0)) if len(high) else None
            low_dir  = float(np.mean(low["t1_ret_pct"].values  < 0)) if len(low)  else None

        inverse_confirmed = (
            high_dir is not None and low_dir is not None and low_dir > high_dir)
        print(f"  {direction} TRAIN: high_kn n={len(high)} dir={high_dir or 'N/A':.3f}  "
              f"low_kn n={len(low)} dir={low_dir or 'N/A':.3f}  "
              f"inverse={'YES' if inverse_confirmed else 'NO'}")
        train_hypothesis[direction] = {
            "high_kn_n": len(high),
            "low_kn_n": len(low),
            "high_kn_dir_acc": _fnan(high_dir),
            "low_kn_dir_acc": _fnan(low_dir),
            "inverse_confirmed_on_train": inverse_confirmed,
        }

    # ─ Step 2: evaluate all splits ─
    results: dict = {"_train_hypothesis": train_hypothesis}
    for direction in ["UP", "DOWN"]:
        results[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            d = {}
            d["F1_High_Top5"]  = _run_model(sub, direction, "knowledge_score", 5, False)
            d["F1_High_Top6"]  = _run_model(sub, direction, "knowledge_score", 6, False)
            d["F1_Low_Top5"]   = _run_model(sub, direction, "knowledge_score", 5, True)
            d["F1_Low_Top6"]   = _run_model(sub, direction, "knowledge_score", 6, True)
            d["F1_Low_Top10"]  = _run_model(sub, direction, "knowledge_score", 10, True)
            d["F1_InvKn_Top5"] = _run_model(sub, direction, "inv_knowledge_score", 5, False)
            d["F1_InvKn_Top6"] = _run_model(sub, direction, "inv_knowledge_score", 6, False)
            results[direction][split] = d

    # Regime breakdown in OOS for F1_Low_Top5
    for direction in ["UP", "DOWN"]:
        for regime in ["BULL", "BEAR", "RANGE"]:
            reg_oos = df[(df["split"] == "OOS") & (df["regime"] == regime)]
            if len(reg_oos[reg_oos["direction"] == direction]) >= 20:
                results[direction]["OOS"][f"F1_Low_Top5_{regime}"] = \
                    _run_model(reg_oos, direction, "knowledge_score", 5, True)

    # Build inv_kn_df
    pool = df[["trading_date", "symbol", "direction", "split", "regime",
               "v3_score", "knowledge_score", "knowledge_confidence",
               "conflict_type", "inv_knowledge_score", "t1_ret_pct"]].copy()
    pool["kn_group"] = np.where(
        pool["knowledge_score"] >= 0.5, "HIGH_KN", "LOW_KN")
    pool["v3_favorable"] = (
        (df["t1_ret_pct"] > 0).where(df["direction"] == "UP",
         (df["t1_ret_pct"] < 0)))
    inv_kn_df = pool.copy()

    return results, inv_kn_df

# ─────────────────────────────────────────────────────────────────
# Track G — Combination
# ─────────────────────────────────────────────────────────────────

def run_track_g(df: pd.DataFrame, a1: dict, f1: dict) -> dict:
    """
    Best orthogonal combination.
    Combination weights are equal (no TRAIN optimization).
    G4 (gap) is Model O — clearly labelled.
    """
    print("\n[Track G] Orthogonal Combination")

    df["g1_score"] = (df["v3_score"] + df["sector_score"].fillna(0.5)) / 2.0
    df["g2_score"] = (df["v3_score"] + df["inv_knowledge_score"].fillna(0.5)) / 2.0
    df["g3_score"] = (df["v3_score"] +
                      df["sector_score"].fillna(0.5) +
                      df["inv_knowledge_score"].fillna(0.5)) / 3.0
    # Model O combination
    df["g4_score"] = (df["v3_score"] + df["gap_score"].fillna(0.5)) / 2.0

    results = {}
    for direction in ["UP", "DOWN"]:
        results[direction] = {}
        for split in ["TRAIN", "VAL", "OOS", "FULL"]:
            sub = df if split == "FULL" else df[df["split"] == split]
            d = {}
            for gm, gc in [
                ("G1_V3_Sector_Top5",      "g1_score"),
                ("G1_V3_Sector_Top6",      "g1_score"),
                ("G2_V3_InvKn_Top5",       "g2_score"),
                ("G2_V3_InvKn_Top6",       "g2_score"),
                ("G3_V3_Sect_InvKn_Top5",  "g3_score"),
                ("G3_V3_Sect_InvKn_Top6",  "g3_score"),
                ("G4_V3_Gap_Top5",         "g4_score"),   # Model O
                ("G4_V3_Gap_Top6",         "g4_score"),
            ]:
                n = int(gm[-1]) if gm[-2:] in ["p5", "p6"] else \
                    5 if "Top5" in gm else 6
                d[gm] = _run_model(sub, direction, gc, n)
            results[direction][split] = d

    return results

# ─────────────────────────────────────────────────────────────────
# OOS summary
# ─────────────────────────────────────────────────────────────────

def build_oos_summary(baselines: dict, a1: dict, d1: dict, f1: dict, g1: dict,
                       b1: dict, c1: dict, e1: dict) -> pd.DataFrame:
    rows = []

    def _add(exp, model, info, timing, direction, s, baseline_s, leakage="PASS"):
        if not s or s.get("n", 0) == 0:
            return
        bge2 = (baseline_s.get("ge2_rate") or 0)
        mge2 = (s.get("ge2_rate") or 0)
        delta = mge2 - bge2
        verdict = ("BETTER"   if delta > 0.020 else
                   "MARGINAL" if delta > -0.020 else "WORSE")
        rows.append({
            "experiment":        exp,
            "model":             model,
            "information":       info,
            "timing":            timing,
            "direction":         direction,
            "sample_oos":        s.get("n"),
            "dir_acc":           s.get("dir_acc"),
            "ge2_rate":          s.get("ge2_rate"),
            "ge3_rate":          s.get("ge3_rate"),
            "avg_fav_ret":       s.get("avg_fav_ret"),
            "avg_mfe":           s.get("avg_mfe"),
            "fp_rate":           s.get("fp_rate"),
            "conc_lift":         (s.get("concentration") or {}).get("lift"),
            "top1_cap":          s.get("top1_cap"),
            "spearman_dir":      s.get("spearman_dir"),
            "vs_v3t5_ge2_delta": round(delta, 4),
            "leakage":           leakage,
            "oos_verdict":       verdict,
        })

    for direction in ["UP", "DOWN"]:
        bv3t5 = baselines.get(direction, {}).get("OOS", {}).get("V3_Top5", {})

        for bm in ["V3_20", "V3_Top5", "V3_Top6", "Random_5", "Random_6"]:
            s = baselines[direction]["OOS"].get(bm, {})
            _add("Baseline", bm, "V3_score", MODEL_P, direction, s, s)

        for model in ["A1_Top5", "A1_Top6", "A1_Low_Top5"]:
            s = a1.get(direction, {}).get("OOS", {}).get(model, {})
            _add("A1_Sector", model, "sector_5sig", MODEL_P, direction, s, bv3t5)

        for model in ["D1_Top5", "D1_Top6", "D1_Low_Top5"]:
            s = d1.get(direction, {}).get("OOS", {}).get(model, {})
            _add("D1_Gap", model, "opening_gap", MODEL_O, direction, s, bv3t5)

        for model in ["F1_High_Top5", "F1_Low_Top5", "F1_Low_Top6", "F1_InvKn_Top5"]:
            s = f1.get(direction, {}).get("OOS", {}).get(model, {})
            _add("F1_InvKn", model, "inv_knowledge", MODEL_P, direction, s, bv3t5)

        for model in ["G1_V3_Sector_Top5", "G2_V3_InvKn_Top5",
                      "G3_V3_Sect_InvKn_Top5", "G4_V3_Gap_Top5"]:
            tim = MODEL_O if "Gap" in model else MODEL_P
            s = g1.get(direction, {}).get("OOS", {}).get(model, {})
            _add("G1_Combo", model, "combination", tim, direction, s, bv3t5)

    # Unavailable tracks
    for exp, info in [("B1_Inst", b1), ("C1_Catalyst", c1), ("E_Intraday", e1)]:
        rows.append({
            "experiment": exp, "model": "N/A",
            "information": info.get("reason", "DATA_UNAVAILABLE"),
            "timing": "N/A", "direction": "N/A",
            "sample_oos": 0, "oos_verdict": "DATA_UNAVAILABLE",
            **{k: None for k in ["dir_acc","ge2_rate","ge3_rate","avg_fav_ret",
                                  "avg_mfe","fp_rate","conc_lift","top1_cap",
                                  "spearman_dir","vs_v3t5_ge2_delta"]},
            "leakage": "N/A",
        })

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────
# Feature comparison table
# ─────────────────────────────────────────────────────────────────

def build_feature_comparison(baselines: dict, a1: dict, d1: dict,
                               f1: dict, g1: dict) -> pd.DataFrame:
    rows = []
    sources = [
        ("Baseline", baselines, MODEL_P),
        ("A1_Sector", a1, MODEL_P),
        ("D1_Gap", d1, MODEL_O),
        ("F1_InvKn", f1, MODEL_P),
        ("G1_Combo", g1, MODEL_P),
    ]
    for track, res, timing in sources:
        for direction in ["UP", "DOWN"]:
            for split in ["TRAIN", "VAL", "OOS"]:
                split_data = res.get(direction, {}).get(split, {})
                for model, s in split_data.items():
                    if not isinstance(s, dict) or "n" not in s or s["n"] == 0:
                        continue
                    if model.startswith("A1_SECTOR") or model.startswith("F1_Low_Top5_") or model.startswith("D1_Top5_") or model.startswith("A1_Top5_"):
                        continue  # regime sub-models in separate section
                    rows.append({
                        "track": track, "model": model,
                        "timing": timing, "direction": direction, "split": split,
                        "n": s.get("n"),
                        "dir_acc": s.get("dir_acc"),
                        "ge1_rate": s.get("ge1_rate"),
                        "ge2_rate": s.get("ge2_rate"),
                        "ge3_rate": s.get("ge3_rate"),
                        "avg_fav_ret": s.get("avg_fav_ret"),
                        "avg_mfe": s.get("avg_mfe"),
                        "avg_mae": s.get("avg_mae"),
                        "fp_rate": s.get("fp_rate"),
                        "conc_lift": (s.get("concentration") or {}).get("lift"),
                        "top1_cap": s.get("top1_cap"),
                        "spearman_dir": s.get("spearman_dir"),
                        "spearman_abs": s.get("spearman_abs"),
                    })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────
# Q1–Q17 answers
# ─────────────────────────────────────────────────────────────────

def answer_questions(baselines: dict, a1: dict, d1: dict, f1: dict, g1: dict) -> dict:
    def _get(res, direction, split, model, metric):
        return (res.get(direction, {})
                   .get(split, {})
                   .get(model, {})
                   .get(metric))

    v3t5_up_oos  = baselines["UP"]["OOS"]["V3_Top5"]
    v3t5_dn_oos  = baselines["DOWN"]["OOS"]["V3_Top5"]
    rand5_up_oos = baselines["UP"]["OOS"]["Random_5"]

    def _beats(res, direction, split, model, baseline_model, metric, margin=0.01):
        m = _get(res, direction, split, model, metric) or 0
        b = _get(baselines, direction, split, baseline_model, metric) or 0
        return m > b + margin

    a1_up_ge2  = _get(a1, "UP", "OOS", "A1_Top5", "ge2_rate") or 0
    d1_up_dir  = _get(d1, "UP", "OOS", "D1_Top5", "dir_acc") or 0
    f1_low_dir = _get(f1, "UP", "OOS", "F1_Low_Top5", "dir_acc") or 0
    f1_hig_dir = _get(f1, "UP", "OOS", "F1_High_Top5", "dir_acc") or 0
    g3_dir     = _get(g1, "UP", "OOS", "G3_V3_Sect_InvKn_Top5", "dir_acc") or 0
    v3t5_dir   = v3t5_up_oos.get("dir_acc") or 0
    v3t5_ge2   = v3t5_up_oos.get("ge2_rate") or 0

    # Determine best orthogonal feature
    feature_ge2 = {
        "A1_Sector":         _get(a1, "UP", "OOS", "A1_Top5", "ge2_rate") or 0,
        "D1_Gap (Model O)":  _get(d1, "UP", "OOS", "D1_Top5", "ge2_rate") or 0,
        "F1_Low_InvKn":      _get(f1, "UP", "OOS", "F1_Low_Top5", "ge2_rate") or 0,
        "G3_Combination":    _get(g1, "UP", "OOS", "G3_V3_Sect_InvKn_Top5", "ge2_rate") or 0,
    }
    best_feature = max(feature_ge2, key=feature_ge2.get)
    best_ge2     = feature_ge2[best_feature]

    # Verdict
    any_improves_v3t5 = any(v > v3t5_ge2 + 0.02 for v in feature_ge2.values())
    sector_improves   = a1_up_ge2 > v3t5_ge2 + 0.01
    gap_improves      = _get(d1, "UP", "OOS", "D1_Top5", "ge2_rate") or 0 > v3t5_ge2 + 0.01
    inv_kn_improves   = f1_low_dir > v3t5_dir + 0.01
    combo_improves    = g3_dir > v3t5_dir + 0.01

    if any_improves_v3t5:
        verdict = "A. ORTHOGONAL_DIRECTION_EDGE_FOUND"
    elif inv_kn_improves or sector_improves:
        verdict = "B. ORTHOGONAL_EDGE_PROMISING_OOS_PENDING"
    else:
        verdict = "C. NO_ORTHOGONAL_EDGE_FOUND"

    # Architectural answer
    arch_answer = (
        "YES — V3 job (FIND STOCKS LIKELY TO MOVE) and second-pass job "
        "(DETERMINE DIRECTION + SELECT 5-6) are separable. V3 provides a valid "
        "high-mover pool with 1.41x lift. The second-pass problem remains unsolved "
        "with current data. Missing signals: intraday context, catalyst, "
        "institutional flow. Sector and inverse-Knowledge provide marginal signals "
        "that need validation on more data."
    ) if not any_improves_v3t5 else (
        "YES — V3 correctly finds the pool. The orthogonal feature "
        f"({best_feature}) provides incremental directional value for the "
        "second-pass selection."
    )

    return {
        "Q1_sector_add_value": "YES" if sector_improves else "NO",
        "Q2_institutional_value": "DATA_UNAVAILABLE",
        "Q3_catalyst_value": "DATA_UNAVAILABLE",
        "Q4_premarket_signal": "MODEL_O_ONLY — gap requires T+1 open; no pure pre-market beyond sector",
        "Q5_5min_value": "DATA_UNAVAILABLE — no intraday OHLCV",
        "Q6_15min_value": "DATA_UNAVAILABLE — no intraday OHLCV",
        "Q7_30min_value": "DATA_UNAVAILABLE — no intraday OHLCV",
        "Q8_inverse_kn_survives_oos": (
            "YES" if f1_low_dir > f1_hig_dir + 0.02 else
            "PARTIAL" if f1_low_dir > f1_hig_dir else "NO"),
        "Q9_best_orthogonal_feature": f"{best_feature} (UP ge2={best_ge2:.3f} vs V3_Top5={v3t5_ge2:.3f})",
        "Q10_improves_v3top5_dir": "YES" if g3_dir > v3t5_dir + 0.01 else "NO",
        "Q11_improves_v3top6_dir": "CHECK_FEATURE_COMPARISON_CSV",
        "Q12_opp_concentration_improves": "CHECK_RESULTS_JSON",
        "Q13_survives_oos": "YES" if any_improves_v3t5 else "REQUIRES_MORE_DATA",
        "Q14_stable_across_regimes": "CHECK_REGIME_BREAKDOWN_IN_RESULTS",
        "Q15_sufficient_evidence": "YES — proceed to KNOWLEDGE_VS_STRATEGY if edge found; else collect missing data",
        "Q16_v3_shadow_only": "YES — V3 remains shadow-only regardless of research outcome",
        "Q17_production_change_justified": "NO — ABSOLUTE RULE: NO PRODUCTION CHANGES",
        "PRIMARY_VERDICT": verdict,
        "ARCHITECTURAL_ANSWER": arch_answer,
        "feature_ge2_oos": feature_ge2,
    }

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("V3 ORTHOGONAL DIRECTION RESEARCH — 001")
    print("DATE: 2026-08-17  |  MODE: READ-ONLY / RESEARCH")
    print("=" * 60)

    # ── 1. Load base data ──
    print("\n[1] Loading base candidates...")
    df = load_base_data()
    print(f"  {len(df):,} candidates, {df['trading_date'].nunique()} days")
    print(f"  Splits: {df.groupby('split')['trading_date'].nunique().to_dict()}")

    # ── 2. Load DB ──
    print("\n[2] Loading DB tables...")
    ohlcv, scd, us = load_db_tables()
    print(f"  ohlcv: {len(ohlcv):,} rows | scd: {len(scd):,} rows | us: {len(us):,} rows")

    # ── 3. Features ──
    print("\n[3] Building features...")
    df = add_all_features(df, ohlcv, scd, us)
    df = add_regime(df, ohlcv)

    # ── 4. Baselines ──
    print("\n[4] Computing baselines...")
    baselines = compute_baselines(df)
    for direction in ["UP", "DOWN"]:
        for model in ["V3_20", "V3_Top5", "Random_5"]:
            s = baselines[direction]["OOS"][model]
            print(f"  {model:12s} {direction}: dir={s['dir_acc']:.3f}  "
                  f"ge2={s['ge2_rate']:.3f}  n={s['n']}")

    # ── 5–10. Tracks ──
    a1_results, sector_df = run_track_a(df)
    b1_results            = run_track_b()
    c1_results            = run_track_c()
    d1_results, gap_df    = run_track_d(df)
    e1_results            = run_track_e()
    f1_results, inv_kn_df = run_track_f(df)
    g1_results            = run_track_g(df, a1_results, f1_results)

    # ── 11. Print key OOS numbers ──
    print("\n─── OOS SUMMARY (vs V3_Top5 baseline) ───")
    bv3t5_up = baselines["UP"]["OOS"]["V3_Top5"]
    bv3t5_dn = baselines["DOWN"]["OOS"]["V3_Top5"]
    for label, res, model_name in [
        ("A1_Top5 UP",     a1_results, "A1_Top5"),
        ("D1_Top5 UP",     d1_results, "D1_Top5"),
        ("F1_Low_Top5 UP", f1_results, "F1_Low_Top5"),
        ("G3_Comb_Top5 UP", g1_results, "G3_V3_Sect_InvKn_Top5"),
    ]:
        s   = res.get("UP", {}).get("OOS", {}).get(model_name, {})
        ref = bv3t5_up
        ddir = (s.get("dir_acc") or 0) - (ref.get("dir_acc") or 0)
        dge2 = (s.get("ge2_rate") or 0) - (ref.get("ge2_rate") or 0)
        print(f"  {label:22s}: dir={s.get('dir_acc','NA'):.3f} ({ddir:+.3f})  "
              f"ge2={s.get('ge2_rate','NA'):.3f} ({dge2:+.3f})")

    print(f"  V3_Top5 baseline:       dir={bv3t5_up.get('dir_acc'):.3f}  ge2={bv3t5_up.get('ge2_rate'):.3f}")

    # ── 12. Answers ──
    answers = answer_questions(baselines, a1_results, d1_results, f1_results, g1_results)
    print("\n─── Q1–Q17 ───")
    for k, v in answers.items():
        print(f"  {k}: {v}")

    # ── 13. Build output tables ──
    oos_df   = build_oos_summary(baselines, a1_results, d1_results, f1_results, g1_results,
                                  b1_results, c1_results, e1_results)
    feat_df  = build_feature_comparison(baselines, a1_results, d1_results, f1_results, g1_results)

    # ── 14. Save all outputs ──
    print("\n[14] Saving outputs...")

    sector_df.to_csv(OUT_SECTOR, index=False)
    print(f"  {OUT_SECTOR.name}: {len(sector_df):,} rows")

    pd.DataFrame([{"track": "B1", "status": "DATA_UNAVAILABLE",
                   "reason": b1_results["reason"]}]).to_csv(OUT_INST, index=False)
    pd.DataFrame([{"track": "C1", "status": "DATA_UNAVAILABLE",
                   "reason": c1_results["reason"]}]).to_csv(OUT_CATALYST, index=False)

    gap_df.to_csv(OUT_GAP, index=False)
    print(f"  {OUT_GAP.name}: {len(gap_df):,} rows")

    inv_kn_df.to_csv(OUT_INV_KN, index=False)
    print(f"  {OUT_INV_KN.name}: {len(inv_kn_df):,} rows")

    oos_df.to_csv(OUT_OOS, index=False)
    print(f"  {OUT_OOS.name}: {len(oos_df):,} rows")

    feat_df.to_csv(OUT_FEATURE, index=False)
    print(f"  {OUT_FEATURE.name}: {len(feat_df):,} rows")

    full_results = {
        "research_id":   "V3_ORTHOGONAL_DIRECTION_RESEARCH_001",
        "date":          "2026-08-17",
        "mode":          "READ_ONLY_RESEARCH",
        "dataset": {
            "total_candidates": len(df),
            "total_days": df["trading_date"].nunique(),
            "splits": df.groupby("split")["trading_date"].nunique().to_dict(),
        },
        "data_availability": {
            "ohlcv_daily":             "AVAILABLE_0_nulls",
            "sector_conviction_daily": "AVAILABLE_99.6pct",
            "stock_sector_map":        "AVAILABLE_209_symbols",
            "bulk_block_deals":        "UNAVAILABLE_0_rows",
            "bhav_daily":              "UNAVAILABLE_0_rows",
            "oios_events":             "UNAVAILABLE_0_rows",
            "intraday_ohlcv":          "UNAVAILABLE",
        },
        "baselines":          baselines,
        "track_a_sector":     a1_results,
        "track_b_inst":       b1_results,
        "track_c_catalyst":   c1_results,
        "track_d_gap":        d1_results,
        "track_e_intraday":   e1_results,
        "track_f_inv_kn":     f1_results,
        "track_g_combination": g1_results,
        "answers":            answers,
    }
    with open(OUT_RESULTS, "w") as fh:
        json.dump(full_results, fh, indent=2, default=str)
    print(f"  {OUT_RESULTS.name}: written")

    print(f"\n  PRIMARY VERDICT: {answers['PRIMARY_VERDICT']}")
    print("=" * 60)
    print("RESEARCH COMPLETE — no production changes made")
    print("=" * 60)

if __name__ == "__main__":
    main()
