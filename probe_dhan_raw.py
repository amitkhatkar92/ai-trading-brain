"""
Probe: run inside container to see what Dhan API actually returns.
docker exec ai-trading-brain python /tmp/probe_dhan_raw.py
"""
import os, sys
sys.path.insert(0, '/app')

from dhanhq import dhanhq

token = os.environ.get('DHAN_ACCESS_TOKEN', '')
cid   = os.environ.get('DHAN_CLIENT_ID', '')

print(f"token_len: {len(token)}  cid_prefix: {cid[:6] if cid else 'MISSING'}")

if not token or not cid:
    print("ABORT: credentials missing")
    sys.exit(1)

dhan = dhanhq(cid, token)

# Test 1: LTP for HDFCBANK (securityId=1333, NSE_EQ)
print("\n--- Test 1: get_ltp_data NSE_EQ ---")
resp = dhan.get_ltp_data(securities={'NSE_EQ': [1333]})
print(f"  type: {type(resp).__name__}")
print(f"  repr: {repr(resp)[:600]}")

# Test 2: market_feed (v2 endpoint)
print("\n--- Test 2: market_feed NSE_EQ HDFCBANK ---")
try:
    resp2 = dhan.market_feed({'NSE_EQ': ['1333']})
    print(f"  type: {type(resp2).__name__}")
    print(f"  repr: {repr(resp2)[:600]}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

# Test 3: intraday_daily_minute_charts
print("\n--- Test 3: intraday_daily_minute_charts HDFCBANK ---")
try:
    resp3 = dhan.intraday_daily_minute_charts('1333', 'NSE', '1')
    print(f"  type: {type(resp3).__name__}")
    print(f"  repr: {repr(resp3)[:600]}")
except Exception as e:
    print(f"  EXCEPTION: {e}")
