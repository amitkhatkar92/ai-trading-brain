"""Deep data availability check for V3 orthogonal direction research."""
import sqlite3, pandas as pd, numpy as np

db_path = "data/study002_replay.db"
con = sqlite3.connect(db_path)

# ---- 1. ohlcv_daily: column name and open price coverage ----
ohlcv = pd.read_sql("SELECT * FROM ohlcv_daily LIMIT 5", con)
print("=== ohlcv_daily columns ===")
print(list(ohlcv.columns))

ohlcv_all = pd.read_sql("SELECT symbol, trade_date, open, high, low, close, volume FROM ohlcv_daily", con)
print(f"\nohlcv_daily: {len(ohlcv_all):,} rows, {ohlcv_all['symbol'].nunique()} symbols")
print(f"  date range: {ohlcv_all['trade_date'].min()} to {ohlcv_all['trade_date'].max()}")
print(f"  open nulls: {ohlcv_all['open'].isna().sum()}")
print(f"  high nulls: {ohlcv_all['high'].isna().sum()}")
print(f"  low nulls: {ohlcv_all['low'].isna().sum()}")
print(f"  close nulls: {ohlcv_all['close'].isna().sum()}")

# Check index symbols
idx = ohlcv_all[ohlcv_all['symbol'].isin(['^NSEI', '^NSEBANK', 'NIFTY50', 'BANKNIFTY'])]
print(f"\n  Index symbols: {idx['symbol'].unique().tolist()}")
print(f"  ^NSEI rows: {len(idx[idx['symbol']=='^NSEI'])}")
print(f"  ^NSEBANK rows: {len(idx[idx['symbol']=='^NSEBANK'])}")

# ---- 2. sector_conviction_daily ----
scd = pd.read_sql("SELECT * FROM sector_conviction_daily", con)
print(f"\n=== sector_conviction_daily ===")
print(f"  rows: {len(scd)}, date range: {scd['record_date'].min()} to {scd['record_date'].max()}")
print(f"  sectors: {scd['sector'].unique().tolist()}")
for col in ['participation_rate_1d', 'participation_rate_5d', 'rs_vs_market_20d',
            'volume_trend_10d', 'sector_conviction_score', 'consensus_score']:
    non_null = scd[col].notna().sum()
    pct = non_null / len(scd) * 100
    print(f"  {col}: {non_null}/{len(scd)} ({pct:.1f}% available)")

# Check sector_conviction_daily quality for TRAIN/VAL/OOS dates
print(f"\n  theme_phase non-null: {scd['theme_phase'].notna().sum()}")
sample = scd[scd['participation_rate_1d'].notna()].head(3)
print(f"  Sample with participation_rate_1d:\n{sample[['record_date','sector','participation_rate_1d','rs_vs_market_20d','sector_conviction_score']].to_string()}")

# ---- 3. stock_sector_map ----
ssm = pd.read_sql("SELECT * FROM stock_sector_map", con)
print(f"\n=== stock_sector_map ===")
print(f"  rows: {len(ssm)}")
print(f"  sectors: {ssm['primary_sector'].value_counts().to_dict()}")

# ---- 4. universe_stocks sector ----
us = pd.read_sql("SELECT symbol, sector FROM universe_stocks WHERE is_active=1", con)
print(f"\n=== universe_stocks sectors ===")
print(us['sector'].value_counts().to_dict())

# ---- 5. Can we compute sector returns from ohlcv_daily? ----
# Check if V3 stocks are in ohlcv_daily
v3_syms = ohlcv_all[~ohlcv_all['symbol'].isin(['^NSEI','^NSEBANK'])]['symbol'].unique()
print(f"\n=== V3 universe symbols in ohlcv_daily: {len(v3_syms)} ===")
print(f"  Sample: {v3_syms[:10].tolist()}")

# Check sector_map coverage vs ohlcv
# Use universe_stocks as the source of sector info
us_sectors = dict(zip(us['symbol'], us['sector']))
v3_with_sector = sum(1 for s in v3_syms if s in us_sectors)
print(f"  V3 symbols with sector in universe_stocks: {v3_with_sector}/{len(v3_syms)}")

# ---- 6. Gap analysis feasibility ----
# We need T+1 open, which is just the open column for the next day
# Let's see what coverage looks like for the OOS period
oos_start = "2026-05-14"
oos_ohlcv = ohlcv_all[(ohlcv_all['trade_date'] >= oos_start) & ~ohlcv_all['symbol'].isin(['^NSEI','^NSEBANK'])]
print(f"\n=== Gap (open price) OOS coverage ===")
print(f"  OOS rows: {len(oos_ohlcv):,}")
print(f"  OOS symbols: {oos_ohlcv['symbol'].nunique()}")
print(f"  OOS open nulls: {oos_ohlcv['open'].isna().sum()}")

# ---- 7. trading_calendar ----
cal = pd.read_sql("SELECT * FROM trading_calendar WHERE is_trading_day=1", con)
print(f"\n=== trading_calendar ===")
print(f"  trading days: {len(cal)}, from {cal['calendar_date'].min()} to {cal['calendar_date'].max()}")

# ---- 8. bulk_block_deals ----
bbd_cnt = pd.read_sql("SELECT COUNT(*) as cnt FROM bulk_block_deals", con).iloc[0,0]
bhav_cnt = pd.read_sql("SELECT COUNT(*) as cnt FROM bhav_daily", con).iloc[0,0]
print(f"\n=== Institutional data ===")
print(f"  bulk_block_deals: {bbd_cnt} rows")
print(f"  bhav_daily: {bhav_cnt} rows")

# ---- 9. sector conviction date coverage in split periods ----
train_start, train_end = "2025-09-16", "2026-02-19"
val_start, val_end     = "2026-02-20", "2026-05-13"
oos_start2, oos_end    = "2026-05-14", "2026-07-30"

for label, s, e in [("TRAIN", train_start, train_end), ("VAL", val_start, val_end), ("OOS", oos_start2, oos_end)]:
    sub = scd[(scd['record_date'] >= s) & (scd['record_date'] <= e)]
    with_data = sub['participation_rate_1d'].notna().sum()
    total = len(sub)
    print(f"  sector_conviction {label}: {with_data}/{total} rows with participation_rate_1d ({100*with_data/max(total,1):.1f}%)")

# ---- 10. Derived sector return from ohlcv_daily ----
# Can we compute daily sector returns from aggregating stocks?
print(f"\n=== Sector return derivation feasibility ===")
sample_date = "2026-01-15"
us_with_ohlcv = ohlcv_all[ohlcv_all['trade_date'] == sample_date]
print(f"  Stocks with OHLCV on {sample_date}: {len(us_with_ohlcv)}")

# Show sectors available
us_tmp = us[us['symbol'].isin(us_with_ohlcv['symbol'])]
print(f"  Sector coverage on {sample_date}:")
print(f"  {us_tmp['sector'].value_counts().to_dict()}")

con.close()
print("\n=== DONE ===")
