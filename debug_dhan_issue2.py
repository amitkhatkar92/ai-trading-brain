"""
Dhan Issue 2 diagnostic — dumps raw ohlc_data response to understand
the actual response structure vs what the code expects.
"""
import sys, json
sys.path.insert(0, "/app")

# Load credentials
token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]

print(f"Client: {client_id}  Token: {token[:12]}...{token[-8:]}")
print()

# Build dhanhq context (new API requires dhan_context object)
from dhanhq import dhanhq, DhanContext
try:
    ctx = DhanContext(client_id, token)
    dhan = dhanhq(ctx)
    print("Connected via DhanContext ✓")
except Exception as e:
    print(f"DhanContext failed: {e}")
    # Try alternate
    try:
        dhan = dhanhq(client_id)
        print("Connected via client_id string")
    except Exception as e2:
        print(f"Both failed: {e2}")
        sys.exit(1)

# ── Test 1: ohlc_data for HDFCBANK (security_id=1333, NSE_EQ) ────────────
print("\n=== Test 1: ohlc_data HDFCBANK (sid=1333, NSE_EQ) ===")
try:
    resp = dhan.ohlc_data(securities={"NSE_EQ": [1333]})
    print(f"Type: {type(resp)}")
    if isinstance(resp, dict):
        print(f"Keys: {list(resp.keys())}")
        print(f"Status: {resp.get('status')}")
        data = resp.get("data", {})
        print(f"Data type: {type(data)}")
        if isinstance(data, dict):
            print(f"Data keys: {list(data.keys())}")
            for k, v in data.items():
                print(f"  [{k}]: {str(v)[:200]}")
        else:
            print(f"Data: {str(data)[:300]}")
    else:
        print(f"Raw: {str(resp)[:400]}")
except Exception as e:
    print(f"Error: {e}")

# ── Test 2: ohlc_data for RELIANCE (security_id=2885, NSE_EQ) ────────────
print("\n=== Test 2: ohlc_data RELIANCE (sid=2885, NSE_EQ) ===")
try:
    resp = dhan.ohlc_data(securities={"NSE_EQ": [2885]})
    print(json.dumps(resp, indent=2)[:600] if isinstance(resp, dict) else str(resp)[:400])
except Exception as e:
    print(f"Error: {e}")

# ── Test 3: Try intraday_daily_minute_charts ──────────────────────────────
print("\n=== Test 3: intraday_daily_minute_charts RELIANCE ===")
try:
    resp = dhan.intraday_daily_minute_charts(
        security_id="2885",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
    )
    if isinstance(resp, dict):
        print(f"Keys: {list(resp.keys())}")
        print(f"Status: {resp.get('status')}")
        data = resp.get("data")
        if isinstance(data, list):
            print(f"Rows: {len(data)}  first: {data[0] if data else 'empty'}")
        else:
            print(f"Data: {str(data)[:300]}")
    else:
        print(str(resp)[:400])
except Exception as e:
    print(f"Error: {e}")

# ── Test 4: market_quote (alternative endpoint) ────────────────────────────
print("\n=== Test 4: market_quote RELIANCE ===")
try:
    resp = dhan.market_quote(securities={"NSE_EQ": [2885]})
    if isinstance(resp, dict):
        print(f"Keys: {list(resp.keys())}")
        data = resp.get("data", {})
        print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        print(str(data)[:400])
    else:
        print(str(resp)[:400])
except Exception as e:
    print(f"Error: {e}")

# ── Test 5: Check all available methods ───────────────────────────────────
print("\n=== Available dhanhq methods (data-related) ===")
methods = [m for m in dir(dhan) if not m.startswith("_") and
           any(w in m for w in ["quote","ohlc","data","candle","chart","market","tick","depth"])]
print(", ".join(methods))
