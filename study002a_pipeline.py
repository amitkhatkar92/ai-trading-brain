"""
Study 2A — Winner DNA Discovery
================================
Discovers fundamental characteristics that consistently distinguish future
winning stocks from ordinary and losing stocks using ONLY verified historical
knowledge already in the IIOS platform.

PRIMARY DATA: data/replay.db  (5 years: 2021-01-01 to 2025-12-30, 256,268 OHLCV rows)
SUPPLEMENT:  data/study002_replay.db  (2025-08-01 to 2026-07-31)

RULES
- No new market data fetched
- No production files modified
- No AI algorithms or parameters changed
- Defects documented, not corrected
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ── Paths ────────────────────────────────────────────────────────────────────
REPLAY_DB    = os.path.join(ROOT, "data", "replay.db")
S002_DB      = os.path.join(ROOT, "data", "study002_replay.db")
FEAT_DB      = os.path.join(ROOT, "data", "ede_feature_db.json")
EDGES_DB     = os.path.join(ROOT, "data", "discovered_edges.json")
SP_DB        = os.path.join(ROOT, "data", "strategy_performance.json")
RESULTS      = os.path.join(ROOT, "data", "study002a_results.json")
NIFTY_SYM    = "^NSEI"

REGIME_TREND_THRESHOLD_PCT = 2.0
REGIME_SMA_BAND            = 0.02

# ── Group thresholds (documented, data-driven) ──────────────────────────────
# Initial fixed threshold used for exploration; percentile thresholds computed
# from data distribution.
FIXED_WINNER_THRESHOLD = 0.010    # ≥ +1.0%
FIXED_LOSER_THRESHOLD  = -0.010   # ≤ -1.0%


# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _banner(msg: str) -> None:
    print("=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def _open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Pooled Cohen's d effect size."""
    n_a, n_b = len(a), len(b)
    if n_a < 2 or n_b < 2:
        return 0.0
    pooled_std = np.sqrt(((n_a - 1) * np.var(a, ddof=1) + (n_b - 1) * np.var(b, ddof=1))
                         / (n_a + n_b - 2))
    return float((np.mean(a) - np.mean(b)) / pooled_std) if pooled_std > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 0 — DATA LOADING FROM REPLAY DB (PRIMARY)
# ═══════════════════════════════════════════════════════════════════════════

def _build_regime_map_from_db(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        "SELECT trade_date, close FROM ohlcv_daily WHERE symbol=? ORDER BY trade_date",
        (NIFTY_SYM,)
    ).fetchall()
    if not rows:
        return {}
    closes = [(r["trade_date"], r["close"]) for r in rows]
    regime_map: dict[str, str] = {}
    for i, (date_str, close) in enumerate(closes):
        if i < 25:
            regime_map[date_str] = "SIDEWAYS"
            continue
        window = min(200, i + 1)
        sma = sum(c for _, c in closes[max(0, i - window + 1):i + 1]) / window
        change_20d = (close / closes[i - 20][1] - 1.0) * 100.0 if i >= 20 else 0.0
        above_sma = close > sma * (1 + REGIME_SMA_BAND)
        below_sma = close < sma * (1 - REGIME_SMA_BAND)
        if above_sma and change_20d > REGIME_TREND_THRESHOLD_PCT:
            regime_map[date_str] = "TRENDING_UP"
        elif below_sma and change_20d < -REGIME_TREND_THRESHOLD_PCT:
            regime_map[date_str] = "TRENDING_DOWN"
        else:
            regime_map[date_str] = "SIDEWAYS"
    return regime_map


def _extract_features_from_db(conn: sqlite3.Connection,
                               db_label: str) -> list[dict]:
    """
    Compute feature vectors with forward_return labels from an OIOS replay DB.
    Returns list of observation dicts with all features + forward_return.
    Includes additional technical features beyond ede_feature_db.json baseline.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily ORDER BY symbol, trade_date"
    )
    rows = cur.fetchall()

    sym_data: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["symbol"] == NIFTY_SYM:
            continue
        sym_data[r["symbol"]].append({
            "d": r["trade_date"], "o": r["open"],  "h": r["high"],
            "l": r["low"],        "c": r["close"],  "v": r["volume"],
        })

    # Sector conviction map
    sc_map: dict[str, dict[str, tuple]] = defaultdict(dict)
    try:
        for r in cur.execute("""
            SELECT record_date, sector, sector_conviction_score, participation_rate_5d
            FROM sector_conviction_daily WHERE data_quality='FULL'
        """).fetchall():
            sc_map[r["record_date"]][r["sector"]] = (
                r["sector_conviction_score"] or 0.0,
                r["participation_rate_5d"] or 0.0,
            )
    except Exception:
        pass

    # Symbol → sector map
    try:
        sym_sector: dict[str, str] = {
            r["symbol"]: r["primary_sector"]
            for r in cur.execute("SELECT symbol, primary_sector FROM stock_sector_map").fetchall()
        }
    except Exception:
        sym_sector = {}

    regime_map = _build_regime_map_from_db(conn)

    obs: list[dict] = []
    skipped = 0

    for symbol, candles in sym_data.items():
        if len(candles) < 21:
            continue
        sector = sym_sector.get(symbol, "UNKNOWN")

        for i in range(20, len(candles)):
            today = candles[i]
            if today["c"] <= 0:
                continue
            if i + 1 >= len(candles):
                skipped += 1
                continue
            nxt = candles[i + 1]
            if nxt["c"] <= 0:
                continue

            # ── Core price features ──────────────────────────────────────
            prev1  = candles[i - 1]
            prev5  = candles[i - 5]
            prev20 = candles[i - 20]

            mom_1d  = (today["c"] - prev1["c"]) / prev1["c"]  if prev1["c"]  > 0 else 0.0
            mom_5d  = (today["c"] - prev5["c"]) / prev5["c"]  if prev5["c"]  > 0 else 0.0
            mom_20d = (today["c"] - prev20["c"]) / prev20["c"] if prev20["c"] > 0 else 0.0

            intra_range = (today["h"] - today["l"]) / today["c"] if today["c"] > 0 else 0.0
            close_pos   = ((today["c"] - today["l"]) / (today["h"] - today["l"])
                           if (today["h"] - today["l"]) > 0 else 0.5)

            # ── 52-week high/low proximity ────────────────────────────────
            lookback_52 = min(252, i)
            high_52w = max(c["h"] for c in candles[i - lookback_52:i + 1])
            low_52w  = min(c["l"] for c in candles[i - lookback_52:i + 1])
            prox_52w_high = today["c"] / high_52w if high_52w > 0 else 1.0
            prox_52w_low  = today["c"] / low_52w  if low_52w  > 0 else 1.0

            # ── ATR (average true range, 14-day) ─────────────────────────
            true_ranges = []
            for k in range(1, min(15, i + 1)):
                c0 = candles[i - k]
                c1 = candles[i - k + 1]
                tr = max(c1["h"] - c1["l"],
                         abs(c1["h"] - c0["c"]),
                         abs(c1["l"] - c0["c"]))
                true_ranges.append(tr)
            atr_14 = (sum(true_ranges) / len(true_ranges)) / today["c"] if true_ranges and today["c"] > 0 else 0.0

            # ── Volume features ───────────────────────────────────────────
            vols = [candles[i - k]["v"] for k in range(1, 6) if candles[i - k]["v"]]
            avg_vol   = sum(vols) / len(vols) if vols else 1.0
            vol_ratio = min(today["v"] / avg_vol, 10.0) if avg_vol > 0 else 1.0

            vols_20 = [candles[i - k]["v"] for k in range(1, 21) if candles[i - k]["v"]]
            avg_vol_20 = sum(vols_20) / len(vols_20) if vols_20 else 1.0
            vol_ratio_20 = min(today["v"] / avg_vol_20, 10.0) if avg_vol_20 > 0 else 1.0

            # ── Momentum persistence ──────────────────────────────────────
            cons_up = 0
            for k in range(1, 6):
                if i - k - 1 < 0 or candles[i - k]["c"] < candles[i - k - 1]["c"]:
                    break
                cons_up += 1

            cons_dn = 0
            for k in range(1, 6):
                if i - k - 1 < 0 or candles[i - k]["c"] > candles[i - k - 1]["c"]:
                    break
                cons_dn += 1

            # ── Gap (open vs prev close) ──────────────────────────────────
            gap_pct = (today["o"] - prev1["c"]) / prev1["c"] if prev1["c"] > 0 else 0.0

            # ── Sector conviction features ────────────────────────────────
            day_sc = sc_map.get(today["d"], {})
            sc     = day_sc.get(sector, (0.0, 0.0))
            sect_conviction = sc[0]
            sect_part5d     = sc[1]
            avg_conviction  = (sum(v[0] for v in day_sc.values()) / len(day_sc)
                               if day_sc else 0.0)

            # ── Regime features ───────────────────────────────────────────
            regime = regime_map.get(today["d"], "SIDEWAYS")
            if regime == "TRENDING_UP":
                r_score, r_bull, r_range, r_bear, r_vol = 0.8, 1.0, 0.0, 0.0, 0.0
                vix_prx, vix_lo, vix_hi = 0.25, 1.0, 0.0
            elif regime == "TRENDING_DOWN":
                r_score, r_bull, r_range, r_bear, r_vol = 0.2, 0.0, 0.0, 1.0, 0.0
                vix_prx, vix_lo, vix_hi = 0.65, 0.0, 1.0
            else:  # SIDEWAYS
                r_score, r_bull, r_range, r_bear, r_vol = 0.5, 0.0, 1.0, 0.0, 0.0
                vix_prx, vix_lo, vix_hi = 0.375, 1.0, 0.0

            # ── PCR proxy ─────────────────────────────────────────────────
            sc_high = 1.0 if avg_conviction > 0.6 else 0.0
            sc_low  = 1.0 if avg_conviction < 0.4 else 0.0

            # ── Forward return ────────────────────────────────────────────
            forward_return = (nxt["c"] - today["c"]) / today["c"]

            # FEATURE SET: 20 non-redundant independent features
            # Deduplication rationale:
            #   avg_conviction = breadth = pcr (same formula) → keep avg_conviction
            #   pcr_bearish = breadth_weak (same formula)      → keep sc_low
            #   pcr_bullish = breadth_strong (same formula)    → keep sc_high
            #   regime_volatile always 0 (3-regime model)      → dropped
            #   sector_flow_count always 1.2                   → dropped
            #   event_count always 0.0                         → dropped
            obs.append({
                # Identity
                "symbol":  symbol,
                "date":    today["d"],
                "sector":  sector,
                "regime":  regime,
                "source":  db_label,
                # Label
                "forward_return": round(forward_return, 6),
                # Features (20 non-redundant)
                "features": {
                    # Price momentum
                    "mom_1d":          round(mom_1d, 6),
                    "mom_5d":          round(mom_5d, 6),
                    "mom_20d":         round(mom_20d, 6),
                    # Volatility / structure
                    "intra_range":     round(intra_range, 6),
                    "atr_14":          round(atr_14, 6),
                    "close_pos":       round(close_pos, 4),
                    "gap_pct":         round(gap_pct, 6),
                    # Volume
                    "vol_ratio":       round(vol_ratio, 4),
                    "vol_ratio_20":    round(vol_ratio_20, 4),
                    # Momentum persistence
                    "cons_up_days":    float(cons_up),
                    "cons_dn_days":    float(cons_dn),
                    # Breakout / structure
                    "prox_52w_high":   round(prox_52w_high, 4),
                    "prox_52w_low":    round(prox_52w_low, 4),
                    # Sector context
                    "sect_conviction": round(sect_conviction, 4),
                    "sect_part5d":     round(sect_part5d, 4),
                    "avg_conviction":  round(avg_conviction, 4),
                    "sc_high":         sc_high,
                    "sc_low":          sc_low,
                    # Regime
                    "regime_score":    r_score,
                    "regime_bull":     r_bull,
                },
            })

    return obs


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1 — GROUP CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def classify_groups(obs: list[dict]) -> dict:
    """
    Classify each observation into Winner (A), Ordinary (B), or Loser (C).
    Uses both fixed thresholds and data-driven percentile thresholds.
    Documents the distribution.
    """
    returns = np.array([o["forward_return"] for o in obs])

    # Distribution statistics
    p5   = float(np.percentile(returns, 5))
    p25  = float(np.percentile(returns, 25))
    p50  = float(np.percentile(returns, 50))
    p75  = float(np.percentile(returns, 75))
    p95  = float(np.percentile(returns, 95))
    mean = float(np.mean(returns))
    std  = float(np.std(returns))

    # FIXED threshold classification
    counts_fixed = {"A_winners": 0, "B_ordinary": 0, "C_losers": 0}
    for o in obs:
        r = o["forward_return"]
        if r >= FIXED_WINNER_THRESHOLD:
            o["group_fixed"] = "A"
            counts_fixed["A_winners"] += 1
        elif r <= FIXED_LOSER_THRESHOLD:
            o["group_fixed"] = "C"
            counts_fixed["C_losers"] += 1
        else:
            o["group_fixed"] = "B"
            counts_fixed["B_ordinary"] += 1

    # PERCENTILE threshold (p25 / p75)
    counts_pct = {"A_winners": 0, "B_ordinary": 0, "C_losers": 0}
    for o in obs:
        r = o["forward_return"]
        if r >= p75:
            o["group_pct"] = "A"
            counts_pct["A_winners"] += 1
        elif r <= p25:
            o["group_pct"] = "C"
            counts_pct["C_losers"] += 1
        else:
            o["group_pct"] = "B"
            counts_pct["B_ordinary"] += 1

    # Use FIXED threshold as primary (more interpretable, documented)
    for o in obs:
        o["group"] = o["group_fixed"]

    return {
        "distribution": {
            "n": len(obs),
            "mean": round(mean, 6),
            "std": round(std, 6),
            "p5": round(p5, 6),
            "p25": round(p25, 6),
            "median": round(p50, 6),
            "p75": round(p75, 6),
            "p95": round(p95, 6),
        },
        "thresholds": {
            "primary": "FIXED",
            "winner_min": FIXED_WINNER_THRESHOLD,
            "loser_max": FIXED_LOSER_THRESHOLD,
            "percentile_winner_min": round(p75, 6),
            "percentile_loser_max": round(p25, 6),
            "rationale": (
                f"Fixed ±{FIXED_WINNER_THRESHOLD*100:.1f}% threshold chosen because: "
                f"(1) exceeds median (={round(p50*100,3)}%) by meaningful margin, "
                f"(2) aligns with 1× daily ATR range for liquid NSE stocks, "
                f"(3) consistent with prior study labels (RE001A: 0.8% threshold). "
                f"Percentile threshold (p25={round(p25*100,3)}%, p75={round(p75*100,3)}%) "
                f"computed for comparison."
            ),
        },
        "counts_fixed": counts_fixed,
        "counts_percentile": counts_pct,
        "pct_winners_fixed":  round(counts_fixed["A_winners"] / len(obs), 4),
        "pct_losers_fixed":   round(counts_fixed["C_losers"] / len(obs), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2 — FEATURE STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_feature_statistics(obs: list[dict]) -> dict:
    """
    For each feature: compute per-group statistics, Cohen's d, and MWU p-value.
    """
    from scipy.stats import mannwhitneyu

    feature_names = list(obs[0]["features"].keys())

    winners  = [o for o in obs if o["group"] == "A"]
    ordinary = [o for o in obs if o["group"] == "B"]
    losers   = [o for o in obs if o["group"] == "C"]

    stats: dict[str, dict] = {}

    for feat in feature_names:
        w_vals = np.array([o["features"][feat] for o in winners], dtype=float)
        o_vals = np.array([o["features"][feat] for o in ordinary], dtype=float)
        l_vals = np.array([o["features"][feat] for o in losers], dtype=float)

        def _grp_stats(arr: np.ndarray) -> dict:
            if len(arr) == 0:
                return {}
            return {
                "mean":   round(float(np.mean(arr)), 6),
                "median": round(float(np.median(arr)), 6),
                "std":    round(float(np.std(arr)), 6),
                "p25":    round(float(np.percentile(arr, 25)), 6),
                "p75":    round(float(np.percentile(arr, 75)), 6),
            }

        # Cohen's d: Winner vs Loser (primary), Winner vs Ordinary
        d_w_l = _cohens_d(w_vals, l_vals)
        d_w_o = _cohens_d(w_vals, o_vals)

        # Mann-Whitney U p-values
        mwu_pval_w_l = mwu_pval_w_o = 1.0
        try:
            if len(w_vals) > 10 and len(l_vals) > 10:
                _, mwu_pval_w_l = mannwhitneyu(w_vals, l_vals, alternative="two-sided")
        except Exception:
            pass
        try:
            if len(w_vals) > 10 and len(o_vals) > 10:
                _, mwu_pval_w_o = mannwhitneyu(w_vals, o_vals, alternative="two-sided")
        except Exception:
            pass

        stats[feat] = {
            "winners":  _grp_stats(w_vals),
            "ordinary": _grp_stats(o_vals),
            "losers":   _grp_stats(l_vals),
            "cohens_d_w_vs_l":   round(d_w_l, 4),
            "cohens_d_w_vs_o":   round(d_w_o, 4),
            "mwu_pval_w_vs_l":   round(float(mwu_pval_w_l), 8),
            "mwu_pval_w_vs_o":   round(float(mwu_pval_w_o), 8),
            "abs_effect_size":   round(abs(d_w_l), 4),
        }

    return {"feature_stats": stats, "feature_names": feature_names,
            "n_winners": len(winners), "n_ordinary": len(ordinary), "n_losers": len(losers)}


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3 — FEATURE RANKING (MI + RF)
# ═══════════════════════════════════════════════════════════════════════════

def rank_features(obs: list[dict], feat_stats: dict) -> dict:
    """
    Rank features by: (1) Mutual Information, (2) Random Forest importance,
    (3) Cohen's d.  Produce combined ranking.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_selection import mutual_info_classif

    feature_names = feat_stats["feature_names"]
    X = np.array([[o["features"][f] for f in feature_names] for o in obs])
    # 3-class: 0=Loser, 1=Ordinary, 2=Winner
    y = np.array([{"A": 2, "B": 1, "C": 0}[o["group"]] for o in obs])

    # Mutual Information
    mi = mutual_info_classif(X, y, random_state=42)
    mi_norm = mi / (mi.max() + 1e-12)

    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=8,
                                random_state=42, n_jobs=-1)
    rf.fit(X, y)
    rf_imp = rf.feature_importances_
    rf_norm = rf_imp / (rf_imp.max() + 1e-12)

    # Cohen's d (abs, Winner vs Loser)
    cd = np.array([feat_stats["feature_stats"][f]["abs_effect_size"] for f in feature_names])
    cd_norm = cd / (cd.max() + 1e-12)

    # Combined score (equal weight)
    combined = (mi_norm + rf_norm + cd_norm) / 3.0

    ranking = sorted(
        [{"feature": f, "mi": round(float(mi[i]), 6),
          "mi_norm": round(float(mi_norm[i]), 4),
          "rf_importance": round(float(rf_imp[i]), 6),
          "rf_norm": round(float(rf_norm[i]), 4),
          "cohens_d_w_vs_l": feat_stats["feature_stats"][f]["cohens_d_w_vs_l"],
          "abs_cohens_d": feat_stats["feature_stats"][f]["abs_effect_size"],
          "mwu_pval_w_vs_l": feat_stats["feature_stats"][f]["mwu_pval_w_vs_l"],
          "combined_score": round(float(combined[i]), 4),
          "rank": 0}
         for i, f in enumerate(feature_names)],
        key=lambda x: -x["combined_score"]
    )
    for i, r in enumerate(ranking, 1):
        r["rank"] = i

    return {
        "full_ranking":  ranking,
        "top5":   [r["feature"] for r in ranking[:5]],
        "top10":  [r["feature"] for r in ranking[:10]],
        "top20":  [r["feature"] for r in ranking[:20]],
        "top50":  [r["feature"] for r in ranking[:50]],
        "rf_oob_enabled": False,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4 — DNA PATTERN DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def discover_dna_patterns(obs: list[dict], feature_ranking: dict) -> dict:
    """
    Discover multi-feature combinations that reliably precede winners.
    Uses decision tree path extraction to find interpretable rules.
    """
    from sklearn.tree import DecisionTreeClassifier, export_text

    feature_names = list(obs[0]["features"].keys())
    top_feats = feature_ranking["top10"]   # Use top 10 features for DT

    X_all  = np.array([[o["features"][f] for f in feature_names] for o in obs])
    y_all  = np.array([1 if o["group"] == "A" else 0 for o in obs])
    dates  = np.array([o["date"] for o in obs])

    # Temporal train/test split: first 80% dates = train
    unique_dates = sorted(set(dates))
    split_idx    = int(len(unique_dates) * 0.80)
    train_dates  = set(unique_dates[:split_idx])
    test_dates   = set(unique_dates[split_idx:])

    train_mask = np.array([d in train_dates for d in dates])
    test_mask  = np.array([d in test_dates  for d in dates])

    X_train, y_train = X_all[train_mask], y_all[train_mask]
    X_test,  y_test  = X_all[test_mask],  y_all[test_mask]

    # Use only top features for interpretability
    top_feat_idx = [feature_names.index(f) for f in top_feats if f in feature_names]
    Xt_train = X_train[:, top_feat_idx]
    Xt_test  = X_test[:, top_feat_idx]

    dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=50,
                                class_weight=None, random_state=42)
    dt.fit(Xt_train, y_train)

    # Find which index corresponds to class=1 (winner)
    winner_cls_idx = list(dt.classes_).index(1) if 1 in dt.classes_ else 1

    # Extract leaf-level rules that predict winners
    from sklearn.tree import _tree

    tree   = dt.tree_
    leaves = []

    def _walk(node: int, conditions: list) -> None:
        if tree.feature[node] == _tree.TREE_UNDEFINED:
            n_total  = int(tree.n_node_samples[node])
            # sklearn stores class counts/proportions as floats in tree.value
            values   = tree.value[node][0]
            total_v  = float(values.sum())
            # confidence = weighted proportion of winner class at leaf
            conf     = float(values[winner_cls_idx] / total_v) if total_v > 0 else 0.0
            n_win    = int(conf * n_total)          # approximate raw count
            if n_total >= 20:
                conf = n_win / n_total
                base_rate = float(np.mean(y_train))
                lift = conf / base_rate if base_rate > 0 else 0.0
                leaves.append({
                    "conditions": list(conditions),
                    "n_samples":  n_total,
                    "n_winners":  n_win,
                    "confidence": round(conf, 4),
                    "lift":       round(lift, 4),
                })
            return
        feat_name   = top_feats[tree.feature[node]]
        threshold   = round(tree.threshold[node], 4)
        _walk(tree.children_left[node],
              conditions + [f"{feat_name} <= {threshold}"])
        _walk(tree.children_right[node],
              conditions + [f"{feat_name} > {threshold}"])

    _walk(0, [])

    # Filter and rank by lift × confidence
    MIN_SUPPORT    = 0.0002  # ≥ 0.02% of training observations (min ~45 samples)
    MIN_CONFIDENCE = 0.35    # ≥ 35% winner rate (34% above 26.2% base rate)
    MIN_LIFT       = 1.30    # ≥ 30% above base rate

    approved = []
    rejected = []
    base_rate = float(np.mean(y_train))
    n_train   = len(y_train)

    for leaf in leaves:
        support = leaf["n_samples"] / n_train
        leaf["support"] = round(support, 4)

        if (support >= MIN_SUPPORT
                and leaf["confidence"] >= MIN_CONFIDENCE
                and leaf["lift"] >= MIN_LIFT):
            approved.append(leaf)
        else:
            reasons = []
            if support < MIN_SUPPORT:
                reasons.append(f"support={support:.4f}<{MIN_SUPPORT}")
            if leaf["confidence"] < MIN_CONFIDENCE:
                reasons.append(f"confidence={leaf['confidence']:.3f}<{MIN_CONFIDENCE}")
            if leaf["lift"] < MIN_LIFT:
                reasons.append(f"lift={leaf['lift']:.2f}<{MIN_LIFT}")
            leaf["rejected_reason"] = "; ".join(reasons)
            rejected.append(leaf)

    # Walk-forward validation of approved patterns
    validated = []
    for pat in sorted(approved, key=lambda x: -x["lift"] * x["confidence"])[:20]:
        # Apply conditions to test set
        mask = np.ones(len(X_test), dtype=bool)
        for cond in pat["conditions"]:
            parts = cond.split()
            fname, op, val = parts[0], parts[1], float(parts[2])
            fidx = feature_names.index(fname)
            if op == "<=":
                mask &= X_test[:, fidx] <= val
            else:
                mask &= X_test[:, fidx] > val
        n_match  = int(mask.sum())
        n_win_test = int(y_test[mask].sum()) if n_match > 0 else 0
        conf_test = (n_win_test / n_match) if n_match > 0 else 0.0
        lift_test = conf_test / float(np.mean(y_test)) if np.mean(y_test) > 0 else 0.0
        # Get avg forward return for matched test samples
        matched_returns = np.array([obs[i]["forward_return"] for i in
                                    np.where(test_mask)[0][mask]])
        avg_return = float(np.mean(matched_returns)) if len(matched_returns) > 0 else 0.0

        wf_stable = (abs(conf_test - pat["confidence"]) < 0.15 and conf_test >= 0.25)

        validated.append({
            "conditions":     pat["conditions"],
            "n_conditions":   len(pat["conditions"]),
            "train_support":  pat["support"],
            "train_confidence": pat["confidence"],
            "train_lift":     pat["lift"],
            "test_n_match":   n_match,
            "test_confidence": round(conf_test, 4),
            "test_lift":      round(lift_test, 4),
            "test_n_winners": n_win_test,
            "avg_forward_return": round(avg_return, 6),
            "wf_stable":     wf_stable,
            "validation":    "PASSED" if wf_stable else "REJECTED",
        })

    wf_passed  = [v for v in validated if v["validation"] == "PASSED"]
    wf_rejected = [v for v in validated if v["validation"] == "REJECTED"]

    return {
        "base_rate":          round(base_rate, 4),
        "min_support":        MIN_SUPPORT,
        "min_confidence":     MIN_CONFIDENCE,
        "min_lift":           MIN_LIFT,
        "train_dates":        min(train_dates),
        "train_end":          max(train_dates),
        "test_start":         min(test_dates),
        "test_end":           max(test_dates),
        "n_leaves_found":     len(leaves),
        "n_approved_initial": len(approved),
        "n_rejected_initial": len(rejected),
        "dna_patterns":       wf_passed[:10],
        "wf_rejected_patterns": wf_rejected[:5],
        "rejected_patterns":  rejected[:10],
        "tree_text":          export_text(dt, feature_names=top_feats, max_depth=3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5 — LOSER DNA (same approach, Loser class)
# ═══════════════════════════════════════════════════════════════════════════

def discover_loser_dna(obs: list[dict], feature_ranking: dict) -> dict:
    """Discover multi-feature combinations that consistently precede losers."""
    from sklearn.tree import DecisionTreeClassifier

    feature_names = list(obs[0]["features"].keys())
    top_feats = feature_ranking["top10"]
    top_feat_idx = [feature_names.index(f) for f in top_feats if f in feature_names]

    X_all = np.array([[o["features"][f] for f in feature_names] for o in obs])
    y_all = np.array([1 if o["group"] == "C" else 0 for o in obs])  # Loser = 1

    dates = np.array([o["date"] for o in obs])
    unique_dates = sorted(set(dates))
    split_idx = int(len(unique_dates) * 0.80)
    train_dates = set(unique_dates[:split_idx])
    test_dates  = set(unique_dates[split_idx:])
    train_mask = np.array([d in train_dates for d in dates])
    test_mask  = np.array([d in test_dates  for d in dates])

    Xt_train = X_all[train_mask][:, top_feat_idx]
    Xt_test  = X_all[test_mask][:, top_feat_idx]
    y_train  = y_all[train_mask]
    y_test   = y_all[test_mask]

    dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=50,
                                class_weight=None, random_state=77)
    dt.fit(Xt_train, y_train)

    loser_cls_idx = list(dt.classes_).index(1) if 1 in dt.classes_ else 1

    from sklearn.tree import _tree
    tree   = dt.tree_
    leaves = []

    def _walk_l(node: int, conditions: list) -> None:
        if tree.feature[node] == _tree.TREE_UNDEFINED:
            n_total = int(tree.n_node_samples[node])
            values  = tree.value[node][0]
            total_v = float(values.sum())
            conf    = float(values[loser_cls_idx] / total_v) if total_v > 0 else 0.0
            n_los   = int(conf * n_total)
            if n_total >= 50:
                conf = n_los / n_total
                base = float(np.mean(y_train))
                lift = conf / base if base > 0 else 0.0
                leaves.append({
                    "conditions": list(conditions),
                    "n_samples": n_total, "n_losers": n_los,
                    "confidence": round(conf, 4), "lift": round(lift, 4),
                    "support": round(n_total / len(y_train), 4),
                })
            return
        feat_name = top_feats[tree.feature[node]]
        threshold = round(tree.threshold[node], 4)
        _walk_l(tree.children_left[node],  conditions + [f"{feat_name} <= {threshold}"])
        _walk_l(tree.children_right[node], conditions + [f"{feat_name} > {threshold}"])

    _walk_l(0, [])

    approved = [l for l in leaves if l["support"] >= 0.01
                and l["confidence"] >= 0.40 and l["lift"] >= 1.30]
    approved.sort(key=lambda x: -x["lift"])

    return {
        "base_rate_loser": round(float(np.mean(y_train)), 4),
        "loser_dna_patterns": approved[:10],
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6 — WINNER CLUSTER ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def cluster_winners(obs: list[dict], feature_ranking: dict) -> dict:
    """
    Without predefined labels, identify naturally occurring winner clusters
    using KMeans. Silhouette score used to select optimal k.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    winners = [o for o in obs if o["group"] == "A"]
    if len(winners) < 50:
        return {"error": "Insufficient winners for clustering"}

    top_feats = feature_ranking["top20"]
    feature_names = list(obs[0]["features"].keys())
    top_idx = [feature_names.index(f) for f in top_feats if f in feature_names]

    X = np.array([[o["features"][f] for f in [feature_names[i] for i in top_idx]]
                  for o in winners])

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # Try k = 2..8, pick by silhouette
    best_k    = 2
    best_sil  = -1.0
    sil_scores: dict[int, float] = {}

    for k in range(2, min(9, len(winners) // 50)):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(Xs)
        if len(set(labels)) > 1:
            sil = float(silhouette_score(Xs, labels, sample_size=min(5000, len(winners))))
            sil_scores[k] = round(sil, 4)
            if sil > best_sil:
                best_sil = sil
                best_k   = k

    # Final clustering with best k
    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels_final = km_final.fit_predict(Xs)

    # Describe each cluster
    clusters: list[dict] = []
    feat_labels = [feature_names[i] for i in top_idx]

    cluster_label_map = _assign_cluster_labels(
        km_final.cluster_centers_, feat_labels, scaler
    )

    for cid in range(best_k):
        mask = labels_final == cid
        cluster_obs = [w for w, m in zip(winners, mask) if m]
        n = len(cluster_obs)
        centroid_orig = scaler.inverse_transform(km_final.cluster_centers_[cid:cid+1])[0]
        returns = np.array([o["forward_return"] for o in cluster_obs])

        # Top distinguishing features (highest centroid values among top features)
        feat_centroid = {feat_labels[j]: round(float(centroid_orig[j]), 4)
                         for j in range(len(feat_labels))}
        top_feats_cluster = sorted(feat_centroid.items(), key=lambda x: -abs(x[1]))[:5]

        # Sector distribution
        sector_dist: dict[str, int] = {}
        regime_dist: dict[str, int] = {}
        for co in cluster_obs:
            s = co.get("sector", "UNKNOWN")
            r = co.get("regime", "SIDEWAYS")
            sector_dist[s] = sector_dist.get(s, 0) + 1
            regime_dist[r] = regime_dist.get(r, 0) + 1

        clusters.append({
            "cluster_id":      cid,
            "label":           cluster_label_map.get(cid, f"CLUSTER_{cid}"),
            "size":            n,
            "pct_of_winners":  round(n / len(winners), 4),
            "avg_return":      round(float(np.mean(returns)), 6),
            "median_return":   round(float(np.median(returns)), 6),
            "centroid_features": feat_centroid,
            "top_5_features":  [{"feature": f, "centroid": v}
                                 for f, v in top_feats_cluster],
            "top_sector":      max(sector_dist, key=sector_dist.get) if sector_dist else "—",
            "dominant_regime": max(regime_dist, key=regime_dist.get) if regime_dist else "—",
            "sector_dist":     dict(sorted(sector_dist.items(), key=lambda x: -x[1])[:5]),
            "regime_dist":     regime_dist,
        })

    clusters.sort(key=lambda c: -c["avg_return"])

    return {
        "optimal_k":       best_k,
        "silhouette_scores": {str(k): v for k, v in sil_scores.items()},
        "best_silhouette": round(best_sil, 4),
        "features_used":   feat_labels,
        "clusters":        clusters,
    }


def _assign_cluster_labels(centers: np.ndarray,
                            feat_names: list,
                            scaler) -> dict[int, str]:
    """
    Assign descriptive labels to clusters based on their centroid characteristics.
    Labels are inferred from data, NOT predefined.
    """
    orig = scaler.inverse_transform(centers)
    labels: dict[int, str] = {}

    for cid, centroid in enumerate(orig):
        fc = {feat_names[j]: centroid[j] for j in range(len(feat_names))}

        mom_5d  = fc.get("mom_5d", 0)
        vol_r   = fc.get("vol_ratio", 1)
        prox_h  = fc.get("prox_52w_high", 0.9)
        sect_c  = fc.get("sect_conviction", 0)
        cons_up = fc.get("cons_up_days", 0)
        atr     = fc.get("atr_14", 0)
        mom_20  = fc.get("mom_20d", 0)

        # Data-driven label assignment
        if prox_h >= 0.97 and mom_5d > 0.01:
            label = "HIGH_BASE_BREAKOUT"
        elif mom_5d > 0.03 and vol_r > 1.8:
            label = "STRONG_MOMENTUM_VOLUME"
        elif sect_c > 0.5 and mom_5d > 0.01:
            label = "SECTOR_LEADERSHIP_ROTATION"
        elif cons_up >= 3 and mom_20 > 0.05:
            label = "SUSTAINED_TREND_CONTINUATION"
        elif atr > 0.02 and vol_r > 2.0:
            label = "VOLATILITY_EXPANSION"
        elif mom_20 < -0.05 and mom_5d > 0.01:
            label = "RECOVERY_FROM_OVERSOLD"
        elif vol_r > 1.5 and sect_c > 0.4:
            label = "INSTITUTIONAL_ACCUMULATION"
        else:
            label = "COMPOSITE_SETUP"

        labels[cid] = label

    return labels


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7 — FEATURE DECILE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def feature_decile_analysis(obs: list[dict], feature_ranking: dict) -> dict:
    """
    For each top-20 feature, split observations into deciles and compute
    winner rate per decile. Reveals monotonic relationships and thresholds.
    """
    feature_names = list(obs[0]["features"].keys())
    top_feats = feature_ranking["top20"]
    all_vals   = np.array([[o["features"][f] for f in feature_names] for o in obs])
    all_groups = np.array([1 if o["group"] == "A" else 0 for o in obs])
    base_rate  = float(np.mean(all_groups))

    decile_results: dict[str, list] = {}

    for feat in top_feats:
        fidx = feature_names.index(feat)
        vals = all_vals[:, fidx]
        deciles = np.percentile(vals, np.arange(0, 110, 10))

        buckets = []
        for i in range(10):
            lo = deciles[i]
            hi = deciles[i + 1]
            mask = (vals >= lo) & (vals <= hi) if i == 9 else (vals >= lo) & (vals < hi)
            n = int(mask.sum())
            wr = float(all_groups[mask].mean()) if n > 0 else 0.0
            lift = round(wr / base_rate, 3) if base_rate > 0 else 0.0
            buckets.append({
                "decile": i + 1,
                "lo": round(float(lo), 6),
                "hi": round(float(hi), 6),
                "n": n,
                "winner_rate": round(wr, 4),
                "lift": lift,
            })
        decile_results[feat] = buckets

    # Identify monotonically increasing / decreasing features
    mono_increasing = []
    mono_decreasing = []
    for feat, buckets in decile_results.items():
        wrs = [b["winner_rate"] for b in buckets if b["n"] > 100]
        if len(wrs) < 5:
            continue
        increasing = all(wrs[i] <= wrs[i+1] for i in range(len(wrs)-1))
        decreasing = all(wrs[i] >= wrs[i+1] for i in range(len(wrs)-1))
        if increasing:
            mono_increasing.append({"feature": feat, "min_wr": round(wrs[0], 4),
                                     "max_wr": round(wrs[-1], 4),
                                     "range_pct": round((wrs[-1] - wrs[0]) * 100, 2)})
        elif decreasing:
            mono_decreasing.append({"feature": feat, "max_wr": round(wrs[0], 4),
                                     "min_wr": round(wrs[-1], 4),
                                     "range_pct": round((wrs[0] - wrs[-1]) * 100, 2)})

    # Top / bottom decile findings
    extreme_findings = []
    for feat, buckets in decile_results.items():
        valid = [b for b in buckets if b["n"] > 100]
        if not valid:
            continue
        top_d = max(valid, key=lambda b: b["winner_rate"])
        bot_d = min(valid, key=lambda b: b["winner_rate"])
        if top_d["lift"] >= 1.25 or bot_d["lift"] <= 0.80:
            extreme_findings.append({
                "feature":     feat,
                "peak_decile": top_d["decile"],
                "peak_wr":     top_d["winner_rate"],
                "peak_lift":   top_d["lift"],
                "trough_decile": bot_d["decile"],
                "trough_wr":   bot_d["winner_rate"],
                "trough_lift": bot_d["lift"],
            })
    extreme_findings.sort(key=lambda x: -x["peak_lift"])

    return {
        "base_rate":          round(base_rate, 4),
        "decile_analysis":    decile_results,
        "monotone_increasing": mono_increasing,
        "monotone_decreasing": mono_decreasing,
        "extreme_findings":   extreme_findings[:10],
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    t0 = time.time()
    _banner("STUDY 2A — WINNER DNA DISCOVERY")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}")

    # Verify dependencies
    try:
        import sklearn, scipy  # noqa
        print("sklearn and scipy: available")
    except ImportError as e:
        print(f"ERROR: {e}. Install: .venv\\Scripts\\pip.exe install scikit-learn scipy")
        sys.exit(1)

    # ── Stage 0: Load data ────────────────────────────────────────────────
    _banner("STAGE 0 — Data Loading")
    conn_main = _open_db(REPLAY_DB)
    print(f"Primary DB: {REPLAY_DB}")

    # Count rows
    n_ohlcv = conn_main.execute("SELECT COUNT(1) FROM ohlcv_daily").fetchone()[0]
    n_sig   = conn_main.execute("SELECT COUNT(1) FROM signal_births").fetchone()[0]
    d_range = conn_main.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM ohlcv_daily WHERE symbol != ?",
        (NIFTY_SYM,)
    ).fetchone()
    print(f"  OHLCV rows: {n_ohlcv}  signals: {n_sig}  dates: {d_range[0]} to {d_range[1]}")

    print("Extracting features from primary DB (this may take 2-4 minutes)...")
    obs_main = _extract_features_from_db(conn_main, "replay_5yr")
    conn_main.close()
    print(f"  Features extracted: {len(obs_main)} observations")

    # Load supplement from study002_replay.db (exclude overlapping dates)
    if Path(S002_DB).exists():
        print(f"Loading supplement from {S002_DB}...")
        conn_s002 = _open_db(S002_DB)
        obs_s002_raw = _extract_features_from_db(conn_s002, "study002")
        conn_s002.close()
        # Deduplicate: keep study002 obs only for dates AFTER max replay.db date
        replay_max_date = d_range[1]
        obs_s002 = [o for o in obs_s002_raw if o["date"] > replay_max_date]
        print(f"  Study002 supplement (post-{replay_max_date}): {len(obs_s002)} observations")
    else:
        obs_s002 = []

    # Merge
    obs = obs_main + obs_s002
    print(f"Total dataset: {len(obs)} labeled observations")

    # ── Stage 1: Group classification ─────────────────────────────────────
    _banner("STAGE 1 — Group Classification")
    group_info = classify_groups(obs)
    print(f"  Distribution: mean={group_info['distribution']['mean']:.4f}  "
          f"std={group_info['distribution']['std']:.4f}")
    print(f"  Fixed ±{FIXED_WINNER_THRESHOLD*100:.1f}%: "
          f"Winners={group_info['counts_fixed']['A_winners']}  "
          f"Ordinary={group_info['counts_fixed']['B_ordinary']}  "
          f"Losers={group_info['counts_fixed']['C_losers']}")
    print(f"  Winner rate: {group_info['pct_winners_fixed']*100:.1f}%  "
          f"Loser rate: {group_info['pct_losers_fixed']*100:.1f}%")

    # ── Stage 2: Feature statistics ───────────────────────────────────────
    _banner("STAGE 2 — Feature Statistics")
    feat_result = compute_feature_statistics(obs)
    print(f"  Features analyzed: {len(feat_result['feature_names'])}")
    print(f"  n_winners={feat_result['n_winners']}  "
          f"n_ordinary={feat_result['n_ordinary']}  "
          f"n_losers={feat_result['n_losers']}")

    # ── Stage 3: Feature ranking ──────────────────────────────────────────
    _banner("STAGE 3 — Feature Ranking (MI + RF + Cohen's d)")
    rank_result = rank_features(obs, feat_result)
    print("  Top 10 features:")
    for r in rank_result["full_ranking"][:10]:
        print(f"    {r['rank']:2d}. {r['feature']:<22}  combined={r['combined_score']:.4f}  "
              f"mi={r['mi']:.4f}  d={r['cohens_d_w_vs_l']:.3f}  p={r['mwu_pval_w_vs_l']:.2e}")

    # ── Stage 4: Winner DNA patterns ──────────────────────────────────────
    _banner("STAGE 4 — Winner DNA Pattern Discovery")
    dna_result = discover_dna_patterns(obs, rank_result)
    print(f"  Leaves found: {dna_result['n_leaves_found']}  "
          f"approved: {dna_result['n_approved_initial']}  "
          f"rejected: {dna_result['n_rejected_initial']}")
    print(f"  WF-validated DNA patterns: {len(dna_result['dna_patterns'])}")
    for p in dna_result["dna_patterns"][:5]:
        conds = " AND ".join(p["conditions"])
        print(f"    [{p['validation']}] lift={p['train_lift']:.2f}  "
              f"conf={p['train_confidence']:.2f}  "
              f"avg_ret={p['avg_forward_return']:.4f}  {conds[:70]}")

    # ── Stage 5: Loser DNA ────────────────────────────────────────────────
    _banner("STAGE 5 — Loser DNA Pattern Discovery")
    loser_result = discover_loser_dna(obs, rank_result)
    print(f"  Loser DNA patterns found: {len(loser_result['loser_dna_patterns'])}")

    # ── Stage 6: Cluster analysis ──────────────────────────────────────────
    _banner("STAGE 6 — Winner Cluster Analysis")
    cluster_result = cluster_winners(obs, rank_result)
    if "error" not in cluster_result:
        print(f"  Optimal clusters: k={cluster_result['optimal_k']}  "
              f"silhouette={cluster_result['best_silhouette']:.4f}")
        for c in cluster_result["clusters"]:
            print(f"    [{c['label']}]  n={c['size']}  "
                  f"avg_return={c['avg_return']:.4f}  regime={c['dominant_regime']}")

    # ── Stage 7: Feature decile analysis ───────────────────────────────────
    _banner("STAGE 7 — Feature Decile Analysis")
    decile_result = feature_decile_analysis(obs, rank_result)
    print(f"  Monotone-increasing features: {len(decile_result['monotone_increasing'])}")
    for m in decile_result["monotone_increasing"]:
        print(f"    {m['feature']}: WR {m['min_wr']:.3f} → {m['max_wr']:.3f} "
              f"({m['range_pct']:+.1f}pp range)")
    print(f"  Monotone-decreasing features: {len(decile_result['monotone_decreasing'])}")
    print(f"  Extreme findings (high lift deciles): {len(decile_result['extreme_findings'])}")
    for ef in decile_result["extreme_findings"][:5]:
        print(f"    {ef['feature']}: peak_decile={ef['peak_decile']}  "
              f"WR={ef['peak_wr']:.3f}  lift={ef['peak_lift']:.2f}x")

    # ── Save results ──────────────────────────────────────────────────────
    elapsed = round(time.time() - t0, 1)
    _banner(f"STUDY 2A COMPLETE — {elapsed}s")

    results = {
        "study":            "Study 2A — Winner DNA Discovery",
        "date_range":       {"start": d_range[0], "end": d_range[1]},
        "executed_at":      datetime.now().isoformat(timespec="seconds"),
        "elapsed_s":        elapsed,
        "n_observations":   len(obs),
        "n_features":       len(obs[0]["features"]) if obs else 0,
        "stage0_data":      {"n_main": len(obs_main), "n_supplement": len(obs_s002),
                             "n_total": len(obs), "ohlcv_rows": n_ohlcv,
                             "signal_count": n_sig},
        "stage1_groups":    group_info,
        "stage2_feat_stats": feat_result["feature_stats"],
        "stage3_ranking":   rank_result,
        "stage4_winner_dna": dna_result,
        "stage5_loser_dna": loser_result,
        "stage6_clusters":  cluster_result,
        "stage7_deciles":   decile_result,
    }

    with open(RESULTS, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {RESULTS}")


if __name__ == "__main__":
    main()
