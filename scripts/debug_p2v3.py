"""
P2 debug v3: Test _normalize_df_columns specifically.
"""
import sys
sys.path.insert(0, "/app")

import yfinance as yf
from data_feeds.yahoo_feed import YahooFeed

feed = YahooFeed()

# Download COALINDIA.NS 
df_raw = yf.download("COALINDIA.NS", period="5d", interval="1d",
                     auto_adjust=True, progress=False, threads=False)
print(f"RAW columns: {type(df_raw.columns).__name__} = {list(df_raw.columns)}")

# Apply normalization
df_norm = feed._normalize_df_columns(df_raw)
print(f"NORM columns: {type(df_norm.columns).__name__} = {list(df_norm.columns)}")

# Check a row
if not df_norm.empty:
    row = df_norm.iloc[-1]
    print(f"row type: {type(row)}")
    print(f"row.index type: {type(row.index)}")
    close_val = row.get("Close", row.get("close", 0.0))
    print(f"close_val type: {type(close_val).__name__}, value: {close_val}")

# Now test _live_history directly to get the actual traceback
import traceback
try:
    bars = feed._live_history("COALINDIA.NS", "COALINDIA", 30, "1d")
    print(f"Bars count: {len(bars)}")
    if bars:
        print(f"First bar: {bars[0]}")
except Exception as e:
    print(f"ERROR in _live_history: {e}")
    traceback.print_exc()
