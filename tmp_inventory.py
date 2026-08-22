"""Inventory all existing research results for consolidation."""
import pandas as pd
import json
from pathlib import Path

REPORT = Path("reports/mover_discovery_v3")

# ── 1. V3 Retrospective ────────────────────────────────────────────────────
r1 = json.loads((REPORT / "mover_discovery_v3_results.json").read_text())
print("=== V3 RETROSPECTIVE REPLAY ===")
print("Keys top-level:", list(r1.keys()))
agg = r1.get("aggregate", r1.get("overall", {}))
print("aggregate:", agg)
print()

# ── 2. Post-open selection ─────────────────────────────────────────────────
r2 = json.loads((REPORT / "post_open_selection_results.json").read_text())
print("=== POST-OPEN SELECTION ===")
print("Keys:", list(r2.keys()))
print()
models = r2.get("models", {})
for m, v in models.items():
    if not isinstance(v, dict):
        continue
    oos = v.get("OOS", {})
    if oos:
        up = oos.get("UP", {})
        dn = oos.get("DOWN", {})
        print(f"  {m}: UP dir={up.get('dir_acc')} ge2={up.get('ge2_rate')} n={up.get('n')} | DOWN dir={dn.get('dir_acc')} ge2={dn.get('ge2_rate')} n={dn.get('n')}")
print()
# Also check the model comparison CSV
pmc = pd.read_csv(REPORT / "post_open_model_comparison.csv")
print("post_open_model_comparison cols:", pmc.columns.tolist())
print(pmc[pmc["split"] == "OOS"].to_string())
print()

# ── 3. Knowledge second pass ───────────────────────────────────────────────
r3 = json.loads((REPORT / "v3_knowledge_second_pass_results.json").read_text())
print("=== V3 KNOWLEDGE SECOND PASS ===")
print("Keys:", list(r3.keys()))
models_k = r3.get("models", {})
for m, v in models_k.items():
    if not isinstance(v, dict):
        continue
    oos = v.get("OOS", {})
    if oos:
        up = oos.get("UP", {})
        print(f"  {m}: UP dir={up.get('dir_acc')} ge2={up.get('ge2_rate')} n={up.get('n')}")
print()
