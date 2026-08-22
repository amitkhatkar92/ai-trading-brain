"""
End-to-end verification: tests all 3 bug fixes in dhan_feed.py
1. Double-nesting: resp["data"]["data"][seg] parsed correctly
2. OHLC sub-dict: row["ohlc"]["open"] extracted correctly  
3. quote_data primary: works for HDFCBANK, RELIANCE, TCS etc.
"""
import sys, json
sys.path.insert(0, "/app")
import logging
logging.basicConfig(level=logging.WARNING)

token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]

from data_feeds.dhan_feed import DhanFeed

print("=== DhanFeed integration test ===\n")
import os
os.environ["DHAN_CLIENT_ID"]    = client_id
os.environ["DHAN_ACCESS_TOKEN"] = token
feed = DhanFeed()

print(f"Live: {feed._live}")

# Trigger readiness probe
feed._readiness_probe()
rr = feed._readiness_probe_result or {}
print(f"\n-- Readiness probe --")
print(f"  equity_verified: {rr.get('equity_verified')}")
print(f"  failure_reason:  {rr.get('failure_reason')}")
print(f"  latency_ms:      {rr.get('latency_ms', 0):.0f}ms")
print(f"  declared_live:   {rr.get('declared_live')}")

# Test get_quote for known symbols
print("\n-- get_quote tests --")
symbols = ["HDFCBANK", "RELIANCE", "TCS", "INFY", "SBIN", "WIPRO"]
for sym in symbols:
    q = feed.get_quote(sym)
    if q and q.feed_source == "DHAN":
        print(f"  {sym:12}  LTP={q.ltp:8.2f}  open={q.open:8.2f}  high={q.high:8.2f}"
              f"  low={q.low:8.2f}  close={q.close:8.2f}  vol={q.volume:,.0f}  [DHAN ✓]")
    elif q:
        print(f"  {sym:12}  LTP={q.ltp:8.2f}  [fallback: {q.feed_source}]")
    else:
        print(f"  {sym:12}  None")

# Test get_multiple_quotes
print("\n-- get_multiple_quotes test --")
batch = ["ICICIBANK", "TATASTEEL", "BANKBARODA", "KOTAKBANK"]
results = feed.get_multiple_quotes(batch)
for sym in batch:
    q = results.get(sym)
    if q and q.feed_source == "DHAN":
        print(f"  {sym:12}  LTP={q.ltp:8.2f}  open={q.open:8.2f}  [DHAN ✓]")
    elif q:
        print(f"  {sym:12}  LTP={q.ltp:8.2f}  [fallback: {q.feed_source}]")
    else:
        print(f"  {sym:12}  None")

print("\n-- Segment health --")
for k, v in feed._segment_health.items():
    print(f"  {k}: {v}")

print("\nDone.")
