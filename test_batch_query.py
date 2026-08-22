"""Test batch query: pass multiple security_ids in a single quote_data call."""
import sys, json
sys.path.insert(0, "/app")
token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]
from dhanhq import dhanhq, DhanContext
dhan = dhanhq(DhanContext(client_id, token))

# All symbols and their security IDs from dhan_feed.py
SYMBOLS = {
    "HDFCBANK":  1333,  "RELIANCE": 2885,  "TCS":       11536,
    "INFY":      1594,  "SBIN":     3045,  "WIPRO":     3787,
    "ICICIBANK": 4963,  "TATASTEEL":3499,  "BANKBARODA":4668,
    "KOTAKBANK": 1922,  "AXISBANK": 5900,  "MARUTI":    10999,
}

# Build batch list
batch_sids = list(SYMBOLS.values())
print(f"Batch query: {len(batch_sids)} symbols in one call")
resp = dhan.quote_data(securities={"NSE_EQ": batch_sids})
print(f"Status: {resp.get('status')}")
data = resp.get("data", {})
if isinstance(data, dict):
    inner = data.get("data", data)
    if isinstance(inner, dict):
        seg_data = inner.get("NSE_EQ", {})
        print(f"Returned {len(seg_data)} symbols:")
        for sid_str, row in seg_data.items():
            # Find symbol name
            name = next((k for k, v in SYMBOLS.items() if str(v) == sid_str), sid_str)
            ltp  = row.get("last_price", "?")
            ohlc = row.get("ohlc", {})
            print(f"  {name:12} sid={sid_str:6}  ltp={ltp:8}  open={ohlc.get('open','?')}  high={ohlc.get('high','?')}")
    else:
        print(f"Inner data type: {type(inner)}: {str(inner)[:200]}")
else:
    print(f"Data: {str(data)[:200]}")

# Also test with just the 9 that were failing
print("\nBatch query for 9 failing symbols only:")
failing_sids = [1333, 11536, 1594, 3045, 4963, 3499, 1922, 5900, 10999]
resp2 = dhan.quote_data(securities={"NSE_EQ": failing_sids})
print(f"Status: {resp2.get('status')}")
data2 = resp2.get("data", {})
if isinstance(data2, dict):
    inner2 = data2.get("data", data2)
    if isinstance(inner2, dict):
        seg2 = inner2.get("NSE_EQ", {})
        print(f"Returned {len(seg2)} symbols: {list(seg2.keys())}")
        for sid_str, row in seg2.items():
            name = next((k for k, v in SYMBOLS.items() if str(v) == sid_str), sid_str)
            print(f"  {name:12} ltp={row.get('last_price','?')}  ohlc={row.get('ohlc','?')}")
    else:
        print(f"Data: {str(inner2)[:200]}")
