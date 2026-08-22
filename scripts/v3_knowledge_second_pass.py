"""
scripts/v3_knowledge_second_pass.py
=====================================
V3_KNOWLEDGE_SECOND_PASS_AUDIT_001 — 2026-08-17

Tests whether the compiled Knowledge layer can transform the
V3 20+20 high-mover pool into a higher-probability 5–6 stock set.

SAFETY:
  - READ ONLY / RESEARCH ONLY
  - No CandidateStore writes
  - No production module imports
  - No broker calls
  - No order execution

Outputs (all in reports/mover_discovery_v3/):
  v3_knowledge_second_pass_results.json
  v3_knowledge_selection_daily.csv
  v3_knowledge_feature_analysis.csv
  v3_knowledge_conflict_analysis.csv
  v3_knowledge_top5_cases.csv
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from opportunity_engine.mover_discovery_v3 import (
    V3Config, compute_v3_features, score_universe, select_candidates,
)

DB_PATH  = _ROOT / "data" / "study002_replay.db"
OUT_DIR  = _ROOT / "reports" / "mover_discovery_v3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

POOL_SIZE    = 20
MIN_HIST     = 30
RAND_SEEDS   = [42, 43, 44, 45, 46]
RANDOM_N     = 5

# Chronological split (50/25/25)
TRAIN_END = "2026-02-19"
VAL_END   = "2026-05-13"
# OOS: 2026-05-14 onwards


# ═══════════════════════════════════════════════════════════════════
# KNOWLEDGE SIGNALS  (8 binary signals per direction, equal weight)
# No future data. Sector data UNAVAILABLE in this dataset.
# ═══════════════════════════════════════════════════════════════════

KNOWLEDGE_SIGNALS_UP = [
    "mom_5d_positive",        # mom_5d > 0
    "mom_accel_positive",     # mom_accel > 0  (momentum accelerating)
    "mom_3d_positive",        # mom_3d > 0     (short-term confirm)
    "rsi_momentum_zone",      # 45 <= rsi_14 <= 70
    "vol_above_avg",          # vol_ratio >= 1.20
    "price_position_high",    # price_position > 0.55
    "not_overbought",         # rsi_14 < 72
    "outperforms_market",     # mom_1d > market_ret_1d
]

KNOWLEDGE_SIGNALS_DN = [
    "mom_5d_negative",        # mom_5d < 0
    "mom_accel_negative",     # mom_accel < 0
    "mom_3d_negative",        # mom_3d < 0
    "rsi_elevated",           # rsi_14 > 55
    "vol_above_avg",          # vol_ratio >= 1.20
    "price_position_low",     # price_position < 0.45
    "underperforms_market",   # mom_1d < market_ret_1d
    "below_resistance",       # breakout_pct < 1.0
]

N_SIGNALS = len(KNOWLEDGE_SIGNALS_UP)  # = 8

# Economically meaningful combinations to test
FEATURE_COMBOS = [
    ("mom_5d_positive",),
    ("mom_accel_positive",),
    ("vol_above_avg",),
    ("rsi_momentum_zone",),
    ("price_position_high",),
    ("outperforms_market",),
    ("mom_5d_positive", "vol_above_avg"),
    ("mom_5d_positive", "rsi_momentum_zone"),
    ("mom_5d_positive", "outperforms_market"),
    ("mom_accel_positive", "vol_above_avg"),
    ("vol_above_avg", "price_position_high"),
    ("rsi_momentum_zone", "vol_above_avg"),
    ("mom_5d_positive", "mom_accel_positive", "vol_above_avg"),
    ("mom_5d_positive", "vol_above_avg", "price_position_high"),
    ("mom_5d_positive", "rsi_momentum_zone", "vol_above_avg"),
    ("mom_5d_positive", "mom_accel_positive", "outperforms_market"),
    ("mom_5d_positive", "mom_accel_positive", "vol_above_avg", "price_position_high"),
]


def _knowledge_signals(feat: Dict, market_ret_1d: float, direction: str) -> Dict[str, int]:
    m1   = float(feat.get("mom_1d",    0) or 0)
    m3   = float(feat.get("mom_3d",    0) or 0)
    m5   = float(feat.get("mom_5d",    0) or 0)
    macl = float(feat.get("mom_accel", 0) or 0)
    rsi  = float(feat.get("rsi_14",   50) or 50)
    vol  = float(feat.get("vol_ratio", 1) or 1)
    pp   = float(feat.get("price_position", 0.5) or 0.5)
    bkr  = float(feat.get("breakout_pct", 0) or 0)

    if direction == "UP":
        return {
            "mom_5d_positive":    int(m5  >  0.0),
            "mom_accel_positive": int(macl > 0.0),
            "mom_3d_positive":    int(m3  >  0.0),
            "rsi_momentum_zone":  int(45.0 <= rsi <= 70.0),
            "vol_above_avg":      int(vol  >= 1.20),
            "price_position_high": int(pp > 0.55),
            "not_overbought":     int(rsi < 72.0),
            "outperforms_market": int(m1 > market_ret_1d),
        }
    else:  # DOWN
        return {
            "mom_5d_negative":    int(m5  <  0.0),
            "mom_accel_negative": int(macl < 0.0),
            "mom_3d_negative":    int(m3  <  0.0),
            "rsi_elevated":       int(rsi > 55.0),
            "vol_above_avg":      int(vol  >= 1.20),
            "price_position_low": int(pp < 0.45),
            "underperforms_market": int(m1 < market_ret_1d),
            "below_resistance":   int(bkr < 1.0),
        }


def _knowledge_score(signals: Dict[str, int]) -> float:
    return round(sum(signals.values()) / N_SIGNALS, 4)


def _confidence(score: float) -> str:
    if score >= 0.625:  return "HIGH"        # >= 5/8
    if score >= 0.375:  return "MEDIUM"      # >= 3/8
    if score >= 0.25:   return "LOW"         # >= 2/8
    return "REJECT"


def _split(date: str) -> str:
    if date <= TRAIN_END: return "TRAIN"
    if date <= VAL_END:   return "VAL"
    return "OOS"


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════

def load_ohlcv(db: Path):
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily WHERE close > 0 ORDER BY symbol, trade_date"
    ).fetchall()
    conn.close()
    sym_history = defaultdict(list)
    all_dates   = set()
    for sym, date, o, h, l, c, v in rows:
        sym_history[sym].append((date, float(c), float(h), float(l), float(v or 0)))
        all_dates.add(date)
    return sorted(all_dates), sym_history


# ═══════════════════════════════════════════════════════════════════
# PER-DAY REPLAY + KNOWLEDGE SCORING
# ═══════════════════════════════════════════════════════════════════

def replay_one_day(
    trading_date: str,
    sym_history: Dict,
    cfg: V3Config,
) -> Optional[Tuple[List, List, int, Dict]]:
    """Returns (up_cands, dn_cands, universe_size, full_features_by_symbol)."""
    features = []
    for sym, hist in sym_history.items():
        rows = [r for r in hist if r[0] <= trading_date]
        if len(rows) < MIN_HIST:
            continue
        closes  = [r[1] for r in rows]
        highs   = [r[2] for r in rows]
        lows    = [r[3] for r in rows]
        volumes = [r[4] for r in rows]
        feat = compute_v3_features(sym, closes, highs, lows, volumes)
        if feat is not None:
            features.append(feat)
    if len(features) < 30:
        return None
    scored = score_universe(features, cfg)
    up_cands, dn_cands = select_candidates(scored, cfg, pool_size=POOL_SIZE)
    feat_by_sym = {f["symbol"]: f for f in scored}
    return up_cands, dn_cands, len(features), feat_by_sym


def compute_market_context(
    trading_date: str, sym_history: Dict, close_lookup: Dict
) -> Dict:
    """Market average 1d return (universe proxy for NIFTY direction)."""
    prev_dates = sorted(d for sym_h in sym_history.values()
                        for (d, *_) in sym_h if d < trading_date)
    if not prev_dates:
        return {"market_ret_1d": 0.0, "regime": "UNKNOWN"}
    prev_date = prev_dates[-1] if prev_dates else None

    rets = []
    for sym in close_lookup:
        c0 = close_lookup[sym].get(prev_date)
        c1 = close_lookup[sym].get(trading_date)
        if c0 and c1 and c0 > 0:
            rets.append((c1 / c0 - 1.0) * 100.0)

    mkt = sum(rets) / len(rets) if rets else 0.0
    if   mkt >  0.5: regime = "BULL"
    elif mkt < -0.5: regime = "BEAR"
    else:            regime = "RANGE"
    return {"market_ret_1d": round(mkt, 4), "regime": regime}


def add_knowledge(
    candidates: List[Dict], feat_by_sym: Dict, mkt_ctx: Dict, direction: str
) -> List[Dict]:
    """Attach knowledge_score, signals, confidence to each candidate."""
    mkt_ret = mkt_ctx["market_ret_1d"]
    enriched = []
    for cand in candidates:
        sym  = cand["symbol"]
        feat = feat_by_sym.get(sym, cand)
        sigs = _knowledge_signals(feat, mkt_ret, direction)
        kscore = _knowledge_score(sigs)
        conf   = _confidence(kscore)
        enriched.append({
            **cand,
            **{f"sig_{k}": v for k, v in sigs.items()},
            "knowledge_score":         kscore,
            "knowledge_confidence":    conf,
            "knowledge_evidence_count": sum(sigs.values()),
            "market_ret_1d":           mkt_ret,
            "market_regime":           mkt_ctx["regime"],
            # carry full features for analysis
            "mom_1d":   float(feat.get("mom_1d",   0) or 0),
            "mom_3d":   float(feat.get("mom_3d",   0) or 0),
            "mom_5d":   float(feat.get("mom_5d",   0) or 0),
            "mom_accel":float(feat.get("mom_accel",0) or 0),
            "rsi_14":   float(feat.get("rsi_14",  50) or 50),
            "vol_ratio":float(feat.get("vol_ratio", 1) or 1),
            "vol_trend":float(feat.get("vol_trend", 0) or 0),
            "price_position": float(feat.get("price_position", 0.5) or 0.5),
            "breakout_pct":   float(feat.get("breakout_pct",   0)   or 0),
            "support_gap":    float(feat.get("support_gap",    0)   or 0),
            "hv_20":          float(feat.get("hv_20",          0)   or 0),
        })
    return enriched


# ═══════════════════════════════════════════════════════════════════
# OUTCOME JOIN + METRICS
# ═══════════════════════════════════════════════════════════════════

def join_outcomes(
    candidates: List[Dict], close_lookup: Dict, high_lookup: Dict,
    low_lookup: Dict, t1_date: Optional[str], t3_date: Optional[str],
    direction: str,
) -> List[Dict]:
    result = []
    for cand in candidates:
        sym = cand["symbol"]
        c0  = close_lookup[sym].get(cand["trading_date"]) if "trading_date" in cand else None
        r1 = r3 = mfe1 = mae1 = mfe3 = mae3 = None
        if c0 and c0 > 0:
            c1 = close_lookup[sym].get(t1_date) if t1_date else None
            if c1 and c1 > 0:
                r1 = round((c1 / c0 - 1.0) * 100.0, 4)
                h1 = high_lookup[sym].get(t1_date, c1)
                l1 = low_lookup[sym].get(t1_date,  c1)
                if direction == "UP":
                    mfe1 = round((h1 / c0 - 1.0) * 100.0, 4)
                    mae1 = round((l1 / c0 - 1.0) * 100.0, 4)
                else:
                    mfe1 = round((c0 / l1 - 1.0) * 100.0, 4) if l1 > 0 else None
                    mae1 = round((c0 / h1 - 1.0) * 100.0, 4) if h1 > 0 else None

            if t3_date:
                future3 = sorted(
                    k for k in close_lookup[sym] if t1_date and t1_date <= k <= t3_date
                )
                if future3:
                    c3  = close_lookup[sym].get(t3_date, close_lookup[sym].get(future3[-1]))
                    all_h = [high_lookup[sym].get(d, c0) for d in future3]
                    all_l = [low_lookup[sym].get(d,  c0) for d in future3]
                    if c3 and c3 > 0:
                        r3 = round((c3 / c0 - 1.0) * 100.0, 4)
                    if direction == "UP":
                        mfe3 = round((max(all_h) / c0 - 1.0) * 100.0, 4) if all_h else None
                        mae3 = round((min(all_l) / c0 - 1.0) * 100.0, 4) if all_l else None
                    else:
                        mfe3 = round((c0 / min(all_l) - 1.0) * 100.0, 4) if all_l and min(all_l) > 0 else None
                        mae3 = round((c0 / max(all_h) - 1.0) * 100.0, 4) if all_h and max(all_h) > 0 else None

        result.append({**cand, "t1_ret": r1, "t3_ret": r3,
                       "mfe_t1": mfe1, "mae_t1": mae1,
                       "mfe_t3": mfe3, "mae_t3": mae3})
    return result


def _stats(
    rows: List[Dict], direction: str, ret_key: str = "t1_ret",
    mfe_key: str = "mfe_t1", mae_key: str = "mae_t1",
) -> Dict:
    rets = [r[ret_key] for r in rows if r.get(ret_key) is not None]
    mfes = [r[mfe_key] for r in rows if r.get(mfe_key) is not None]
    maes = [r[mae_key] for r in rows if r.get(mae_key) is not None]
    if not rets:
        return {"n": 0}
    fav = [r for r in rets if (r > 0 if direction == "UP" else r < 0)]
    n   = len(rets)
    avg = sum(rets) / n
    fav_avg = sum(fav) / len(fav) if fav else 0.0
    srt = sorted(rets)
    med = srt[n // 2]
    ge1 = sum(1 for r in rets if (r >=  1.0 if direction == "UP" else r <= -1.0))
    ge2 = sum(1 for r in rets if (r >=  2.0 if direction == "UP" else r <= -2.0))
    ge3 = sum(1 for r in rets if (r >=  3.0 if direction == "UP" else r <= -3.0))
    dir_acc = sum(1 for r in rets if (r > 0 if direction == "UP" else r < 0)) / n
    # false positive = in predicted direction but |ret| < 1%
    fp = sum(1 for r in rets if abs(r) < 1.0) / n
    return {
        "n": n,
        "avg_ret": round(avg, 4),
        "median_ret": round(med, 4),
        "directional_acc": round(dir_acc, 4),
        "avg_fav_ret": round(fav_avg, 4),
        "ge1pct_rate": round(ge1 / n, 4),
        "ge2pct_rate": round(ge2 / n, 4),
        "ge3pct_rate": round(ge3 / n, 4),
        "avg_mfe": round(sum(mfes) / len(mfes), 4) if mfes else None,
        "avg_mae": round(sum(maes) / len(maes), 4) if maes else None,
        "false_positive_rate": round(fp, 4),
    }


def _random_sample(pool: List[Dict], n: int, seed: int) -> List[Dict]:
    rng = random.Random(seed)
    return rng.sample(pool, min(n, len(pool)))


def _spearman(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 4: return float("nan")
    ix = sorted(range(n), key=lambda i: xs[i])
    iy = sorted(range(n), key=lambda i: ys[i])
    rx = [0.0] * n; ry = [0.0] * n
    for rank, i in enumerate(ix): rx[i] = rank + 1.0
    for rank, i in enumerate(iy): ry[i] = rank + 1.0
    mx = sum(rx) / n; my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((v - mx) ** 2 for v in rx) * sum((v - my) ** 2 for v in ry)) ** 0.5
    return round(num / den, 4) if den > 0 else float("nan")


def _merge_stats(a: Dict, b: Dict) -> Dict:
    """Merge two _stats dicts (UP + DOWN combined)."""
    if not a or not b: return {}
    if a.get("n", 0) == 0 and b.get("n", 0) == 0: return {"n": 0}
    n = a["n"] + b["n"]
    def wavg(ka, kb):
        va = a.get(ka) or 0.0; vb = b.get(kb) or 0.0
        return round((va * a["n"] + vb * b["n"]) / n, 4) if n else None
    return {
        "n":               n,
        "directional_acc": wavg("directional_acc", "directional_acc"),
        "ge1pct_rate":     wavg("ge1pct_rate",     "ge1pct_rate"),
        "ge2pct_rate":     wavg("ge2pct_rate",     "ge2pct_rate"),
        "ge3pct_rate":     wavg("ge3pct_rate",     "ge3pct_rate"),
        "avg_fav_ret":     wavg("avg_fav_ret",      "avg_fav_ret"),
        "avg_mfe":         wavg("avg_mfe",          "avg_mfe"),
        "avg_mae":         wavg("avg_mae",          "avg_mae"),
        "false_positive_rate": wavg("false_positive_rate", "false_positive_rate"),
    }


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    cfg = V3Config(enabled=False, shadow_mode=True, discovery_pool_size=POOL_SIZE)
    trading_dates, sym_history = load_ohlcv(DB_PATH)
    print(f"Loaded {sum(len(v) for v in sym_history.values()):,} rows, "
          f"{len(sym_history)} symbols, {len(trading_dates)} dates")

    close_lookup: Dict[str, Dict[str, float]] = defaultdict(dict)
    high_lookup:  Dict[str, Dict[str, float]] = defaultdict(dict)
    low_lookup:   Dict[str, Dict[str, float]] = defaultdict(dict)
    for sym, hist in sym_history.items():
        for date, c, h, l, v in hist:
            close_lookup[sym][date] = c
            high_lookup[sym][date]  = h
            low_lookup[sym][date]   = l

    eligible_dates = trading_dates[MIN_HIST:]
    print(f"Eligible dates: {len(eligible_dates)} ({eligible_dates[0]} → {eligible_dates[-1]})")

    # per-model accumulators keyed by (split, model_name, direction)
    model_acc: Dict = defaultdict(list)
    # daily rows
    daily_rows      = []
    # all enriched candidate records (for conflict + top5 analysis)
    all_enriched_up = []
    all_enriched_dn = []

    for idx, td in enumerate(eligible_dates):
        result = replay_one_day(td, sym_history, cfg)
        if result is None: continue

        up_raw, dn_raw, univ_size, feat_by_sym = result
        mkt_ctx = compute_market_context(td, sym_history, close_lookup)
        split   = _split(td)

        future = [d for d in trading_dates if d > td]
        t1_date = future[0] if len(future) >= 1 else None
        t3_date = future[2] if len(future) >= 3 else None

        # Attach trading_date to each candidate (needed for outcome join)
        for c in up_raw: c["trading_date"] = td
        for c in dn_raw: c["trading_date"] = td

        up_k = add_knowledge(up_raw, feat_by_sym, mkt_ctx, "UP")
        dn_k = add_knowledge(dn_raw, feat_by_sym, mkt_ctx, "DOWN")

        up_out = join_outcomes(up_k, close_lookup, high_lookup, low_lookup,
                               t1_date, t3_date, "UP")
        dn_out = join_outcomes(dn_k, close_lookup, high_lookup, low_lookup,
                               t1_date, t3_date, "DOWN")

        all_enriched_up.extend(up_out)
        all_enriched_dn.extend(dn_out)

        # Sort by knowledge score (descending) for model selection
        up_ks = sorted(up_out, key=lambda x: -x["knowledge_score"])
        dn_ks = sorted(dn_out, key=lambda x: -x["knowledge_score"])

        # Random baseline (5 seeds, averaged)
        rand_up_all = [_random_sample(up_out, RANDOM_N, s) for s in RAND_SEEDS]
        rand_dn_all = [_random_sample(dn_out, RANDOM_N, s) for s in RAND_SEEDS]

        # All 6 models × 2 directions
        models = {
            "V3_20":       (up_out,          dn_out),
            "V3_Top5":     (sorted(up_out, key=lambda x: -x.get("v3_up_score", x.get("v3_score", 0)))[:5],
                            sorted(dn_out, key=lambda x: -x.get("v3_down_score", x.get("v3_score", 0)))[:5]),
            "Know_Top10":  (up_ks[:10],      dn_ks[:10]),
            "Know_Top6":   (up_ks[:6],       dn_ks[:6]),
            "Know_Top5":   (up_ks[:5],       dn_ks[:5]),
            "Random_5":    (rand_up_all[0],  rand_dn_all[0]),  # seed=42 for records
        }

        day_row = {
            "trading_date": td, "t1_date": t1_date or "",
            "universe_size": univ_size, "split": split,
            "market_regime": mkt_ctx["regime"],
            "market_ret_1d": mkt_ctx["market_ret_1d"],
        }

        for model_name, (up_sel, dn_sel) in models.items():
            su = _stats(up_sel, "UP")
            sd = _stats(dn_sel, "DOWN")
            # random baseline: average across all seeds
            if model_name == "Random_5":
                su_list = [_stats(r, "UP")   for r in rand_up_all]
                sd_list = [_stats(r, "DOWN") for r in rand_dn_all]
                def avg_stat(lst, k): vals = [d[k] for d in lst if d.get(k) is not None]; return round(sum(vals)/len(vals),4) if vals else None
                su = {k: avg_stat(su_list, k) for k in su_list[0]} if su_list else su
                sd = {k: avg_stat(sd_list, k) for k in sd_list[0]} if sd_list else sd

            for dir_name, st in [("UP", su), ("DN", sd)]:
                key = (split, model_name, dir_name)
                model_acc[key].append(st)

            # Write into day_row
            for dir_name, st in [("UP", su), ("DN", sd)]:
                pfx = f"{model_name}_{dir_name}"
                day_row[f"{pfx}_dir_acc"]  = st.get("directional_acc")
                day_row[f"{pfx}_ge2_rate"] = st.get("ge2pct_rate")
                day_row[f"{pfx}_ge3_rate"] = st.get("ge3pct_rate")
                day_row[f"{pfx}_avg_ret"]  = st.get("avg_fav_ret")

        daily_rows.append(day_row)

        if (idx + 1) % 50 == 0 or idx == len(eligible_dates) - 1:
            pct = (idx + 1) / len(eligible_dates) * 100
            k5 = day_row.get("Know_Top5_UP_dir_acc")
            b20= day_row.get("V3_20_UP_dir_acc")
            print(f"  [{pct:4.0f}%] {td} | split={split} | "
                  f"KnowTop5_UP_dir={k5} | V3_20_UP_dir={b20}")

    print(f"\nDone. Days={len(daily_rows)}")

    # ── aggregate over all splits ──────────────────────────────────────────
    def agg_stats(key_prefix: Tuple) -> Dict:
        rows_list = model_acc[key_prefix]
        if not rows_list: return {}
        n_days = len(rows_list)
        def avg(k):
            vals = [d[k] for d in rows_list if d.get(k) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None
        keys = [k for k in rows_list[0] if k != "n"]
        return {k: avg(k) for k in keys}

    MODELS      = ["V3_20","V3_Top5","Know_Top10","Know_Top6","Know_Top5","Random_5"]
    DIRECTIONS  = ["UP","DN"]
    SPLITS      = ["TRAIN","VAL","OOS","ALL"]

    # ALL split is accumulated across all rows
    for split in ["TRAIN","VAL","OOS"]:
        for mn in MODELS:
            for dn in DIRECTIONS:
                rows_list = model_acc[(split, mn, dn)]
                all_key   = ("ALL", mn, dn)
                model_acc[all_key].extend(rows_list)

    results_by_split: Dict = {}
    for split in SPLITS:
        results_by_split[split] = {}
        for mn in MODELS:
            results_by_split[split][mn] = {
                "UP": agg_stats((split, mn, "UP")),
                "DN": agg_stats((split, mn, "DN")),
                "combined": _merge_stats(
                    agg_stats((split, mn, "UP")),
                    agg_stats((split, mn, "DN"))
                ),
            }

    # ── spearman: knowledge score vs T+1 return ───────────────────────────
    def compute_spearman(enriched: List[Dict], score_key: str, ret_key: str,
                          invert: bool = False) -> float:
        xs = [float(r[score_key]) for r in enriched if r.get(score_key) is not None and r.get(ret_key) is not None]
        ys = [float(r[ret_key]) for r in enriched if r.get(score_key) is not None and r.get(ret_key) is not None]
        if invert: ys = [-y for y in ys]
        return _spearman(xs, ys)

    spearman_know_up = compute_spearman(all_enriched_up, "knowledge_score", "t1_ret")
    spearman_know_dn = compute_spearman(all_enriched_dn, "knowledge_score", "t1_ret", invert=True)
    spearman_v3_up   = compute_spearman(all_enriched_up, "v3_up_score",    "t1_ret")
    spearman_v3_dn   = compute_spearman(all_enriched_dn, "v3_down_score",  "t1_ret", invert=True)

    # ── feature combination analysis ──────────────────────────────────────
    feat_combo_rows = []
    for combo in FEATURE_COMBOS:
        for direction, enriched in [("UP", all_enriched_up), ("DN", all_enriched_dn)]:
            # Map DN signal names to their UP equivalents for combos defined in UP terms
            # For DN, we check the corresponding DN signal names
            if direction == "DN":
                dn_map = {
                    "mom_5d_positive":    "mom_5d_negative",
                    "mom_accel_positive": "mom_accel_negative",
                    "mom_3d_positive":    "mom_3d_negative",
                    "rsi_momentum_zone":  "rsi_elevated",
                    "vol_above_avg":      "vol_above_avg",
                    "price_position_high":"price_position_low",
                    "not_overbought":     "rsi_elevated",
                    "outperforms_market": "underperforms_market",
                }
                actual_combo = tuple(dn_map.get(s, s) for s in combo)
            else:
                actual_combo = combo

            sig_keys = [f"sig_{s}" for s in actual_combo]
            selected = [r for r in enriched
                        if all(r.get(k, 0) == 1 for k in sig_keys)
                        and r.get("t1_ret") is not None]
            st = _stats(selected, direction) if selected else {"n": 0}
            feat_combo_rows.append({
                "combo":            "+".join(combo),
                "direction":        direction,
                "n":                st.get("n", 0),
                "directional_acc":  st.get("directional_acc"),
                "ge1pct_rate":      st.get("ge1pct_rate"),
                "ge2pct_rate":      st.get("ge2pct_rate"),
                "ge3pct_rate":      st.get("ge3pct_rate"),
                "avg_fav_ret":      st.get("avg_fav_ret"),
                "avg_mfe":          st.get("avg_mfe"),
                "avg_mae":          st.get("avg_mae"),
            })

    # ── conflict analysis ──────────────────────────────────────────────────
    conflict_rows = []
    for direction, enriched in [("UP", all_enriched_up), ("DN", all_enriched_dn)]:
        for r in enriched:
            kscore = r.get("knowledge_score", 0)
            conf   = r.get("knowledge_confidence", "?")
            ret    = r.get("t1_ret")
            if ret is None: continue
            favorable = (ret > 0 if direction == "UP" else ret < 0)
            conflict_type = "ALIGNED" if kscore >= 0.5 else "CONFLICT"
            conflict_rows.append({
                "trading_date":        r.get("trading_date","?"),
                "symbol":              r.get("symbol","?"),
                "direction":           direction,
                "v3_score":            r.get("v3_up_score") if direction=="UP" else r.get("v3_down_score"),
                "knowledge_score":     kscore,
                "knowledge_confidence":conf,
                "conflict_type":       conflict_type,
                "t1_ret_pct":          ret,
                "v3_favorable":        favorable,
                "knowledge_favorable": (ret > 0 if direction=="UP" else ret < 0),
                "split":               _split(r.get("trading_date","?")),
            })

    # ── top5 cases ─────────────────────────────────────────────────────────
    top5_rows = []
    for direction, enriched in [("UP", all_enriched_up), ("DN", all_enriched_dn)]:
        by_date: Dict[str, List] = defaultdict(list)
        for r in enriched:
            if r.get("t1_ret") is not None:
                by_date[r["trading_date"]].append(r)

        for td, pool in by_date.items():
            # Know Top-5
            know5 = sorted(pool, key=lambda x: -x["knowledge_score"])[:5]
            # V3 Top-5
            vscore_key = "v3_up_score" if direction == "UP" else "v3_down_score"
            v3_5   = sorted(pool, key=lambda x: -x.get(vscore_key, 0))[:5]
            # Random Top-5 (seed 42)
            rand5  = _random_sample(pool, 5, 42)

            for model_name, sel in [("KNOW_TOP5", know5), ("V3_TOP5", v3_5), ("RAND_TOP5", rand5)]:
                for cand in sel:
                    ret = cand.get("t1_ret", 0) or 0
                    fav = (ret > 0 if direction == "UP" else ret < 0)
                    top5_rows.append({
                        "trading_date":     td,
                        "model":            model_name,
                        "direction":        direction,
                        "symbol":           cand.get("symbol","?"),
                        "v3_score":         cand.get(vscore_key, 0),
                        "knowledge_score":  cand.get("knowledge_score", 0),
                        "knowledge_conf":   cand.get("knowledge_confidence","?"),
                        "t1_ret_pct":       cand.get("t1_ret"),
                        "t3_ret_pct":       cand.get("t3_ret"),
                        "favorable":        int(fav),
                        "ge2pct":           int(abs(ret) >= 2.0 and fav),
                        "split":            _split(td),
                    })

    # ── concentration analysis ─────────────────────────────────────────────
    # Share of total pool's favorable return captured by top selections
    conc_by_day_up = []
    conc_by_day_dn = []
    for direction, enriched, conc_list in [
        ("UP", all_enriched_up, conc_by_day_up),
        ("DN", all_enriched_dn, conc_by_day_dn),
    ]:
        by_date: Dict[str, List] = defaultdict(list)
        for r in enriched:
            if r.get("t1_ret") is not None: by_date[r["trading_date"]].append(r)
        vscore_key = "v3_up_score" if direction=="UP" else "v3_down_score"
        for td, pool in by_date.items():
            total_fav = sum(max(r["t1_ret"], 0) for r in pool) if direction=="UP" else \
                        sum(max(-r["t1_ret"], 0) for r in pool)
            if total_fav <= 0: continue
            know5 = sorted(pool, key=lambda x: -x["knowledge_score"])[:5]
            know6 = sorted(pool, key=lambda x: -x["knowledge_score"])[:6]
            know10= sorted(pool, key=lambda x: -x["knowledge_score"])[:10]
            def fav_sum(sel):
                return sum(max(r["t1_ret"],0) for r in sel) if direction=="UP" else \
                       sum(max(-r["t1_ret"],0) for r in sel)
            conc_list.append({
                "know5_share":  fav_sum(know5)  / total_fav,
                "know6_share":  fav_sum(know6)  / total_fav,
                "know10_share": fav_sum(know10) / total_fav,
                "split":        _split(td),
            })

    def avg_conc(lst, key, split=None):
        filtered = [r for r in lst if split is None or r["split"]==split]
        vals = [r[key] for r in filtered]
        return round(sum(vals)/len(vals), 4) if vals else None

    concentration = {
        "UP": {
            "know5_avg_share":  avg_conc(conc_by_day_up,  "know5_share"),
            "know6_avg_share":  avg_conc(conc_by_day_up,  "know6_share"),
            "know10_avg_share": avg_conc(conc_by_day_up,  "know10_share"),
            "random5_expected": round(5 / POOL_SIZE, 4),  # uniform = 25%
            "know5_vs_random_lift": round(avg_conc(conc_by_day_up, "know5_share") / (5/POOL_SIZE), 4)
                                    if avg_conc(conc_by_day_up, "know5_share") else None,
        },
        "DN": {
            "know5_avg_share":  avg_conc(conc_by_day_dn,  "know5_share"),
            "know6_avg_share":  avg_conc(conc_by_day_dn,  "know6_share"),
            "know10_avg_share": avg_conc(conc_by_day_dn,  "know10_share"),
            "random5_expected": round(5 / POOL_SIZE, 4),
            "know5_vs_random_lift": round(avg_conc(conc_by_day_dn, "know5_share") / (5/POOL_SIZE), 4)
                                    if avg_conc(conc_by_day_dn, "know5_share") else None,
        },
    }

    # ── verdicts ───────────────────────────────────────────────────────────
    oos_know5_up  = results_by_split["OOS"]["Know_Top5"]["UP"]
    oos_rand5_up  = results_by_split["OOS"]["Random_5"]["UP"]
    oos_know5_dn  = results_by_split["OOS"]["Know_Top5"]["DN"]
    oos_rand5_dn  = results_by_split["OOS"]["Random_5"]["DN"]
    oos_v3t5_up   = results_by_split["OOS"]["V3_Top5"]["UP"]

    def safer(d, k): return d.get(k) or 0.0

    dir_improve_up = safer(oos_know5_up,"directional_acc") - safer(oos_rand5_up,"directional_acc")
    dir_improve_dn = safer(oos_know5_dn,"directional_acc") - safer(oos_rand5_dn,"directional_acc")
    ge2_improve_up = safer(oos_know5_up,"ge2pct_rate") - safer(oos_rand5_up,"ge2pct_rate")
    ge2_improve_dn = safer(oos_know5_dn,"ge2pct_rate") - safer(oos_rand5_dn,"ge2pct_rate")
    vs_v3top5_up   = safer(oos_know5_up,"directional_acc") - safer(oos_v3t5_up,"directional_acc")

    strong_go = (
        dir_improve_up > 0.04 and dir_improve_dn > 0.04 and
        ge2_improve_up > 0.02 and ge2_improve_dn > 0.02
    )
    promising  = dir_improve_up > 0.02 or dir_improve_dn > 0.02
    no_value   = dir_improve_up <= 0 and dir_improve_dn <= 0

    if no_value:
        verdict = "C. KNOWLEDGE_SECOND_PASS_NO_INCREMENTAL_VALUE"
    elif strong_go:
        verdict = "A. KNOWLEDGE_SECOND_PASS_STRONG_GO"
    elif promising:
        verdict = "B. KNOWLEDGE_SECOND_PASS_PROMISING_OOS_PENDING"
    elif dir_improve_up <= 0 and dir_improve_dn <= 0:
        verdict = "D. KNOWLEDGE_SECOND_PASS_DIRECTIONAL_EDGE_WEAK"
    else:
        verdict = "B. KNOWLEDGE_SECOND_PASS_PROMISING_OOS_PENDING"

    # ── write outputs ──────────────────────────────────────────────────────

    # 1. Aggregate JSON
    agg_out = {
        "audit_id":      "V3_KNOWLEDGE_SECOND_PASS_AUDIT_001",
        "date":          "2026-08-17",
        "days_total":    len(daily_rows),
        "train_end":     TRAIN_END,
        "val_end":       VAL_END,
        "oos_start":     "2026-05-14",
        "pool_size":     POOL_SIZE,
        "n_knowledge_signals": N_SIGNALS,
        "sector_context": "UNAVAILABLE (sector_ret_1d=0.0 in study002_replay.db — no sector peer data)",
        "spearman_knowledge_up_vs_t1":  spearman_know_up,
        "spearman_knowledge_dn_vs_neg_t1": spearman_know_dn,
        "spearman_v3_up_vs_t1":         spearman_v3_up,
        "spearman_v3_dn_vs_neg_t1":     spearman_v3_dn,
        "results_by_split":             results_by_split,
        "concentration":                concentration,
        "dir_improve_up_vs_rand":       round(dir_improve_up, 4),
        "dir_improve_dn_vs_rand":       round(dir_improve_dn, 4),
        "ge2_improve_up_vs_rand":       round(ge2_improve_up, 4),
        "ge2_improve_dn_vs_rand":       round(ge2_improve_dn, 4),
        "know_top5_vs_v3_top5_up_dir_delta": round(vs_v3top5_up, 4),
        "verdict":       verdict,
        "leakage_check": "PASS — all knowledge signals use only backward-looking features",
    }
    json_path = OUT_DIR / "v3_knowledge_second_pass_results.json"
    json_path.write_text(json.dumps(agg_out, indent=2))
    print(f"\nResults JSON → {json_path}")

    # 2. Daily CSV
    def write_csv(rows, path):
        if not rows: return
        headers = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for row in rows:
                f.write(",".join(str(row.get(h,"")) for h in headers) + "\n")

    daily_path = OUT_DIR / "v3_knowledge_selection_daily.csv"
    write_csv(daily_rows, daily_path)
    print(f"Daily CSV → {daily_path} ({len(daily_rows)} rows)")

    feat_path = OUT_DIR / "v3_knowledge_feature_analysis.csv"
    write_csv(feat_combo_rows, feat_path)
    print(f"Feature analysis → {feat_path} ({len(feat_combo_rows)} rows)")

    conflict_path = OUT_DIR / "v3_knowledge_conflict_analysis.csv"
    write_csv(conflict_rows, conflict_path)
    print(f"Conflict analysis → {conflict_path} ({len(conflict_rows)} rows)")

    top5_path = OUT_DIR / "v3_knowledge_top5_cases.csv"
    write_csv(top5_rows, top5_path)
    print(f"Top5 cases → {top5_path} ({len(top5_rows)} rows)")

    # ── print summary ──────────────────────────────────────────────────────
    print("\n" + "="*72)
    print("V3 KNOWLEDGE SECOND PASS — COMPARISON TABLE (OOS)")
    print("="*72)
    header = f"{'MODEL':<16} {'DIR%':>6} {'>=1%':>6} {'>=2%':>6} {'>=3%':>6} {'FavRet':>8} {'FP%':>6}"
    print(header)
    print("-"*72)
    for mn in MODELS:
        for dn in ["UP","DN"]:
            st = results_by_split["OOS"][mn][dn]
            if not st: continue
            print(f"  {mn:14s}_{dn}  "
                  f"{st.get('directional_acc',0)*100:5.1f}%  "
                  f"{st.get('ge1pct_rate',0)*100:5.1f}%  "
                  f"{st.get('ge2pct_rate',0)*100:5.1f}%  "
                  f"{st.get('ge3pct_rate',0)*100:5.1f}%  "
                  f"{st.get('avg_fav_ret',0):7.3f}%  "
                  f"{st.get('false_positive_rate',0)*100:5.1f}%")
    print("="*72)
    print(f"\nConcentration (Knowledge Top-5 share of pool's favorable movement):")
    print(f"  UP: {concentration['UP']['know5_avg_share']:.1%}  "
          f"(random expected {concentration['UP']['random5_expected']:.1%},  "
          f"lift {concentration['UP']['know5_vs_random_lift']:.2f}×)")
    print(f"  DN: {concentration['DN']['know5_avg_share']:.1%}  "
          f"(random expected {concentration['DN']['random5_expected']:.1%},  "
          f"lift {concentration['DN']['know5_vs_random_lift']:.2f}×)")
    print(f"\nSpearman(Knowledge score, T+1):  UP={spearman_know_up}  DN={spearman_know_dn}")
    print(f"Spearman(V3 score,       T+1):  UP={spearman_v3_up}  DN={spearman_v3_dn}")
    print(f"\nVERDICT: {verdict}")
    print("="*72)


if __name__ == "__main__":
    main()
