"""Probe DTA-001 - part 2: features, DNA, IKN, edges for a symbol."""
import sqlite3, json
from pathlib import Path

DATA = Path("data")

# EDE feature records for RELIANCE
print("=== EDE FEATURES FOR RELIANCE ===")
ede = json.loads((DATA / "ede_feature_db.json").read_text(encoding="utf-8", errors="replace"))
if isinstance(ede, list):
    rel_features = [r for r in ede if isinstance(r, dict) and
                    r.get("symbol", "") == "RELIANCE"]
    print(f"RELIANCE records: {len(rel_features)}")
    if rel_features:
        # Most recent
        sorted_feats = sorted(rel_features, key=lambda x: x.get("date", ""), reverse=True)
        print(f"Most recent date: {sorted_feats[0].get('date')}")
        print(f"Fields: {list(sorted_feats[0].keys())}")
        print(f"Sample (most recent):")
        print(json.dumps(sorted_feats[0], indent=2, default=str)[:1000])

print()
# DNA matches for RELIANCE features
print("=== DNA DB ===")
conn = sqlite3.connect(str(DATA / "mls" / "institutional_dna.db"))
conn.row_factory = sqlite3.Row

# All DNA with feature names
dna = conn.execute("""
    SELECT id, feature_name, direction, category, lifecycle,
           consensus_score, confidence, version
    FROM dna ORDER BY confidence DESC LIMIT 20
""").fetchall()
print(f"Total DNA records: {conn.execute('SELECT COUNT(*) FROM dna').fetchone()[0]}")
print("Top 5 by confidence:")
for r in dna[:5]:
    print(f"  {r['feature_name']} dir={r['direction']} cat={r['category']} conf={r['confidence']:.3f}")

conn.close()

print()
# IKN nodes for RELIANCE-related knowledge
conn2 = sqlite3.connect(str(DATA / "ikn" / "ikn.db"))
conn2.row_factory = sqlite3.Row

nodes = conn2.execute("SELECT * FROM nodes ORDER BY created_at DESC LIMIT 20").fetchall()
print("=== IKN NODES (recent 20) ===")
for n in nodes:
    print(f"  [{n['node_type']}] {n['name'][:60]} id={n['node_id'][:8]}")

print()
rels = conn2.execute("""
    SELECT r.*, n1.name src_name, n1.node_type src_type,
           n2.name tgt_name, n2.node_type tgt_type
    FROM relationships r
    JOIN nodes n1 ON r.source_id = n1.node_id
    JOIN nodes n2 ON r.target_id = n2.node_id
    LIMIT 10
""").fetchall()
print("=== IKN RELATIONSHIPS ===")
for r in rels:
    print(f"  [{r['src_type']}]{r['src_name'][:30]} --{r['relationship_type']}--> [{r['tgt_type']}]{r['tgt_name'][:30]}")
conn2.close()

print()
# Discovered edges - get active ones
print("=== ACTIVE EDGES ===")
edges = json.loads((DATA / "discovered_edges.json").read_text())
for eid, e in edges.items():
    if e.get("status") == "ACTIVE":
        print(f"  {eid}: prec={e.get('precision')}% sharpe={e.get('sharpe_ratio')} oos_wr={e.get('oos_win_rate')}")
        print(f"    conditions: {e.get('entry_conditions', '')[:200]}")

print()
# Strategy performance
print("=== STRATEGY PERFORMANCE ===")
sp = json.loads((DATA / "strategy_performance.json").read_text())
for name, s in sp.items():
    print(f"  {name}: trades={s['total_trades']} wins={s['wins']} enabled={s['enabled']}")

print()
# Hypothesis registry - most relevant
print("=== RELEVANT HYPOTHESES ===")
reg = json.loads((DATA / "ars_hypothesis_registry.json").read_text())
hyps = reg.get("hypotheses", {})
for hid, h in list(hyps.items())[:5]:
    print(f"  {hid}: status={h.get('status')} title={h.get('title','')[:60]}")
