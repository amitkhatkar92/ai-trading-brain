"""
Quick test: RELIANCE with quote_data vs ohlc_data to diagnose failure.
Also tests different common security IDs for RELIANCE.
"""
import sys
sys.path.insert(0, "/app")

token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]

from dhanhq import dhanhq, DhanContext
ctx  = DhanContext(client_id, token)
dhan = dhanhq(ctx)

# Test quote_data (different endpoint, may work differently)
print("=== quote_data RELIANCE (2885) ===")
try:
    resp = dhan.quote_data(securities={"NSE_EQ": [2885]})
    import json; print(json.dumps(resp, indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")

# Test ohlc_data for multiple known NSE blue-chips to find which fail
print("\n=== ohlc_data batch test ===")
tests = [
    ("HDFCBANK",  1333),
    ("RELIANCE",  2885),
    ("TCS",       11536),
    ("INFY",      10999),
    ("ICICIBANK", 4963),
    ("TATASTEEL", 3499),
    ("SBIN",      3045),
    ("WIPRO",     3787),
]
for name, sid in tests:
    try:
        resp = dhan.ohlc_data(securities={"NSE_EQ": [sid]})
        s = (resp or {}).get("status", "none")
        d = (resp or {}).get("data", "")
        if isinstance(d, dict):
            inner = d.get("data", d)
            seg   = inner.get("NSE_EQ", {})
            row   = seg.get(str(sid), {})
            ltp   = row.get("last_price", "?")
            print(f"  {name:12} sid={sid:6}  status={s}  ltp={ltp}")
        else:
            print(f"  {name:12} sid={sid:6}  status={s}  data={str(d)[:60]}")
    except Exception as e:
        print(f"  {name:12} sid={sid:6}  ERROR: {e}")

# Test quote_data for RELIANCE (alternative endpoint)
print("\n=== ticker_data RELIANCE (2885) ===")
try:
    resp = dhan.ticker_data(securities={"NSE_EQ": [2885]})
    import json; print(json.dumps(resp, indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")
