import json, sqlite3

db = sqlite3.connect("data/re001_replay.db")
c = db.cursor()
c.execute("SELECT COUNT(*) FROM signal_births"); sb = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM opportunities"); opp = c.fetchone()[0]
c.execute("SELECT current_state, COUNT(*) FROM opportunities GROUP BY current_state")
opp_states = dict(c.fetchall())
c.execute("SELECT archetype_id, COUNT(*) FROM signal_births GROUP BY archetype_id ORDER BY 2 DESC")
archetypes = c.fetchall()
c.execute("SELECT COUNT(DISTINCT trade_date) FROM ohlcv_daily"); dates = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv_daily"); syms_ohlcv = c.fetchone()[0]
dq = "FULL"
c.execute("SELECT COUNT(*) FROM sector_conviction_daily WHERE data_quality=?", (dq,))
sc_full = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM universe_stocks"); universe = c.fetchone()[0]
db.close()

print("=== RE001 DB ===")
print(f"  signal_births: {sb}")
print(f"  opportunities: {opp}  states: {opp_states}")
for a, n in archetypes:
    print(f"  {a}: {n}")
print(f"  ohlcv dates: {dates}  symbols: {syms_ohlcv}")
print(f"  universe_stocks: {universe}")
print(f"  sector_conviction FULL rows: {sc_full}")

with open("data/re001a_results.json") as f:
    r = json.load(f)
b = r["baseline"]; s7 = r["stage7"]; s1 = r["stage1"]; s26 = r["stage2_6"]
print()
print("=== RE001A ===")
print(f"  feat before: {b['feat_total']} labeled={b['feat_labeled']}")
print(f"  feat after:  {s7['feat_total']} labeled={s7['feat_labeled']} re001={s7['feat_re001']} symbols={s7['feat_symbols']}")
print(f"  edges before: {b['edges_total']} {b['edges_by_status']}")
print(f"  edges after:  {s7['edges_total']} ACTIVE={s7['edges_active']} CANDIDATE={s7['edges_candidate']} DECAYING={s7['edges_decaying']}")
print(f"  patterns discovered: 3  approved: 0 (WF gate failed)")
print(f"  ML trained: {r['stage6_meta']['model_trained']}")
print(f"  elapsed: {r['elapsed_s']:.1f}s")

with open("data/ede_feature_db.json") as f:
    feat = json.load(f)
labeled = sum(1 for x in feat if x.get("forward_return", 0.0) != 0.0)
pos = sum(1 for x in feat if x.get("forward_return", 0.0) >= 0.008)
re001_src = sum(1 for x in feat if x.get("source") == "RE001_OHLCV")
syms_feat = len(set(x.get("symbol", "") for x in feat))
print()
print("=== ede_feature_db FINAL ===")
print(f"  total: {len(feat)}  labeled: {labeled}  positive: {pos}  re001_src: {re001_src}")
if labeled > 0:
    print(f"  positive_rate: {pos/labeled*100:.1f}% (of labeled)")
print(f"  unique symbols: {syms_feat}")
