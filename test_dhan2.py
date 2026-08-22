import sys, inspect
sys.path.insert(0, "/app")
from dhanhq import dhanhq
print("Constructor sig:", inspect.signature(dhanhq.__init__))

# Check token age
import os
from pathlib import Path
from datetime import datetime

env_path = Path("/app/.env")
token = ""
client_id = ""
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("DHAN_ACCESS_TOKEN="):
            token = line.split("=", 1)[1].strip()
        if line.startswith("DHAN_CLIENT_ID="):
            client_id = line.split("=", 1)[1].strip()

mtime = datetime.fromtimestamp(env_path.stat().st_mtime)
age_hours = (datetime.now() - mtime).total_seconds() / 3600
print(f"\n.env last modified : {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({age_hours:.1f} hours ago)")
print(f"Token first 12 chars: {token[:12]}...")

# Try correct constructor
print("\nTesting with correct constructor...")
try:
    dhan = dhanhq(client_id)
    print("  1-arg constructor works")
except Exception as e:
    print(f"  1-arg failed: {e}")
    try:
        dhan = dhanhq(client_id, token)
        print("  2-arg constructor works")
    except Exception as e2:
        print(f"  2-arg failed: {e2}")

# Now test data API via dhan_feed directly
print("\nTesting via DhanFeed.get_quote('RELIANCE')...")
try:
    from data_feeds.dhan_feed import DhanFeed
    feed = DhanFeed()
    q = feed.get_quote("RELIANCE")
    if q:
        print(f"  SUCCESS: RELIANCE LTP = {q.ltp}")
    else:
        print("  None returned — feed returned no data")
except Exception as e:
    print(f"  Error: {e}")
    if "451" in str(e):
        print("  → 451 = ENTITLEMENT_MISSING")
    elif "401" in str(e):
        print("  → 401 = TOKEN EXPIRED")
