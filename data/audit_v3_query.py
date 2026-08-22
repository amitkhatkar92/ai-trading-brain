"""Temporary audit query script — run inside container via docker exec."""
import sqlite3, json, sys
from pathlib import Path

DB = "/app/data/market_behavior.db"
JSONL = "/app/data/logs/mover_discovery_v3_shadow.jsonl"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. Recent OHLCV dates
dates = [r[0] for r in conn.execute(
    "SELECT DISTINCT trade_date FROM ohlcv_daily ORDER BY trade_date DESC LIMIT 15"
).fetchall()]
print("OHLCV_DATES:", dates)

# 2. Parse shadow JSONL
records = [json.loads(line) for line in open(JSONL)]
summaries = [r for r in records if r.get("record_type") == "SHADOW_SUMMARY"]
candidates = [r for r in records if r.get("record_type") == "SHADOW_CANDIDATE"]
print(f"SUMMARIES: {len(summaries)}")
print(f"CANDIDATES: {len(candidates)}")
for s in summaries:
    print(f"  RUN: ts={s['timestamp']} tdate={s['trading_date']} "
          f"up={s['v3_up_count']} dn={s['v3_down_count']} "
          f"universe={s['universe_size']} dur={s['v3_shadow_duration_ms']}ms "
          f"overlap={s['total_overlap']} v3only={s['v3_only_candidates']}")

# 3. Collect all unique symbols from candidates
all_syms = sorted({c["symbol"] for c in candidates})
print(f"UNIQUE_SYMBOLS: {len(all_syms)}")

# 4. Get T+1 returns for Run 1 candidates (base=2026-08-13, t1=2026-08-14)
run1_cands = [c for c in candidates if c["trading_date"] == "2026-08-13"]
run1_syms = [c["symbol"] for c in run1_cands]
t1_date = "2026-08-14"
base_date = "2026-08-13"

outcomes = {}
for sym in run1_syms:
    rows = conn.execute(
        "SELECT trade_date, close FROM ohlcv_daily WHERE symbol=? AND trade_date IN (?,?) ORDER BY trade_date",
        (sym, base_date, t1_date)
    ).fetchall()
    row_d = {r[0]: r[1] for r in rows}
    if base_date in row_d and t1_date in row_d:
        ret = (row_d[t1_date] / row_d[base_date] - 1) * 100
        outcomes[sym] = {"base": row_d[base_date], "t1": row_d[t1_date], "ret_1d": round(ret, 4)}

print(f"RUN1_T1_OUTCOMES: {len(outcomes)}/{len(run1_syms)} symbols resolved")
for sym, o in sorted(outcomes.items(), key=lambda x: -x[1]["ret_1d"])[:10]:
    print(f"  {sym}: ret_1d={o['ret_1d']:.2f}%")

# 5. Direction-aware outcome analysis
up_run1 = [c["symbol"] for c in run1_cands if c["direction"] == "UP"]
dn_run1 = [c["symbol"] for c in run1_cands if c["direction"] == "DOWN"]

up_outcomes = {s: outcomes[s]["ret_1d"] for s in up_run1 if s in outcomes}
dn_outcomes = {s: outcomes[s]["ret_1d"] for s in dn_run1 if s in outcomes}

if up_outcomes:
    vals = list(up_outcomes.values())
    print(f"UP_T1: n={len(vals)} avg={sum(vals)/len(vals):.3f}% "
          f"pos={sum(1 for v in vals if v>=0)} "
          f"ge1pct={sum(1 for v in vals if v>=1.0)} "
          f"ge2pct={sum(1 for v in vals if v>=2.0)}")
if dn_outcomes:
    vals = list(dn_outcomes.values())
    # DOWN: favorable = negative return
    fav = [-v for v in vals]
    print(f"DOWN_T1: n={len(vals)} avg_favorable={sum(fav)/len(fav):.3f}% "
          f"neg={sum(1 for v in vals if v<=0)} "
          f"le-1pct={sum(1 for v in vals if v<=-1.0)} "
          f"le-2pct={sum(1 for v in vals if v<=-2.0)}")

# 6. All eligible universe movers on T+1 date (to compute capture rate)
all_universe = [r[0] for r in conn.execute(
    "SELECT DISTINCT symbol FROM ohlcv_daily WHERE trade_date=?", (t1_date,)
).fetchall()]
universe_outcomes = {}
for sym in all_universe:
    rows = conn.execute(
        "SELECT trade_date, close FROM ohlcv_daily WHERE symbol=? AND trade_date IN (?,?) ORDER BY trade_date",
        (sym, base_date, t1_date)
    ).fetchall()
    row_d = {r[0]: r[1] for r in rows}
    if base_date in row_d and t1_date in row_d:
        ret = (row_d[t1_date] / row_d[base_date] - 1) * 100
        universe_outcomes[sym] = round(ret, 4)

print(f"UNIVERSE_T1: {len(universe_outcomes)} symbols with both dates")

# Top movers on T+1
top_up = sorted(universe_outcomes.items(), key=lambda x: -x[1])[:10]
top_dn = sorted(universe_outcomes.items(), key=lambda x: x[1])[:10]
print("TOP_10_UP_ACTUAL:", [(s, round(r,2)) for s,r in top_up])
print("TOP_10_DN_ACTUAL:", [(s, round(r,2)) for s,r in top_dn])

# Strong movers (>=2% up)
strong_up = {s for s,r in universe_outcomes.items() if r >= 2.0}
strong_dn = {s for s,r in universe_outcomes.items() if r <= -2.0}
v3_up_set = set(up_run1)
v3_dn_set = set(dn_run1)
print(f"STRONG_UP_UNIVERSE: {len(strong_up)} stocks >=2%")
print(f"STRONG_DN_UNIVERSE: {len(strong_dn)} stocks <=-2%")
print(f"V3_UP_CAPTURED_STRONG: {len(v3_up_set & strong_up)}/{len(strong_up)}")
print(f"V3_DN_CAPTURED_STRONG: {len(v3_dn_set & strong_dn)}/{len(strong_dn)}")
print(f"TOP5_UP_ACTUAL: {[s for s,_ in top_up[:5]]}")
print(f"V3_UP_TOP5_CAPTURE: {len(set(s for s,_ in top_up[:5]) & v3_up_set)}/5")
print(f"TOP5_DN_ACTUAL: {[s for s,_ in top_dn[:5]]}")
print(f"V3_DN_TOP5_CAPTURE: {len(set(s for s,_ in top_dn[:5]) & v3_dn_set)}/5")

conn.close()
