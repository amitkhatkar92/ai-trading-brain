import json
with open("data/re001a_results.json") as f:
    r = json.load(f)

b   = r["baseline"]
f2  = r["final"]
s1  = r["stage1"]
s26 = r["stage2_6"]
s6m = r["stage6_meta"]
s7  = r["stage7"]

print("=== BASELINE ===")
print(f"  feat_total={b['feat_total']}  labeled={b['feat_labeled']}  symbols={b['feat_symbols']}")
print(f"  edges={b['edges_total']} by_status={b['edges_by_status']}")
print(f"  strats={b['strats_total']}  perf={b['perf_tracked']}  ml={b['ml_records']}")

print("\n=== STAGE 1 ===")
for k, v in s1.items():
    print(f"  {k}: {v}")

print("\n=== STAGE 2-6 EDE ===")
print(f"  edges_before={s26['edges_before']}  edges_after={s26['edges_after']}")
print(f"  new_edges={s26['new_edges']}")
print(f"  updated_edges={s26['updated_edges']}")
print(f"  removed_edges={s26['removed_edges']}")
print(f"  edges_by_status_after={s26['edges_by_status_after']}")
print(f"  strats_before={s26['strats_before']}  strats_after={s26['strats_after']}")
print(f"  new_strats={s26['new_strats']}")

print("\n=== STAGE 6 META ===")
for k, v in s6m.items():
    print(f"  {k}: {v}")

print("\n=== STAGE 7 FINAL ===")
for k, v in s7.items():
    print(f"  {k}: {v}")

print("\n=== FINAL vs BASELINE ===")
print(f"  feat:    {b['feat_total']}  ->  {f2['feat_total']}  (+{f2['feat_total']-b['feat_total']})")
print(f"  labeled: {b['feat_labeled']} ->  {f2['feat_labeled']}  (+{f2['feat_labeled']-b['feat_labeled']})")
print(f"  edges:   {b['edges_total']}  ->  {f2['edges_total']}")
print(f"  strats:  {b['strats_total']}  ->  {f2['strats_total']}")
print(f"  elapsed: {r['elapsed_s']:.1f}s")
