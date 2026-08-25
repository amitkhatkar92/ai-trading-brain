import json
f = "/root/ai-trading-brain/data/lol/LOL_2026-08-25.jsonl"
recs = {}
for line in open(f):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
        oid = r.get("obs_id") or r.get("observation_id", "")
        recs[oid] = r
    except:
        pass

live = [r for r in recs.values() if not r.get("recovery_source")]
print(f"LIVE SIGNALS TODAY: {len(live)}")
print()

up   = [r for r in live if str(r.get("signal_direction","")).upper() in ("LONG","UP","BUY")]
down = [r for r in live if str(r.get("signal_direction","")).upper() in ("SHORT","DOWN","SELL")]

print(f"UPSIDE  (LONG/BUY):  {len(up)}")
for r in up:
    print(f"  {r.get('symbol','?'):15s}  strat={r.get('strategy','?'):20s}  score={r.get('edge_score') or r.get('_obs_candidate_score','?')}  rr={r.get('rr') or r.get('expected_rr','?')}  kda={r.get('kda_decision','?')}")

print()
print(f"DOWNSIDE (SHORT/SELL): {len(down)}")
for r in down:
    print(f"  {r.get('symbol','?'):15s}  strat={r.get('strategy','?'):20s}  score={r.get('edge_score') or r.get('_obs_candidate_score','?')}  rr={r.get('rr') or r.get('expected_rr','?')}  kda={r.get('kda_decision','?')}")

print()
print("=== ALL FIELDS OF FIRST LIVE RECORD ===")
if live:
    for k, v in live[0].items():
        print(f"  {k}: {v}")
