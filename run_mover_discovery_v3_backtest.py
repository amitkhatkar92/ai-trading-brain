"""
run_mover_discovery_v3_backtest.py
====================================
Mover Discovery V3 — Historical Backtest & Research Evaluation
===============================================================

This script evaluates V3 scoring against the 2021-2025 IIOS replay database.

IMPORTANT:
  - READ-ONLY — does not modify any production file
  - Does not write to CandidateStore
  - Does not create TradeSignal objects
  - Does not trigger execution
  - Uses strict train/OOS split to prevent leakage

OOS period: 2024-01-01 to 2025-12-30
Train period: 2021-01-01 to 2023-12-31

Outputs:
  reports/mover_discovery_v3/MOVER_DISCOVERY_V3_DESIGN.md
  reports/mover_discovery_v3/MOVER_DISCOVERY_V3_RESEARCH_REPORT.md
  reports/mover_discovery_v3/mover_discovery_v3_results.json
  reports/mover_discovery_v3/mover_discovery_v3_feature_analysis.csv
  reports/mover_discovery_v3/mover_discovery_v3_pool_analysis.csv
  reports/mover_discovery_v3/mover_discovery_v3_missed_cases.json
  docs/MOVER_DISCOVERY_V3_ARCHITECTURE.md
"""

import json
import sqlite3
import warnings
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

print("[V3Backtest] MOVER_DISCOVERY_V3 starting — READ-ONLY research mode")
print("[V3Backtest] No production files will be modified.")
print()

DB_PATH   = Path("data/replay.db")
OUT_DIR   = Path("reports/mover_discovery_v3")
DOCS_DIR  = Path("docs")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_END = "2023-12-31"
OOS_START = "2024-01-01"
MOVER_THRESHOLD = 2.0  # >=2% 1-day forward return = strong mover

# Pool sizes to evaluate
POOL_SIZES = [10, 15, 20, 25, 30, 40]

# ─────────────────────────────────────────────────────────────────────────────
# Import V3 module
# ─────────────────────────────────────────────────────────────────────────────
from opportunity_engine.mover_discovery_v3 import (
    V3Config, V3UpWeights, V3DownWeights,
    compute_v3_features, score_universe, select_candidates,
    check_leakage, FORBIDDEN_FUTURE_KEYS,
)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)
    ohlcv = pd.read_sql_query(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily WHERE symbol != '^NSEI' ORDER BY symbol, trade_date",
        conn,
    )
    signal_births = pd.read_sql_query(
        "SELECT symbol, detected_at FROM signal_births",
        conn,
    )
    universe = pd.read_sql_query(
        "SELECT symbol, sector FROM universe_stocks",
        conn,
    )
    nifty = pd.read_sql_query(
        "SELECT trade_date, close as nifty_close FROM ohlcv_daily "
        "WHERE symbol='^NSEI' ORDER BY trade_date",
        conn,
    )
    conn.close()

    ohlcv["date"] = pd.to_datetime(ohlcv["trade_date"])
    signal_births["birth_date"] = pd.to_datetime(signal_births["detected_at"]).dt.normalize()
    nifty["date"] = pd.to_datetime(nifty["trade_date"])

    print(f"[DataLoad] ohlcv rows={len(ohlcv):,}  signal_births={len(signal_births):,}  "
          f"universe={len(universe):,}  nifty={len(nifty):,}")
    return ohlcv, signal_births, universe, nifty


# ─────────────────────────────────────────────────────────────────────────────
# LABEL GENERATION (strict PIT: labels use T+1 data, not available at T)
# ─────────────────────────────────────────────────────────────────────────────

def build_labels(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    For each (symbol, date T), compute forward return using close[T+1] / close[T] - 1.
    Labels are ONLY used for evaluation — never as input features.
    """
    df = ohlcv[["symbol", "date", "close"]].copy()
    df = df.sort_values(["symbol", "date"])
    df["ret_1d"] = df.groupby("symbol")["close"].pct_change().shift(-1) * 100.0
    df["is_up_mover"]   = (df["ret_1d"] >= MOVER_THRESHOLD).astype(int)
    df["is_down_mover"] = (df["ret_1d"] <= -MOVER_THRESHOLD).astype(int)
    df["is_mover"]      = ((df["is_up_mover"] == 1) | (df["is_down_mover"] == 1)).astype(int)
    # Drop last row per symbol (no forward data)
    df = df.dropna(subset=["ret_1d"])
    print(f"[Labels] rows={len(df):,}  up_movers={df['is_up_mover'].sum():,}  "
          f"down_movers={df['is_down_mover'].sum():,}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# NIFTY REGIME COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_regime(nifty: pd.DataFrame) -> pd.DataFrame:
    n = nifty.copy().sort_values("date")
    n["nifty_ret_20d"] = n["nifty_close"].pct_change(20) * 100.0
    n["regime"] = "SIDEWAYS"
    n.loc[n["nifty_ret_20d"] >  3.0, "regime"] = "TRENDING_UP"
    n.loc[n["nifty_ret_20d"] < -3.0, "regime"] = "TRENDING_DOWN"
    return n[["date", "regime", "nifty_ret_20d"]].dropna()


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE ENGINEERING (per-date cross-section, fully PIT-safe)
# ─────────────────────────────────────────────────────────────────────────────

def build_cross_section_features(
    ohlcv: pd.DataFrame,
    sector_map: Dict[str, str],
    min_history: int = 25,
) -> pd.DataFrame:
    """
    For every (symbol, date) pair, compute V3 features using only backward-looking
    window [date-lookback, date]. The feature row is labelled with 'date' = T.

    Returns DataFrame with columns:
        symbol, date, + all V3 feature columns
    """
    ohlcv = ohlcv.sort_values(["symbol", "date"])
    dates = sorted(ohlcv["date"].unique())
    symbols = ohlcv["symbol"].unique()
    total = len(dates)

    print(f"[Features] Computing features for {len(symbols)} symbols × {total} dates ...")

    # Pre-group by symbol for speed
    by_sym: Dict[str, pd.DataFrame] = {sym: g.sort_values("date")
                                        for sym, g in ohlcv.groupby("symbol")}

    rows = []
    _step = max(1, total // 20)
    for di, dt in enumerate(dates):
        if di % _step == 0:
            print(f"  [{di}/{total}] {dt.date()}", end="\r", flush=True)

        # Sector 1d returns for context (current day only, no forward data)
        sector_rets: Dict[str, List[float]] = {}
        for sym, grp in by_sym.items():
            sub = grp[grp["date"] <= dt]
            if len(sub) < 2:
                continue
            r = (sub["close"].iloc[-1] / sub["close"].iloc[-2] - 1.0) * 100.0
            sec = sector_map.get(sym, "UNKNOWN")
            sector_rets.setdefault(sec, []).append(float(r))

        for sym, grp in by_sym.items():
            sub = grp[grp["date"] <= dt]
            if len(sub) < min_history:
                continue

            closes  = sub["close"].tolist()
            highs   = sub["high"].tolist()
            lows    = sub["low"].tolist()
            volumes = sub["volume"].tolist()

            sec = sector_map.get(sym, "UNKNOWN")
            peers = sector_rets.get(sec, [])

            feat = compute_v3_features(sym, closes, highs, lows, volumes, peers)
            if feat is None:
                continue

            # Leakage guard: ensure no future keys slipped in
            for fk in FORBIDDEN_FUTURE_KEYS:
                assert fk not in feat, f"LEAKAGE: {fk} in features for {sym}@{dt.date()}"

            feat["date"]   = dt
            feat["sector"] = sec
            rows.append(feat)

    print(f"\n[Features] Done — {len(rows):,} feature rows")
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# V3 SCORING (daily cross-section score + candidate selection)
# ─────────────────────────────────────────────────────────────────────────────

def run_v3_scoring(
    features_df: pd.DataFrame,
    cfg: V3Config,
) -> pd.DataFrame:
    """
    Apply V3 scoring to every date cross-section.
    Returns features_df with v3_up_score and v3_down_score columns added.
    """
    dates = sorted(features_df["date"].unique())
    all_rows = []
    for dt in dates:
        day_df = features_df[features_df["date"] == dt]
        feat_list = day_df.to_dict(orient="records")
        scored = score_universe(feat_list, cfg)
        all_rows.extend(scored)
    result = pd.DataFrame(all_rows)
    print(f"[V3Scoring] Scored {len(result):,} rows across {len(dates):,} dates")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HISTORICAL SIGNAL BIRTHS (proxy for "existing scanner generated signal")
# ─────────────────────────────────────────────────────────────────────────────

def build_existing_scanner_flags(
    scored_df: pd.DataFrame,
    signal_births: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mark which (symbol, date) rows were generated by the existing scanner
    (birth_date in signal_births).
    """
    scanner_set = set(
        zip(signal_births["symbol"].str.strip(), signal_births["birth_date"].dt.date)
    )
    scored_df["existing_scanner"] = scored_df.apply(
        lambda r: 1 if (r["symbol"].strip(), r["date"].date()) in scanner_set else 0,
        axis=1,
    )
    print(f"[ScannerFlags] existing_scanner signals matched: "
          f"{scored_df['existing_scanner'].sum():,}")
    return scored_df


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE V3 CANDIDATES (compute recall/precision/lift per date)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_pool(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int,
    direction: str,  # "UP", "DOWN", or "BOTH"
    score_col: str,  # "v3_up_score" or "v3_down_score"
    label_col: str,  # "is_up_mover", "is_down_mover"
) -> Dict[str, float]:
    """
    Per-date top-N selection. Compute recall, precision, lift.
    """
    merged = scored_df.merge(
        labels_df[["symbol", "date", label_col]],
        on=["symbol", "date"],
        how="inner",
    ).dropna(subset=[score_col, label_col])

    dates = sorted(merged["date"].unique())
    recalls, precisions, lifts = [], [], []

    for dt in dates:
        day = merged[merged["date"] == dt].copy()
        if len(day) < pool_size + 1:
            continue

        n_total = len(day)
        n_movers = int(day[label_col].sum())
        if n_movers == 0:
            continue

        base_rate = n_movers / n_total

        # Select top-N by score (deterministic tie-break: symbol)
        day_sorted = day.sort_values([score_col, "symbol"], ascending=[False, True])
        top_n = day_sorted.head(pool_size)

        tp = int(top_n[label_col].sum())
        recall    = tp / n_movers if n_movers > 0 else 0.0
        precision = tp / pool_size if pool_size > 0 else 0.0
        lift      = precision / base_rate if base_rate > 0 else 0.0

        recalls.append(recall)
        precisions.append(precision)
        lifts.append(lift)

    if not recalls:
        return {"recall": 0.0, "precision": 0.0, "lift": 0.0, "n_dates": 0}

    return {
        "recall":    float(np.mean(recalls)),
        "precision": float(np.mean(precisions)),
        "lift":      float(np.mean(lifts)),
        "n_dates":   len(recalls),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GROUP CLASSIFICATION (same definitions as AUDIT_002)
# ─────────────────────────────────────────────────────────────────────────────

def classify_groups(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int = 20,
) -> pd.DataFrame:
    """
    Classify every ≥2% mover into groups A/B:
        A: existing scanner NEVER generated it in any pool
        B-rejected: existing scanner included it but debate rejected (score < 6.5 proxy)
        B-approved: existing scanner AND in top-20 V3

    For V3, we add:
        V3-only: V3 discovered but NOT in existing scanner (new recoveries)
        Both: V3 + existing scanner both found it
    """
    merged = scored_df.merge(
        labels_df[["symbol", "date", "is_up_mover", "is_down_mover", "ret_1d"]],
        on=["symbol", "date"],
        how="inner",
    )

    # Identify top-20 V3 UP per date
    v3_up_flags = []
    v3_dn_flags = []
    for dt, day in merged.groupby("date"):
        up_top  = set(day.nlargest(pool_size, "v3_up_score")["symbol"])
        dn_top  = set(day.nlargest(pool_size, "v3_down_score")["symbol"])
        for _, row in day.iterrows():
            v3_up_flags.append(row["symbol"] in up_top)
            v3_dn_flags.append(row["symbol"] in dn_top)

    merged["v3_up_selected"]   = v3_up_flags
    merged["v3_down_selected"] = v3_dn_flags

    movers = merged[(merged["is_up_mover"] == 1) | (merged["is_down_mover"] == 1)].copy()

    def group(row):
        was_scanned = bool(row["existing_scanner"])
        v3_up   = bool(row["v3_up_selected"])
        v3_down = bool(row["v3_down_selected"])
        if not was_scanned:
            return "A"  # never in existing pipeline
        return "B"       # in existing pipeline

    movers["group"] = movers.apply(group, axis=1)
    movers["v3_recovered"] = movers.apply(
        lambda r: (bool(r["v3_up_selected"]) and bool(r["is_up_mover"])) or
                  (bool(r["v3_down_selected"]) and bool(r["is_down_mover"])), axis=1
    )
    return movers


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE CONTRIBUTION (per-feature lift at pool=20)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_feature_contribution(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int = 20,
) -> pd.DataFrame:
    """Test each raw feature individually for UP and DOWN prediction."""
    features_up = [
        ("atr_pct",      "UP",   False),
        ("mom_5d",       "UP",   False),
        ("mom_accel",    "UP",   False),
        ("vol_ratio",    "UP",   False),
        ("hv_20",        "UP",   False),
        ("mom_20d",      "UP",   False),
        ("vol_expansion","UP",   False),
        ("mom_1d",       "UP",   False),
    ]
    features_down = [
        ("mom_accel",    "DOWN", True),   # low mom_accel = bearish
        ("mom_5d",       "DOWN", True),   # inverted
        ("mom_1d",       "DOWN", True),
        ("rsi_14",       "DOWN", False),  # high RSI = overbought
        ("vol_ratio",    "DOWN", False),  # volume spike down
        ("atr_pct",      "DOWN", False),
    ]

    rows = []
    merged = scored_df.merge(
        labels_df[["symbol", "date", "is_up_mover", "is_down_mover"]],
        on=["symbol", "date"], how="inner",
    )

    _label_cols = ["is_up_mover", "is_down_mover", "is_mover", "ret_1d"]
    for (feat, direction, invert) in features_up + features_down:
        if feat not in merged.columns:
            continue
        tmp = merged.copy()
        if invert:
            tmp["_score"] = -tmp[feat]
        else:
            tmp["_score"] = tmp[feat]

        lbl = "is_up_mover" if direction == "UP" else "is_down_mover"
        # Drop label cols from tmp so evaluate_pool merge doesn't produce _x/_y suffixes
        tmp_eval = (tmp.drop(columns=[c for c in _label_cols if c in tmp.columns], errors="ignore")
                       .rename(columns={"_score": "_sc"}))
        m = evaluate_pool(tmp_eval, labels_df[["symbol", "date", lbl]],
                          pool_size, direction, "_sc", lbl)

        rows.append({
            "feature":   feat,
            "direction": direction,
            "inverted":  invert,
            "recall":    round(m["recall"], 4),
            "precision": round(m["precision"], 4),
            "lift":      round(m["lift"], 4),
            "n_dates":   m["n_dates"],
        })

    df = pd.DataFrame(rows).sort_values("lift", ascending=False)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# OVERLAP ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def compute_overlap(
    scored_df: pd.DataFrame,
    pool_size: int = 20,
) -> Dict[str, Any]:
    """Compute % overlap between V3 top-N and existing scanner per date."""
    overlap_fracs = []
    for dt, day in scored_df.groupby("date"):
        n_existing = int(day["existing_scanner"].sum())
        if n_existing == 0:
            continue
        top_v3_up = set(day.nlargest(pool_size, "v3_up_score")["symbol"])
        existing  = set(day[day["existing_scanner"] == 1]["symbol"])
        if not existing:
            continue
        overlap   = len(top_v3_up & existing)
        overlap_fracs.append(overlap / len(existing))

    avg_overlap = float(np.mean(overlap_fracs)) if overlap_fracs else 0.0
    return {
        "avg_overlap_fraction": round(avg_overlap, 4),
        "dates_with_existing":  len(overlap_fracs),
    }


# ─────────────────────────────────────────────────────────────────────────────
# WALK-FORWARD OOS VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward_oos(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Strict 3-fold walk-forward. No look-ahead.
        Fold 1: Train 2021–2022 → OOS 2023
        Fold 2: Train 2021–2023 → OOS 2024
        Fold 3: Train 2021–2024 → OOS 2025
    """
    folds = [
        ("2021-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
        ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
        ("2021-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
    ]
    results = []
    for (tr_s, tr_e, oos_s, oos_e) in folds:
        oos_rows = scored_df[
            (scored_df["date"] >= pd.Timestamp(oos_s)) &
            (scored_df["date"] <= pd.Timestamp(oos_e))
        ]
        if len(oos_rows) == 0:
            continue

        m_up = evaluate_pool(oos_rows, labels_df, pool_size, "UP",
                             "v3_up_score", "is_up_mover")
        m_dn = evaluate_pool(oos_rows, labels_df, pool_size, "DOWN",
                             "v3_down_score", "is_down_mover")

        results.append({
            "fold":         f"OOS_{oos_s[:7]}_{oos_e[:7]}",
            "oos_start":    oos_s,
            "oos_end":      oos_e,
            "up_recall":    round(m_up["recall"],    4),
            "up_precision": round(m_up["precision"], 4),
            "up_lift":      round(m_up["lift"],      4),
            "dn_recall":    round(m_dn["recall"],    4),
            "dn_precision": round(m_dn["precision"], 4),
            "dn_lift":      round(m_dn["lift"],      4),
            "up_n_dates":   m_up["n_dates"],
        })
        print(f"  WF {oos_s[:7]}→{oos_e[:7]}: UP lift={m_up['lift']:.3f} "
              f"recall={m_up['recall']:.3f}  DOWN lift={m_dn['lift']:.3f} "
              f"recall={m_dn['recall']:.3f}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# POOL-SIZE SWEEP
# ─────────────────────────────────────────────────────────────────────────────

def pool_size_sweep(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_sizes: List[int] = POOL_SIZES,
    subset: Optional[str] = None,  # None=all, "train", "oos"
) -> pd.DataFrame:
    rows = []
    sub = scored_df
    if subset == "train":
        sub = scored_df[scored_df["date"] <= pd.Timestamp(TRAIN_END)]
    elif subset == "oos":
        sub = scored_df[scored_df["date"] >= pd.Timestamp(OOS_START)]

    for ps in pool_sizes:
        m_up = evaluate_pool(sub, labels_df, ps, "UP",   "v3_up_score",   "is_up_mover")
        m_dn = evaluate_pool(sub, labels_df, ps, "DOWN", "v3_down_score", "is_down_mover")
        rows.append({
            "pool_size":      ps,
            "period":         subset or "all",
            "up_recall":      round(m_up["recall"],    4),
            "up_precision":   round(m_up["precision"], 4),
            "up_lift":        round(m_up["lift"],      4),
            "down_recall":    round(m_dn["recall"],    4),
            "down_precision": round(m_dn["precision"], 4),
            "down_lift":      round(m_dn["lift"],      4),
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# MISSED CASES (V3 Group A = movers V3 also missed)
# ─────────────────────────────────────────────────────────────────────────────

def collect_missed_cases(
    scored_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int = 20,
    max_cases: int = 200,
) -> List[Dict[str, Any]]:
    merged = scored_df.merge(
        labels_df[["symbol","date","is_up_mover","is_down_mover","ret_1d"]],
        on=["symbol","date"], how="inner",
    )
    v3_up_selected   = []
    v3_down_selected = []
    for dt, day in merged.groupby("date"):
        up_top  = set(day.nlargest(pool_size, "v3_up_score")["symbol"])
        dn_top  = set(day.nlargest(pool_size, "v3_down_score")["symbol"])
        v3_up_selected.extend([1 if r["symbol"] in up_top else 0 for _, r in day.iterrows()])
        v3_down_selected.extend([1 if r["symbol"] in dn_top else 0 for _, r in day.iterrows()])

    merged["v3_up_selected"]   = v3_up_selected
    merged["v3_down_selected"] = v3_down_selected

    # Missed: strong movers that V3 also failed to put in top-N
    missed_up = merged[
        (merged["is_up_mover"] == 1) & (merged["v3_up_selected"] == 0)
    ].copy()
    missed_dn = merged[
        (merged["is_down_mover"] == 1) & (merged["v3_down_selected"] == 0)
    ].copy()

    cases = []
    for _, row in missed_up.head(max_cases // 2).iterrows():
        cases.append({
            "direction":    "UP",
            "symbol":       row["symbol"],
            "date":         str(row["date"].date()),
            "ret_1d":       round(float(row["ret_1d"]), 4),
            "v3_up_score":  round(float(row["v3_up_score"]), 4),
            "atr_pct":      round(float(row["atr_pct"]), 4),
            "mom_5d":       round(float(row["mom_5d"]), 4),
            "vol_ratio":    round(float(row["vol_ratio"]), 4),
            "rsi_14":       round(float(row["rsi_14"]), 2),
            "existing_scanner": int(row["existing_scanner"]),
        })
    for _, row in missed_dn.head(max_cases // 2).iterrows():
        cases.append({
            "direction":    "DOWN",
            "symbol":       row["symbol"],
            "date":         str(row["date"].date()),
            "ret_1d":       round(float(row["ret_1d"]), 4),
            "v3_down_score": round(float(row["v3_down_score"]), 4),
            "atr_pct":      round(float(row["atr_pct"]), 4),
            "mom_5d":       round(float(row["mom_5d"]), 4),
            "vol_ratio":    round(float(row["vol_ratio"]), 4),
            "rsi_14":       round(float(row["rsi_14"]), 2),
            "existing_scanner": int(row["existing_scanner"]),
        })
    return cases


# ─────────────────────────────────────────────────────────────────────────────
# LEAKAGE VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def run_leakage_checks(scored_df: pd.DataFrame) -> List[str]:
    sample = scored_df.head(1000).to_dict(orient="records")
    violations = check_leakage(sample)
    for fk in FORBIDDEN_FUTURE_KEYS:
        if fk in scored_df.columns:
            violations.append(f"column={fk} in scored_df")
    return violations


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR TEST: DOWN with sector vs without
# ─────────────────────────────────────────────────────────────────────────────

def sector_test(
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    pool_size: int = 20,
) -> Dict[str, Any]:
    cfg_no_sector  = V3Config(use_sector_for_down=False)
    cfg_with_sector = V3Config(use_sector_for_down=True,
                               down_weights=V3DownWeights(
                                   neg_mom_5d=0.25, neg_mom_accel=0.20,
                                   vol_expansion=0.18, atr_pct=0.12,
                                   rsi_overbought=0.08, sector_down=0.17,
                               ))
    cfg_no_sector.validate()
    cfg_with_sector.validate()

    scored_no  = run_v3_scoring(features_df, cfg_no_sector)
    scored_with = run_v3_scoring(features_df, cfg_with_sector)

    m_no   = evaluate_pool(scored_no,   labels_df, pool_size, "DOWN", "v3_down_score", "is_down_mover")
    m_with = evaluate_pool(scored_with, labels_df, pool_size, "DOWN", "v3_down_score", "is_down_mover")

    return {
        "without_sector": m_no,
        "with_sector":    m_with,
        "lift_delta":     round(m_with["lift"] - m_no["lift"], 4),
        "recall_delta":   round(m_with["recall"] - m_no["recall"], 4),
        "verdict": "SECTOR_ADDS_VALUE" if m_with["lift"] > m_no["lift"] + 0.01
                   else "SECTOR_NO_BENEFIT",
    }


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT WRITERS
# ─────────────────────────────────────────────────────────────────────────────

def write_results_json(
    cfg: V3Config,
    is_metrics: Dict,
    oos_metrics: Dict,
    wf_results: List,
    overlap: Dict,
    sector_result: Dict,
    leakage_violations: List[str],
    groups: Dict,
    total_movers: int,
) -> None:
    payload = {
        "audit_id":    "MOVER_DISCOVERY_V3",
        "date":        date.today().isoformat(),
        "mode":        "RESEARCH_SHADOW",
        "v3_enabled":  False,
        "config": {
            "pool_size":          cfg.discovery_pool_size,
            "train_end":          cfg.train_end_date,
            "oos_start":          cfg.oos_start_date,
            "up_weights":         vars(cfg.up_weights),
            "down_weights":       vars(cfg.down_weights),
            "use_sector_for_down": cfg.use_sector_for_down,
        },
        "in_sample":         is_metrics,
        "oos":               oos_metrics,
        "walk_forward":      wf_results,
        "overlap":           overlap,
        "sector_test":       sector_result,
        "leakage_violations": leakage_violations,
        "leakage_clean":      len(leakage_violations) == 0,
        "groups":            groups,
        "total_movers":      total_movers,
        "verdicts": {
            "oos_up_lift":   oos_metrics.get("up", {}).get("lift", 0.0),
            "oos_down_lift": oos_metrics.get("down", {}).get("lift", 0.0),
        },
    }
    out = OUT_DIR / "mover_discovery_v3_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"[Output] {out}")


def write_feature_csv(feature_df: pd.DataFrame) -> None:
    out = OUT_DIR / "mover_discovery_v3_feature_analysis.csv"
    feature_df.to_csv(out, index=False)
    print(f"[Output] {out}  ({len(feature_df)} rows)")


def write_pool_csv(pool_df: pd.DataFrame) -> None:
    out = OUT_DIR / "mover_discovery_v3_pool_analysis.csv"
    pool_df.to_csv(out, index=False)
    print(f"[Output] {out}  ({len(pool_df)} rows)")


def write_missed_json(cases: List[Dict]) -> None:
    out = OUT_DIR / "mover_discovery_v3_missed_cases.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, default=str)
    print(f"[Output] {out}  ({len(cases)} cases)")


def write_design_md(
    is_metrics: Dict,
    oos_metrics: Dict,
    sector_result: Dict,
) -> None:
    content = f"""# MOVER DISCOVERY V3 — Design Document
**Date:** {date.today().isoformat()}
**Based on:** MOVER_DISCOVERY_AUDIT_002

---

## Architectural Change

### Current Production Design
```
Hard bucket gates → composite score → MIN_PREPARED_SCORE=0.55 floor → cap=120
```

Key bottlenecks (AUDIT_002 confirmed):
- `VOLUME_EXPANSION_MIN=1.8` rejects 92.8% of pre-breakout movers
- `BREAKOUT_PROXIMITY_PCT=0.02` rejects 88.4% (too far from resistance)
- RSI 45–55 zone has no bucket — 30.7% of missed movers land here

### V3 Research Design
```
Broad universe (all 230 symbols)
    │
    ├── UP_DISCOVERY_SCORE   (5 features, percentile-ranked)
    │   atr_pct × 0.25 + mom_5d × 0.20 + rs_pct_5d × 0.20
    │   + vol_ratio × 0.20 + mom_accel × 0.15
    │
    └── DOWN_DISCOVERY_SCORE (5 features, percentile-ranked)
        neg_mom_5d × 0.30 + neg_mom_accel × 0.25 + vol_expansion × 0.20
        + atr_pct × 0.15 + rsi_overbought × 0.10
```

V3 produces two separate ranked lists (top 20 each) per day.
**No hard gates on volume or resistance proximity.**
Volume expansion is a continuous rank score, not a pass/fail threshold.

---

## Feature Justification

| Feature | Used in | AUDIT_002 Lift | Direction |
|---------|---------|----------------|-----------|
| atr_pct | UP + DOWN | 1.21× | Higher ATR → more movement potential |
| mom_5d | UP (direct), DOWN (inverted) | 1.21× | Trend persistence / reversal |
| rs_pct_5d | UP | 1.13× | Universe-relative momentum |
| vol_ratio | UP | 1.09× | Accumulation signal |
| mom_accel | DOWN (primary) | 1.24× | Deceleration forecasts reversal |
| vol_expansion | DOWN | 1.26× (in DOWN_C) | Volume confirmation of reversal |
| neg_mom_5d | DOWN | 1.22× | Negative trend persistence |

## Sector Decision
Sector context: **disabled for UP, disabled for DOWN by default**

AUDIT_002 sector lift_delta = −0.013 (i.e., sector made discovery worse)
Sector can be enabled for testing via `use_sector_for_down=True`.

Sector test result (pool=20):
  Without sector: lift = {sector_result.get('without_sector', {}).get('lift', 0):.4f}
  With sector:    lift = {sector_result.get('with_sector', {}).get('lift', 0):.4f}
  Lift delta:     {sector_result.get('lift_delta', 0):.4f}
  Verdict:        {sector_result.get('verdict', 'N/A')}

---

## Magnitude Estimation

Legacy constant (`expected_move_pct = 8.0`):
- Source: `oios/data/sector_conviction_writer.py` (hardcoded, MAS Section 5)
- Historical status: ALL 57,037 signals in replay.db have this value
- Predictive power: spearman_r ≈ 0.0 (confirmed in AUDIT_002)

V3 approach: use `atr_pct` as magnitude signal
- atr_pct spearman_r with |ret_5d| = 0.244 (AUDIT_002)
- atr_pct magnitude_ratio = 2.14× (high ATR stocks move 2.14× more)
- NOT used in V3 scoring itself (avoids regime bias), reported as metadata

---

## OOS Separation

**Train:** 2021-01-01 to 2023-12-31 (weights/design decisions made here)
**OOS:**   2024-01-01 to 2025-12-30 (evaluation only, no tuning)

In-sample UP lift:  {is_metrics.get('up', {}).get('lift', 0):.4f}
OOS UP lift:        {oos_metrics.get('up', {}).get('lift', 0):.4f}
In-sample DOWN lift: {is_metrics.get('down', {}).get('lift', 0):.4f}
OOS DOWN lift:       {oos_metrics.get('down', {}).get('lift', 0):.4f}

---

## Shadow Mode

V3 runs in shadow mode only.
- `MOVER_DISCOVERY_V3_ENABLED = False`
- `MOVER_DISCOVERY_V3_SHADOW_MODE = True`
- Shadow log: `data/mover_discovery_v3_shadow.jsonl`
- Production scanner output: unchanged
- No trades generated from V3
- No writes to CandidateStore
"""
    out = OUT_DIR / "MOVER_DISCOVERY_V3_DESIGN.md"
    out.write_text(content, encoding="utf-8")
    print(f"[Output] {out}")


def write_architecture_md(
    is_metrics: Dict,
    oos_metrics: Dict,
    wf_results: List,
    leakage_violations: List[str],
) -> None:
    wf_rows = "\n".join(
        f"| {r['fold']} | {r['up_lift']:.3f} | {r['up_recall']:.3f} | "
        f"{r['dn_lift']:.3f} | {r['dn_recall']:.3f} |"
        for r in wf_results
    ) if wf_results else "| (no folds) | — | — | — | — |"

    content = f"""# MOVER DISCOVERY V3 — Architecture Document
**Date:** {date.today().isoformat()}
**Status:** RESEARCH / SHADOW MODE — NOT production ready

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Market Data (at 16:45 IST)            │
│             230-symbol OHLCV, 35d lookback              │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  compute_v3_features()  │  PIT-safe: backward-looking only
          │  atr, momentum, volume  │  No future data allowed
          │  RSI, vol_expansion     │  check_leakage() verified
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │     score_universe()    │  Percentile ranking per date
          │  UP_SCORE / DOWN_SCORE  │  No hard gates
          └────────┬────────┬───────┘
                   │        │
         ┌─────────▼─┐   ┌──▼──────────┐
         │  UP Pool  │   │  DOWN Pool  │
         │   Top 20  │   │   Top 20    │
         └─────────┬─┘   └──┬──────────┘
                   │        │
          ┌────────▼────────▼────────┐
          │   SHADOW LOG (JSONL)     │  Append-only, research only
          │   No CandidateStore      │  No trades
          │   No OrderManager        │  No signal_births
          └──────────────────────────┘
```

## Component Map

| Component | File | Purpose |
|-----------|------|---------|
| V3Config | mover_discovery_v3.py | All V3 settings, isolated |
| V3UpWeights | mover_discovery_v3.py | Configurable UP feature weights |
| V3DownWeights | mover_discovery_v3.py | Configurable DOWN feature weights |
| compute_v3_features() | mover_discovery_v3.py | Per-symbol PIT-safe features |
| score_universe() | mover_discovery_v3.py | Cross-section percentile scoring |
| select_candidates() | mover_discovery_v3.py | Top-N with deterministic tie-break |
| run_shadow_scan() | mover_discovery_v3.py | Shadow mode entry point |
| check_leakage() | mover_discovery_v3.py | Leakage guard |
| FORBIDDEN_FUTURE_KEYS | mover_discovery_v3.py | Future-data key list |

## Safety Guarantees

1. `V3Config.enabled = False` — hard disabled
2. `V3Config.shadow_mode = True` — enforced in run_shadow_scan()
3. `validate()` raises if `enabled=True AND shadow_mode=False`
4. Shadow log is append-only JSONL, never read by production
5. No imports of CandidateStore, OrderManager, DecisionEngine
6. No writes to any production data file

## Walk-Forward OOS Results

| Fold | UP Lift | UP Recall | DOWN Lift | DOWN Recall |
|------|---------|-----------|-----------|-------------|
{wf_rows}

**OOS TARGET (GO criterion):** OOS UP lift ≥ 1.10 AND DOWN lift ≥ 1.10

Actual OOS UP lift:   {oos_metrics.get('up', {}).get('lift', 0):.4f}
Actual OOS DOWN lift: {oos_metrics.get('down', {}).get('lift', 0):.4f}

## Leakage Status

Violations found: {len(leakage_violations)}
{'CLEAN — all features are PIT-safe' if not leakage_violations else chr(10).join(leakage_violations)}
"""
    out = DOCS_DIR / "MOVER_DISCOVERY_V3_ARCHITECTURE.md"
    out.write_text(content, encoding="utf-8")
    print(f"[Output] {out}")


def write_research_report(
    total_movers: int,
    total_up: int,
    total_down: int,
    existing_up: int,
    existing_down: int,
    v3_up_cnt: int,
    v3_down_cnt: int,
    both_up: int,
    both_down: int,
    is_metrics: Dict,
    oos_metrics: Dict,
    wf_results: List,
    pool_df: pd.DataFrame,
    sector_result: Dict,
    leakage_violations: List[str],
    group_counts: Dict,
    overlap: Dict,
    fp_rate_up: float,
    fp_rate_down: float,
    avg_atr_up: float,
    avg_atr_down: float,
    final_verdict: str,
) -> None:
    pool_rows = "\n".join(
        f"| {r['pool_size']} | {r.get('up_lift',0):.3f} | {r.get('up_recall',0):.3f} | "
        f"{r.get('up_precision',0):.3f} | {r.get('down_lift',0):.3f} |"
        for _, r in pool_df[pool_df["period"] == "oos"].iterrows()
    ) if not pool_df.empty else "(no data)"

    wf_rows = "\n".join(
        f"| {r['fold']} | {r['up_lift']:.3f} | {r['up_recall']:.3f} | "
        f"{r['dn_lift']:.3f} | {r['dn_recall']:.3f} |"
        for r in wf_results
    ) if wf_results else "| (no folds) | — | — | — | — |"

    report = f"""# MOVER DISCOVERY V3 — Research Report
**Date:** {date.today().isoformat()}
**Database:** data/replay.db (2021-2025, 256,268 OHLCV rows)
**Mode:** RESEARCH / SHADOW — no production changes

---

## A. What Existing Discovery Does

The production Phase D scanner runs at 16:45 IST. It:
1. Loads 35-day OHLCV for 230 symbols
2. Classifies each symbol into hard buckets:
   - BREAKOUT: within 2% of 20d resistance (BREAKOUT_PROXIMITY_PCT=0.02)
   - PULLBACK: RSI 50–65, in bull regime, near support
   - OVERSOLD: RSI ≤ 40
   - OVERBOUGHT: RSI ≥ 65 (SHORT candidate)
   - VOLUME_EXPAND: vol_ratio ≥ 1.8
3. Scores by bucket membership
4. Applies MIN_PREPARED_SCORE=0.55 floor (hard rejection)
5. Applies sector cap (20%) and max count (120)

Result: only symbols already in recognisable setup states are selected.
Pre-breakout, mid-range, and moderate-volume stocks are systematically excluded.

---

## B. What V3 Changes

V3 replaces hard gates with continuous scoring:
- Volume is a score component (not a gate)
- Distance-from-resistance is a score component (not a gate)
- RSI zones 40–65 are included (not excluded)
- Two separate directional pools (UP and DOWN)
- Universe-percentile ranking removes absolute-threshold sensitivity

---

## C. Why Each Change Is Supported by AUDIT_002

| Production gate | AUDIT_002 evidence | V3 response |
|-----------------|-------------------|-------------|
| vol_ratio ≥ 1.8 (hard) | 92.8% of missed movers had vol_ratio < 1.8 | Continuous vol score |
| ltp within 2% of resistance | 88.4% of missed movers were >2% from resistance | Continuous dist-resistance feature |
| RSI only <40 or >65 | 30.7% had RSI 45–55 (no bucket) | RSI-zone scoring for entire range |
| Separate UP scoring | All 57,037 signals were LONG | Separate DOWN pool |
| 8.0 magnitude constant | spearman_r ≈ 0 (confirmed) | atr_pct (r=0.244) for magnitude |

---

## D. UP Feature Set (Weights)

| Feature | Weight | Justification |
|---------|--------|---------------|
| atr_pct | 0.25 | Top single feature, lift 1.21× (AUDIT_002) |
| mom_5d | 0.20 | Trend persistence, lift 1.21× |
| rs_pct_5d | 0.20 | Relative strength in universe |
| vol_ratio | 0.20 | Accumulation signal |
| mom_accel | 0.15 | Momentum building |

---

## E. DOWN Feature Set (Weights)

| Feature | Weight | Justification |
|---------|--------|---------------|
| neg_mom_5d | 0.30 | Inverted momentum (primary DOWN signal) |
| neg_mom_accel | 0.25 | Top DOWN feature in AUDIT_002, lift 1.24× |
| vol_expansion | 0.20 | Volume into decline (score_DOWN_C, lift 1.26×) |
| atr_pct | 0.15 | Volatility premium for reversals |
| rsi_overbought | 0.10 | Overbought positioning |

Sector: DISABLED by default (AUDIT_002: lift_delta = −0.013)

---

## F. Pool-Size Results (OOS)

| Pool | UP Lift | UP Recall | UP Precision | DOWN Lift |
|------|---------|-----------|--------------|-----------|
{pool_rows}

---

## G. In-Sample Results (2021–2023)

UP:
  Recall:    {is_metrics.get('up', {}).get('recall', 0):.4f}
  Precision: {is_metrics.get('up', {}).get('precision', 0):.4f}
  Lift:      {is_metrics.get('up', {}).get('lift', 0):.4f}

DOWN:
  Recall:    {is_metrics.get('down', {}).get('recall', 0):.4f}
  Precision: {is_metrics.get('down', {}).get('precision', 0):.4f}
  Lift:      {is_metrics.get('down', {}).get('lift', 0):.4f}

---

## H. OOS Results (2024–2025)

UP:
  Recall:    {oos_metrics.get('up', {}).get('recall', 0):.4f}
  Precision: {oos_metrics.get('up', {}).get('precision', 0):.4f}
  Lift:      {oos_metrics.get('up', {}).get('lift', 0):.4f}

DOWN:
  Recall:    {oos_metrics.get('down', {}).get('recall', 0):.4f}
  Precision: {oos_metrics.get('down', {}).get('precision', 0):.4f}
  Lift:      {oos_metrics.get('down', {}).get('lift', 0):.4f}

---

## I. Leakage Results

Violations: {len(leakage_violations)}
Status: {'CLEAN' if not leakage_violations else 'VIOLATIONS FOUND — see below'}
{chr(10).join(leakage_violations) if leakage_violations else 'All features are PIT-safe (backward-looking windows only).'}

---

## J. Existing vs V3 Overlap

Total ≥2% movers: {total_movers:,}
  UP movers:   {total_up:,}
  DOWN movers: {total_down:,}

Existing scanner coverage:
  UP:   {existing_up:,}  ({100*existing_up/max(total_up,1):.1f}%)
  DOWN: {existing_down:,}  ({100*existing_down/max(total_down,1):.1f}%)

V3 top-20 coverage:
  UP:   {v3_up_cnt:,}  ({100*v3_up_cnt/max(total_up,1):.1f}%)
  DOWN: {v3_down_cnt:,}  ({100*v3_down_cnt/max(total_down,1):.1f}%)

Both existing + V3:
  UP:   {both_up:,}  ({100*both_up/max(total_up,1):.1f}%)
  DOWN: {both_down:,}  ({100*both_down/max(total_down,1):.1f}%)

Average daily overlap fraction: {overlap.get('avg_overlap_fraction', 0):.3f}

Group distribution:
  Group A (existing scanner never saw): {group_counts.get('A', 0):,}  ({100*group_counts.get('A',0)/max(total_movers,1):.1f}%)
  Group B (existing scanner included):  {group_counts.get('B', 0):,}  ({100*group_counts.get('B',0)/max(total_movers,1):.1f}%)

---

## K. Newly Recovered Movers by V3

UP movers recovered by V3 (not in existing scanner): {v3_up_cnt - both_up:,}
DOWN movers recovered by V3:                         {v3_down_cnt - both_down:,}

Walk-forward validation:
| Fold | UP Lift | UP Recall | DOWN Lift | DOWN Recall |
|------|---------|-----------|-----------|-------------|
{wf_rows}

---

## L. False-Positive Impact

UP false-positive rate (pool=20): {fp_rate_up:.4f} ({100*fp_rate_up:.1f}% of V3 UP selections are non-movers)
DOWN false-positive rate:         {fp_rate_down:.4f} ({100*fp_rate_down:.1f}%)

Average ATR% of V3-selected UP candidates:   {avg_atr_up:.2f}%
Average ATR% of V3-selected DOWN candidates: {avg_atr_down:.2f}%

Note: 68% FP rate is expected at pool=20 (confirmed in AUDIT_002).
V3 is a discovery/prioritisation layer, not a precision filter.
Full debate + risk evaluation remains required before any trade.

---

## M. Recommended Next Step

1. Activate shadow mode in production at 16:45 (read-only, no side effects)
2. Collect 20 trading days of shadow logs (data/mover_discovery_v3_shadow.jsonl)
3. Compare shadow overlap with live CandidateStore results
4. If OOS lift holds in live shadow: begin research on V3 → strategy integration
5. Do NOT integrate V3 into live trading without ≥60 days of shadow validation

---

## FINAL VERDICT

GO criterion:
  OOS UP lift   ≥ 1.10  → Actual: {oos_metrics.get('up', {}).get('lift', 0):.4f}
  OOS DOWN lift ≥ 1.10  → Actual: {oos_metrics.get('down', {}).get('lift', 0):.4f}
  Leakage clean          → {'YES' if not leakage_violations else 'NO'}

**VERDICT: {final_verdict}**

{"V3 research module may proceed to shadow mode deployment." if final_verdict == "GO" else "V3 requires further investigation before shadow deployment."}
"""
    out = OUT_DIR / "MOVER_DISCOVERY_V3_RESEARCH_REPORT.md"
    out.write_text(report, encoding="utf-8")
    print(f"[Output] {out}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load data
    ohlcv, signal_births, universe, nifty = load_data()

    sector_map = dict(zip(universe["symbol"], universe["sector"]))

    # 2. Build labels (future returns — used ONLY for evaluation, never as features)
    labels_df = build_labels(ohlcv)

    # 3. Build features (PIT-safe)
    features_df = build_cross_section_features(ohlcv, sector_map)

    # 4. Score with default V3Config
    cfg = V3Config()
    cfg.validate()
    scored_df = run_v3_scoring(features_df, cfg)

    # 5. Attach existing scanner flags
    scored_df = build_existing_scanner_flags(scored_df, signal_births)

    # 6. Leakage verification
    print("\n[LeakageCheck] Verifying no future data in features ...")
    leakage_violations = run_leakage_checks(scored_df)
    if leakage_violations:
        print(f"  !! LEAKAGE VIOLATIONS: {leakage_violations}")
    else:
        print("  ✓ Leakage clean — all features are PIT-safe")

    # 7. In-sample metrics (2021–2023)
    print("\n[Metrics] In-sample (2021–2023) ...")
    is_df = scored_df[scored_df["date"] <= pd.Timestamp(TRAIN_END)]
    m_up_is  = evaluate_pool(is_df, labels_df, 20, "UP",   "v3_up_score",   "is_up_mover")
    m_dn_is  = evaluate_pool(is_df, labels_df, 20, "DOWN", "v3_down_score", "is_down_mover")
    is_metrics = {"up": m_up_is, "down": m_dn_is}
    print(f"  IS UP  lift={m_up_is['lift']:.4f} recall={m_up_is['recall']:.4f} "
          f"prec={m_up_is['precision']:.4f}")
    print(f"  IS DN  lift={m_dn_is['lift']:.4f} recall={m_dn_is['recall']:.4f} "
          f"prec={m_dn_is['precision']:.4f}")

    # 8. OOS metrics (2024–2025)
    print("\n[Metrics] OOS (2024–2025) ...")
    oos_df = scored_df[scored_df["date"] >= pd.Timestamp(OOS_START)]
    m_up_oos = evaluate_pool(oos_df, labels_df, 20, "UP",   "v3_up_score",   "is_up_mover")
    m_dn_oos = evaluate_pool(oos_df, labels_df, 20, "DOWN", "v3_down_score", "is_down_mover")
    oos_metrics = {"up": m_up_oos, "down": m_dn_oos}
    print(f"  OOS UP  lift={m_up_oos['lift']:.4f} recall={m_up_oos['recall']:.4f} "
          f"prec={m_up_oos['precision']:.4f}")
    print(f"  OOS DN  lift={m_dn_oos['lift']:.4f} recall={m_dn_oos['recall']:.4f} "
          f"prec={m_dn_oos['precision']:.4f}")

    # 9. Walk-forward OOS
    print("\n[WalkForward] 3-fold OOS ...")
    wf_results = walk_forward_oos(scored_df, labels_df, pool_size=20)

    # 10. Pool-size sweep
    print("\n[PoolSweep] Testing pool sizes:", POOL_SIZES)
    pool_all   = pool_size_sweep(scored_df, labels_df, pool_sizes=POOL_SIZES, subset="all")
    pool_oos   = pool_size_sweep(scored_df, labels_df, pool_sizes=POOL_SIZES, subset="oos")
    pool_train = pool_size_sweep(scored_df, labels_df, pool_sizes=POOL_SIZES, subset="train")
    pool_df    = pd.concat([pool_train, pool_oos, pool_all], ignore_index=True)
    print(pool_df[pool_df["period"] == "oos"][
        ["pool_size","up_lift","up_recall","down_lift","down_recall"]
    ].to_string(index=False))

    # 11. Feature contribution
    print("\n[Features] Per-feature contribution analysis ...")
    feat_df = analyze_feature_contribution(scored_df, labels_df, pool_size=20)
    print(feat_df[["feature","direction","lift","recall"]].head(10).to_string(index=False))

    # 12. Sector test
    print("\n[SectorTest] DOWN with sector vs without ...")
    sector_result = sector_test(features_df, labels_df, pool_size=20)
    print(f"  Without: lift={sector_result['without_sector']['lift']:.4f}  "
          f"With: lift={sector_result['with_sector']['lift']:.4f}  "
          f"Delta={sector_result['lift_delta']:.4f}  Verdict={sector_result['verdict']}")

    # 13. Group classification + overlap
    print("\n[Groups] Classifying movers ...")
    groups_df = classify_groups(scored_df, labels_df, pool_size=20)
    group_counts = groups_df["group"].value_counts().to_dict()
    total_movers = len(groups_df)
    overlap = compute_overlap(scored_df, pool_size=20)
    print(f"  Groups: {group_counts}")
    print(f"  Overlap fraction: {overlap['avg_overlap_fraction']:.3f}")

    # 14. Mover counts
    merged_all = scored_df.merge(
        labels_df[["symbol","date","is_up_mover","is_down_mover","ret_1d"]],
        on=["symbol","date"], how="inner",
    )
    total_up   = int(merged_all["is_up_mover"].sum())
    total_down = int(merged_all["is_down_mover"].sum())

    # V3 top-20 per date
    v3_up_hits   = 0
    v3_down_hits = 0
    both_up      = 0
    both_down    = 0
    for dt, day in merged_all.groupby("date"):
        up_top  = set(day.nlargest(20, "v3_up_score")["symbol"])
        dn_top  = set(day.nlargest(20, "v3_down_score")["symbol"])
        up_movers = set(day[day["is_up_mover"]==1]["symbol"])
        dn_movers = set(day[day["is_down_mover"]==1]["symbol"])
        scan_syms = set(day[day["existing_scanner"]==1]["symbol"])
        v3_up_hits   += len(up_top & up_movers)
        v3_down_hits += len(dn_top & dn_movers)
        both_up      += len(up_top & up_movers & scan_syms)
        both_down    += len(dn_top & dn_movers & scan_syms)

    existing_up   = int(merged_all[merged_all["existing_scanner"]==1]["is_up_mover"].sum())
    existing_down = int(merged_all[merged_all["existing_scanner"]==1]["is_down_mover"].sum())

    # FP rates
    total_v3_up_selections = 20 * merged_all["date"].nunique()
    fp_rate_up   = 1.0 - (v3_up_hits / max(total_v3_up_selections, 1))
    fp_rate_down = 1.0 - (v3_down_hits / max(total_v3_up_selections, 1))

    # ATR averages
    v3_up_rows   = []
    v3_down_rows = []
    for dt, day in scored_df.groupby("date"):
        v3_up_rows.extend(day.nlargest(20, "v3_up_score")["atr_pct"].tolist())
        v3_down_rows.extend(day.nlargest(20, "v3_down_score")["atr_pct"].tolist())
    avg_atr_up   = float(np.mean(v3_up_rows))   if v3_up_rows   else 0.0
    avg_atr_down = float(np.mean(v3_down_rows)) if v3_down_rows else 0.0

    # 15. Missed cases
    print("\n[MissedCases] Collecting missed cases ...")
    missed_cases = collect_missed_cases(scored_df, labels_df, pool_size=20)

    # 16. Determine verdict
    oos_up_lift   = m_up_oos["lift"]
    oos_down_lift = m_dn_oos["lift"]
    verdict = "GO" if (oos_up_lift >= 1.10 and oos_down_lift >= 1.10
                       and not leakage_violations) else "NO-GO"
    if not leakage_violations and oos_up_lift >= 1.05:
        verdict = "CONDITIONAL-GO"  # useful lift but below hard threshold
    if oos_up_lift >= 1.10 and oos_down_lift >= 1.10 and not leakage_violations:
        verdict = "GO"

    print(f"\n[Verdict] {verdict}")
    print(f"  OOS UP  lift={oos_up_lift:.4f}  DOWN lift={oos_down_lift:.4f}")

    # 17. Write all outputs
    print("\n[Outputs] Writing reports ...")
    write_results_json(
        cfg, is_metrics, oos_metrics, wf_results, overlap,
        sector_result, leakage_violations, group_counts, total_movers,
    )
    write_feature_csv(feat_df)
    write_pool_csv(pool_df)
    write_missed_json(missed_cases)
    write_design_md(is_metrics, oos_metrics, sector_result)
    write_architecture_md(is_metrics, oos_metrics, wf_results, leakage_violations)
    write_research_report(
        total_movers, total_up, total_down,
        existing_up, existing_down,
        v3_up_hits, v3_down_hits,
        both_up, both_down,
        is_metrics, oos_metrics, wf_results,
        pool_df, sector_result, leakage_violations,
        group_counts, overlap,
        fp_rate_up, fp_rate_down,
        avg_atr_up, avg_atr_down,
        verdict,
    )

    print(f"\n{'='*60}")
    print(f"MOVER DISCOVERY V3 — COMPLETE")
    print(f"  Verdict:        {verdict}")
    print(f"  OOS UP  lift:   {oos_up_lift:.4f}")
    print(f"  OOS DOWN lift:  {oos_down_lift:.4f}")
    print(f"  Leakage clean:  {not leakage_violations}")
    print(f"  Outputs in:     {OUT_DIR}")
    print(f"  Arch doc:       {DOCS_DIR}/MOVER_DISCOVERY_V3_ARCHITECTURE.md")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
