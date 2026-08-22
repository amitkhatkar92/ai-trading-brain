"""Complete evidence inventory script."""
import json, pandas as pd
from pathlib import Path

REPORT = Path("reports/mover_discovery_v3")

# ── Knowledge second pass OOS ──────────────────────────────────────────────
r3 = json.loads((REPORT / "v3_knowledge_second_pass_results.json").read_text())
sp = r3.get("results_by_split", {})
oos_k = sp.get("OOS", {})
print("=== KNOWLEDGE 2nd PASS OOS ===")
for m, v in oos_k.items():
    if isinstance(v, dict):
        up = v.get("UP", {})
        dn = v.get("DOWN", {})
        if up.get("n"):
            print(f"  {m}: UP dir={up.get('dir_acc')} ge2={up.get('ge2_rate')} n={up.get('n')}"
                  f"  | DOWN dir={dn.get('dir_acc')} ge2={dn.get('ge2_rate')} n={dn.get('n')}")
print("verdict:", r3.get("verdict"))
print("know_top5_vs_v3_delta_UP:", r3.get("know_top5_vs_v3_top5_up_dir_delta"))
print()

# ── Orthogonal direction OOS ───────────────────────────────────────────────
r4 = json.loads((REPORT / "v3_orthogonal_direction_results.json").read_text())
print("=== ORTHOGONAL DIRECTION ===")
print("Keys:", list(r4.keys())[:10])
oos_o = r4.get("oos", {})
for k in ["UP", "DOWN"]:
    sub = oos_o.get(k, {})
    if isinstance(sub, dict):
        for m, v in sub.items():
            if isinstance(v, dict) and v.get("n"):
                print(f"  {k} {m}: dir={v.get('dir_acc')} ge2={v.get('ge2_rate')} n={v.get('n')}")
verdict_o = r4.get("verdict", r4.get("primary_verdict", ""))
print("verdict:", verdict_o)
print()

# ── Shadow audit ───────────────────────────────────────────────────────────
sa = json.loads((REPORT / "mover_discovery_v3_shadow_results.json").read_text())
print("=== V3 SHADOW AUDIT ===")
print("Keys:", list(sa.keys()))
for k, v in sa.items():
    if isinstance(v, dict) or isinstance(v, (int, float, str)):
        if "v3" in k.lower() or "pool" in k.lower() or "recall" in k.lower() or "hit" in k.lower():
            print(f"  {k}:", v)
print()

# ── V3 retrospective aggregate ────────────────────────────────────────────
r1 = json.loads((REPORT / "mover_discovery_v3_results.json").read_text())
print("=== V3 RETROSPECTIVE SUMMARY ===")
in_s = r1.get("in_sample", {})
oos_v = r1.get("oos", {})
print("in_sample keys:", list(in_s.keys()) if isinstance(in_s, dict) else in_s)
print("oos keys:", list(oos_v.keys()) if isinstance(oos_v, dict) else oos_v)
print("verdicts:", r1.get("verdicts"))
print("groups:", r1.get("groups"))
print()

# ── Pool analysis ──────────────────────────────────────────────────────────
pool = pd.read_csv(REPORT / "mover_discovery_v3_pool_analysis.csv")
print("=== POOL ANALYSIS ===")
print("cols:", pool.columns.tolist())
print(pool.head(5).to_string())
print()

# ── V3 retro aggregate ─────────────────────────────────────────────────────
retro_agg = json.loads((REPORT / "v3_retro_aggregate.json").read_text())
print("=== V3 RETRO AGGREGATE ===")
print("Keys:", list(retro_agg.keys()))
for k, v in retro_agg.items():
    print(f"  {k}:", v)
