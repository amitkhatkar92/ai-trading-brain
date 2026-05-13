"""Debug raw Dhan API responses to fix options chain and history."""
import sys, json
sys.path.insert(0, '/app')

import os
from dhanhq import dhanhq
client_id = os.getenv("DHAN_CLIENT_ID", "")
token = os.getenv("DHAN_ACCESS_TOKEN", "")
dhan = dhanhq(client_id, token)

print("=== RAW API DEBUG ===\n")

# Test 1: historical_daily_data for NIFTY (security_id=13, IDX_I, INDEX)
print("[1] historical_daily_data — NIFTY")
try:
    r = dhan.historical_daily_data(
        security_id="13",
        exchange_segment="IDX_I",
        instrument_type="INDEX",
        from_date="2026-05-06",
        to_date="2026-05-11",
    )
    print(f"  Type: {type(r)}")
    if isinstance(r, dict):
        print(f"  Keys: {list(r.keys())}")
        print(f"  Sample: {str(r)[:300]}")
    else:
        print(f"  Value: {str(r)[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: historical_daily_data for RELIANCE (security_id=2885, NSE_EQ, EQUITY)
print("\n[2] historical_daily_data — RELIANCE")
try:
    r = dhan.historical_daily_data(
        security_id="2885",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
        from_date="2026-05-06",
        to_date="2026-05-11",
    )
    print(f"  Type: {type(r)}")
    if isinstance(r, dict):
        print(f"  Keys: {list(r.keys())}")
        print(f"  Sample: {str(r)[:300]}")
    else:
        print(f"  Value: {str(r)[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: option_chain for NIFTY
print("\n[3] option_chain — NIFTY (expiry 2026-05-15)")
try:
    r = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry="2026-05-15",
    )
    print(f"  Type: {type(r)}")
    if isinstance(r, dict):
        print(f"  Keys: {list(r.keys())}")
        # Print a snippet
        s = str(r)
        print(f"  Sample: {s[:500]}")
    else:
        print(f"  Value: {str(r)[:300]}")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 4: option_chain — nearest expiry (2026-05-14 Thursday)
print("\n[4] option_chain — NIFTY nearest expiry 2026-05-14")
try:
    r = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry="2026-05-14",
    )
    print(f"  Type: {type(r)}")
    if isinstance(r, dict):
        print(f"  Keys: {list(r.keys())}")
        print(f"  Sample: {str(r)[:500]}")
    else:
        print(f"  Value: {str(r)[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 5: Check available dhanhq methods
print("\n[5] Available dhanhq methods related to data")
methods = [m for m in dir(dhan) if not m.startswith('_') and any(x in m for x in ['data','chain','quote','history','intraday','market','ohlc','tick'])]
print(f"  {methods}")

print("\n=== DEBUG COMPLETE ===")
