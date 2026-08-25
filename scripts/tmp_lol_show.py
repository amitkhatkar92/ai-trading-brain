import json, datetime

today = datetime.date.today().strftime("%Y-%m-%d")
f = f"/root/ai-trading-brain/data/lol/LOL_{today}.jsonl"
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
up   = sorted([r for r in live if r.get("direction","").upper() in ("BUY","LONG")],  key=lambda x: -(x.get("klp_score") or 0))
down = sorted([r for r in live if r.get("direction","").upper() in ("SELL","SHORT")], key=lambda x: -(x.get("klp_score") or 0))

print(f"LIVE SIGNALS TODAY ({today}): {len(live)}  |  UPSIDE={len(up)}  DOWNSIDE={len(down)}")
print()
print(f"{'Symbol':<14} {'Dir':5} {'Strategy':<28} {'Entry':>9} {'SL':>9} {'Target':>9} {'RR':>5} {'KLP':>6} {'Sel':>5} {'Exec':>5} KDA")
print("-"*120)
for r in up + down:
    print(f"{r.get('symbol','?'):<14} {r.get('direction','?'):5} {r.get('strategy_name','?'):<28} "
          f"{str(r.get('entry_price','?')):>9} {str(r.get('stop_loss','?')):>9} {str(r.get('target_price','?')):>9} "
          f"{str(round(r.get('rr_ratio',0),2)):>5} {str(r.get('klp_score','?')):>6} "
          f"{str(r.get('klp_selected','?')):>5} {str(r.get('executed','?')):>5} "
          f"{r.get('kda_decision','?')}")
print()
print("Reasons no position taken:")
for r in live:
    reason = []
    if not r.get("klp_selected"):
        reason.append("KLP_NOT_SELECTED")
    if not r.get("executed"):
        reason.append("NOT_EXECUTED")
    kda = r.get("kda_decision","")
    if kda not in ("KDA_APPROVED", None):
        reason.append(f"KDA={kda}")
    print(f"  {r.get('symbol','?'):14} {', '.join(reason)}")
