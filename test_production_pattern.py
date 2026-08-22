"""
Production-pattern test: one readiness probe then ONE batch for 30 symbols.
Simulates what actually happens every 30 seconds in the trading engine.
"""
import sys, time
sys.path.insert(0, "/app")
import logging
logging.disable(logging.DEBUG)  # suppress debug noise

token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]

import os
os.environ["DHAN_CLIENT_ID"]    = client_id
os.environ["DHAN_ACCESS_TOKEN"] = token

from data_feeds.dhan_feed import DhanFeed
feed = DhanFeed()   # auto-runs readiness probe

print(f"Mode: {feed.get_runtime_mode()}  equity_verified={feed._equity_verified}")
print()

# Production pattern: wait a bit, then do ONE batch call
time.sleep(1.5)   # brief pause between probe and scan (in prod = 30 sec)

# The 38-symbol watchlist from equity_scanner
watchlist = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY", "BANKBARODA",
    "WIPRO", "SBIN", "TCS", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "LT",
    "NTPC", "POWERGRID", "ONGC", "COALINDIA", "DIVISLAB", "SUNPHARMA",
    "CIPLA", "DRREDDY", "APOLLOHOSP", "HCLTECH", "TECHM", "MARUTI",
    "TITAN", "NESTLEIND", "HINDUNILVR", "ASIANPAINT", "ULTRACEMCO",
    "GRASIM", "BHARTIARTL", "INDUSINDBK", "EICHERMOT", "BAJAJ_AUTO",
    "TATACONSUM", "JSWSTEEL", "VEDL",
]
print(f"Batch get_multiple_quotes for {len(watchlist)} symbols...")
t0 = time.time()
results = feed.get_multiple_quotes(watchlist)
elapsed = time.time() - t0

dhan_count = sum(1 for q in results.values() if q and q.feed_source == "DHAN")
yf_count   = sum(1 for q in results.values() if q and q.feed_source != "DHAN")
no_count   = len(watchlist) - len(results)

print(f"  Time: {elapsed:.1f}s")
print(f"  DHAN: {dhan_count}/{len(watchlist)} symbols")
print(f"  YAHOO fallback: {yf_count}")
print(f"  No data: {no_count}")
print()

# Print first 10 results
print("Sample results (first 10):")
for sym in watchlist[:10]:
    q = results.get(sym)
    if q and q.feed_source == "DHAN":
        print(f"  {sym:14} LTP={q.ltp:9.2f}  O={q.open:9.2f}  H={q.high:9.2f}  L={q.low:9.2f}  vol={q.volume:>12,.0f}  [DHAN ✓]")
    elif q:
        print(f"  {sym:14} LTP={q.ltp:9.2f}  [{q.feed_source}]")
    else:
        print(f"  {sym:14} None")
