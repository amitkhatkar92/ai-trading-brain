import sqlite3, pandas as pd, numpy as np

con = sqlite3.connect("data/study002_replay.db")

tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("All tables:", tables)

nsei = pd.read_sql("SELECT symbol, trade_date, open, high, low, close FROM ohlcv_daily WHERE symbol='^NSEI' ORDER BY trade_date", con)
print(f"NSEI rows: {len(nsei)}, dates: {nsei['trade_date'].min()} to {nsei['trade_date'].max()}")
print(nsei.head(3).to_string())
con.close()

rc = pd.read_csv("reports/mover_discovery_v3/v3_retro_candidates.csv")
print(f"\nretro_candidates: {len(rc)} rows, cols: {list(rc.columns)}")
print(f"direction values: {rc['direction'].unique()}")
print(f"date range: {rc['trading_date'].min()} to {rc['trading_date'].max()}")

gap = pd.read_csv("reports/mover_discovery_v3/v3_intraday_gap_analysis.csv")
print(f"\nprior gap_analysis: {len(gap)} rows, cols: {list(gap.columns)}")
print(f"gap_pct null: {gap['gap_pct'].isna().sum()}")
print(f"gap_pct stats: min={gap['gap_pct'].min():.2f} max={gap['gap_pct'].max():.2f} mean={gap['gap_pct'].mean():.2f}")

# Check gap distribution
q = gap[gap['gap_pct'].notna() & (gap['direction']=='UP')]
print(f"\nUP gap distribution:")
print(f"  >0.3%: {(q['gap_pct']>0.3).mean():.2f}  {(q['gap_pct']>0.3).sum()}")
print(f"  <-0.3%: {(q['gap_pct']<-0.3).mean():.2f}  {(q['gap_pct']<-0.3).sum()}")
print(f"  -0.3 to 0.3: {((q['gap_pct']>=-0.3)&(q['gap_pct']<=0.3)).mean():.2f}")
print(f"  >1%: {(q['gap_pct']>1).sum()}")
print(f"  >2%: {(q['gap_pct']>2).sum()}")

# Check NIFTY gap availability
con = sqlite3.connect("data/study002_replay.db")
ohlcv_all = pd.read_sql("SELECT symbol, trade_date, open, close FROM ohlcv_daily", con)
con.close()
nsei2 = ohlcv_all[ohlcv_all['symbol']=='^NSEI'].sort_values('trade_date').copy()
nsei2['nsei_gap'] = (nsei2['open'] / nsei2['close'].shift(1) - 1) * 100
print(f"\nNSEI gap stats: null={nsei2['nsei_gap'].isna().sum()}, non-null={nsei2['nsei_gap'].notna().sum()}")
print(f"NSEI gap >0.3%: {(nsei2['nsei_gap']>0.3).sum()}, <-0.3%: {(nsei2['nsei_gap']<-0.3).sum()}")
