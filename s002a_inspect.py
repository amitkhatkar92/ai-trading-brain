"""Inspect Study 2A results and diagnose pattern rejection."""
import json

with open("data/study002a_results.json") as f:
    r = json.load(f)

print("=== GROUP DISTRIBUTION ===")
g = r["stage1_groups"]
print(f"  n={g['distribution']['n']}  mean={g['distribution']['mean']:.4f}  std={g['distribution']['std']:.4f}")
print(f"  Fixed threshold: winner>={0.01:.3f}  loser<={-0.01:.3f}")
print(f"  Winners: {g['counts_fixed']['A_winners']} ({g['pct_winners_fixed']*100:.1f}%)")
print(f"  Ordinary: {g['counts_fixed']['B_ordinary']}")
print(f"  Losers: {g['counts_fixed']['C_losers']} ({g['pct_losers_fixed']*100:.1f}%)")

print("\n=== TOP 20 FEATURES ===")
for i, feat in enumerate(r["stage3_ranking"]["full_ranking"][:20], 1):
    fs = r["stage2_feat_stats"][feat["feature"]]
    wd = fs.get("winners", {})
    ld = fs.get("losers", {})
    print(f"  {i:2d}. {feat['feature']:<22}  combined={feat['combined_score']:.4f}  "
          f"d(W-L)={feat['cohens_d_w_vs_l']:+.3f}  "
          f"W.mean={wd.get('mean','?'):.4f}  L.mean={ld.get('mean','?'):.4f}  "
          f"p={feat['mwu_pval_w_vs_l']:.2e}")

print("\n=== ALL REJECTED DNA PATTERNS (top 10) ===")
for p in r["stage4_winner_dna"]["rejected_patterns"][:10]:
    print(f"  conf={p['confidence']:.3f}  lift={p['lift']:.2f}  "
          f"sup={p['support']:.4f}  n={p['n_samples']}  "
          f"reason=[{p.get('rejected_reason','ok')}]")
    print(f"    {' AND '.join(p['conditions'][:3])}")

print("\n=== CLUSTER SUMMARY ===")
for c in r["stage6_clusters"]["clusters"]:
    print(f"  [{c['label']}]  n={c['size']}  avg_ret={c['avg_return']:.4f}  regime={c['dominant_regime']}")
    print(f"    Top features:", [f['feature'] for f in c['top_5_features']])
