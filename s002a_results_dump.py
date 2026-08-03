"""Print comprehensive Study 2A results for document generation."""
import json
from pathlib import Path

with open("data/study002a_results.json") as f:
    r = json.load(f)

print("=== STAGE 4: ALL 9 WF-VALIDATED WINNER DNA PATTERNS ===")
for i, p in enumerate(r["stage4_winner_dna"]["dna_patterns"], 1):
    print(f"\nPattern {i}: {p['validation']}")
    print(f"  Conditions: {' AND '.join(p['conditions'])}")
    print(f"  train: conf={p['train_confidence']:.4f}  lift={p['train_lift']:.4f}  support={p['train_support']:.5f}")
    print(f"  test:  conf={p['test_confidence']:.4f}  lift={p['test_lift']:.4f}  n_match={p['test_n_match']}  n_win={p['test_n_winners']}")
    print(f"  avg_forward_return={p['avg_forward_return']:.6f}  n_conditions={p['n_conditions']}")

print("\n=== STAGE 5: LOSER DNA PATTERNS ===")
for p in r["stage5_loser_dna"]["loser_dna_patterns"]:
    print(f"  conf={p['confidence']:.4f}  lift={p['lift']:.4f}  support={p['support']:.5f}")
    print(f"  n={p['n_samples']}  conditions: {' AND '.join(p['conditions'])}")

print("\n=== STAGE 7: FEATURE DECILE HIGHLIGHTS ===")
for feat in ["atr_14", "intra_range", "mom_5d", "mom_1d", "avg_conviction"]:
    buckets = r["stage7_deciles"]["decile_analysis"].get(feat, [])
    if buckets:
        print(f"\n{feat}:")
        for b in buckets:
            bar = "█" * int(b["winner_rate"] * 50)
            print(f"  D{b['decile']:02d} [{b['lo']:.4f}-{b['hi']:.4f}] n={b['n']:6d} WR={b['winner_rate']:.3f} lift={b['lift']:.2f}x {bar}")

print("\n=== STAGE 6: CLUSTER DETAILS ===")
for c in r["stage6_clusters"]["clusters"]:
    print(f"\n[{c['label']}]  n={c['size']}  avg_return={c['avg_return']:.6f}")
    print(f"  pct_of_winners={c['pct_of_winners']:.3f}  dominant_regime={c['dominant_regime']}")
    print(f"  top_sector={c['top_sector']}")
    print("  top_5_features:")
    for tf in c["top_5_features"]:
        print(f"    {tf['feature']}: centroid={tf['centroid']}")
    print("  sector_dist:", c["sector_dist"])
    print("  regime_dist:", c["regime_dist"])

print("\n=== STAGE 3: FULL TOP-20 RANKING ===")
for r2 in r["stage3_ranking"]["full_ranking"][:20]:
    fs = r["stage2_feat_stats"][r2["feature"]]
    wd = fs.get("winners", {})
    od = fs.get("ordinary", {})
    ld = fs.get("losers", {})
    print(f"  {r2['rank']:2d}. {r2['feature']:<22}  combined={r2['combined_score']:.4f}  "
          f"mi={r2['mi']:.5f}  rf={r2['rf_importance']:.5f}  d={r2['cohens_d_w_vs_l']:+.4f}  "
          f"p={r2['mwu_pval_w_vs_l']:.2e}")
    print(f"        W.mean={wd.get('mean',0):.5f}  O.mean={od.get('mean',0):.5f}  "
          f"L.mean={ld.get('mean',0):.5f}")

print("\n=== MONOTONE FEATURES ===")
print("Monotone-increasing:", r["stage7_deciles"]["monotone_increasing"])
print("Monotone-decreasing:", r["stage7_deciles"]["monotone_decreasing"])
print("Extreme findings:", r["stage7_deciles"]["extreme_findings"])

print("\n=== WF-REJECTED PATTERNS ===")
for p in r["stage4_winner_dna"].get("wf_rejected_patterns", []):
    print(f"  train_conf={p['train_confidence']:.3f}  test_conf={p['test_confidence']:.3f}  "
          f"reason: WF failed")

print("\n=== STAGE 4 METADATA ===")
dna = r["stage4_winner_dna"]
print(f"  base_rate={dna['base_rate']}  min_support={dna['min_support']}  "
      f"min_confidence={dna['min_confidence']}  min_lift={dna['min_lift']}")
print(f"  train: {dna['train_dates']} to {dna['train_end']}")
print(f"  test:  {dna['test_start']} to {dna['test_end']}")
print(f"  leaves_found={dna['n_leaves_found']}  approved={dna['n_approved_initial']}  "
      f"wf_rejected={len(dna.get('wf_rejected_patterns',[]))}")
