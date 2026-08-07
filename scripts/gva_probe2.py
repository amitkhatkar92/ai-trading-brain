"""Probe for GVA-001 data inventory."""
import json, sqlite3
from pathlib import Path

DATA = Path("data")

# re001a
try:
    r = json.loads((DATA / "re001a_results.json").read_text())
    print("=== RE001A ===")
    for k, v in r.items():
        if not isinstance(v, (dict, list)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:5]}")
        else:
            print(f"  {k}: list len={len(v)}")
except Exception as e:
    print(f"RE001A: {e}")

print()
# strategy performance
sp = json.loads((DATA / "strategy_performance.json").read_text())
for name, s in sp.items():
    tt = s["total_trades"]
    wr = (s["wins"] / tt * 100) if tt else 0
    print(f"Strategy {name}: trades={tt} wins={s['wins']} win_rate={wr:.0f}%")

print()
# IKN node distribution
conn = sqlite3.connect(str(DATA / "ikn" / "ikn.db"))
types = conn.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type").fetchall()
print("=== IKN NODE TYPES ===")
for t in types:
    print(f"  {t[0]}: {t[1]}")
reltypes = conn.execute("SELECT relationship_type, COUNT(*) FROM relationships GROUP BY relationship_type").fetchall()
print("=== IKN RELATIONSHIP TYPES ===")
for r in reltypes:
    print(f"  {r[0]}: {r[1]}")
conn.close()

print()
# DNA DB details
conn2 = sqlite3.connect(str(DATA / "mls" / "institutional_dna.db"))
cats = conn2.execute("SELECT category, lifecycle, COUNT(*) FROM dna GROUP BY category, lifecycle").fetchall()
print("=== DNA BY CATEGORY/LIFECYCLE ===")
for c in cats:
    print(f"  cat={c[0]} lifecycle={c[1]}: {c[2]}")
dirs = conn2.execute("SELECT direction, COUNT(*) FROM dna GROUP BY direction").fetchall()
print("=== DNA BY DIRECTION ===")
for d in dirs:
    print(f"  dir={d[0]}: {d[1]}")
studies_dna = conn2.execute("SELECT study_id, COUNT(*) FROM dna_evidence GROUP BY study_id").fetchall()
print("=== DNA EVIDENCE BY STUDY ===")
for s in studies_dna:
    print(f"  study={s[0]}: {s[1]}")

# audit log
audit = conn2.execute("SELECT operation, COUNT(*) FROM audit_log GROUP BY operation").fetchall()
print("=== DNA AUDIT LOG ===")
for a in audit:
    print(f"  op={a[0]}: {a[1]}")
conn2.close()

print()
# Paper trading daily
ptd = json.loads((DATA / "paper_trading_daily.json").read_text())
print("=== PAPER TRADING DAILY ===")
print(f"Keys: {list(ptd.keys())}")
cum = ptd.get("cumulative", {})
print(f"Cumulative: {cum}")

print()
# Control tower cycle stats
conn3 = sqlite3.connect(str(DATA / "control_tower.db"))
err_rate = conn3.execute("SELECT COUNT(*) total, SUM(had_error) errors FROM ct_cycles").fetchone()
print(f"=== CT CYCLES: total={err_rate[0]} errors={err_rate[1]} error_rate={err_rate[1]/err_rate[0]*100:.1f}%")
regimes = conn3.execute("SELECT regime, COUNT(*) FROM ct_cycles GROUP BY regime ORDER BY COUNT(*) DESC").fetchall()
print("Regime dist:", regimes[:5])

decisions = conn3.execute("SELECT decision, COUNT(*) FROM ct_decisions GROUP BY decision ORDER BY COUNT(*) DESC").fetchall()
print("Decision dist:", decisions[:5])
conf_avg = conn3.execute("SELECT AVG(confidence) FROM ct_decisions").fetchone()
print(f"Avg decision confidence: {conf_avg[0]:.3f}")
conn3.close()

print()
# EDE feature DB
ede = json.loads((DATA / "ede_feature_db.json").read_text())
print("=== EDE FEATURE DB ===")
if isinstance(ede, list):
    print(f"Type: list  Count: {len(ede)}")
elif isinstance(ede, dict):
    print(f"Type: dict  Keys: {list(ede.keys())[:10]}")
    # Count total records
    total = sum(len(v) for v in ede.values() if isinstance(v, list))
    print(f"Total feature records: {total}")
