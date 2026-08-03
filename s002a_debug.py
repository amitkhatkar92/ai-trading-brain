"""Deep debug: print actual DT leaf values for Study 2A."""
import json
import sqlite3, sys, os, numpy as np
from pathlib import Path
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

with open("data/study002a_results.json") as f:
    r = json.load(f)

# Load the feature data to re-run DT and inspect leaves directly
from study002a_pipeline import (
    _open_db, _extract_features_from_db, classify_groups, REPLAY_DB, S002_DB, NIFTY_SYM
)

print("Loading data...")
conn = _open_db(REPLAY_DB)
d_range = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM ohlcv_daily WHERE symbol != ?", (NIFTY_SYM,)).fetchone()
obs_main = _extract_features_from_db(conn, "replay_5yr")
conn.close()

conn2 = _open_db(S002_DB)
obs_s002_raw = _extract_features_from_db(conn2, "study002")
conn2.close()
replay_max = d_range[1]
obs_s002 = [o for o in obs_s002_raw if o["date"] > replay_max]
obs = obs_main + obs_s002
classify_groups(obs)

print(f"Loaded {len(obs)} observations")
print(f"Base rate: {sum(1 for o in obs if o['group']=='A') / len(obs):.4f}")

feature_names = list(obs[0]["features"].keys())
top_feats = r["stage3_ranking"]["top10"]
top_idx = [feature_names.index(f) for f in top_feats if f in feature_names]

X = np.array([[o["features"][f] for f in feature_names] for o in obs])
y = np.array([1 if o["group"] == "A" else 0 for o in obs])
dates = np.array([o["date"] for o in obs])
unique_dates = sorted(set(dates))
split_idx = int(len(unique_dates) * 0.80)
train_dates = set(unique_dates[:split_idx])
train_mask = np.array([d in train_dates for d in dates])

Xt_train = X[train_mask][:, top_idx]
y_train = y[train_mask]

from sklearn.tree import DecisionTreeClassifier, _tree

print(f"\nTraining DT on {len(y_train)} samples, base_rate={np.mean(y_train):.4f}")
dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=50, class_weight=None, random_state=42)
dt.fit(Xt_train, y_train)
print(f"DT classes: {dt.classes_}  winner_idx: {list(dt.classes_).index(1)}")
winner_idx = list(dt.classes_).index(1)

tree = dt.tree_
leaves = []

def _walk(node, conditions):
    if tree.feature[node] == _tree.TREE_UNDEFINED:
        n_total = int(tree.n_node_samples[node])
        val0 = tree.value[node][0][0]
        val1 = tree.value[node][0][winner_idx]
        n_win = int(val1)
        conf = val1 / (val0 + val1) if (val0 + val1) > 0 else 0
        leaves.append({
            "conditions": list(conditions), "n": n_total, "n_win": n_win,
            "val0": round(float(val0), 2), "val1": round(float(val1), 2),
            "confidence": round(float(conf), 4),
            "support": round(n_total / len(y_train), 4),
        })
        return
    fname = top_feats[tree.feature[node]]
    thresh = round(tree.threshold[node], 4)
    _walk(tree.children_left[node],  conditions + [f"{fname} <= {thresh}"])
    _walk(tree.children_right[node], conditions + [f"{fname} > {thresh}"])

_walk(0, [])

# Print all leaves sorted by confidence
print(f"\nAll {len(leaves)} DT leaves (sorted by confidence desc):")
for l in sorted(leaves, key=lambda x: -x["confidence"])[:15]:
    print(f"  conf={l['confidence']:.4f}  lift={l['confidence']/np.mean(y_train):.3f}  "
          f"sup={l['support']:.4f}  n={l['n']}  n_win={l['n_win']}  "
          f"val0={l['val0']}  val1={l['val1']}")
    for c in l["conditions"]:
        print(f"    {c}")

# Feature decile analysis (key insight)
print("\n\n=== FEATURE DECILE ANALYSIS ===")
for feat in r["stage3_ranking"]["top5"]:
    vals = np.array([o["features"][feat] for o in obs])
    grps = np.array([1 if o["group"] == "A" else 0 for o in obs])
    
    deciles = np.percentile(vals, np.arange(0, 110, 10))
    print(f"\n{feat}:")
    for i in range(10):
        lo, hi = deciles[i], deciles[i+1]
        mask = (vals >= lo) & (vals < hi)
        n = mask.sum()
        wr = grps[mask].mean() if n > 0 else 0
        print(f"  [{lo:.4f}-{hi:.4f}]  n={n}  WinRate={wr:.3f}")
