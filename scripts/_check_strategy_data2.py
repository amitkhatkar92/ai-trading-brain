import sqlite3, json
from pathlib import Path

con = sqlite3.connect("data/study002_replay.db")

# Sector conviction quality
r = con.execute("SELECT COUNT(*) FROM sector_conviction_daily WHERE consensus_score IS NOT NULL").fetchone()
print("sector_conviction non-null consensus_score:", r[0])

r = con.execute("SELECT COUNT(*) FROM sector_conviction_daily").fetchone()
print("sector_conviction total rows:", r[0])

# Sample sector conviction
rows = con.execute("SELECT record_date, sector, consensus_score, capital_flow_score FROM sector_conviction_daily WHERE consensus_score IS NOT NULL LIMIT 5").fetchall()
print("sample sector rows:", rows)

# NIFTY volume
rows = con.execute("SELECT trade_date, volume FROM ohlcv_daily WHERE symbol='^NSEI' ORDER BY trade_date LIMIT 5").fetchall()
print("NIFTY volume sample:", rows)

# Stock volumes
r = con.execute("SELECT AVG(volume), COUNT(CASE WHEN volume IS NULL THEN 1 END), COUNT(*) FROM ohlcv_daily WHERE symbol != '^NSEI'").fetchone()
print("Stock avg_vol, null_count, total:", r)

# Check all features computable from NIFTY
nifty_rows = con.execute("SELECT trade_date, open, high, low, close, volume FROM ohlcv_daily WHERE symbol='^NSEI' ORDER BY trade_date").fetchall()
print(f"\nNIFTY rows: {len(nifty_rows)}, first: {nifty_rows[0]}, last: {nifty_rows[-1]}")

# Evolved strategies summary
es = json.loads(Path("data/evolved_strategies.json").read_text())
unavail_feats = {"vix", "iv_rank", "pcr"}
avail = []
unavail = []
for name, data in es.items():
    if "entry_conditions" not in data:
        avail.append(name)
        continue
    needs_unavail = any(c["feature"] in unavail_feats for c in data["entry_conditions"])
    if needs_unavail:
        unavail.append(name)
    else:
        avail.append(name)
        
print(f"\nTotal strategies: {len(es)}")
print(f"Evaluable (no vix/iv/pcr): {len(avail)}")
print(f"Unavailable (need vix/iv/pcr): {len(unavail)}")

# What are the Breakout_Volume base strategies?
base_strats = {}
for name, data in es.items():
    base = data.get("base_strategy", "no_base")
    base_strats[base] = base_strats.get(base, 0) + 1
print("\nBase strategy distribution:", base_strats)

# Check direction distribution in EDG strategies
dir_dist = {}
for name, data in es.items():
    d = data.get("direction", "no_direction")
    dir_dist[d] = dir_dist.get(d, 0) + 1
print("Direction distribution:", dir_dist)

con.close()
