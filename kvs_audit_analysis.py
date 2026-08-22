"""
KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001
Research-only script. Runs entirely offline. No production changes.
Reads from VPS databases. Produces JSON/CSV outputs for report.
"""

import sqlite3
import json
import csv
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
import random

DATA_DIR = "/root/ai-trading-brain/data"
OUT_DIR  = "/tmp/kvs_audit_output"
os.makedirs(OUT_DIR, exist_ok=True)

# ─── helpers ──────────────────────────────────────────────────────────────────

def bootstrap_ci(values, n_boot=1000, ci=0.95):
    """Bootstrap confidence interval for the mean."""
    if len(values) < 5:
        return None, None
    rng = random.Random(42)
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(values) for _ in range(len(values))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int((1 - ci) / 2 * n_boot)]
    hi = means[int((1 + ci) / 2 * n_boot)]
    return round(lo, 4), round(hi, 4)

def safe_mean(lst):
    return round(sum(lst) / len(lst), 4) if lst else None

def directional_accuracy(actuals, predictions):
    """actuals = list of floats (actual move). predictions = list of +1/-1."""
    correct = sum(1 for a, p in zip(actuals, predictions) if (a >= 0) == (p >= 0))
    return round(correct / len(actuals), 4) if actuals else None

def capture_rate(actuals, threshold):
    """Fraction of trades where |actual| >= threshold."""
    return round(sum(1 for a in actuals if a >= threshold) / len(actuals), 4) if actuals else 0.0

# ─── LOAD DATA ────────────────────────────────────────────────────────────────

print("Loading databases...")

# 1. control_tower.db
ct_con = sqlite3.connect(f"{DATA_DIR}/control_tower.db")
ct_con.row_factory = sqlite3.Row

cycles = ct_con.execute("SELECT * FROM ct_cycles").fetchall()
decisions = ct_con.execute("SELECT * FROM ct_decisions").fetchall()
ct_con.close()

print(f"  ct_cycles: {len(cycles)}")
print(f"  ct_decisions: {len(decisions)}")

# 2. market_behavior.db
mb_con = sqlite3.connect(f"{DATA_DIR}/market_behavior.db")
mb_con.row_factory = sqlite3.Row

signal_births = mb_con.execute("SELECT * FROM signal_births").fetchall()
market_leaders = mb_con.execute("SELECT ml.*, mlo.return_1d, mlo.return_3d, mlo.return_5d, mlo.return_10d, mlo.return_20d, mlo.max_favorable, mlo.max_adverse, mlo.outcome_class FROM market_leaders_daily ml JOIN market_leader_outcomes mlo ON ml.leader_id = mlo.leader_id").fetchall()
feature_rows = mb_con.execute("SELECT * FROM market_leader_features").fetchall()
feature_diffs = mb_con.execute("SELECT * FROM feature_differentials WHERE ABS(outcome_gap_5d) > 0.5").fetchall()
mb_con.close()

print(f"  signal_births: {len(signal_births)}")
print(f"  market_leaders_with_outcomes: {len(market_leaders)}")
print(f"  leader_features: {len(feature_rows)}")
print(f"  feature_differentials: {len(feature_diffs)}")

# 3. paper_trades.csv
paper_trades = []
csv_path = f"{DATA_DIR}/paper_trades.csv"
if os.path.exists(csv_path):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_trades.append(row)
print(f"  paper_trades: {len(paper_trades)}")

# 4. learning_db.json
learning_data = {}
ldb_path = f"{DATA_DIR}/learning_db.json"
if os.path.exists(ldb_path):
    with open(ldb_path) as f:
        learning_data = json.load(f)
print(f"  learning_db: {len(learning_data)} keys")

# ─── SECTION 1: ARCHITECTURE LAYER CLASSIFICATION ─────────────────────────────

print("\n=== SECTION 1: PIPELINE COMPONENT CLASSIFICATION ===")

arch = {
    "knowledge_sources": [
        "GlobalDataAI: S&P500/Nikkei/Crude/Gold/FX overnight context",
        "MarketIntelligence: regime(range/bull/bear/volatile), VIX, PCR, breadth, sector_leaders",
        "EquityScannerAI: RSI(14), ATR(14), volume_ratio, support/resistance levels",
        "CandidateStore: Phase-D score (0.55 floor), sector rank, conviction decay",
        "MarketBehaviorDB: DNA archetypes (signal_births), market_leader_features",
        "MetaLearning: k-NN regime->strategy weight predictor",
    ],
    "knowledge_consumed_at": [
        "StrategyLab (regime mapping only) — knowledge used to select strategy, NOT evaluate signal quality",
        "Debate Layer (5 agents + DNA): TechnicalAnalystAI, MacroAnalystAI, RiskDebateAI, SentimentAI, RegimeDebateAI, InstitutionalDNAAI",
        "DecisionEngine: aggregates debate votes",
    ],
    "strategy_gate_location": "LAYER 4 — MetaStrategyController+StrategyHealthMonitor, BEFORE debate agents",
    "strategy_gate_type": "HARD MANDATORY GATE — strategy-blocked signals never reach debate/knowledge agents",
    "direction_source": "EquityScannerAI._identify_setup() — RSI extremes, price vs resistance/support, vol_ratio",
    "entry_source": "EquityScannerAI._identify_setup() — current LTP or resistance level (breakout)",
    "sl_source": "EquityScannerAI._identify_setup() — entry ± ATR×factor",
    "target_source": "EquityScannerAI._identify_setup() — entry + 2.5×ATR (mrb) or next resistance",
    "expected_move_pct_source": "EquityScannerAI.scan() — computed AFTER signal: (atr/entry)×rr×100. Observational only.",
    "capital_constraint_entry": "CRE Layer 7 — SL-based sizing; QTY_ZERO if budget < entry_price",
    "veto_authority": "Strategy gate has hard veto. DecisionEngine has threshold veto. Any debate agent can hard-reject.",
}

# ─── SECTION 2: SIGNAL BIRTHS ANALYSIS ────────────────────────────────────────
print("\n=== SECTION 2: SIGNAL BIRTHS OUTCOME ANALYSIS ===")

# Filter to signals with outcomes
sb_with_outcomes = [
    s for s in signal_births
    if s["actual_move_pct"] is not None or s["trade_outcome_pct"] is not None
]
print(f"  Signal births with outcomes: {len(sb_with_outcomes)}")

# Knowledge-led model: use base_score and expected_move_direction
# Current model: use trade_executed flag

# Separate by whether a trade was actually executed
sb_traded  = [s for s in sb_with_outcomes if s["trade_executed"] == 1]
sb_blocked = [s for s in sb_with_outcomes if s["trade_executed"] == 0]

print(f"  Traded signals (Model A proxy): {len(sb_traded)}")
print(f"  Non-traded signals (knowledge-only): {len(sb_blocked)}")

def compute_signal_metrics(signals, label):
    """Compute directional accuracy and magnitude capture for a set of signals."""
    if not signals:
        return {"label": label, "n": 0}
    
    actual_moves   = [float(s["actual_move_pct"]) for s in signals if s["actual_move_pct"] is not None]
    peak_moves     = [float(s["peak_move_pct"]) for s in signals if s["peak_move_pct"] is not None]
    expected_moves = [float(s["expected_move_pct"]) for s in signals if s["expected_move_pct"] is not None]
    
    directions     = [s["expected_move_direction"] for s in signals if s["expected_move_direction"]]
    
    # Directional accuracy: did the signal get direction right?
    dir_matches = []
    for s in signals:
        if s["actual_move_pct"] is None or not s["expected_move_direction"]:
            continue
        actual = float(s["actual_move_pct"])
        pred_dir = s["expected_move_direction"]
        if pred_dir in ("LONG", "UP", "BUY"):
            correct = actual >= 0
        elif pred_dir in ("SHORT", "DOWN", "SELL"):
            correct = actual < 0
        else:
            continue
        dir_matches.append(correct)
    
    dir_acc = round(sum(dir_matches) / len(dir_matches), 4) if dir_matches else None
    
    # Score distribution by final state
    state_counts = defaultdict(int)
    for s in signals:
        state_counts[s["final_state"] or "UNKNOWN"] += 1
    
    # Magnitude: what fraction had meaningful moves?
    cap_1pct = capture_rate([abs(m) for m in actual_moves], 1.0)
    cap_2pct = capture_rate([abs(m) for m in actual_moves], 2.0)
    cap_3pct = capture_rate([abs(m) for m in actual_moves], 3.0)
    
    # Base score analysis
    base_scores = [float(s["base_score"]) for s in signals if s["base_score"] is not None]
    
    ci_lo, ci_hi = bootstrap_ci(actual_moves)
    
    return {
        "label": label,
        "n": len(signals),
        "n_with_actual_move": len(actual_moves),
        "directional_accuracy": dir_acc,
        "n_directional_evaluated": len(dir_matches),
        "avg_actual_move_pct": safe_mean(actual_moves),
        "avg_peak_move_pct": safe_mean(peak_moves),
        "avg_base_score": safe_mean(base_scores),
        "capture_1pct": cap_1pct,
        "capture_2pct": cap_2pct,
        "capture_3pct": cap_3pct,
        "avg_expected_move_pct": safe_mean(expected_moves),
        "actual_move_ci_95": [ci_lo, ci_hi],
        "final_state_distribution": dict(state_counts),
    }

model_a_sb = compute_signal_metrics(sb_traded,  "MODEL_A_STRATEGY_GATED (traded)")
model_b_sb = compute_signal_metrics(sb_blocked, "MODEL_B_KNOWLEDGE_ONLY (not traded)")
model_all  = compute_signal_metrics(list(signal_births), "ALL_SIGNALS (before gate)")

print(json.dumps(model_a_sb, indent=2))
print(json.dumps(model_b_sb, indent=2))

# ─── SECTION 3: STRATEGY SCORE THRESHOLD TEST ─────────────────────────────────
print("\n=== SECTION 3: KNOWLEDGE SCORE THRESHOLD TEST ===")

# Can a higher base_score threshold replicate/improve strategy gate?
score_buckets = {"low": (0, 5), "medium": (5, 7), "high": (7, 9), "very_high": (9, 100)}
score_analysis = {}
for bucket_name, (lo, hi) in score_buckets.items():
    bucket = [
        s for s in sb_with_outcomes
        if s["base_score"] is not None and lo <= float(s["base_score"]) < hi
        and s["actual_move_pct"] is not None
    ]
    if bucket:
        moves = [float(s["actual_move_pct"]) for s in bucket]
        peaks = [float(s["peak_move_pct"]) for s in bucket if s["peak_move_pct"] is not None]
        score_analysis[bucket_name] = {
            "score_range": f"{lo}-{hi}",
            "n": len(bucket),
            "avg_move": safe_mean(moves),
            "avg_peak": safe_mean(peaks),
            "cap_2pct": capture_rate([abs(m) for m in moves], 2.0),
            "cap_3pct": capture_rate([abs(m) for m in moves], 3.0),
        }

print(json.dumps(score_analysis, indent=2))

# ─── SECTION 4: MARKET LEADER OUTCOMES ANALYSIS ───────────────────────────────
print("\n=== SECTION 4: MARKET LEADER FEATURE ANALYSIS ===")

# Group features by leader_id
leader_feature_map = defaultdict(dict)
for f in feature_rows:
    leader_feature_map[f["leader_id"]][f["feature_name"]] = f["feature_value"]

# Each market leader has known features at time of detection + subsequent outcomes
leaders_with_features = []
for ldr in market_leaders:
    lid = ldr["leader_id"]
    features = leader_feature_map.get(lid, {})
    if not features:
        continue
    leaders_with_features.append({
        "leader_id": lid,
        "trade_date": ldr["trade_date"],
        "symbol": ldr["symbol"],
        "leader_type": ldr["leader_type"],
        "day_return_pct": ldr["day_return_pct"],
        "volume_ratio": ldr["volume_ratio"],
        "sector": ldr["sector"],
        "regime": ldr["regime"],
        "return_1d": ldr["return_1d"],
        "return_3d": ldr["return_3d"],
        "return_5d": ldr["return_5d"],
        "return_10d": ldr["return_10d"],
        "return_20d": ldr["return_20d"],
        "max_favorable": ldr["max_favorable"],
        "max_adverse": ldr["max_adverse"],
        "outcome_class": ldr["outcome_class"],
        "features": features,
    })

print(f"  Leaders with features: {len(leaders_with_features)}")

# Feature importance: which features distinguish winners (WINNER) from CONTROL?
winner_leaders = [l for l in leaders_with_features if l["leader_type"] == "WINNER"]
ctrl_leaders   = [l for l in leaders_with_features if l["leader_type"] != "WINNER"]

print(f"  Winners: {len(winner_leaders)},  Controls: {len(ctrl_leaders)}")

# Compare key features
feature_names = ["above_20dma", "volume_ratio", "rsi", "rs_vs_nifty_5d", "atr_pct",
                 "near_52w_high", "gap_up", "sector_strength"]

feature_comparison = {}
for feat in feature_names:
    w_vals = [float(l["features"][feat]) for l in winner_leaders if feat in l["features"] and l["features"][feat] is not None]
    c_vals = [float(l["features"][feat]) for l in ctrl_leaders if feat in l["features"] and l["features"][feat] is not None]
    if w_vals and c_vals:
        feature_comparison[feat] = {
            "winner_mean": safe_mean(w_vals),
            "control_mean": safe_mean(c_vals),
            "n_winner": len(w_vals),
            "n_control": len(c_vals),
            "winner_ci": bootstrap_ci(w_vals),
            "control_ci": bootstrap_ci(c_vals),
        }

print(json.dumps(feature_comparison, indent=2))

# ─── SECTION 5: 230→20→5/6 SIMULATION ────────────────────────────────────────
print("\n=== SECTION 5: 230→20→5/6 STRONG-MOVER SELECTION SIMULATION ===")

# For each trade date in market_leaders, simulate 4 models selecting from the universe
# Model A: uses leader_type WINNER (detection-day identification, volume_ratio based)
# Model B: uses base_score from signal_births (knowledge score)
# Model C: uses both signal_births + leader features
# Model D: uses feature combination discovered from feature_differentials

# Get all trade dates
trade_dates = sorted(set(l["trade_date"] for l in market_leaders))
print(f"  Trade dates in market_leaders: {len(trade_dates)}")

# For each date, get winners and their outcomes
date_winner_map = defaultdict(list)
for ldr in leaders_with_features:
    date_winner_map[ldr["trade_date"]].append(ldr)

# Signal births by date
sb_date_map = defaultdict(list)
for s in signal_births:
    if s["detected_at"]:
        d = s["detected_at"][:10]
        sb_date_map[d].append(s)

# Build per-date comparison
model_results = {"A": [], "B": [], "C": [], "D": []}

for date in trade_dates:
    day_leaders = date_winner_map.get(date, [])
    day_sb = sb_date_map.get(date, [])
    if not day_leaders:
        continue
    
    # Actual strong movers that day (ground truth): top 6 by max_favorable
    long_movers = [l for l in day_leaders if l["leader_type"] == "WINNER" and (l["max_favorable"] or 0) > 0]
    long_movers.sort(key=lambda x: -(x["max_favorable"] or 0))
    true_strong_longs = set(l["symbol"] for l in long_movers[:6])
    
    # Model A: WINNER-type leaders ranked by day_return_pct (proxy for strategy-gated)
    model_a_sel = [l for l in day_leaders if l["leader_type"] == "WINNER"]
    model_a_sel.sort(key=lambda x: -(x["day_return_pct"] or 0))
    model_a_top6 = set(l["symbol"] for l in model_a_sel[:6])
    
    # Model B: knowledge-only using signal_births base_score for this date
    model_b_sel = [s for s in day_sb if s["expected_move_direction"] in ("LONG", "UP", "BUY")]
    model_b_sel.sort(key=lambda x: -(float(x["base_score"]) if x["base_score"] else 0))
    model_b_syms = [s["symbol"].replace(".NS", "") for s in model_b_sel[:20]]
    # From top 20, pick 6 with highest score
    model_b_top6 = set(model_b_syms[:6])
    
    # Model C: knowledge score + sector strength feature
    def model_c_score(ldr):
        fs = ldr.get("features", {})
        sector_str = float(fs.get("sector_strength", 0.5) or 0.5)
        vol_ratio  = float(fs.get("volume_ratio", 1.0) or 1.0)
        above_dma  = float(fs.get("above_20dma", 0) or 0)
        return (sector_str * 0.4 + vol_ratio * 0.3 + above_dma * 0.3)
    
    model_c_sel = [l for l in day_leaders if l["leader_type"] == "WINNER"]
    model_c_sel.sort(key=model_c_score, reverse=True)
    model_c_top6 = set(l["symbol"] for l in model_c_sel[:6])
    
    # Model D: feature combination (volume_ratio + above_20dma + rs_vs_nifty_5d)
    def model_d_score(ldr):
        fs = ldr.get("features", {})
        vol  = float(fs.get("volume_ratio", 1.0) or 1.0)
        adma = float(fs.get("above_20dma", 0) or 0)
        rs5d = float(fs.get("rs_vs_nifty_5d", 0) or 0)
        return vol * 0.5 + adma * 0.3 + rs5d * 0.2
    
    model_d_sel = sorted(day_leaders, key=model_d_score, reverse=True)
    model_d_top6 = set(l["symbol"] for l in model_d_sel[:6])
    
    if not true_strong_longs:
        continue
    
    def precision_at_k(selected, truth):
        if not selected:
            return 0.0
        hits = len(selected & truth)
        return round(hits / len(selected), 4)
    
    model_results["A"].append(precision_at_k(model_a_top6, true_strong_longs))
    model_results["B"].append(precision_at_k(model_b_top6, true_strong_longs))
    model_results["C"].append(precision_at_k(model_c_top6, true_strong_longs))
    model_results["D"].append(precision_at_k(model_d_top6, true_strong_longs))

print("\n  Model performance (Precision@6 for strong mover selection):")
for m, scores in model_results.items():
    if scores:
        avg = safe_mean(scores)
        ci = bootstrap_ci(scores)
        print(f"    Model {m}: avg_precision@6={avg:.3f} n_days={len(scores)} CI_95={ci}")

# ─── SECTION 6: INFORMATION COMBINATION ANALYSIS ──────────────────────────────
print("\n=== SECTION 6: INFORMATION COMBINATION ANALYSIS ===")

# Use feature_differentials: winner vs control stock, and which features differ most
diff_features = defaultdict(list)  # feature_name → list of (winner_val, control_val, outcome_gap_5d)
for d in feature_diffs:
    try:
        diffs = json.loads(d["differing_features"]) if isinstance(d["differing_features"], str) else d["differing_features"]
        if diffs:
            for fd in diffs:
                feat = fd.get("feature", "unknown")
                wv = fd.get("winner_value")
                cv = fd.get("control_value")
                gap = d["outcome_gap_5d"]
                if wv is not None and cv is not None and gap is not None:
                    diff_features[feat].append({
                        "winner_val": float(wv),
                        "control_val": float(cv),
                        "outcome_gap": float(gap),
                    })
    except Exception:
        continue

combo_analysis = {}
for feat, entries in sorted(diff_features.items(), key=lambda x: -len(x[1]))[:15]:
    if len(entries) < 10:
        continue
    winner_vals  = [e["winner_val"] for e in entries]
    control_vals = [e["control_val"] for e in entries]
    outcome_gaps = [e["outcome_gap"] for e in entries]
    combo_analysis[feat] = {
        "n_observations": len(entries),
        "avg_winner_val": safe_mean(winner_vals),
        "avg_control_val": safe_mean(control_vals),
        "avg_outcome_gap_5d": safe_mean(outcome_gaps),
        "winner_ci": bootstrap_ci(winner_vals),
        "control_ci": bootstrap_ci(control_vals),
    }

print(json.dumps(combo_analysis, indent=2))

# ─── SECTION 7: STRATEGY WIN RATE vs KNOWLEDGE SCORE CORRELATION ──────────────
print("\n=== SECTION 7: STRATEGY PERFORMANCE FROM LEARNING DB ===")

strategy_perf = {}
if isinstance(learning_data, dict):
    for key, val in learning_data.items():
        if isinstance(val, dict) and "win_rate" in val:
            strategy_perf[key] = {
                "win_rate": val.get("win_rate"),
                "trades": val.get("total_trades") or val.get("trade_count"),
                "avg_pnl": val.get("avg_pnl") or val.get("avg_return"),
                "sharpe": val.get("sharpe"),
            }

print(json.dumps(strategy_perf, indent=2))

# ─── SECTION 8: REGIME-STRATIFIED ANALYSIS ────────────────────────────────────
print("\n=== SECTION 8: REGIME-STRATIFIED ANALYSIS ===")

regime_sb = defaultdict(list)
for s in sb_with_outcomes:
    r = s["regime_at_birth"] or "unknown"
    if s["actual_move_pct"] is not None:
        regime_sb[r].append({
            "actual": float(s["actual_move_pct"]),
            "peak": float(s["peak_move_pct"]) if s["peak_move_pct"] else None,
            "base_score": float(s["base_score"]) if s["base_score"] else None,
            "traded": s["trade_executed"] == 1,
            "direction": s["expected_move_direction"],
        })

regime_analysis = {}
for regime, entries in regime_sb.items():
    if len(entries) < 5:
        continue
    actuals = [e["actual"] for e in entries]
    traded  = [e["actual"] for e in entries if e["traded"]]
    not_traded = [e["actual"] for e in entries if not e["traded"]]
    regime_analysis[regime] = {
        "n_total": len(entries),
        "n_traded": len(traded),
        "n_blocked": len(not_traded),
        "traded_avg_move": safe_mean(traded),
        "blocked_avg_move": safe_mean(not_traded),
        "all_avg_move": safe_mean(actuals),
        "traded_cap_2pct": capture_rate([abs(m) for m in traded], 2.0) if traded else None,
        "blocked_cap_2pct": capture_rate([abs(m) for m in not_traded], 2.0) if not_traded else None,
    }

print(json.dumps(regime_analysis, indent=2))

# ─── SECTION 9: DECISION QUALITY ANALYSIS ─────────────────────────────────────
print("\n=== SECTION 9: DECISION QUALITY (ct_decisions) ===")

# Approved vs rejected decisions and their debate scores
approved = [d for d in decisions if d["decision"] == "APPROVED"]
rejected = [d for d in decisions if d["decision"] == "REJECTED"]

def decision_stats(decs, label):
    if not decs:
        return {"label": label, "n": 0}
    conf_scores = [float(d["confidence"]) for d in decs if d["confidence"] is not None]
    tech_scores = [float(d["technical_score"]) for d in decs if d["technical_score"]]
    risk_scores = [float(d["risk_score"]) for d in decs if d["risk_score"]]
    macro_scores = [float(d["macro_score"]) for d in decs if d["macro_score"]]
    by_strategy = defaultdict(int)
    for d in decs:
        by_strategy[d["strategy"] or "UNKNOWN"] += 1
    return {
        "label": label,
        "n": len(decs),
        "avg_confidence": safe_mean(conf_scores),
        "avg_technical": safe_mean(tech_scores),
        "avg_risk": safe_mean(risk_scores),
        "avg_macro": safe_mean(macro_scores),
        "strategy_distribution": dict(sorted(by_strategy.items(), key=lambda x: -x[1])[:10]),
    }

dec_approved_stats = decision_stats(approved, "APPROVED")
dec_rejected_stats = decision_stats(rejected, "REJECTED")
print(json.dumps(dec_approved_stats, indent=2))
print(json.dumps(dec_rejected_stats, indent=2))

# ─── SECTION 10: TODAY'S BLOCKED SIGNALS INTEGRATION ─────────────────────────
print("\n=== SECTION 10: TODAY'S BLOCKED SIGNALS (from audit files) ===")

today_blocked_outcomes = {
    "APOLLOHOSP": {"grade": "A", "mfe": 3.66, "move_at_11h": 2.77, "dir": "BUY", "score": 0.9441, "sector": "Healthcare"},
    "MRF":        {"grade": "B", "mfe": 0.45, "move_at_11h": 0.36, "dir": "BUY", "score": 0.8951, "sector": "Auto"},
    "HDFCAMC":    {"grade": "D", "mfe": 0.05, "move_at_11h": -0.63, "dir": "BUY", "score": 0.8918, "sector": "Finance"},
    "PAGEIND":    {"grade": "D", "mfe": -1.61, "move_at_11h": -2.70, "dir": "BUY", "score": 0.8810, "sector": "Consumer"},
    "BIOCON":     {"grade": "D", "mfe": -0.69, "move_at_11h": -0.96, "dir": "BUY", "score": 0.8624, "sector": "Pharma"},
    "ICICIBANK":  {"grade": "C", "mfe": 0.51, "move_at_11h": 0.26,  "dir": "BUY", "score": 0.8624, "sector": "Finance"},
    "AMBUJACEM":  {"grade": "D", "mfe": -0.07, "move_at_11h": -0.70, "dir": "BUY", "score": 0.8426, "sector": "Cement"},
    "MUTHOOTFIN": {"grade": "D", "mfe": -0.80, "move_at_11h": -0.94, "dir": "BUY", "score": 0.8401, "sector": "Finance"},
    "FORTIS":     {"grade": "B", "mfe": 0.81, "move_at_11h": 0.49,  "dir": "BUY", "score": 0.8276, "sector": "Healthcare"},
    "GODREJPROP": {"grade": "D", "mfe": -0.75, "move_at_11h": -1.63, "dir": "BUY", "score": 0.7524, "sector": "Realty"},
    "CROMPTON":   {"grade": "D", "mfe": -1.09, "move_at_11h": -1.43, "dir": "BUY", "score": 0.7136, "sector": "Consumer"},
    "ALKEM":      {"grade": "D", "mfe": -1.25, "move_at_11h": -1.70, "dir": "BUY", "score": 0.7056, "sector": "Pharma"},
    "SBILIFE":    {"grade": "D", "mfe": -1.81, "move_at_11h": -2.00, "dir": "BUY", "score": 0.6859, "sector": "Insurance"},
    "ITC":        {"grade": "C", "mfe": -0.14, "move_at_11h": -0.16, "dir": "BUY", "score": 0.6832, "sector": "FMCG"},
    "TATASTEEL":  {"grade": "D", "mfe": -1.63, "move_at_11h": -1.75, "dir": "BUY", "score": 0.6818, "sector": "Metals"},
    "INOXWIND":   {"grade": "D", "mfe": -0.61, "move_at_11h": -1.01, "dir": "BUY", "score": 0.6722, "sector": "Energy"},
    "VOLTAS":     {"grade": "B", "mfe": 2.07,  "move_at_11h": 1.91,  "dir": "BUY", "score": 0.6648, "sector": "Consumer"},
    "NHPC":       {"grade": "C", "mfe": 0.32,  "move_at_11h": -0.40, "dir": "BUY", "score": 0.6428, "sector": "Power"},
    "BSE":        {"grade": "D", "mfe": -0.23, "move_at_11h": -1.59, "dir": "BUY", "score": 0.6065, "sector": "Finance"},
    "TATACOMM":   {"grade": "C", "mfe": 0.24,  "move_at_11h": 0.06,  "dir": "BUY", "score": 0.5947, "sector": "Telecom"},
    "DIXON":      {"grade": "C", "mfe": 0.60,  "move_at_11h": 0.25,  "dir": "BUY", "score": 0.5706, "sector": "Electronics"},
    "HDFCLIFE":   {"grade": "C", "mfe": 0.13,  "move_at_11h": -0.20, "dir": "BUY", "score": 0.5354, "sector": "Insurance"},
    "ADANIENT":   {"grade": "B", "mfe": 1.40,  "move_at_11h": 1.23,  "dir": "BUY", "score": 0.5351, "sector": "Conglomerate"},
    "DABUR":      {"grade": "C", "mfe": 0.07,  "move_at_11h": -0.23, "dir": "BUY", "score": 0.5326, "sector": "FMCG"},
    "CUMMINSIND": {"grade": "C", "mfe": 0.45,  "move_at_11h": -0.05, "dir": "BUY", "score": 0.5292, "sector": "Engineering"},
    "COALINDIA":  {"grade": "D", "mfe": -0.12, "move_at_11h": -0.85, "dir": "BUY", "score": None,   "sector": "Mining"},
    "ULTRACEMCO": {"grade": "D", "mfe": -0.43, "move_at_11h": -0.84, "dir": "BUY", "score": None,   "sector": "Cement"},
    "POWERGRID":  {"grade": "C", "mfe": 0.19,  "move_at_11h": 0.15,  "dir": "BUY", "score": None,   "sector": "Power"},
}

grade_counts = defaultdict(int)
for sym, d in today_blocked_outcomes.items():
    grade_counts[d["grade"]] += 1

today_summary = {
    "date": "2026-08-14",
    "n_blocked": len(today_blocked_outcomes),
    "grade_A": grade_counts["A"],
    "grade_B": grade_counts["B"],
    "grade_C": grade_counts["C"],
    "grade_D": grade_counts["D"],
    "useful_rate": round((grade_counts["A"] + grade_counts["B"]) / len(today_blocked_outcomes), 4),
    "bad_rate": round(grade_counts["D"] / len(today_blocked_outcomes), 4),
    "avg_mfe_all": safe_mean([d["mfe"] for d in today_blocked_outcomes.values()]),
    "avg_mfe_useful": safe_mean([d["mfe"] for d in today_blocked_outcomes.values() if d["grade"] in ("A","B")]),
    "avg_mfe_bad": safe_mean([d["mfe"] for d in today_blocked_outcomes.values() if d["grade"] == "D"]),
    "score_grade_a_b": safe_mean([d["score"] for d in today_blocked_outcomes.values() if d["grade"] in ("A","B") and d["score"]]),
    "score_grade_d": safe_mean([d["score"] for d in today_blocked_outcomes.values() if d["grade"] == "D" and d["score"]]),
}
print(json.dumps(today_summary, indent=2))

# ─── SECTION 11: COMPOSITE INCREMENTAL VALUE ANALYSIS ─────────────────────────
print("\n=== SECTION 11: STRATEGY INCREMENTAL VALUE ANALYSIS ===")

# Compare: signals that reached debate layer (ct_decisions) vs all signal_births
# "Strategy value" = does the strategy gate improve the quality of what reaches the debate layer?

# We need outcomes for ct_decisions approved signals → paper_trades
# Build a map from paper_trades
trade_outcome_by_symbol = {}
for t in paper_trades:
    sym = t.get("symbol", "")
    event = t.get("event", "")
    pnl = t.get("pnl", "")
    exit_price = t.get("exit_price", "")
    if sym and pnl:
        try:
            trade_outcome_by_symbol[sym] = float(pnl)
        except:
            pass

# ct_decisions approved → look for outcomes in paper trades
ct_approved_syms = set(d["symbol"] for d in approved)
traded_with_pnl = {sym: pnl for sym, pnl in trade_outcome_by_symbol.items() if sym in ct_approved_syms}

print(f"  ct_decisions approved: {len(approved)}")
print(f"  ct_approved with P&L data: {len(traded_with_pnl)}")

# Compute expected value metrics for the approved path
approved_pnls = list(traded_with_pnl.values())
approved_wins = sum(1 for p in approved_pnls if p > 0)
approved_wr = round(approved_wins / len(approved_pnls), 4) if approved_pnls else None

incremental_value = {
    "strategy_gate_approved_count": len(approved),
    "strategy_gate_rejected_count": len(rejected),
    "gate_pass_rate": round(len(approved) / (len(approved) + len(rejected)), 4) if decisions else None,
    "matched_trade_outcomes": len(approved_pnls),
    "actual_win_rate_approved": approved_wr,
    "avg_pnl_approved": safe_mean(approved_pnls),
    "signal_births_all_avg_move": model_all["avg_actual_move_pct"],
    "signal_births_traded_avg_move": model_a_sb["avg_actual_move_pct"],
    "signal_births_blocked_avg_move": model_b_sb["avg_actual_move_pct"],
    "today_blocked_useful_rate": today_summary["useful_rate"],
    "historical_live_strategy_wr": "20% (from StrategyHealthMonitor logs)",
    "governance_threshold_wr": "50%",
}
print(json.dumps(incremental_value, indent=2))

# ─── WRITE OUTPUT FILES ────────────────────────────────────────────────────────
print("\n=== WRITING OUTPUT FILES ===")

# 1. knowledge_vs_strategy_results.json
results_json = {
    "metadata": {"date": "2026-08-14", "version": "001", "read_only": True},
    "architecture": arch,
    "model_a_signal_births": model_a_sb,
    "model_b_signal_births": model_b_sb,
    "all_signals": model_all,
    "score_bucket_analysis": score_analysis,
    "regime_stratified": regime_analysis,
    "decision_approved_stats": dec_approved_stats,
    "decision_rejected_stats": dec_rejected_stats,
    "today_blocked_summary": today_summary,
    "incremental_value": incremental_value,
    "model_precision_at_6": {m: {"avg": safe_mean(v), "n_days": len(v), "ci_95": bootstrap_ci(v)} for m, v in model_results.items() if v},
}
with open(f"{OUT_DIR}/knowledge_vs_strategy_results.json", "w") as f:
    json.dump(results_json, f, indent=2)
print(f"  Written: knowledge_vs_strategy_results.json")

# 2. knowledge_combination_analysis.json
combo_output = {
    "feature_comparison_winner_vs_control": feature_comparison,
    "feature_differentials_top15": combo_analysis,
    "note": "winner_mean - control_mean > 0 means winners had higher value of this feature",
}
with open(f"{OUT_DIR}/knowledge_combination_analysis.json", "w") as f:
    json.dump(combo_output, f, indent=2)
print(f"  Written: knowledge_combination_analysis.json")

# 3. strategy_incremental_value_summary.csv
csv_rows = []
metrics = [
    ("directional_accuracy_model_a", model_a_sb.get("directional_accuracy"), "Model A (strategy-gated traded signals)"),
    ("directional_accuracy_model_b", model_b_sb.get("directional_accuracy"), "Model B (knowledge-only untraded signals)"),
    ("capture_2pct_model_a",         model_a_sb.get("capture_2pct"),         "Model A: ≥2% move capture rate"),
    ("capture_2pct_model_b",         model_b_sb.get("capture_2pct"),         "Model B: ≥2% move capture rate"),
    ("capture_3pct_model_a",         model_a_sb.get("capture_3pct"),         "Model A: ≥3% move capture rate"),
    ("capture_3pct_model_b",         model_b_sb.get("capture_3pct"),         "Model B: ≥3% move capture rate"),
    ("avg_actual_move_model_a",      model_a_sb.get("avg_actual_move_pct"),  "Model A: avg actual move pct"),
    ("avg_actual_move_model_b",      model_b_sb.get("avg_actual_move_pct"),  "Model B: avg actual move pct"),
    ("avg_base_score_model_a",       model_a_sb.get("avg_base_score"),       "Model A: avg knowledge base_score"),
    ("avg_base_score_model_b",       model_b_sb.get("avg_base_score"),       "Model B: avg knowledge base_score"),
    ("model_c_precision_at_6",       safe_mean(model_results.get("C", [])),  "Model C precision@6 for strong mover selection"),
    ("model_d_precision_at_6",       safe_mean(model_results.get("D", [])),  "Model D precision@6 for strong mover selection"),
    ("ct_gate_pass_rate",            incremental_value["gate_pass_rate"],    "Strategy gate pass rate (approved/total)"),
    ("today_blocked_useful_rate",    today_summary["useful_rate"],           "2026-08-14 blocked signals: useful rate (A+B)"),
    ("today_blocked_bad_rate",       today_summary["bad_rate"],              "2026-08-14 blocked signals: bad rate (D)"),
    ("strategy_live_win_rate",       0.20,                                   "Mean_Reversion live win rate (StrategyHealthMonitor)"),
    ("governance_threshold",         0.50,                                   "Governance win rate threshold to re-enable strategy"),
]
with open(f"{OUT_DIR}/strategy_incremental_value_summary.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["metric", "value", "description"])
    for name, val, desc in metrics:
        writer.writerow([name, val, desc])
print(f"  Written: strategy_incremental_value_summary.csv")

# 4. Today's blocked signals JSON
with open(f"{OUT_DIR}/today_blocked_signals.json", "w") as f:
    json.dump(today_blocked_outcomes, f, indent=2)
print(f"  Written: today_blocked_signals.json")

print("\n=== ANALYSIS COMPLETE ===")
print(f"Output directory: {OUT_DIR}")

# Print key summary for report
print("\n--- KEY FINDINGS FOR REPORT ---")
print(f"Model A (strategy-gated): dir_acc={model_a_sb.get('directional_accuracy')}, cap_2pct={model_a_sb.get('capture_2pct')}, n={model_a_sb.get('n')}")
print(f"Model B (knowledge-only): dir_acc={model_b_sb.get('directional_accuracy')}, cap_2pct={model_b_sb.get('capture_2pct')}, n={model_b_sb.get('n')}")
print(f"Model A avg base_score={model_a_sb.get('avg_base_score')}, Model B avg base_score={model_b_sb.get('avg_base_score')}")
print(f"Score bucket analysis: {score_analysis}")
print(f"Regime analysis: {json.dumps(regime_analysis, indent=2)}")
print(f"Precision@6 by model: {[(m, safe_mean(v)) for m, v in model_results.items() if v]}")
