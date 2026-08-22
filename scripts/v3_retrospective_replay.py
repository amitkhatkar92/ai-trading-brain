"""
scripts/v3_retrospective_replay.py
====================================
Option A: V3 Retrospective Replay

Runs V3 scorer over every trading day in study002_replay.db (248 days,
2025-08-01 to 2026-07-30) using only backward-looking OHLCV features.
Computes T+1 and T+3 mover capture rates and score-vs-return Spearman
correlation, then compares against a random-selection baseline.

Outputs:
  reports/mover_discovery_v3/v3_retro_daily.csv
  reports/mover_discovery_v3/v3_retro_aggregate.json
  reports/mover_discovery_v3/v3_retro_candidates.csv  (all picks + outcomes)

Usage:
  python scripts/v3_retrospective_replay.py [--db data/study002_replay.db]
"""
from __future__ import annotations

import json
import sqlite3
import sys
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from opportunity_engine.mover_discovery_v3 import (
    V3Config,
    compute_v3_features,
    score_universe,
    select_candidates,
)

DB_PATH  = _ROOT / "data" / "study002_replay.db"
OUT_DIR  = _ROOT / "reports" / "mover_discovery_v3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

POOL_SIZE   = 20
MIN_HIST    = 30   # require 30 days of history before first eligible date
T1_THRESH_UP  =  2.0  # ≥+2% = strong UP mover
T1_THRESH_DN  = -2.0  # ≤-2% = strong DN mover


# ── helpers ───────────────────────────────────────────────────────────────────

def _spearman(xs: List[float], ys: List[float]) -> float:
    """Spearman rank correlation between two lists."""
    n = len(xs)
    if n < 4:
        return float("nan")
    def _ranks(vals):
        indexed = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        for rank, i in enumerate(indexed):
            r[i] = rank + 1.0
        return r
    rx, ry = _ranks(xs), _ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((v - mx)**2 for v in rx) * sum((v - my)**2 for v in ry)) ** 0.5
    return round(num / den, 4) if den > 0 else float("nan")


def _pct_ret(close_t: float, close_t1: Optional[float]) -> Optional[float]:
    if close_t and close_t > 0 and close_t1 and close_t1 > 0:
        return round((close_t1 / close_t - 1.0) * 100.0, 4)
    return None


# ── load OHLCV ────────────────────────────────────────────────────────────────

def load_ohlcv(db: Path) -> Tuple[List[str], Dict[str, List]]:
    """
    Returns:
      trading_dates: sorted list of all trade_dates in DB
      sym_history:   {symbol: [(date, close, high, low, volume), ...]} sorted ASC
    """
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily WHERE close > 0 ORDER BY symbol, trade_date"
    ).fetchall()
    conn.close()

    sym_history: Dict[str, List] = defaultdict(list)
    all_dates_set = set()
    for sym, date, o, h, l, c, v in rows:
        sym_history[sym].append((date, float(c), float(h), float(l), float(v or 0)))
        all_dates_set.add(date)

    trading_dates = sorted(all_dates_set)
    print(f"Loaded {len(rows):,} OHLCV rows, {len(sym_history)} symbols, {len(trading_dates)} dates")
    print(f"Date range: {trading_dates[0]} → {trading_dates[-1]}")
    return trading_dates, sym_history


# ── single-day replay ─────────────────────────────────────────────────────────

def replay_one_day(
    trading_date: str,
    sym_history: Dict[str, List],
    cfg: V3Config,
) -> Optional[Tuple[List, List, int]]:
    """
    Returns (up_candidates, dn_candidates, universe_size) for trading_date,
    or None if fewer than 30 symbols have sufficient history.
    """
    features = []
    for sym, hist in sym_history.items():
        # Slice only rows UP TO trading_date (PIT-safe)
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
    return up_cands, dn_cands, len(features)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    cfg = V3Config(enabled=False, shadow_mode=True, discovery_pool_size=POOL_SIZE)

    trading_dates, sym_history = load_ohlcv(db_path)

    # Build fast lookup: sym → {date → close}
    close_lookup: Dict[str, Dict[str, float]] = defaultdict(dict)
    for sym, hist in sym_history.items():
        for date, c, h, l, v in hist:
            close_lookup[sym][date] = c

    # Skip first MIN_HIST dates (insufficient history for any symbol)
    eligible_dates = trading_dates[MIN_HIST:]
    print(f"Eligible dates for replay: {len(eligible_dates)} "
          f"({eligible_dates[0]} → {eligible_dates[-1]})")

    # ── per-day results ───────────────────────────────────────────────────────
    daily_rows = []       # for CSV
    all_cand_rows = []    # full candidate-level records

    # Aggregate accumulators
    acc = {
        "days_total": 0,
        "days_with_t1": 0,
        "days_with_t3": 0,

        "up_t1_returns": [],     # T+1 return for all UP picks
        "dn_t1_returns": [],     # T+1 return for all DN picks (positive = adverse)
        "up_t3_returns": [],
        "dn_t3_returns": [],

        # mover capture numerators / denominators
        "up_t1_ge1_found": 0, "up_t1_ge1_total": 0,
        "up_t1_ge2_found": 0, "up_t1_ge2_total": 0,
        "up_t1_ge3_found": 0, "up_t1_ge3_total": 0,
        "dn_t1_le1_found": 0, "dn_t1_le1_total": 0,
        "dn_t1_le2_found": 0, "dn_t1_le2_total": 0,
        "dn_t1_le3_found": 0, "dn_t1_le3_total": 0,

        "up_t3_ge2_found": 0, "up_t3_ge2_total": 0,
        "dn_t3_le2_found": 0, "dn_t3_le2_total": 0,
        "n_univ_t1_total": 0,  # total universe symbol-days with T+1 — random baseline denominator

        # score vs return lists for Spearman
        "up_scores": [], "up_t1_rets": [],
        "dn_scores": [], "dn_t1_rets": [],

        # random baseline
        "random_baseline_days": [],  # expected hit rate per day
    }

    for idx, td in enumerate(eligible_dates):
        result = replay_one_day(td, sym_history, cfg)
        if result is None:
            continue

        up_cands, dn_cands, univ_size = result
        acc["days_total"] += 1

        # ── find T+1 and T+3 dates ─────────────────────────────────────────
        future_dates = [d for d in trading_dates if d > td]
        t1_date = future_dates[0] if len(future_dates) >= 1 else None
        t3_date = future_dates[2] if len(future_dates) >= 3 else None  # 3 trading days later

        # ── universe mover counts (random baseline denominator) ────────────
        if t1_date:
            acc["days_with_t1"] += 1
            random_base = POOL_SIZE / max(univ_size, 1)
            acc["random_baseline_days"].append(random_base)

            # Count strong movers in the FULL universe on T+1
            universe_t1_rets = []
            for sym in close_lookup:
                c_t  = close_lookup[sym].get(td)
                c_t1 = close_lookup[sym].get(t1_date)
                if c_t and c_t1:
                    universe_t1_rets.append(_pct_ret(c_t, c_t1))
            universe_t1_rets = [r for r in universe_t1_rets if r is not None]

            n_strong_up_ge1 = sum(1 for r in universe_t1_rets if r >=  1.0)
            n_strong_up_ge2 = sum(1 for r in universe_t1_rets if r >=  2.0)
            n_strong_up_ge3 = sum(1 for r in universe_t1_rets if r >=  3.0)
            n_strong_dn_le1 = sum(1 for r in universe_t1_rets if r <= -1.0)
            n_strong_dn_le2 = sum(1 for r in universe_t1_rets if r <= -2.0)
            n_strong_dn_le3 = sum(1 for r in universe_t1_rets if r <= -3.0)
            n_univ = len(universe_t1_rets)

            acc["up_t1_ge1_total"] += n_strong_up_ge1
            acc["up_t1_ge2_total"] += n_strong_up_ge2
            acc["up_t1_ge3_total"] += n_strong_up_ge3
            acc["dn_t1_le1_total"] += n_strong_dn_le1
            acc["dn_t1_le2_total"] += n_strong_dn_le2
            acc["dn_t1_le3_total"] += n_strong_dn_le3
            acc["n_univ_t1_total"] += n_univ

        # ── UP candidates ──────────────────────────────────────────────────
        day_up_t1 = []
        for rank, cand in enumerate(up_cands, 1):
            sym   = cand["symbol"]
            score = cand["v3_up_score"]
            c_t   = close_lookup[sym].get(td)
            ret_1 = _pct_ret(c_t, close_lookup[sym].get(t1_date)) if t1_date and c_t else None
            ret_3 = _pct_ret(c_t, close_lookup[sym].get(t3_date)) if t3_date and c_t else None

            all_cand_rows.append({
                "trading_date": td, "direction": "UP", "rank": rank,
                "symbol": sym, "v3_score": score,
                "atr_pct": round(cand.get("atr_pct", 0), 4),
                "mom_5d": round(cand.get("mom_5d", 0), 4),
                "t1_date": t1_date, "t1_ret_pct": ret_1,
                "t3_date": t3_date, "t3_ret_pct": ret_3,
            })

            if ret_1 is not None:
                acc["up_t1_returns"].append(ret_1)
                day_up_t1.append(ret_1)
                acc["up_scores"].append(score)
                acc["up_t1_rets"].append(ret_1)
                acc["up_t1_ge1_found"] += (1 if ret_1 >=  1.0 else 0)
                acc["up_t1_ge2_found"] += (1 if ret_1 >=  2.0 else 0)
                acc["up_t1_ge3_found"] += (1 if ret_1 >=  3.0 else 0)
            if ret_3 is not None:
                acc["up_t3_returns"].append(ret_3)
                acc["up_t3_ge2_found"] += (1 if ret_3 >=  2.0 else 0)
                if t3_date:
                    acc["up_t3_ge2_total"] += (1 if ret_1 is not None else 0)

        # ── DN candidates ──────────────────────────────────────────────────
        day_dn_t1 = []
        for rank, cand in enumerate(dn_cands, 1):
            sym   = cand["symbol"]
            score = cand["v3_down_score"]
            c_t   = close_lookup[sym].get(td)
            ret_1 = _pct_ret(c_t, close_lookup[sym].get(t1_date)) if t1_date and c_t else None
            ret_3 = _pct_ret(c_t, close_lookup[sym].get(t3_date)) if t3_date and c_t else None

            all_cand_rows.append({
                "trading_date": td, "direction": "DN", "rank": rank,
                "symbol": sym, "v3_score": score,
                "atr_pct": round(cand.get("atr_pct", 0), 4),
                "mom_5d": round(cand.get("mom_5d", 0), 4),
                "t1_date": t1_date, "t1_ret_pct": ret_1,
                "t3_date": t3_date, "t3_ret_pct": ret_3,
            })

            if ret_1 is not None:
                acc["dn_t1_returns"].append(ret_1)
                day_dn_t1.append(ret_1)
                acc["dn_scores"].append(score)
                acc["dn_t1_rets"].append(ret_1)
                acc["dn_t1_le1_found"] += (1 if ret_1 <= -1.0 else 0)
                acc["dn_t1_le2_found"] += (1 if ret_1 <= -2.0 else 0)
                acc["dn_t1_le3_found"] += (1 if ret_1 <= -3.0 else 0)
            if ret_3 is not None:
                acc["dn_t3_returns"].append(ret_3)
                acc["dn_t3_le2_found"] += (1 if ret_3 <= -2.0 else 0)

        # ── daily summary row ─────────────────────────────────────────────
        daily_rows.append({
            "trading_date":     td,
            "universe_size":    univ_size,
            "up_pool":          len(up_cands),
            "dn_pool":          len(dn_cands),
            "t1_date":          t1_date or "",
            "up_avg_t1":        round(sum(day_up_t1) / len(day_up_t1), 4) if day_up_t1 else "",
            "dn_avg_t1":        round(sum(day_dn_t1) / len(day_dn_t1), 4) if day_dn_t1 else "",
            "up_ge2pct_t1":     sum(1 for r in day_up_t1 if r >= 2.0),
            "dn_le_neg2pct_t1": sum(1 for r in day_dn_t1 if r <= -2.0),
            "random_base":      round(POOL_SIZE / max(univ_size, 1), 4),
        })

        if (idx + 1) % 50 == 0 or idx == len(eligible_dates) - 1:
            pct = (idx + 1) / len(eligible_dates) * 100
            print(f"  [{pct:4.0f}%] {td} | universe={univ_size} | "
                  f"UP avg_t1={daily_rows[-1]['up_avg_t1']} | "
                  f"days_done={acc['days_total']}")

    # ── aggregate statistics ──────────────────────────────────────────────────

    def safe_div(n, d):
        return round(n / d, 4) if d > 0 else None

    n_up_t1 = len(acc["up_t1_returns"])
    n_dn_t1 = len(acc["dn_t1_returns"])
    avg_rand = (sum(acc["random_baseline_days"]) / len(acc["random_baseline_days"])
                if acc["random_baseline_days"] else 0)

    # Capture rate = (V3 candidates that were movers) / (total V3 candidates with T+1)
    # vs random = (universe movers) / (universe total) × pool_size
    # Lift = V3 capture rate / random rate

    def capture_rate_and_lift(found, n_picks, total_movers, n_univ_symbols):
        if n_picks == 0 or n_univ_symbols == 0:
            return None, None, None
        rate = found / n_picks
        rand = total_movers / n_univ_symbols
        lift = rate / rand if rand > 0 else None
        return round(rate, 4), round(rand, 4), round(lift, 4) if lift else None

    n_univ_total = acc["n_univ_t1_total"]  # total universe symbol-days with T+1

    # Universe strong movers across all days
    # random baseline = total_movers / total_universe_symbol_days
    up_ge1_rate, up_ge1_rand, up_ge1_lift = capture_rate_and_lift(
        acc["up_t1_ge1_found"], n_up_t1, acc["up_t1_ge1_total"], n_univ_total)

    up_ge2_rate, up_ge2_rand, up_ge2_lift = capture_rate_and_lift(
        acc["up_t1_ge2_found"], n_up_t1, acc["up_t1_ge2_total"], n_univ_total)

    up_ge3_rate, up_ge3_rand, up_ge3_lift = capture_rate_and_lift(
        acc["up_t1_ge3_found"], n_up_t1, acc["up_t1_ge3_total"], n_univ_total)

    dn_le1_rate, dn_le1_rand, dn_le1_lift = capture_rate_and_lift(
        acc["dn_t1_le1_found"], n_dn_t1, acc["dn_t1_le1_total"], n_univ_total)

    dn_le2_rate, dn_le2_rand, dn_le2_lift = capture_rate_and_lift(
        acc["dn_t1_le2_found"], n_dn_t1, acc["dn_t1_le2_total"], n_univ_total)

    dn_le3_rate, dn_le3_rand, dn_le3_lift = capture_rate_and_lift(
        acc["dn_t1_le3_found"], n_dn_t1, acc["dn_t1_le3_total"], n_univ_total)

    # Spearman correlation: v3_score vs T+1 return
    spearman_up = _spearman(acc["up_scores"], acc["up_t1_rets"])
    spearman_dn = _spearman(acc["dn_scores"], acc["dn_t1_rets"])
    # For DN: higher score should predict MORE negative return, so invert
    spearman_dn_inv = _spearman(acc["dn_scores"], [-r for r in acc["dn_t1_rets"]])

    # Directional accuracy
    up_directional_acc = safe_div(sum(1 for r in acc["up_t1_returns"] if r > 0), n_up_t1)
    dn_directional_acc = safe_div(sum(1 for r in acc["dn_t1_returns"] if r < 0), n_dn_t1)

    agg = {
        "replay_db":           str(db_path),
        "days_eligible":       len(eligible_dates),
        "days_replayed":       acc["days_total"],
        "days_with_t1":        acc["days_with_t1"],
        "days_with_t3":        len(acc["up_t3_returns"]) // POOL_SIZE if acc["up_t3_returns"] else 0,
        "pool_size":           POOL_SIZE,

        "UP_T1": {
            "n_picks":                n_up_t1,
            "avg_return_pct":         round(sum(acc["up_t1_returns"]) / n_up_t1, 4) if n_up_t1 else None,
            "positive_pct":           up_directional_acc,
            "ge1pct_capture_rate":    up_ge1_rate,
            "ge1pct_random_baseline": up_ge1_rand,
            "ge1pct_lift":            up_ge1_lift,
            "ge2pct_capture_rate":    up_ge2_rate,
            "ge2pct_random_baseline": up_ge2_rand,
            "ge2pct_lift":            up_ge2_lift,
            "ge3pct_capture_rate":    up_ge3_rate,
            "ge3pct_random_baseline": up_ge3_rand,
            "ge3pct_lift":            up_ge3_lift,
            "spearman_score_vs_ret":  spearman_up,
            "note": "lift > 1.0 means V3 outperforms random for that threshold",
        },

        "DN_T1": {
            "n_picks":                        n_dn_t1,
            "avg_return_pct":                 round(sum(acc["dn_t1_returns"]) / n_dn_t1, 4) if n_dn_t1 else None,
            "negative_directional_acc":       dn_directional_acc,
            "le_neg1pct_capture_rate":        dn_le1_rate,
            "le_neg1pct_random_baseline":     dn_le1_rand,
            "le_neg1pct_lift":                dn_le1_lift,
            "le_neg2pct_capture_rate":        dn_le2_rate,
            "le_neg2pct_random_baseline":     dn_le2_rand,
            "le_neg2pct_lift":                dn_le2_lift,
            "le_neg3pct_capture_rate":        dn_le3_rate,
            "le_neg3pct_random_baseline":     dn_le3_rand,
            "le_neg3pct_lift":                dn_le3_lift,
            "spearman_score_vs_neg_ret":      spearman_dn_inv,
            "note": "favorable = actual return is negative (moved DOWN as predicted)",
        },

        "UP_T3": {
            "n_picks":             len(acc["up_t3_returns"]),
            "avg_return_pct":      round(sum(acc["up_t3_returns"]) / len(acc["up_t3_returns"]), 4) if acc["up_t3_returns"] else None,
            "ge2pct_capture_rate": safe_div(acc["up_t3_ge2_found"], len(acc["up_t3_returns"])) if acc["up_t3_returns"] else None,
        },

        "DN_T3": {
            "n_picks":             len(acc["dn_t3_returns"]),
            "avg_return_pct":      round(sum(acc["dn_t3_returns"]) / len(acc["dn_t3_returns"]), 4) if acc["dn_t3_returns"] else None,
            "le_neg2pct_capture":  safe_div(acc["dn_t3_le2_found"], len(acc["dn_t3_returns"])) if acc["dn_t3_returns"] else None,
        },

        "verdict": None,  # filled below
    }

    # Verdict logic
    verdicts = []
    if up_ge2_lift and up_ge2_lift > 1.10:
        verdicts.append(f"UP_POOL_OUTPERFORMS_RANDOM (≥2% lift={up_ge2_lift:.2f}×)")
    elif up_ge2_lift and up_ge2_lift >= 0.90:
        verdicts.append(f"UP_POOL_AT_RANDOM (≥2% lift={up_ge2_lift:.2f}×)")
    else:
        verdicts.append(f"UP_POOL_UNDERPERFORMS_RANDOM (≥2% lift={up_ge2_lift}×)")

    if dn_le2_lift and dn_le2_lift > 1.10:
        verdicts.append(f"DN_POOL_OUTPERFORMS_RANDOM (≤-2% lift={dn_le2_lift:.2f}×)")
    elif dn_le2_lift and dn_le2_lift >= 0.90:
        verdicts.append(f"DN_POOL_AT_RANDOM (≤-2% lift={dn_le2_lift:.2f}×)")
    else:
        verdicts.append(f"DN_POOL_UNDERPERFORMS_RANDOM (≤-2% lift={dn_le2_lift}×)")

    if spearman_up and abs(spearman_up) > 0.05:
        verdicts.append(f"SCORE_RANK_PREDICTIVE_UP (spearman={spearman_up})")
    else:
        verdicts.append(f"SCORE_RANK_NOT_PREDICTIVE_UP (spearman={spearman_up})")

    if spearman_dn_inv and abs(spearman_dn_inv) > 0.05:
        verdicts.append(f"SCORE_RANK_PREDICTIVE_DN (spearman={spearman_dn_inv})")
    else:
        verdicts.append(f"SCORE_RANK_NOT_PREDICTIVE_DN (spearman={spearman_dn_inv})")

    agg["verdict"] = verdicts

    # ── write outputs ─────────────────────────────────────────────────────────

    # 1. Aggregate JSON
    agg_path = OUT_DIR / "v3_retro_aggregate.json"
    agg_path.write_text(json.dumps(agg, indent=2))
    print(f"\nAggregates → {agg_path}")

    # 2. Daily CSV
    daily_path = OUT_DIR / "v3_retro_daily.csv"
    headers = list(daily_rows[0].keys()) if daily_rows else []
    with open(daily_path, "w", newline="") as f:
        f.write(",".join(headers) + "\n")
        for row in daily_rows:
            f.write(",".join(str(row.get(h, "")) for h in headers) + "\n")
    print(f"Daily CSV → {daily_path} ({len(daily_rows)} rows)")

    # 3. Candidate CSV
    cand_path = OUT_DIR / "v3_retro_candidates.csv"
    c_headers = list(all_cand_rows[0].keys()) if all_cand_rows else []
    with open(cand_path, "w", newline="") as f:
        f.write(",".join(c_headers) + "\n")
        for row in all_cand_rows:
            f.write(",".join(str(row.get(h, "")) for h in c_headers) + "\n")
    print(f"Candidate CSV → {cand_path} ({len(all_cand_rows)} rows)")

    # ── print summary ─────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("V3 RETROSPECTIVE REPLAY — SUMMARY")
    print("="*65)
    print(f"Days replayed:       {acc['days_total']}  (with T+1: {acc['days_with_t1']})")
    print(f"Total UP T+1 picks:  {n_up_t1}")
    print(f"Total DN T+1 picks:  {n_dn_t1}")
    print()
    print("UP POOL — T+1")
    print(f"  Avg return:        {agg['UP_T1']['avg_return_pct']:+.3f}%")
    print(f"  Directional acc:   {up_directional_acc:.1%}  (positive T+1)")
    print(f"  ≥+1% capture:      {up_ge1_rate:.1%}  vs random {up_ge1_rand:.1%}  → lift {up_ge1_lift:.2f}×")
    print(f"  ≥+2% capture:      {up_ge2_rate:.1%}  vs random {up_ge2_rand:.1%}  → lift {up_ge2_lift:.2f}×")
    print(f"  ≥+3% capture:      {up_ge3_rate:.1%}  vs random {up_ge3_rand:.1%}  → lift {up_ge3_lift:.2f}×")
    print(f"  Spearman(score,ret):{spearman_up}")
    print()
    print("DOWN POOL — T+1")
    print(f"  Avg return:        {agg['DN_T1']['avg_return_pct']:+.3f}%  (negative = favorable)")
    print(f"  Directional acc:   {dn_directional_acc:.1%}  (negative T+1)")
    print(f"  ≤-1% capture:      {dn_le1_rate:.1%}  vs random {dn_le1_rand:.1%}  → lift {dn_le1_lift:.2f}×")
    print(f"  ≤-2% capture:      {dn_le2_rate:.1%}  vs random {dn_le2_rand:.1%}  → lift {dn_le2_lift:.2f}×")
    print(f"  ≤-3% capture:      {dn_le3_rate:.1%}  vs random {dn_le3_rand:.1%}  → lift {dn_le3_lift:.2f}×")
    print(f"  Spearman(score,neg_ret): {spearman_dn_inv}")
    print()
    print("VERDICTS:")
    for v in verdicts:
        print(f"  {v}")
    print("="*65)


if __name__ == "__main__":
    main()
