"""Pool validity, score ordering, duplicate checks for both V3 runs."""
import sqlite3, json

conn = sqlite3.connect('/app/data/market_behavior.db')
r = conn.execute("SELECT COUNT(*) FROM ohlcv_daily WHERE trade_date='2026-08-15'").fetchone()
print("Aug15_OHLCV_rows:", r[0])

records = [json.loads(l) for l in open('/app/data/logs/mover_discovery_v3_shadow.jsonl')]

for run_td in ["2026-08-13", "2026-08-14"]:
    up = sorted([x for x in records if x.get("trading_date")==run_td and x.get("direction")=="UP"], key=lambda x: x["v3_rank"])
    dn = sorted([x for x in records if x.get("trading_date")==run_td and x.get("direction")=="DOWN"], key=lambda x: x["v3_rank"])
    print(f"\n=== Run trading_date={run_td} ===")
    print(f"UP count={len(up)} DN count={len(dn)}")
    up_syms = [x["symbol"] for x in up]
    dn_syms = [x["symbol"] for x in dn]
    print("UP_dupes:", [s for s in up_syms if up_syms.count(s) > 1])
    print("DN_dupes:", [s for s in dn_syms if dn_syms.count(s) > 1])
    print("UP_DN_overlap:", sorted(set(up_syms) & set(dn_syms)))
    ranks_unique = len(set(x["v3_rank"] for x in up)) == len(up)
    print("UP_ranks_unique:", ranks_unique)
    scores_ok_up = all(up[i]["v3_score"] >= up[i+1]["v3_score"] for i in range(len(up)-1))
    scores_ok_dn = all(dn[i]["v3_score"] >= dn[i+1]["v3_score"] for i in range(len(dn)-1))
    print("UP_scores_descending:", scores_ok_up)
    print("DN_scores_descending:", scores_ok_dn)
    nan_up = [x for x in up if x.get("v3_score") is None or str(x.get("v3_score")) in ("None","nan","NaN")]
    nan_dn = [x for x in dn if x.get("v3_score") is None or str(x.get("v3_score")) in ("None","nan","NaN")]
    print("NaN_scores:", len(nan_up)+len(nan_dn))
    print("Top3 UP:", [(x["v3_rank"], x["symbol"], x["v3_score"]) for x in up[:3]])
    print("Top3 DN:", [(x["v3_rank"], x["symbol"], x["v3_score"]) for x in dn[:3]])

# Leakage check over all records
future_keys = {"ret_1d","ret_3d","ret_5d","mfe_5d","mae_5d","future_close","future_ret","forward_return","actual_move_pct","final_state","MFE","MAE"}
cands = [x for x in records if x.get("record_type")=="SHADOW_CANDIDATE"]
leaks = [(x["symbol"], k) for x in cands for k in future_keys if k in x]
print("\nLEAKAGE_VIOLATIONS:", leaks)
print("NO_TRADES_GEN_ALL:", all(x.get("no_trades_generated") for x in cands))

# Isolation check via source text
shadow_src = open('/app/opportunity_engine/mover_discovery_v3_shadow_runner.py').read()
forbidden_imports = ["decision_engine","risk_control","execution_engine","order_manager","dhan_feed","broker"]
for fi in forbidden_imports:
    found = any(fi.lower() in line.lower() for line in shadow_src.splitlines() if not line.strip().startswith('#') and 'import' in line.lower())
    print(f"IMPORT_{fi.upper()}:", "FOUND" if found else "CLEAN")
